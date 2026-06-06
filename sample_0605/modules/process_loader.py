import json
from pathlib import Path
from typing import Any, Dict

from modules.s3_client import ensure_local_path

DEFAULT_PROCESS_PATH = 'process.json'


def load_process_config(process_path: str = DEFAULT_PROCESS_PATH) -> Dict[str, Any]:
    path = Path(process_path)
    if not path.exists():
        try:
            path = Path(ensure_local_path(process_path))
        except Exception:
            path = Path(process_path)
    if not path.exists():
        return {
            'version': '1.0',
            'description': 'default process',
            'max_token': 1000,
            'project_type': 'auto',
            'limit_per_domain': 25,
            'steps': [
                {'id': 'requirement_spec', 'enabled': True},
                {'id': 'wbs', 'enabled': True},
                {'id': 'screen_plan', 'enabled': True},
            ],
        }
    return json.loads(path.read_text(encoding='utf-8'))


def is_step_enabled(process_config: Dict[str, Any], step_id: str, default: bool = True) -> bool:
    for step in process_config.get('steps', []):
        if step.get('id') == step_id:
            return bool(step.get('enabled', default))
    return default


def get_step(process_config: Dict[str, Any], step_id: str) -> Dict[str, Any]:
    for step in process_config.get('steps', []):
        if step.get('id') == step_id:
            return step
    return {}
