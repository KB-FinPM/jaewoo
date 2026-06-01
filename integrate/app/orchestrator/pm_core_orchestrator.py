from typing import Any, Dict, List

from app.agents.core_agents.requirement_agent.agent import RequirementAgent
from app.agents.core_agents.storyboard_agent.agent import StoryboardAgent
from app.agents.core_agents.wbs_agent.agent import WBSAgent
from app.core.pm_logger import log_step
from app.rag.qdrant_store import QdrantRequirementStore
from app.schemas.pm_artifacts import RequirementAtom


class CoreOrchestrator:
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
