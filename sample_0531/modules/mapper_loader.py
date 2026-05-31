import json
import unicodedata
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_MAPPER_PATH = 'template/output_mapper.json'


def resolve_path(path: str) -> str:
    """Resolve paths even when Korean filenames are stored as NFD on macOS ZIPs."""
    p = Path(path)
    if p.exists():
        return str(p)

    parent = p.parent if str(p.parent) != '' else Path('.')
    target = unicodedata.normalize('NFC', p.name)
    if parent.exists():
        for candidate in parent.iterdir():
            if unicodedata.normalize('NFC', candidate.name) == target:
                return str(candidate)
    raise FileNotFoundError(f'파일을 찾을 수 없습니다: {path}')


def load_mapper(mapper_path: str = DEFAULT_MAPPER_PATH) -> Dict[str, Any]:
    mapper_file = resolve_path(mapper_path)
    with open(mapper_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_context(project_name: str, author: str) -> Dict[str, str]:
    return {
        'project_name': project_name or '',
        'author': author or '',
        'today': datetime.today().strftime('%Y-%m-%d'),
    }


def get_nested(config: Dict[str, Any], *keys: str, default: Optional[Any] = None) -> Any:
    current: Any = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def get_value(source: Any, field_expr: str, context: Optional[Dict[str, str]] = None, row_number: Optional[int] = None) -> Any:
    """
    mapper field expression examples:
      - category
      - note|description         : first non-empty field
      - screen_id|screen_no      : first non-empty field
      - row_number               : generated row number
      - project_name / author    : context value
      - ''                       : fixed blank
    """
    if field_expr is None:
        return ''
    if not isinstance(field_expr, str):
        return field_expr
    if field_expr == '':
        return ''
    if field_expr == 'row_number':
        return row_number or ''
    if context and field_expr in context:
        return context.get(field_expr, '')

    for field in field_expr.split('|'):
        field = field.strip()
        if not field:
            continue
        if context and field in context:
            value = context.get(field, '')
        elif isinstance(source, dict):
            value = source.get(field, '')
        else:
            value = getattr(source, field, '')
        if value not in (None, ''):
            return value
    return ''


def build_placeholder_values(placeholders: Dict[str, str], source: Any, context: Dict[str, str]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for placeholder, field_expr in placeholders.items():
        value = get_value(source, field_expr, context=context)
        values[placeholder] = '' if value is None else str(value)
    return values


def deepcopy_mapper_section(mapper: Dict[str, Any], section_name: str) -> Dict[str, Any]:
    return deepcopy(mapper.get(section_name, {}))
