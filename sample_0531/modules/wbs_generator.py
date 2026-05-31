import json
from typing import List, Dict

from modules.schemas import RequirementAtom, WBSItem
from modules.bedrock_client import invoke_bedrock
from modules.json_utils import clean_json_response, safe_json_loads, repair_json_array
from modules.logger_utils import log_info

WBS_SYSTEM_PROMPT = '''
너는 PM Agent의 WBS 생성기다.
입력된 요구사항 목록을 기반으로 WBS를 생성하라.
반드시 JSON 배열만 반환한다.
각 항목 schema:
[{"level":"1 | 1.1 | 1.1.1","wbs_name":"WBS명","start_date":"","end_date":"","assignee":"","deliverable":"산출물"}]
규칙:
- 시작예정일, 종료예정일, 작업자는 문서에 없으면 빈 문자열로 둔다.
- 요구사항을 개발 작업 단위로 분해한다.
- 분석, 설계, 개발, 테스트, 산출물 작성 관점으로 구성한다.
- 한 번의 응답에서 최대 20개 WBS 항목만 생성한다.
- JSON 외의 설명 문장은 절대 출력하지 않는다.
'''


def _compact_requirements(atoms: List[RequirementAtom]):
    return [{'requirement_id': a.requirement_id, 'category': a.category, 'requirement_name': a.requirement_name, 'requirement_type': a.requirement_type, 'domain': a.domain, 'feature': a.feature, 'description': a.description} for a in atoms]


def generate_wbs_items_for_domain(domain: str, atoms: List[RequirementAtom]) -> List[WBSItem]:
    prompt = f'''다음은 RAG로 검색한 "{domain}" 영역 관련 요구사항이다. 이 요구사항만 근거로 WBS를 생성하라.

요구사항:
{json.dumps(_compact_requirements(atoms), ensure_ascii=False, indent=2)}'''
    raw = invoke_bedrock(system_prompt=WBS_SYSTEM_PROMPT, user_prompt=prompt, max_tokens=5000).strip()
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
