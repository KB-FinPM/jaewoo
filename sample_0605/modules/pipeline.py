import os
import re
import tempfile
from pathlib import Path
from typing import List

from modules.config import (
    AUTHOR_NAME,
    CHUNK_MAX_CHARS,
    CHUNK_OVERLAP_CHARS,
    PROJECT_NAME,
    REQUIREMENT_TEMPLATE_PATH,
    SCREEN_TEMPLATE_PATH,
    WBS_TEMPLATE_PATH,
    OUTPUT_MAPPER_PATH,
)
from modules.chunker import make_id, semantic_chunk
from modules.docx_reader import read_docx_text
from modules.extractor import extract_requirement_atoms
from modules.vector_store_factory import create_requirement_store
from modules.rag_service import build_domain_contexts
from modules.wbs_generator import generate_structured_wbs_items
from modules.screen_planner import generate_screen_plan_items_from_rag
from modules.excel_writer import save_requirement_excel, save_wbs_excel
from modules.ppt_writer import save_screen_plan_ppt
from modules.mapper_loader import load_mapper
from modules.process_loader import load_process_config, is_step_enabled, get_step
from modules.project_profile import classify_project_type
from modules.schemas import RequirementAtom
from modules.logger_utils import log_step, log_info
from modules.s3_client import ensure_local_path, list_s3_keys, upload_file
from modules.token_tracker import print_usage_summary
from modules.version_manager import build_doc_version_info, find_latest_versioned_docx, get_saved_document_info, is_version_analyzed, load_atoms_cache, save_atoms_cache


def _safe_project_name(project_name: str, space_replacement: str = '_') -> str:
    """파일명에 사용할 프로젝트명으로 변환한다."""
    name = (project_name or '프로젝트명').strip()
    name = re.sub(r'\s+', space_replacement, name)
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    return name or '프로젝트명'


def _next_versioned_output_path(output_dir: str, project_name: str, document_key: str, mapper: dict) -> str:
    """mapper의 output_files 설정을 기준으로 산출물 파일명을 만들고 기존 파일이 있으면 minor version을 증가한다."""
    output_mapper = mapper.get('output_files', {})
    doc_mapper = output_mapper.get('documents', {}).get(document_key, {})
    document_name = doc_mapper.get('document_name', document_key)
    extension = doc_mapper.get('extension', '')
    initial_major = int(output_mapper.get('initial_major', 0))
    initial_minor = int(output_mapper.get('initial_minor', 1))
    space_replacement = output_mapper.get('space_replacement', '_')

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_project_name(project_name, space_replacement=space_replacement)
    pattern = re.compile(
        rf'^{re.escape(safe_name)}_{re.escape(document_name)}_v\.(\d+)\.(\d+){re.escape(extension)}$'
    )

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


def _next_versioned_generated_path(project_name: str, document_key: str, mapper: dict) -> str:
    """S3_GENERATED_PREFIX 아래에 생성 파일명을 결정한다."""
    output_mapper = mapper.get('output_files', {})
    doc_mapper = output_mapper.get('documents', {}).get(document_key, {})
    document_name = doc_mapper.get('document_name', document_key)
    extension = doc_mapper.get('extension', '')
    initial_major = int(output_mapper.get('initial_major', 0))
    initial_minor = int(output_mapper.get('initial_minor', 1))
    space_replacement = output_mapper.get('space_replacement', '_')

    safe_name = _safe_project_name(project_name, space_replacement=space_replacement)
    pattern = re.compile(
        rf'^{re.escape(safe_name)}_{re.escape(document_name)}_v\.(\d+)\.(\d+){re.escape(extension)}$'
    )

    prefix = os.getenv('S3_GENERATED_PREFIX', 'storage/generated_files')
    bucket_name = os.getenv('S3_BUCKET_NAME')
    if not bucket_name:
        return _next_versioned_output_path('output', project_name, document_key, mapper)

    max_major = None
    max_minor = None
    for key in list_s3_keys(prefix, bucket_name=bucket_name):
        file_name = Path(key).name
        match = pattern.match(file_name)
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

    file_name = f'{safe_name}_{document_name}_v.{major}.{minor}{extension}'
    return f's3://{bucket_name}/{prefix.rstrip("/")}/{file_name}'


def _s3_key_from_uri(uri: str) -> str:
    return uri.replace('s3://', '').split('/', 1)[1]


def _atom_group_key(atom: RequirementAtom):
    return (
        atom.category.strip(),
        (atom.biz_requirement_name or atom.domain).strip(),
        atom.requirement_name.strip(),
        atom.requirement_type.strip(),
        atom.description.strip()[:120],
    )


def deduplicate_atoms(atoms: List[RequirementAtom]) -> List[RequirementAtom]:
    seen = set()
    result = []
    for atom in atoms:
        key = _atom_group_key(atom)
        if key in seen:
            continue
        seen.add(key)
        result.append(atom)
    return result


def assign_requirement_ids(atoms: List[RequirementAtom]) -> List[RequirementAtom]:
    biz_seq = {}
    for idx, atom in enumerate(atoms, start=1):
        biz_name = atom.biz_requirement_name or atom.domain or '공통'
        biz_seq.setdefault(biz_name, len(biz_seq) + 1)
        if not atom.biz_requirement_id:
            atom.biz_requirement_id = f'BIZ-{biz_seq[biz_name]:03d}'
        if not atom.biz_requirement_name:
            atom.biz_requirement_name = atom.domain or '공통'
        if not atom.domain:
            atom.domain = atom.biz_requirement_name or '공통'
        atom.requirement_id = f'REQ-{idx:04d}'
    return atoms


def analyze_document(
    docx_path: str,
    output_dir: str,
    store,
    recreate_collection: bool,
    project_type: str = 'auto',
    requirement_instruction_md: str = '',
) -> List[RequirementAtom]:
    doc_info = build_doc_version_info(docx_path)
    log_step(f'[버전 확인] 문서={doc_info.file_name}, 버전={doc_info.version}, key={doc_info.doc_key}')
    store.create_collection(recreate=recreate_collection)
    if is_version_analyzed(output_dir, doc_info):
        log_step('동일 파일로 확인되어 기존 분석 결과를 사용합니다.')
        cached_atoms = load_atoms_cache(output_dir, doc_info)
        if cached_atoms:
            log_info(f'기존 분석 결과 사용: {len(cached_atoms)}건')
            return cached_atoms
        log_info('캐시 파일이 없어 PgVector에서 기존 분석 결과를 조회합니다.')
        existing_atoms = store.scroll_atoms_by_doc_key(doc_info.doc_key)
        if existing_atoms:
            log_info(f'PgVector 기존 분석 결과 사용: {len(existing_atoms)}건')
            return existing_atoms
        log_info('기존 분석 메타데이터는 있으나 데이터가 없어 재분석합니다.')
    else:
        saved_info = get_saved_document_info(output_dir, doc_info)
        if saved_info:
            log_step('파일명은 같지만 생성/수정시각, 파일용량 또는 해시가 달라 새 파일로 판단했습니다. 재분석합니다.')

    if hasattr(store, 'delete_atoms_by_doc_key'):
        store.delete_atoms_by_doc_key(doc_info.doc_key)

    log_step('[1] DOCX 읽기')
    text = read_docx_text(docx_path)
    resolved_project_type = classify_project_type(text=text, configured=project_type)
    log_info(f'프로젝트 유형: {resolved_project_type}')
    log_step('[2] Semantic Chunking')
    chunks = semantic_chunk(text=text, doc_id=make_id(doc_info.doc_key), source_file=doc_info.file_name, max_chars=CHUNK_MAX_CHARS, overlap_chars=CHUNK_OVERLAP_CHARS)
    log_info(f'chunk count: {len(chunks)}')
    all_atoms: List[RequirementAtom] = []
    log_step('[3] 요구사항 Atom 추출 및 PgVector 저장')
    for idx, chunk in enumerate(chunks, start=1):
        log_info(f'  - chunk {idx}/{len(chunks)}: {chunk.title}, chars={len(chunk.text)}')
        atoms = extract_requirement_atoms(chunk, doc_info, project_type=resolved_project_type, instruction_md=requirement_instruction_md)
        for atom in atoms:
            atom.requirement_id = f'REQ-{len(all_atoms) + 1:04d}'
            atom.doc_key = doc_info.doc_key
            atom.doc_version = doc_info.version
        all_atoms.extend(atoms)
        store.upsert_atoms(atoms)
        log_info(f'    extracted: {len(atoms)}')
    log_step('[4] 중복 제거')
    all_atoms = assign_requirement_ids(deduplicate_atoms(all_atoms))
    store.upsert_atoms(all_atoms)
    save_atoms_cache(output_dir, doc_info, all_atoms)
    log_info(f'final requirement count: {len(all_atoms)}')
    return all_atoms


def run_pipeline(
    docx_path: str = None,
    output_dir: str = 'output',
    recreate_collection: bool = False,
    project_name: str = PROJECT_NAME,
    author: str = AUTHOR_NAME,
    mapper_path: str = OUTPUT_MAPPER_PATH,
    process_path: str = 'process.json',
):
    os.makedirs(output_dir, exist_ok=True)

    mapper = load_mapper(mapper_path)
    process_config = load_process_config(process_path)
    max_token = int(process_config.get('max_token', 0) or 0)
    limit_per_domain = int(process_config.get('limit_per_domain', 25) or 25)
    configured_project_type = process_config.get('project_type') or mapper.get('project_profile', {}).get('project_type', 'auto')

    if not docx_path:
        latest_doc_mapper = mapper.get('input_document', {})
        docx_path = find_latest_versioned_docx(
            input_dir=latest_doc_mapper.get('input_dir', 'input'),
            base_name=latest_doc_mapper.get('base_name', '구축요건정의서'),
        )

    docx_path = ensure_local_path(docx_path)

    temp_output_dir = tempfile.TemporaryDirectory(prefix='pm-generated-')

    log_step('[시작] PM Agent 산출물 생성')
    log_info(f'분석 대상 문서: {docx_path}')
    log_info(f'process 설정: project_type={configured_project_type}, max_token={max_token}, limit_per_domain={limit_per_domain}')
    doc_info = build_doc_version_info(docx_path)
    store = create_requirement_store()

    requirement_step = get_step(process_config, 'requirement_spec')
    all_atoms = analyze_document(
        docx_path=docx_path,
        output_dir=output_dir,
        store=store,
        recreate_collection=recreate_collection,
        project_type=configured_project_type,
        requirement_instruction_md=requirement_step.get('instruction_md', ''),
    )
    resolved_project_type = classify_project_type(atoms=all_atoms, configured=configured_project_type)
    generated_paths = []

    if is_step_enabled(process_config, 'requirement_spec'):
        log_step('[5] 요구사항명세서.xlsx 생성')
        requirement_excel_path = _next_versioned_generated_path(project_name, 'requirement_spec', mapper)
        local_requirement_excel_path = os.path.join(temp_output_dir.name, Path(_s3_key_from_uri(requirement_excel_path)).name)
        save_requirement_excel(
            atoms=all_atoms,
            template_path=mapper.get('requirement_spec', {}).get('template_path', REQUIREMENT_TEMPLATE_PATH),
            output_path=local_requirement_excel_path,
            project_name=project_name,
            author=author,
            mapper=mapper.get('requirement_spec'),
            max_token=max_token,
        )
        if requirement_excel_path.startswith('s3://'):
            upload_file(local_requirement_excel_path, _s3_key_from_uri(requirement_excel_path))
        generated_paths.append(requirement_excel_path)
    else:
        log_info('요구사항명세서 생성 비활성화됨')

    if is_step_enabled(process_config, 'wbs'):
        log_step('[6] WBS 생성을 위한 RAG 검색')
        build_domain_contexts(store=store, all_atoms=all_atoms, doc_key=doc_info.doc_key, purpose='WBS 개발 작업 분해', limit_per_domain=limit_per_domain)
        log_step('[7] 참고 WBS 규칙 기반 WBS.xlsx 생성')
        wbs_step = get_step(process_config, 'wbs')
        wbs_mapper = mapper.get('wbs', {})
        wbs_items = generate_structured_wbs_items(
            atoms=all_atoms,
            project_name=project_name,
            project_type=resolved_project_type,
            wbs_template_path=wbs_mapper.get('common_template_path', 'template/wbs_template.json'),
            deliverable_mapper_path=wbs_mapper.get('deliverable_mapper_path', 'template/deliverable_mapper.json'),
        )
        wbs_excel_path = _next_versioned_generated_path(project_name, 'wbs', mapper)
        local_wbs_excel_path = os.path.join(temp_output_dir.name, Path(_s3_key_from_uri(wbs_excel_path)).name)
        save_wbs_excel(
            items=wbs_items,
            template_path=wbs_mapper.get('template_path', WBS_TEMPLATE_PATH),
            output_path=local_wbs_excel_path,
            mapper=wbs_mapper,
            max_token=max_token,
        )
        if wbs_excel_path.startswith('s3://'):
            upload_file(local_wbs_excel_path, _s3_key_from_uri(wbs_excel_path))
        generated_paths.append(wbs_excel_path)
    else:
        log_info('WBS 생성 비활성화됨')

    if is_step_enabled(process_config, 'screen_plan'):
        log_step('[8] 화면기획서 생성을 위한 RAG 검색')
        screen_contexts = build_domain_contexts(store=store, all_atoms=all_atoms, doc_key=doc_info.doc_key, purpose='화면기획 UI 화면 표시 항목', limit_per_domain=limit_per_domain)
        log_step('[9] RAG 기반 화면기획서.pptx 생성')
        screen_step = get_step(process_config, 'screen_plan')
        screen_items = generate_screen_plan_items_from_rag(screen_contexts, instruction_md=screen_step.get('instruction_md', ''))
        screen_ppt_path = _next_versioned_generated_path(project_name, 'screen_plan', mapper)
        local_screen_ppt_path = os.path.join(temp_output_dir.name, Path(_s3_key_from_uri(screen_ppt_path)).name)
        save_screen_plan_ppt(
            items=screen_items,
            template_path=mapper.get('screen_plan', {}).get('template_path', SCREEN_TEMPLATE_PATH),
            output_path=local_screen_ppt_path,
            project_name=project_name,
            author=author,
            mapper=mapper.get('screen_plan'),
            max_token=max_token,
        )
        if screen_ppt_path.startswith('s3://'):
            upload_file(local_screen_ppt_path, _s3_key_from_uri(screen_ppt_path))
        generated_paths.append(screen_ppt_path)
    else:
        log_info('화면기획서 생성 비활성화됨')

    temp_output_dir.cleanup()

    log_step('[완료] 산출물 생성 완료')
    for path in generated_paths:
        log_info(f'- {path}')
    print_usage_summary(log_func=log_info)
