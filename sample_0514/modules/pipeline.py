import os
from typing import List

from modules.config import CHUNK_MAX_CHARS, CHUNK_OVERLAP_CHARS
from modules.chunker import make_id, semantic_chunk
from modules.docx_reader import read_docx_text
from modules.extractor import extract_requirement_atoms
from modules.qdrant_store import QdrantRequirementStore
from modules.rag_service import build_domain_contexts
from modules.wbs_generator import generate_wbs_items_from_rag
from modules.screen_planner import generate_screen_plan_items_from_rag
from modules.excel_writer import save_requirement_excel, save_wbs_excel
from modules.ppt_writer import save_screen_plan_ppt
from modules.schemas import RequirementAtom
from modules.logger_utils import log_step, log_info
from modules.token_tracker import print_usage_summary
from modules.version_manager import build_doc_version_info, is_version_analyzed, load_atoms_cache, save_atoms_cache


def deduplicate_atoms(atoms: List[RequirementAtom]) -> List[RequirementAtom]:
    seen = set()
    result = []
    for atom in atoms:
        key = (atom.category.strip(), atom.requirement_name.strip(), atom.requirement_type.strip(), atom.description.strip()[:120])
        if key in seen:
            continue
        seen.add(key)
        result.append(atom)
    return result


def assign_requirement_ids(atoms: List[RequirementAtom]) -> List[RequirementAtom]:
    for idx, atom in enumerate(atoms, start=1):
        atom.requirement_id = f'REQ-{idx:04d}'
    return atoms


def analyze_document(docx_path: str, output_dir: str, store: QdrantRequirementStore, recreate_collection: bool) -> List[RequirementAtom]:
    doc_info = build_doc_version_info(docx_path)
    log_step(f'[버전 확인] 문서={doc_info.file_name}, 버전={doc_info.version}, key={doc_info.doc_key}')
    store.create_collection(recreate=recreate_collection)
    if is_version_analyzed(output_dir, doc_info):
        log_step('기존에 이미 분석한 내용이라 다시 저장하지 않습니다.')
        cached_atoms = load_atoms_cache(output_dir, doc_info)
        if cached_atoms:
            log_info(f'기존 분석 결과 사용: {len(cached_atoms)}건')
            return cached_atoms
        log_info('캐시 파일이 없어 Qdrant에서 기존 분석 결과를 조회합니다.')
        qdrant_atoms = store.scroll_atoms_by_doc_key(doc_info.doc_key)
        if qdrant_atoms:
            log_info(f'Qdrant 기존 분석 결과 사용: {len(qdrant_atoms)}건')
            return qdrant_atoms
        log_info('기존 분석 메타데이터는 있으나 데이터가 없어 재분석합니다.')

    log_step('[1] DOCX 읽기')
    text = read_docx_text(docx_path)
    log_step('[2] Semantic Chunking')
    chunks = semantic_chunk(text=text, doc_id=make_id(doc_info.doc_key), source_file=doc_info.file_name, max_chars=CHUNK_MAX_CHARS, overlap_chars=CHUNK_OVERLAP_CHARS)
    log_info(f'chunk count: {len(chunks)}')
    all_atoms: List[RequirementAtom] = []
    log_step('[3] 요구사항 Atom 추출 및 Qdrant 저장')
    for idx, chunk in enumerate(chunks, start=1):
        log_info(f'  - chunk {idx}/{len(chunks)}: {chunk.title}, chars={len(chunk.text)}')
        atoms = extract_requirement_atoms(chunk, doc_info)
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


def run_pipeline(docx_path: str = '구축요건정의서.v.1.docx', output_dir: str = 'output', recreate_collection: bool = False):
    os.makedirs(output_dir, exist_ok=True)
    log_step('[시작] PM Agent 산출물 생성')
    doc_info = build_doc_version_info(docx_path)
    store = QdrantRequirementStore()
    all_atoms = analyze_document(docx_path=docx_path, output_dir=output_dir, store=store, recreate_collection=recreate_collection)
    log_step('[5] 요구사항명세서.xlsx 생성')
    requirement_excel_path = os.path.join(output_dir, '요구사항명세서.xlsx')
    save_requirement_excel(all_atoms, requirement_excel_path)
    log_step('[6] WBS 생성을 위한 RAG 검색')
    wbs_contexts = build_domain_contexts(store=store, all_atoms=all_atoms, doc_key=doc_info.doc_key, purpose='WBS 개발 작업 분해', limit_per_domain=25)
    log_step('[7] RAG 기반 WBS.xlsx 생성')
    wbs_items = generate_wbs_items_from_rag(wbs_contexts)
    wbs_excel_path = os.path.join(output_dir, 'WBS.xlsx')
    save_wbs_excel(wbs_items, wbs_excel_path)
    log_step('[8] 화면기획서 생성을 위한 RAG 검색')
    screen_contexts = build_domain_contexts(store=store, all_atoms=all_atoms, doc_key=doc_info.doc_key, purpose='화면기획 UI 화면 표시 항목', limit_per_domain=25)
    log_step('[9] RAG 기반 화면기획서.pptx 생성')
    screen_items = generate_screen_plan_items_from_rag(screen_contexts)
    screen_ppt_path = os.path.join(output_dir, '화면기획서.pptx')
    save_screen_plan_ppt(screen_items, screen_ppt_path)
    log_step('[완료] 산출물 생성 완료')
    log_info(f'- {requirement_excel_path}')
    log_info(f'- {wbs_excel_path}')
    log_info(f'- {screen_ppt_path}')
    print_usage_summary(log_func=log_info)
