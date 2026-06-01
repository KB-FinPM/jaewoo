import re
from pathlib import Path
from typing import Dict, Any


def safe_project_name(project_name: str, space_replacement: str = '_') -> str:
    """파일명에 사용할 수 있는 안전한 프로젝트명으로 변환한다."""
    name = (project_name or '프로젝트명').strip()
    name = re.sub(r'\s+', space_replacement, name)
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    return name or '프로젝트명'


def next_versioned_output_path(output_dir: str, project_name: str, document_key: str, mapper: Dict[str, Any], fallback_extension: str = '') -> str:
    """mapper의 output_files 설정을 기준으로 산출물 파일명을 만들고 기존 파일이 있으면 minor version을 증가한다."""
    output_mapper = mapper.get('output_files', {})
    doc_mapper = output_mapper.get('documents', {}).get(document_key, {})
    document_name = doc_mapper.get('document_name', document_key)
    extension = doc_mapper.get('extension', fallback_extension)
    initial_major = int(output_mapper.get('initial_major', 0))
    initial_minor = int(output_mapper.get('initial_minor', 1))
    space_replacement = output_mapper.get('space_replacement', '_')

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = safe_project_name(project_name, space_replacement=space_replacement)
    pattern = re.compile(rf'^{re.escape(safe_name)}_{re.escape(document_name)}_v\.(\d+)\.(\d+){re.escape(extension)}$')

    max_major = None
    max_minor = None
    for file_path in out_dir.glob(f'{safe_name}_{document_name}_v.*{extension}'):
        match = pattern.match(file_path.name)
        if not match:
            continue
        major = int(match.group(1))
        minor = int(match.group(2))
        if max_major is None or (major, minor) > (max_major, max_minor):
            max_major, max_minor = major, minor

    if max_major is None:
        major, minor = initial_major, initial_minor
    else:
        major, minor = max_major, max_minor + 1

    return str(out_dir / f'{safe_name}_{document_name}_v.{major}.{minor}{extension}')
