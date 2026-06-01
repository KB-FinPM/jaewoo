from typing import Any, Dict, Optional, Tuple

from app.agents.input_agents.document_parser_agent.agent import DocumentParserAgent
from app.core.pm_logger import log_info, log_step
from app.rag.qdrant_store import QdrantRequirementStore
from app.storage.version_manager import build_doc_version_info, find_latest_versioned_docx


class InputOrchestrator:
    """입력 문서 선택과 document_parser_agent 실행을 담당한다."""

    def __init__(self, process: Dict[str, Any], store: QdrantRequirementStore):
        self.process = process
        self.store = store

    def resolve_docx_path(self, docx_path: Optional[str]) -> str:
        if docx_path:
            return docx_path

        agent_config = self.process.get('input', {}).get('document_parser_agent', {})
        return find_latest_versioned_docx(
            input_dir=agent_config.get('input_dir', 'input'),
            base_name=agent_config.get('base_name', '구축요건정의서'),
        )

    def run(self, docx_path: Optional[str], output_dir: str, recreate_collection: bool = False) -> Tuple[str, Any, list]:
        resolved_docx_path = self.resolve_docx_path(docx_path)
        log_info(f'분석 대상 문서: {resolved_docx_path}')

        doc_info = build_doc_version_info(resolved_docx_path)
        parser_agent = DocumentParserAgent(self.store)
        atoms = parser_agent.analyze(
            docx_path=resolved_docx_path,
            output_dir=output_dir,
            recreate_collection=recreate_collection,
        )
        return resolved_docx_path, doc_info, atoms
