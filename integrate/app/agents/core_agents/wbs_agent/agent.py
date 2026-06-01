from typing import List

from app.rag.rag_service import build_domain_contexts
from app.agents.core_agents.wbs_agent.generator import generate_wbs_items_from_rag
from app.rag.qdrant_store import QdrantRequirementStore
from app.schemas.pm_artifacts import RequirementAtom, WBSItem


class WBSAgent:
    """요구사항 RAG 결과를 기반으로 WBS 데이터를 생성하는 Core Agent."""

    def __init__(self, store: QdrantRequirementStore):
        self.store = store

    def run(self, atoms: List[RequirementAtom], doc_key: str, purpose: str, limit_per_domain: int = 25) -> List[WBSItem]:
        contexts = build_domain_contexts(
            store=self.store,
            all_atoms=atoms,
            doc_key=doc_key,
            purpose=purpose,
            limit_per_domain=limit_per_domain,
        )
        return generate_wbs_items_from_rag(contexts)
