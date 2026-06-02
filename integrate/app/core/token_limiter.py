"""Token limiting helpers for PM-Agent LLM calls.

This module limits only final artifact output text using the max_token value
configured in process.json. JSON LLM responses are not truncated because cutting
JSON in the middle can cause parsing errors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple

DEFAULT_MAX_TOKEN = 1000
SOFT_MARGIN_TOKEN = 150
_MIN_AGENT_MD_TOKENS = 250

_current_max_token = DEFAULT_MAX_TOKEN

_TOKEN_PATTERN = re.compile(r"[가-힣]|[A-Za-z0-9_]+|[^\s]", re.UNICODE)
_SENTENCE_END_PATTERN = re.compile(r"[.!?。！？]\s|[다요음임함됨됨니다]\.\s|\n{2,}|\n[-*0-9#]")


@dataclass(frozen=True)
class TokenLimitResult:
    text: str
    original_tokens: int
    limited_tokens: int
    truncated: bool


def set_max_token(max_token: int | str | None) -> int:
    """Set the process-wide max token value."""
    global _current_max_token
    try:
        parsed = int(max_token) if max_token is not None else DEFAULT_MAX_TOKEN
    except (TypeError, ValueError):
        parsed = DEFAULT_MAX_TOKEN
    _current_max_token = max(1, parsed)
    return _current_max_token


def get_max_token(default: int = DEFAULT_MAX_TOKEN) -> int:
    return int(_current_max_token or default)


def estimate_tokens(text: str | None) -> int:
    """Approximate token count without external tokenizer dependencies."""
    if not text:
        return 0
    return len(_TOKEN_PATTERN.findall(str(text)))


def limit_text(
    text: str | None,
    max_tokens: int | None = None,
    *,
    soft_margin: int = SOFT_MARGIN_TOKEN,
    suffix: str = "\n\n...[max_token 제한으로 이하 내용 생략]",
) -> TokenLimitResult:
    """Limit text while avoiding mid-word or mid-sentence cuts.

    If text is only slightly over the configured limit, up to soft_margin tokens
    are allowed so a nearby sentence boundary can be preserved.
    """
    value = "" if text is None else str(text)
    limit = int(max_tokens or get_max_token())
    original = estimate_tokens(value)
    if original <= limit + soft_margin:
        return TokenLimitResult(value, original, original, False)

    matches = list(_TOKEN_PATTERN.finditer(value))
    if len(matches) <= limit + soft_margin:
        return TokenLimitResult(value, original, original, False)

    target_idx = min(limit, len(matches)) - 1
    min_idx = max(0, limit - soft_margin) - 1
    max_idx = min(len(matches) - 1, limit + soft_margin - 1)

    # Prefer a sentence/line boundary near max_token, scanning backward first so
    # the result stays close to the requested budget and does not break context.
    candidate_end = matches[target_idx].end()
    search_start = matches[min_idx].end() if min_idx >= 0 else 0
    search_end = matches[max_idx].end()
    window = value[search_start:search_end]
    sentence_ends = [m.end() for m in _SENTENCE_END_PATTERN.finditer(window)]
    if sentence_ends:
        candidate_end = search_start + sentence_ends[-1]
    else:
        # Fall back to whitespace boundary before the target token.
        raw_end = matches[target_idx].end()
        ws = value.rfind(" ", 0, raw_end)
        nl = value.rfind("\n", 0, raw_end)
        boundary = max(ws, nl)
        if boundary > 0:
            candidate_end = boundary

    limited = value[:candidate_end].rstrip() + suffix
    limited_tokens = estimate_tokens(limited)
    return TokenLimitResult(limited, original, limited_tokens, True)


def limit_llm_messages(system_prompt: str, user_prompt: str, max_tokens: int | None = None) -> Tuple[str, str]:
    """Limit system and user prompts under one shared max_token budget."""
    limit = int(max_tokens or get_max_token())
    system_tokens = estimate_tokens(system_prompt)

    if system_tokens >= limit:
        system_limited = limit_text(system_prompt, max(_MIN_AGENT_MD_TOKENS, limit // 3), soft_margin=50).text
        user_budget = max(1, limit - estimate_tokens(system_limited))
        return system_limited, limit_text(user_prompt, user_budget, soft_margin=50).text

    user_budget = max(1, limit - system_tokens)
    return system_prompt, limit_text(user_prompt, user_budget).text


def limit_llm_output(output_text: str | None, max_tokens: int | None = None) -> str:
    """Limit model output before downstream parsing/logging."""
    return limit_text(output_text, max_tokens).text



def limit_output_text(output_text: str | None, max_tokens: int | None = None) -> str:
    """Limit text only at the final artifact output-writing stage."""
    return limit_text(output_text, max_tokens).text
