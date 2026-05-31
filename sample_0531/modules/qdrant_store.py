import uuid
from typing import List, Dict, Any, Optional

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, FilterSelector

from modules.config import QDRANT_URL, QDRANT_COLLECTION, EMBEDDING_MODEL
from modules.schemas import RequirementAtom


class QdrantRequirementStore:
    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL)
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.vector_size = self.embedding_model.get_sentence_embedding_dimension()

    def create_collection(self, recreate: bool = False):
        exists = self.client.collection_exists(QDRANT_COLLECTION)
        if exists and recreate:
            self.client.delete_collection(QDRANT_COLLECTION)
            exists = False
        if not exists:
            self.client.create_collection(collection_name=QDRANT_COLLECTION, vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE))

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
        points = []
        for atom in atoms:
            if not atom.requirement_id:
                atom.requirement_id = f'REQ-{uuid.uuid4().hex[:8].upper()}'
            embedding_text = self.build_embedding_text(atom)
            vector = self.embedding_model.encode(embedding_text, normalize_embeddings=True).tolist()
            payload = atom.model_dump()
            payload['embedding_text'] = embedding_text
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'{atom.doc_key}:{atom.requirement_id}'))
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))
        if points:
            self.client.upsert(collection_name=QDRANT_COLLECTION, points=points)

    def _make_filter(self, filters: Optional[Dict[str, Any]] = None):
        if not filters:
            return None
        return Filter(must=[FieldCondition(key=key, match=MatchValue(value=value)) for key, value in filters.items()])

    def search(self, query: str, limit: int = 20, filters: Optional[Dict[str, Any]] = None):
        query_vector = self.embedding_model.encode(query, normalize_embeddings=True).tolist()
        return self.client.search(collection_name=QDRANT_COLLECTION, query_vector=query_vector, query_filter=self._make_filter(filters), limit=limit, with_payload=True)

    def search_atoms(self, query: str, limit: int = 20, filters: Optional[Dict[str, Any]] = None) -> List[RequirementAtom]:
        results = self.search(query=query, limit=limit, filters=filters)
        return [RequirementAtom(**item.payload) for item in results if item.payload]


    def delete_atoms_by_doc_key(self, doc_key: str):
        self.client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=FilterSelector(filter=self._make_filter({'doc_key': doc_key})),
        )

    def scroll_atoms_by_doc_key(self, doc_key: str, limit: int = 500) -> List[RequirementAtom]:
        atoms = []
        next_offset = None
        scroll_filter = self._make_filter({'doc_key': doc_key})
        while True:
            points, next_offset = self.client.scroll(collection_name=QDRANT_COLLECTION, scroll_filter=scroll_filter, limit=limit, offset=next_offset, with_payload=True, with_vectors=False)
            atoms.extend([RequirementAtom(**point.payload) for point in points if point.payload])
            if next_offset is None:
                break
        return atoms
