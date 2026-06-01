import json
from pathlib import Path
from typing import Any, Dict

from app.core.mapper_loader import resolve_path


DEFAULT_PROCESS_PATH = 'process.json'


def load_process(process_path: str = DEFAULT_PROCESS_PATH) -> Dict[str, Any]:
    """process.json을 읽어 Agent/산출물 실행 여부를 반환한다."""
    path = resolve_path(process_path)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


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
