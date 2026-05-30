import json

from modules.bedrock_client import invoke_bedrock


def clean_json_response(raw: str) -> str:
    raw = raw.strip()

    if raw.startswith("```json"):
        raw = raw.replace("```json", "", 1).strip()

    if raw.startswith("```"):
        raw = raw.replace("```", "", 1).strip()

    if raw.endswith("```"):
        raw = raw[:-3].strip()

    return raw


def safe_json_loads(raw: str, error_label: str):
    raw = clean_json_response(raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"{error_label} JSON 파싱 실패")
        print(f"error: {e}")
        print(f"raw tail: {raw[-500:]}")
        raise


def repair_json_array(raw: str, label: str, max_tokens: int = 4000):
    repair_prompt = f"""
아래 텍스트는 잘리거나 깨진 JSON 배열이다.

작업:
- 유효한 JSON 배열로 복구한다.
- 복구 불가능한 마지막 미완성 객체는 버린다.
- JSON 배열 외 설명 문장은 출력하지 않는다.
- 문자열 따옴표, 쉼표, 배열 닫힘을 올바르게 보정한다.

텍스트:
{raw}
"""

    repaired = invoke_bedrock(
        system_prompt="너는 JSON 복구기다. JSON 배열 외 설명은 절대 출력하지 않는다.",
        user_prompt=repair_prompt,
        max_tokens=max_tokens,
    ).strip()

    try:
        return safe_json_loads(repaired, f"{label} JSON 복구")
    except json.JSONDecodeError:
        print(f"{label} JSON 복구 실패. 해당 데이터는 건너뜁니다.")
        return []
