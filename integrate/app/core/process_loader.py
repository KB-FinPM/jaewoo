import json
from pathlib import Path
from typing import Any, Dict

from app.core.token_limiter import DEFAULT_MAX_TOKEN, set_max_token
from app.core.mapper_loader import resolve_path


DEFAULT_PROCESS_PATH = 'process.json'


def load_process(process_path: str = DEFAULT_PROCESS_PATH) -> Dict[str, Any]:
    """process.json을 읽어 Agent/산출물 실행 여부와 max_token을 반환한다."""
    path = resolve_path(process_path)
    with open(path, 'r', encoding='utf-8') as f:
        process = json.load(f)
    configure_token_limit(process)
    return process


def get_process_max_token(process: Dict[str, Any]) -> int:
    """process.json의 max_token 값을 정수로 반환한다."""
    try:
        return int(process.get('max_token', DEFAULT_MAX_TOKEN))
    except (TypeError, ValueError):
        return DEFAULT_MAX_TOKEN


def configure_token_limit(process: Dict[str, Any]) -> int:
    """process.json max_token을 공통 토큰 제한기에 반영한다."""
    return set_max_token(get_process_max_token(process))


def is_enabled(config: Dict[str, Any], *keys: str, default: bool = False) -> bool:
    current: Any = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    if isinstance(current, dict):
        return bool(current.get('enabled', default))
    return bool(current)


def enabled_outputs(process: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    outputs = process.get('output_agents', {})
    return {key: value for key, value in outputs.items() if bool(value.get('enabled', False))}
