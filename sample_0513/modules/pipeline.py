import os
from typing import List

from modules.config import CHUNK_MAX_CHARS, CHUNK_OVERLAP_CHARS
from modules.chunker import make_id, semantic_chunk
from modules.docx_reader import read_docx_text
from modules.extractor import extract_requirement_atoms
from modules.qdrant_store import QdrantRequirementStore
from modules.wbs_generator import generate_wbs_items
from modules.excel_writer import save_requirement_excel, save_wbs_excel
from modules.schemas import RequirementAtom
from modules.token_tracker import print_usage_summary


def deduplicate_atoms(atoms: List[RequirementAtom]) -> List[RequirementAtom]:
    seen = set()
    result = []

    for atom in atoms:
        key = (
            atom.category.strip(),
            atom.requirement_name.strip(),
            atom.requirement_type.strip(),
            atom.description.strip()[:120],
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(atom)

    return result


def run_pipeline(
    docx_path: str = "구축요건정의서.docx",
    output_dir: str = "output",
    recreate_collection: bool = True,
):
    os.makedirs(output_dir, exist_ok=True)

    source_file = os.path.basename(docx_path)
    doc_id = make_id(source_file)

    print("[1] DOCX 읽기")
    text = read_docx_text(docx_path)

    print("[2] Semantic Chunking")
    chunks = semantic_chunk(
        text=text,
        doc_id=doc_id,
        source_file=source_file,
        max_chars=CHUNK_MAX_CHARS,
        overlap_chars=CHUNK_OVERLAP_CHARS,
    )
    print(f"chunk count: {len(chunks)}")

    print("[3] Qdrant 준비")
    store = QdrantRequirementStore()
    store.create_collection(recreate=recreate_collection)

    all_atoms: List[RequirementAtom] = []

    print("[4] 요구사항 Atom 추출 및 Qdrant 저장")
    for idx, chunk in enumerate(chunks, start=1):
        print(f"  - chunk {idx}/{len(chunks)}: {chunk.title}, chars={len(chunk.text)}")

        atoms = extract_requirement_atoms(chunk)

        for atom in atoms:
            atom.requirement_id = f"REQ-{len(all_atoms) + 1:04d}"

        all_atoms.extend(atoms)
        store.upsert_atoms(atoms)

        print(f"    extracted: {len(atoms)}")

    print("[5] 중복 제거")
    all_atoms = deduplicate_atoms(all_atoms)

    for idx, atom in enumerate(all_atoms, start=1):
        atom.requirement_id = f"REQ-{idx:04d}"

    print(f"final requirement count: {len(all_atoms)}")

    print("[6] 요구사항명세서.xlsx 생성")
    requirement_excel_path = os.path.join(output_dir, "요구사항명세서.xlsx")
    save_requirement_excel(all_atoms, requirement_excel_path)

    print("[7] WBS 배치 생성")
    wbs_items = generate_wbs_items(all_atoms)

    print("[8] WBS.xlsx 생성")
    wbs_excel_path = os.path.join(output_dir, "WBS.xlsx")
    save_wbs_excel(wbs_items, wbs_excel_path)

    print("완료")
    print(f"- {requirement_excel_path}")
    print(f"- {wbs_excel_path}")

    print_usage_summary()
