import re
from typing import Any


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    # Korean/English mixed text에서 대략 1 token ~= 2.2 chars 정도로 보수 계산
    return max(1, int(len(str(text)) / 2.2))


def limit_text_for_output(text: Any, max_token: int = 0, flexible_tokens: int = 150) -> str:
    """최종 산출물 텍스트만 제한한다. JSON/LLM 원문에는 사용하지 않는다."""
    if text is None:
        return ''
    value = str(text)
    if not max_token or max_token <= 0:
        return value
    if estimate_tokens(value) <= max_token + flexible_tokens:
        return value

    max_chars = int(max_token * 2.2)
    candidate = value[:max_chars]

    # 문장 또는 공백 경계에서 자른다. 단어 중간 절단을 최대한 피한다.
    boundaries = [candidate.rfind(x) for x in ['. ', '? ', '! ', '\n', '。', '다.', '요.', ' ', ',']]
    boundary = max(boundaries)
    if boundary > max_chars * 0.65:
        candidate = candidate[:boundary + 1]
    return candidate.rstrip() + '…'
