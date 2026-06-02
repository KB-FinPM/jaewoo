import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from app.schemas.artifact import RequirementAtom


@dataclass
class DocumentVersionInfo:
    file_path: str
    file_name: str
    doc_name: str
    version: str
    doc_key: str
    file_hash: str
    file_size: int
    created_at: str
    modified_at: str


def find_latest_versioned_docx(
    input_dir: str = 'input',
    base_name: str = '구축요건정의서',
) -> str:
    """
    input_dir 아래에서 base_name.v.#.docx 형식의 파일 중 숫자 버전이 가장 큰 파일 경로를 반환한다.

    예) 구축요건정의서.v.1.docx, 구축요건정의서.v.2.docx 가 있으면 v.2 파일을 선택한다.
    """
    directory = Path(input_dir)
    if not directory.exists():
        raise FileNotFoundError(f'입력 디렉토리가 없습니다: {input_dir}')

    normalized_base_name = unicodedata.normalize('NFC', base_name)
    pattern = re.compile(rf'^{re.escape(normalized_base_name)}\.v\.(\d+)\.docx$', re.IGNORECASE)

    candidates = []
    for file_path in directory.glob('*.docx'):
        normalized_file_name = unicodedata.normalize('NFC', file_path.name)
        match = pattern.match(normalized_file_name)
        if not match:
            continue
        candidates.append((int(match.group(1)), file_path))

    if not candidates:
        raise FileNotFoundError(
            f'{input_dir}에서 {base_name}.v.#.docx 형식의 파일을 찾을 수 없습니다.'
        )

    candidates.sort(key=lambda item: item[0], reverse=True)
    return str(candidates[0][1])


def parse_version_from_filename(file_name: str):
    normalized_file_name = unicodedata.normalize('NFC', file_name)
    match = re.match(r'(.+)\.v\.([^.]+)\.docx$', normalized_file_name)
    if match:
        return match.group(1), match.group(2)
    return Path(normalized_file_name).stem, 'unknown'


def compute_file_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _format_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).isoformat(timespec='seconds')


def build_doc_version_info(file_path: str) -> DocumentVersionInfo:
    path = Path(file_path)
    stat = path.stat()
    file_name = unicodedata.normalize('NFC', path.name)
    doc_name, version = parse_version_from_filename(file_name)
    doc_key = f'{doc_name}.v.{version}'
    return DocumentVersionInfo(
        file_path=str(path),
        file_name=file_name,
        doc_name=doc_name,
        version=version,
        doc_key=doc_key,
        file_hash=compute_file_hash(str(path)),
        file_size=stat.st_size,
        # Linux/macOS의 ctime은 순수 생성일이 아니라 metadata 변경 시각일 수 있다.
        # 사용자가 요청한 생성날짜 비교 목적에 맞춰 created_at 이름으로 저장하되,
        # 실제 변경 감지는 modified_at, file_size, file_hash까지 함께 사용한다.
        created_at=_format_timestamp(stat.st_ctime),
        modified_at=_format_timestamp(stat.st_mtime),
    )


def safe_key(doc_key: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', doc_key)


def cache_dir(output_dir: str) -> Path:
    path = Path(output_dir) / 'cache'
    path.mkdir(parents=True, exist_ok=True)
    return path


def metadata_path(output_dir: str) -> Path:
    return cache_dir(output_dir) / 'doc_versions.json'


def atoms_cache_path(output_dir: str, doc_key: str) -> Path:
    return cache_dir(output_dir) / f'atoms_{safe_key(doc_key)}.json'


def load_metadata(output_dir: str) -> dict:
    path = metadata_path(output_dir)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def save_metadata(output_dir: str, metadata: dict):
    metadata_path(output_dir).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def document_identity(doc_info: DocumentVersionInfo) -> dict:
    return {
        'file_name': doc_info.file_name,
        'doc_name': doc_info.doc_name,
        'version': doc_info.version,
        'doc_key': doc_info.doc_key,
        'file_size': doc_info.file_size,
        'created_at': doc_info.created_at,
        'modified_at': doc_info.modified_at,
        'file_hash': doc_info.file_hash,
    }


def is_same_document_file(saved_info: dict, doc_info: DocumentVersionInfo) -> bool:
    """파일명이 같아도 크기/시각/hash 중 하나라도 다르면 다른 파일로 판단한다."""
    if not saved_info:
        return False

    current = document_identity(doc_info)
    compare_keys = [
        'file_name',
        'doc_key',
        'file_size',
        'created_at',
        'modified_at',
        'file_hash',
    ]
    return all(saved_info.get(key) == current.get(key) for key in compare_keys)


def is_version_analyzed(output_dir: str, doc_info: DocumentVersionInfo) -> bool:
    metadata = load_metadata(output_dir)
    saved_info = metadata.get(doc_info.doc_key)
    return is_same_document_file(saved_info, doc_info)


def get_saved_document_info(output_dir: str, doc_info: DocumentVersionInfo) -> dict:
    return load_metadata(output_dir).get(doc_info.doc_key, {})


def save_atoms_cache(output_dir: str, doc_info: DocumentVersionInfo, atoms: List[RequirementAtom]):
    atoms_cache_path(output_dir, doc_info.doc_key).write_text(
        json.dumps([atom.model_dump() for atom in atoms], ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    metadata = load_metadata(output_dir)
    metadata[doc_info.doc_key] = {
        **document_identity(doc_info),
        'analyzed_at': datetime.now().isoformat(timespec='seconds'),
        'atom_count': len(atoms),
    }
    save_metadata(output_dir, metadata)


def load_atoms_cache(output_dir: str, doc_info: DocumentVersionInfo) -> List[RequirementAtom]:
    path = atoms_cache_path(output_dir, doc_info.doc_key)
    if not path.exists():
        return []
    return [RequirementAtom(**item) for item in json.loads(path.read_text(encoding='utf-8'))]
