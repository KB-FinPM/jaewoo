import json
from typing import Dict, List

from app.core.agent_instruction import load_agent_instruction
from app.core.bedrock_client import invoke_bedrock
from app.core.json_utils import clean_json_response, repair_json_array, safe_json_loads
from app.core.logger import log_info
from app.schemas.artifact import RequirementAtom, WBSItem


BASE_SYSTEM_PROMPT = '너는 PM Agent의 WBS 생성기다.'


def system_prompt() -> str:
    guide = load_agent_instruction(__file__)
    return f'{BASE_SYSTEM_PROMPT}\n\n{guide}'.strip()


def _compact_requirements(atoms: List[RequirementAtom]):
    return [
        {
            'requirement_id': a.requirement_id,
            'category': a.category,
            'requirement_name': a.requirement_name,
            'requirement_type': a.requirement_type,
            'domain': a.domain,
            'feature': a.feature,
            'description': a.description,
        }
        for a in atoms
    ]


def generate_wbs_items_for_domain(domain: str, atoms: List[RequirementAtom]) -> List[WBSItem]:
    prompt = f'''다음은 RAG로 검색한 "{domain}" 영역 관련 요구사항이다. 이 요구사항만 근거로 WBS를 생성하라.

요구사항:
{json.dumps(_compact_requirements(atoms), ensure_ascii=False, indent=2)}'''
    raw = invoke_bedrock(system_prompt=system_prompt(), user_prompt=prompt, max_tokens=5000).strip()
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


def generate_wbs_items_from_rag(domain_contexts: Dict[str, List[RequirementAtom]]) -> List[WBSItem]:
    all_items = []
    for idx, (domain, atoms) in enumerate(domain_contexts.items(), start=1):
        log_info(f'  - WBS RAG domain {idx}/{len(domain_contexts)}: {domain}, 요구사항 {len(atoms)}건')
        all_items.extend(generate_wbs_items_for_domain(domain, atoms))
    return normalize_wbs_levels(all_items)
