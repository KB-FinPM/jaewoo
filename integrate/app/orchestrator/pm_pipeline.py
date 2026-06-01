import os
from typing import Optional

from app.core.pm_config import AUTHOR_NAME, OUTPUT_MAPPER_PATH, PROJECT_NAME, RECREATE_COLLECTION
from app.core.pm_logger import log_info, log_step
from app.core.mapper_loader import load_mapper
from app.core.process_loader import load_process
from app.rag.qdrant_store import QdrantRequirementStore
from app.core.token_tracker import print_usage_summary
from app.orchestrator.pm_core_orchestrator import CoreOrchestrator
from app.orchestrator.pm_input_orchestrator import InputOrchestrator
from app.orchestrator.pm_output_orchestrator import OutputOrchestrator


# 하위 호환용 alias
from app.storage.file_version import next_versioned_output_path as _next_versioned_output_path  # noqa: F401
from app.storage.file_version import safe_project_name as _safe_project_name  # noqa: F401


def run_pipeline(
    docx_path: Optional[str] = None,
    output_dir: str = 'output',
    recreate_collection: bool = False,
    project_name: str = PROJECT_NAME,
    author: str = AUTHOR_NAME,
    mapper_path: str = OUTPUT_MAPPER_PATH,
    process_path: str = 'process.json',
):
    """Multi-agent orchestrator 기반 전체 파이프라인 실행."""
    os.makedirs(output_dir, exist_ok=True)
    mapper = load_mapper(mapper_path)
    process = load_process(process_path)

    log_step('[시작] PM Multi-Agent 산출물 생성')

    store = QdrantRequirementStore()

    input_orchestrator = InputOrchestrator(process=process, store=store)
    _, doc_info, atoms = input_orchestrator.run(
        docx_path=docx_path,
        output_dir=output_dir,
        recreate_collection=recreate_collection,
    )

    core_orchestrator = CoreOrchestrator(process=process, store=store)
    core_data = core_orchestrator.run(atoms=atoms, doc_key=doc_info.doc_key)

    output_orchestrator = OutputOrchestrator(process=process, mapper=mapper)
    generated = output_orchestrator.run(
        core_data=core_data,
        output_dir=output_dir,
        project_name=project_name,
        author=author,
    )

    if not generated:
        log_info('process.json에서 enabled=true인 출력 산출물이 없습니다.')

    print_usage_summary(log_func=log_info)
    return generated
