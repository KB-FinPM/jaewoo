import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from modules.schemas import RequirementAtom, WBSItem
from modules.bedrock_client import invoke_bedrock
from modules.json_utils import clean_json_response, safe_json_loads, repair_json_array
from modules.logger_utils import log_info
from modules.agent_instruction import load_agent_instruction
from modules.project_profile import get_phase_names, get_profile_instruction
from modules.s3_client import ensure_local_path

WBS_SYSTEM_PROMPT = '''
너는 PM Agent의 WBS 생성기다.
입력된 요구사항 목록을 기반으로 WBS를 생성하라.
반드시 JSON 배열만 반환한다.
각 항목 schema:
[{"level":"1 | 1.1 | 1.1.1","wbs_name":"WBS명","start_date":"","end_date":"","assignee":"","deliverable":"산출물"}]
규칙:
- 시작예정일, 종료예정일, 작업자는 문서에 없으면 빈 문자열로 둔다.
- 요구사항을 개발/구축 작업 단위로 분해한다.
- 분석, 설계, 개발/구축, 스테이징, 운영 관점으로 구성한다.
- 한 번의 응답에서 최대 20개 WBS 항목만 생성한다.
- JSON 외의 설명 문장은 절대 출력하지 않는다.
'''


def _load_json(path: str, default: dict) -> dict:
    try:
        resolved = ensure_local_path(path)
        p = Path(resolved)
    except Exception:
        p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding='utf-8'))


def _compact_requirements(atoms: List[RequirementAtom]):
    return [
        {
            'requirement_id': a.requirement_id,
            'category': a.category,
            'biz_requirement_id': a.biz_requirement_id,
            'biz_requirement_name': a.biz_requirement_name,
            'requirement_name': a.requirement_name,
            'requirement_type': a.requirement_type,
            'domain': a.domain,
            'feature': a.feature,
            'description': a.description,
        }
        for a in atoms
    ]


def _biz_name(atom: RequirementAtom) -> str:
    return (atom.biz_requirement_name or atom.domain or atom.category or '공통').strip() or '공통'


def _group_atoms(atoms: Iterable[RequirementAtom]) -> Dict[str, List[RequirementAtom]]:
    grouped: Dict[str, List[RequirementAtom]] = {}
    for atom in atoms:
        grouped.setdefault(_biz_name(atom), []).append(atom)
    return grouped


def _find_deliverable(name: str, phase: str, deliverable_mapper: dict) -> str:
    text = f'{name} {phase}'
    for rule in deliverable_mapper.get('keyword_rules', []):
        if any(str(keyword).lower() in text.lower() for keyword in rule.get('keywords', [])):
            deliverables = rule.get('deliverables') or []
            return ', '.join(deliverables[:2])
    default_by_phase = deliverable_mapper.get('default_by_phase', {})
    for key, value in default_by_phase.items():
        if key in phase:
            return value
    return ''


def _hierarchy_level(item_id: str) -> int:
    return 0 if str(item_id or '').strip() == '0' else len(str(item_id or '').split('.'))


def _render_common_items(project_name: str, template_path: str = 'template/wbs_template.json') -> List[WBSItem]:
    template = _load_json(template_path, {'common_items': []})
    items: List[WBSItem] = []
    path = [0]
    previous_depth = 0

    for raw in template.get('common_items', []):
        depth = int(str(raw.get('level', '0')).strip())
        if depth == 0:
            path = [0]
            item_id = '0'
        elif depth > previous_depth:
            path = path[:depth] + [1]
            item_id = '.'.join(str(part) for part in path[1:])
        else:
            path = path[:depth + 1]
            path[-1] += 1
            item_id = '.'.join(str(part) for part in path[1:])

        name = str(raw.get('wbs_name', '')).replace('{project_name}', project_name or '프로젝트명')
        deliverable = str(raw.get('deliverable', '')).replace('{project_name}', project_name or '프로젝트명')
        items.append(WBSItem(id=item_id, level=str(_hierarchy_level(item_id)), wbs_name=name, deliverable=deliverable))
        previous_depth = depth

    return items


def generate_structured_wbs_items(
    atoms: List[RequirementAtom],
    project_name: str,
    project_type: str = 'hybrid',
    wbs_template_path: str = 'template/wbs_template.json',
    deliverable_mapper_path: str = 'template/deliverable_mapper.json',
) -> List[WBSItem]:
    """참고용 WBS 규칙 기반 생성. No 1~36 공통 + No 37부터 Biz요건명 기준."""
    items = _render_common_items(project_name=project_name, template_path=wbs_template_path)
    deliverable_mapper = _load_json(deliverable_mapper_path, {})
    phases = get_phase_names(project_type)

    grouped = _group_atoms(atoms)
    top_index = 1
    for biz_name, biz_atoms in grouped.items():
        if not biz_name or biz_name == '공통' and len(grouped) > 1:
            continue
        items.append(WBSItem(id=str(top_index), level=str(_hierarchy_level(str(top_index))), wbs_name=biz_name, deliverable=''))
        for phase_idx, phase in enumerate(phases, start=1):
            deliverable = _find_deliverable(biz_name, phase, deliverable_mapper)
            phase_id = f'{top_index}.{phase_idx}'
            items.append(WBSItem(id=phase_id, level=str(_hierarchy_level(phase_id)), wbs_name=f'{biz_name} {phase}', deliverable=deliverable))
            # 대표 요구사항이 명확하면 하위 작업을 1~3개만 생성한다.
            for req_idx, atom in enumerate(biz_atoms[:3], start=1):
                req_name = atom.requirement_name or atom.feature or atom.description[:30]
                if not req_name:
                    continue
                req_id = f'{top_index}.{phase_idx}.{req_idx}'
                items.append(WBSItem(id=req_id, level=str(_hierarchy_level(req_id)), wbs_name=f'{req_name} {phase}', deliverable=deliverable))
        top_index += 1
    return items


def generate_wbs_items_for_domain(
    domain: str,
    atoms: List[RequirementAtom],
    project_type: str = 'hybrid',
    instruction_md: str = '',
) -> List[WBSItem]:
    agent_instruction = load_agent_instruction(instruction_md)
    system_prompt = f"""{WBS_SYSTEM_PROMPT}\n\n{get_profile_instruction(project_type)}\n\n{agent_instruction}""".strip()
    prompt = f'''다음은 RAG로 검색한 "{domain}" 영역 관련 요구사항이다. 이 요구사항만 근거로 WBS를 생성하라.

요구사항:
{json.dumps(_compact_requirements(atoms), ensure_ascii=False, indent=2)}'''
    raw = invoke_bedrock(system_prompt=system_prompt, user_prompt=prompt, max_tokens=5000).strip()
    raw = clean_json_response(raw)
    try:
        items = safe_json_loads(raw, f'WBS-{domain}')
    except json.JSONDecodeError:
        items = repair_json_array(raw, f'WBS-{domain}', max_tokens=4000)
    result = []
    for item in items:
        try:
            result.append(WBSItem(**item))
        except Exception as e:
            log_info(f'WBS item 변환 실패, skip: {e}')
    return result


def normalize_wbs_levels(items: List[WBSItem]) -> List[WBSItem]:
    normalized = []
    top_no = 0
    child_count_map = {}
    for item in items:
        raw_level = str(item.level).strip()
        if not raw_level or '.' not in raw_level:
            top_no += 1
            child_count_map[str(top_no)] = 0
            item.level = str(top_no)
        else:
            if top_no == 0:
                top_no = 1
                child_count_map[str(top_no)] = 0
            child_count_map[str(top_no)] += 1
            item.level = f'{top_no}.{child_count_map[str(top_no)]}'
        normalized.append(item)
    return normalized


def generate_wbs_items_from_rag(
    domain_contexts: Dict[str, List[RequirementAtom]],
    project_type: str = 'hybrid',
    instruction_md: str = '',
) -> List[WBSItem]:
    all_items = []
    for idx, (domain, atoms) in enumerate(domain_contexts.items(), start=1):
        log_info(f'  - WBS RAG domain {idx}/{len(domain_contexts)}: {domain}, 요구사항 {len(atoms)}건')
        all_items.extend(generate_wbs_items_for_domain(domain, atoms, project_type=project_type, instruction_md=instruction_md))
    return normalize_wbs_levels(all_items)
