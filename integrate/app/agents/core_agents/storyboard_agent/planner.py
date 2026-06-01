import json
from typing import Dict, List

from app.core.agent_instruction import load_agent_instruction
from app.core.bedrock_client import invoke_bedrock
from app.core.json_utils import clean_json_response, repair_json_array, safe_json_loads
from app.core.pm_logger import log_info
from app.schemas.pm_artifacts import RequirementAtom, ScreenDisplayItem, ScreenPlanItem


BASE_SYSTEM_PROMPT = '너는 PM Agent의 화면기획서 생성기다.'


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


def generate_screen_items_for_domain(domain: str, atoms: List[RequirementAtom]) -> List[ScreenPlanItem]:
    prompt = f'''다음은 RAG로 검색한 "{domain}" 영역 관련 요구사항이다. 화면과 관련된 요구사항만 골라 화면기획 데이터를 생성하라.

요구사항:
{json.dumps(_compact_requirements(atoms), ensure_ascii=False, indent=2)}'''
    raw = invoke_bedrock(system_prompt=system_prompt(), user_prompt=prompt, max_tokens=5000).strip()
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
        if not item.screen_id or not item.screen_id.startswith('SCR-'):
            item.screen_id = f'SCR-{idx:03d}'
        if not item.screen_no or not item.screen_no.startswith('SCR-'):
            item.screen_no = item.screen_id
    return items


def generate_screen_plan_items_from_rag(domain_contexts: Dict[str, List[RequirementAtom]]) -> List[ScreenPlanItem]:
    all_items = []
    for idx, (domain, atoms) in enumerate(domain_contexts.items(), start=1):
        log_info(f'  - 화면기획 RAG domain {idx}/{len(domain_contexts)}: {domain}, 요구사항 {len(atoms)}건')
        all_items.extend(generate_screen_items_for_domain(domain, atoms))
    return normalize_screen_numbers(all_items)
