import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from modules.schemas import RequirementAtom


@dataclass
class DocumentVersionInfo:
    file_path: str
    file_name: str
    doc_name: str
    version: str
    doc_key: str
    file_hash: str


def parse_version_from_filename(file_name: str):
    match = re.match(r'(.+)\.v\.([^.]+)\.docx$', file_name)
    if match:
        return match.group(1), match.group(2)
    return Path(file_name).stem, 'unknown'


def compute_file_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def build_doc_version_info(file_path: str) -> DocumentVersionInfo:
    file_name = Path(file_path).name
    doc_name, version = parse_version_from_filename(file_name)
    doc_key = f'{doc_name}.v.{version}'
    return DocumentVersionInfo(file_path=file_path, file_name=file_name, doc_name=doc_name, version=version, doc_key=doc_key, file_hash=compute_file_hash(file_path))


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
    metadata_path(output_dir).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')


def is_version_analyzed(output_dir: str, doc_info: DocumentVersionInfo) -> bool:
    return doc_info.doc_key in load_metadata(output_dir)


def save_atoms_cache(output_dir: str, doc_info: DocumentVersionInfo, atoms: List[RequirementAtom]):
    atoms_cache_path(output_dir, doc_info.doc_key).write_text(json.dumps([atom.model_dump() for atom in atoms], ensure_ascii=False, indent=2), encoding='utf-8')
    metadata = load_metadata(output_dir)
    metadata[doc_info.doc_key] = {
        'file_name': doc_info.file_name,
        'doc_name': doc_info.doc_name,
        'version': doc_info.version,
        'doc_key': doc_info.doc_key,
        'file_hash': doc_info.file_hash,
        'analyzed_at': datetime.now().isoformat(timespec='seconds'),
        'atom_count': len(atoms),
    }
    save_metadata(output_dir, metadata)


def load_atoms_cache(output_dir: str, doc_info: DocumentVersionInfo) -> List[RequirementAtom]:
    path = atoms_cache_path(output_dir, doc_info.doc_key)
    if not path.exists():
        return []
    return [RequirementAtom(**item) for item in json.loads(path.read_text(encoding='utf-8'))]
