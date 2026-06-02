# EN: Orchestrates source-document based artifact generation flows.
# KO: 선행 문서 기반 후행 산출물 생성 흐름을 제어합니다.

from typing import Any
from uuid import uuid4

from app.agents.core_agents.requirement_agent.agent import requirement_agent
from app.agents.core_agents.validator_agent.agent import validator_agent
from app.core.logger import get_logger
from app.rag.retrieval import retrieval_service
from app.schemas.agent import AgentRequest, AgentResponse
from app.schemas.artifact import ArtifactType
from app.schemas.request import GenerationRequest
from app.schemas.response import GenerationResponse

logger = get_logger(__name__)


class GenerationOrchestrator:
    """Coordinates generation flows across retrieval, core agents, and validation."""

    def __init__(
        self,
        retrieval: Any = retrieval_service,
        requirement_generator: Any = requirement_agent,
        validator: Any = validator_agent,
    ) -> None:
        self.retrieval = retrieval
        self.requirement_generator = requirement_generator
        self.validator = validator

    async def generate_requirement(
        self,
        request: GenerationRequest,
        artifact_service: Any = None,
        retrieval_service: Any = None,
        template_service: Any = None,
    ) -> GenerationResponse:
        return await self.generate_artifact(
            request,
            artifact_service=artifact_service,
            retrieval_service=retrieval_service,
            template_service=template_service,
        )

    async def generate_artifact(
        self,
        request: GenerationRequest,
        artifact_service: Any = None,
        retrieval_service: Any = None,
        template_service: Any = None,
    ) -> GenerationResponse:
        generation_flow = request.generation_flow()
        if generation_flow.target_artifact_type == ArtifactType.REQUIREMENT_SPEC:
            return await self._generate_requirement_artifact(
                request,
                artifact_service=artifact_service,
                retrieval_service=retrieval_service,
                template_service=template_service,
            )

        # TODO: Wire WBS, Screen Design, and Action Items agents into this
        # dispatch table as each agent source is delivered.
        return self._not_implemented_response(
            request,
            generation_flow.target_artifact_type,
        )

    async def _generate_requirement_artifact(
        self,
        request: GenerationRequest,
        artifact_service: Any = None,
        retrieval_service: Any = None,
        template_service: Any = None,
    ) -> GenerationResponse:
        generation_flow = request.generation_flow()
        logger.info(
            "[Orchestrator] generate_requirement start | "
            f"project_id={request.project_id} | "
            f"target_artifact_type={generation_flow.target_artifact_type}"
        )

        resolved_template = None
        if template_service is not None:
            resolved_template = await template_service.resolve_template(
                reference=generation_flow.template,
                artifact_type=generation_flow.target_artifact_type,
            )
            if generation_flow.template.template_id and resolved_template is None:
                return self._failed_response(
                    request,
                    AgentResponse(
                        success=False,
                        agent_name="TemplateService",
                        error="template not found",
                    ),
                )

        template_context = (
            resolved_template.model_dump(mode="json")
            if resolved_template is not None
            else generation_flow.template.model_dump(mode="json")
        )

        retrieval = retrieval_service or self.retrieval
        documents = await retrieval.search(
            project_id=request.project_id,
            permission_scope=request.permission_scope,
            query=request.query or "",
        )

        agent_request = AgentRequest(
            project_id=request.project_id,
            documents=documents,
            context={
                "source_document_ids": request.source_document_ids,
                "document_ids": request.document_ids,
                "source_document_type": (
                    generation_flow.source_document_type.value
                    if generation_flow.source_document_type
                    else None
                ),
                "target_artifact_type": generation_flow.target_artifact_type.value,
                "template": template_context,
                "query": request.query,
                "permission_scope": request.permission_scope,
            },
        )
        agent_response = await self.requirement_generator.generate(agent_request)
        if not agent_response.success:
            return self._failed_response(request, agent_response)

        validated_response = await self.validator.validate(agent_response.result)
        if not validated_response.success:
            return self._failed_response(request, validated_response)

        if artifact_service is not None:
            artifact = await artifact_service.create_artifact(
                artifact_id=f"ART-{uuid4().hex[:12].upper()}",
                project_id=request.project_id,
                artifact_type=generation_flow.target_artifact_type,
                name=generation_flow.target_artifact_type.value,
                source_document_ids=request.source_document_ids,
                template_id=(
                    resolved_template.template_id
                    if resolved_template is not None
                    else generation_flow.template.template_id
                ),
                template_version=(
                    resolved_template.template_version
                    if resolved_template is not None
                    else generation_flow.template.template_version
                ),
                result_json=validated_response.result,
            )
            result = {
                "artifact": artifact.model_dump(mode="json"),
                "generated": validated_response.result,
            }
        else:
            result = validated_response.result

        logger.info(
            "[Orchestrator] generate_requirement done | "
            f"project_id={request.project_id}"
        )
        return GenerationResponse(
            project_id=request.project_id,
            message="artifact generated" if artifact_service is not None else "ok",
            result=result,
        )

    def _not_implemented_response(
        self,
        request: GenerationRequest,
        artifact_type: ArtifactType,
    ) -> GenerationResponse:
        message = f"{artifact_type.value} generation is not implemented yet"
        logger.warning(
            "[Orchestrator] generation not implemented | "
            f"project_id={request.project_id} | artifact_type={artifact_type.value}"
        )
        return GenerationResponse(
            success=False,
            message=message,
            project_id=request.project_id,
            result={
                "artifact_type": artifact_type.value,
                "error": message,
            },
        )

    def _failed_response(
        self,
        request: GenerationRequest,
        agent_response: AgentResponse,
    ) -> GenerationResponse:
        logger.warning(
            "[Orchestrator] generate_requirement failed | "
            f"project_id={request.project_id} | "
            f"agent={agent_response.agent_name} | error={agent_response.error}"
        )
        return GenerationResponse(
            success=False,
            message=agent_response.error or "generation failed",
            project_id=request.project_id,
            result={
                "agent_name": agent_response.agent_name,
                "error": agent_response.error,
            },
        )


generation_orchestrator = GenerationOrchestrator()


# PM artifact generation core flow
# 기존 pm_core_orchestrator.py를 backend 표준 generation_orchestrator.py에 통합했습니다.
from typing import Any, Dict, List

from app.agents.core_agents.requirement_agent.agent import RequirementAgent
from app.agents.core_agents.storyboard_agent.agent import StoryboardAgent
from app.agents.core_agents.wbs_agent.agent import WBSAgent
from app.core.logger import log_step
from app.rag.qdrant_store import QdrantRequirementStore
from app.schemas.artifact import RequirementAtom


class ArtifactCoreOrchestrator:
    """Core Agent 실행 순서를 관리한다."""

    def __init__(self, process: Dict[str, Any], store: QdrantRequirementStore):
        self.process = process
        self.store = store

    def _output_enabled(self, output_key: str) -> bool:
        return bool(self.process.get('output_agents', {}).get(output_key, {}).get('enabled', False))

    def _core_enabled(self, agent_key: str) -> bool:
        return bool(self.process.get('core_agents', {}).get(agent_key, {}).get('enabled', True))

    def run(self, atoms: List[RequirementAtom], doc_key: str) -> Dict[str, Any]:
        core_data: Dict[str, Any] = {
            'requirements': [],
            'wbs_items': [],
            'screen_items': [],
        }

        # 산출물 중 하나라도 요구사항 기반이면 requirement_agent는 내부적으로 실행한다.
        needs_requirements = any(
            self._output_enabled(key)
            for key in ['requirement_spec', 'wbs', 'screen_plan', 'markdown_summary']
        )
        if needs_requirements and self._core_enabled('requirement_agent'):
            log_step('[5] Requirement Agent 실행')
            core_data['requirements'] = RequirementAgent().run(atoms)
        else:
            core_data['requirements'] = atoms

        if self._output_enabled('wbs') and self._core_enabled('wbs_agent'):
            cfg = self.process.get('core_agents', {}).get('wbs_agent', {})
            log_step('[6] WBS Agent 실행')
            core_data['wbs_items'] = WBSAgent(self.store).run(
                atoms=core_data['requirements'],
                doc_key=doc_key,
                purpose=cfg.get('rag_purpose', 'WBS 개발 작업 분해'),
                limit_per_domain=int(cfg.get('limit_per_domain', 25)),
            )

        if self._output_enabled('screen_plan') and self._core_enabled('storyboard_agent'):
            cfg = self.process.get('core_agents', {}).get('storyboard_agent', {})
            log_step('[7] Storyboard Agent 실행')
            core_data['screen_items'] = StoryboardAgent(self.store).run(
                atoms=core_data['requirements'],
                doc_key=doc_key,
                purpose=cfg.get('rag_purpose', '화면기획 UI 화면 표시 항목'),
                limit_per_domain=int(cfg.get('limit_per_domain', 25)),
            )

        return core_data


# PM artifact generation local pipeline
# 기존 pm_pipeline.py를 generation_orchestrator.py에 통합했습니다.
import os
from typing import Optional

from app.core.config import AUTHOR_NAME, OUTPUT_MAPPER_PATH, PROJECT_NAME, RECREATE_COLLECTION
from app.core.logger import log_info, log_step
from app.core.mapper_loader import load_mapper
from app.core.process_loader import load_process
from app.rag.qdrant_store import QdrantRequirementStore
from app.core.token_tracker import print_usage_summary
from app.orchestrator.input_orchestrator import DocumentArtifactInputOrchestrator
from app.orchestrator.output_orchestrator import ArtifactFileOutputOrchestrator


def run_pm_pipeline(
    docx_path: Optional[str] = None,
    output_dir: str = 'output',
    recreate_collection: bool = False,
    project_name: str = PROJECT_NAME,
    author: str = AUTHOR_NAME,
    mapper_path: str = OUTPUT_MAPPER_PATH,
    process_path: str = 'process.json',
):
    """Multi-agent 기반 PM 산출물 전체 파이프라인 실행."""
    os.makedirs(output_dir, exist_ok=True)
    mapper = load_mapper(mapper_path)
    process = load_process(process_path)

    log_step('[시작] PM Multi-Agent 산출물 생성')

    store = QdrantRequirementStore()

    input_orchestrator_for_artifacts = DocumentArtifactInputOrchestrator(process=process, store=store)
    _, doc_info, atoms = input_orchestrator_for_artifacts.run(
        docx_path=docx_path,
        output_dir=output_dir,
        recreate_collection=recreate_collection,
    )

    core_orchestrator_for_artifacts = ArtifactCoreOrchestrator(process=process, store=store)
    core_data = core_orchestrator_for_artifacts.run(atoms=atoms, doc_key=doc_info.doc_key)

    output_orchestrator_for_artifacts = ArtifactFileOutputOrchestrator(process=process, mapper=mapper)
    generated = output_orchestrator_for_artifacts.run(
        core_data=core_data,
        output_dir=output_dir,
        project_name=project_name,
        author=author,
    )

    if not generated:
        log_info('process.json에서 enabled=true인 출력 산출물이 없습니다.')

    print_usage_summary(log_func=log_info)
    return generated
