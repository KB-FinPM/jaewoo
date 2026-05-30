import json
from typing import List, Dict

from modules.schemas import RequirementAtom, ScreenPlanItem, ScreenDisplayItem
from modules.bedrock_client import invoke_bedrock
from modules.json_utils import clean_json_response, safe_json_loads, repair_json_array
from modules.logger_utils import log_info

SCREEN_SYSTEM_PROMPT = '''
너는 PM Agent의 화면기획서 생성기다.
입력된 요구사항 목록을 기반으로 화면기획서 슬라이드에 들어갈 화면 계획 데이터를 생성하라.
반드시 JSON 배열만 반환한다.
각 항목 schema:
[{"requirement_id":"REQ-0001","screen_no":"SCR-001","screen_name":"화면명","screen_summary":"화면 기획 요약","display_items":[{"item_name":"표시항목명","description":"화면에 표시해야 할 내용 설명"}]}]
규칙:
- 문서에 없는 화면명을 과도하게 추측하지 않는다.
- 요구사항 하나가 명확한 화면을 의미하면 하나의 화면으로 만든다.
- API, 배치, 인프라처럼 화면과 직접 관련이 낮은 요구사항은 제외한다.
- 각 화면에는 display_items를 3~8개 작성한다.
- JSON 외 설명은 출력하지 않는다.
'''


def _compact_requirements(atoms: List[RequirementAtom]):
    return [{'requirement_id': a.requirement_id, 'category': a.category, 'requirement_name': a.requirement_name, 'requirement_type': a.requirement_type, 'domain': a.domain, 'feature': a.feature, 'description': a.description} for a in atoms]


def generate_screen_items_for_domain(domain: str, atoms: List[RequirementAtom]) -> List[ScreenPlanItem]:
    prompt = f'''다음은 RAG로 검색한 "{domain}" 영역 관련 요구사항이다. 화면과 관련된 요구사항만 골라 화면기획 데이터를 생성하라.

요구사항:
{json.dumps(_compact_requirements(atoms), ensure_ascii=False, indent=2)}'''
    raw = invoke_bedrock(system_prompt=SCREEN_SYSTEM_PROMPT, user_prompt=prompt, max_tokens=5000).strip()
    raw = clean_json_response(raw)
    try:
        items = safe_json_loads(raw, f'화면기획-{domain}')
    except json.JSONDecodeError:
        items = repair_json_array(raw, f'화면기획-{domain}', max_tokens=4000)
    result = []
    for item in items:
        try:
            item['display_items'] = [ScreenDisplayItem(**x) for x in item.get('display_items', [])]
            result.append(ScreenPlanItem(**item))
        except Exception as e:
            log_info(f'화면기획 item 변환 실패, skip: {e}')
    return result


def normalize_screen_numbers(items: List[ScreenPlanItem]) -> List[ScreenPlanItem]:
    for idx, item in enumerate(items, start=1):
        if not item.screen_no or not item.screen_no.startswith('SCR-'):
            item.screen_no = f'SCR-{idx:03d}'
    return items


def generate_screen_plan_items_from_rag(domain_contexts: Dict[str, List[RequirementAtom]]) -> List[ScreenPlanItem]:
    all_items = []
    for idx, (domain, atoms) in enumerate(domain_contexts.items(), start=1):
        log_info(f'  - 화면기획 RAG domain {idx}/{len(domain_contexts)}: {domain}, 요구사항 {len(atoms)}건')
        all_items.extend(generate_screen_items_for_domain(domain, atoms))
    return normalize_screen_numbers(all_items)
