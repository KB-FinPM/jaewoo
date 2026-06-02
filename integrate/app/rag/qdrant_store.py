import uuid
from typing import Any, Dict, List, Optional

from app.core.config import EMBEDDING_MODEL, QDRANT_COLLECTION, QDRANT_URL
from app.schemas.artifact import RequirementAtom


class QdrantRequirementStore:
    """Qdrant 기반 요구사항 벡터 저장소.

    qdrant-client와 sentence-transformers는 로컬 PM 파이프라인 실행 시점에만
    필요하도록 lazy import한다. 이를 통해 FastAPI 앱 기본 import가 무거운
    ML 패키지 설치 여부에 영향을 받지 않도록 한다.
    """

    def __init__(self):
        from qdrant_client import QdrantClient
        from sentence_transformers import SentenceTransformer

        self.client = QdrantClient(url=QDRANT_URL)
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.vector_size = self.embedding_model.get_sentence_embedding_dimension()

    def _models(self):
        from qdrant_client.models import (
            Distance,
            FieldCondition,
            Filter,
            FilterSelector,
            MatchValue,
            PointStruct,
            VectorParams,
        )

        return {
            'Distance': Distance,
            'FieldCondition': FieldCondition,
            'Filter': Filter,
            'FilterSelector': FilterSelector,
            'MatchValue': MatchValue,
            'PointStruct': PointStruct,
            'VectorParams': VectorParams,
        }

    def create_collection(self, recreate: bool = False):
        m = self._models()
        exists = self.client.collection_exists(QDRANT_COLLECTION)
        if exists and recreate:
            self.client.delete_collection(QDRANT_COLLECTION)
            exists = False
        if not exists:
            self.client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=m['VectorParams'](
                    size=self.vector_size,
                    distance=m['Distance'].COSINE,
                ),
            )

    def build_embedding_text(self, atom: RequirementAtom) -> str:
        return f'''
문서버전: {atom.doc_version}
구분: {atom.category}
요구사항ID: {atom.requirement_id}
요구사항명: {atom.requirement_name}
요구사항유형: {atom.requirement_type}
도메인: {atom.domain}
기능: {atom.feature}
설명: {atom.description}
비고: {atom.note}
'''.strip()

    def upsert_atoms(self, atoms: List[RequirementAtom]):
        m = self._models()
        points = []
        for atom in atoms:
            if not atom.requirement_id:
                atom.requirement_id = f'REQ-{uuid.uuid4().hex[:8].upper()}'
            embedding_text = self.build_embedding_text(atom)
            vector = self.embedding_model.encode(
                embedding_text,
                normalize_embeddings=True,
            ).tolist()
            payload = atom.model_dump()
            payload['embedding_text'] = embedding_text
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'{atom.doc_key}:{atom.requirement_id}'))
            points.append(m['PointStruct'](id=point_id, vector=vector, payload=payload))
        if points:
            self.client.upsert(collection_name=QDRANT_COLLECTION, points=points)

    def _make_filter(self, filters: Optional[Dict[str, Any]] = None):
        if not filters:
            return None
        m = self._models()
        return m['Filter'](
            must=[
                m['FieldCondition'](key=key, match=m['MatchValue'](value=value))
                for key, value in filters.items()
            ]
        )

    def search(self, query: str, limit: int = 20, filters: Optional[Dict[str, Any]] = None):
        query_vector = self.embedding_model.encode(query, normalize_embeddings=True).tolist()
        return self.client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=query_vector,
            query_filter=self._make_filter(filters),
            limit=limit,
            with_payload=True,
        )

    def search_atoms(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RequirementAtom]:
        results = self.search(query=query, limit=limit, filters=filters)
        return [RequirementAtom(**item.payload) for item in results if item.payload]

    def delete_atoms_by_doc_key(self, doc_key: str):
        m = self._models()
        self.client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=m['FilterSelector'](
                filter=self._make_filter({'doc_key': doc_key})
            ),
        )

    def scroll_atoms_by_doc_key(self, doc_key: str, limit: int = 500) -> List[RequirementAtom]:
        atoms = []
        next_offset = None
        scroll_filter = self._make_filter({'doc_key': doc_key})
        while True:
            points, next_offset = self.client.scroll(
                collection_name=QDRANT_COLLECTION,
                scroll_filter=scroll_filter,
                limit=limit,
                offset=next_offset,
                with_payload=True,
                with_vectors=False,
            )
            atoms.extend([RequirementAtom(**point.payload) for point in points if point.payload])
            if next_offset is None:
                break
        return atoms
