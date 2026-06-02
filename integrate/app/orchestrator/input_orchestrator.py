# EN: Orchestrates user input normalization before domain processing.
# KO: 도메인 처리 전 사용자 입력 표준화를 제어하는 Orchestrator입니다.

from app.agents.input_agents.document_parser_agent.agent import (
    DocumentParserAgent,
    document_parser_agent,
)
from app.schemas.io_agent import (
    InputAgentRequest,
    InputAgentResponse,
    InputType,
    NormalizedRequestType,
)


class InputOrchestrator:
    """Routes raw user input to the proper input agent and returns standard JSON."""

    def __init__(
        self,
        document_parser: DocumentParserAgent = document_parser_agent,
    ) -> None:
        self.document_parser = document_parser

    async def normalize(self, request: InputAgentRequest) -> InputAgentResponse:
        # TODO: Route TEXT, MEETING_NOTES, and ARTIFACT_REQUEST inputs to dedicated
        # input agents once those agents are implemented.
        if request.input_type == InputType.FILE:
            return await self.document_parser.parse(request)

        return InputAgentResponse(
            success=False,
            agent_name="InputOrchestrator",
            normalized_request_type=NormalizedRequestType.UNKNOWN,
            error="unsupported input type",
            validation_errors=["unsupported input type"],
        )


input_orchestrator = InputOrchestrator()


# PM artifact generation input flow
# 기존 pm_input_orchestrator.py를 backend 표준 input_orchestrator.py에 통합했습니다.
from typing import Any, Dict, Optional, Tuple

from app.agents.input_agents.document_parser_agent.agent import DocumentParserAgent
from app.core.logger import log_info, log_step
from app.rag.qdrant_store import QdrantRequirementStore
from app.storage.version_manager import build_doc_version_info, find_latest_versioned_docx


class DocumentArtifactInputOrchestrator:
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
