import json
import os
import uuid
from typing import Any, Dict, List, Optional

import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

from modules.config import DATABASE_URL, EMBEDDING_MODEL
from modules.schemas import RequirementAtom


class PgVectorRequirementStore:
    def __init__(self, table_name: Optional[str] = None):
        self.database_url = DATABASE_URL or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError('DATABASE_URL이 .env에 설정되어 있지 않습니다.')
        self.table_name = table_name or os.getenv('PGVECTOR_TABLE', 'requirement_atoms')
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.vector_size = self.embedding_model.get_sentence_embedding_dimension()

    def _connect(self):
        conn = psycopg2.connect(self.database_url)
        register_vector(conn)
        return conn

    def create_collection(self, recreate: bool = False):
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')
                if recreate:
                    cur.execute(f'DROP TABLE IF EXISTS {self.table_name};')
                cur.execute(
                    f'''
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        doc_key TEXT NOT NULL,
                        requirement_id TEXT NOT NULL,
                        embedding vector({self.vector_size}) NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                    '''
                )
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_doc_key ON {self.table_name} (doc_key)')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_embedding ON {self.table_name} USING hnsw (embedding vector_cosine_ops)')
            conn.commit()
        finally:
            conn.close()

    def build_embedding_text(self, atom: RequirementAtom) -> str:
        return f'''
문서버전: {atom.doc_version}
구분: {atom.category}
요구사항ID: {atom.requirement_id}
요구사항명: {atom.requirement_name}
요구사항유형: {atom.requirement_type}
Biz요건ID: {atom.biz_requirement_id}
Biz요건명: {atom.biz_requirement_name}
도메인: {atom.domain}
기능: {atom.feature}
설명: {atom.description}
비고: {atom.note}
'''.strip()

    def upsert_atoms(self, atoms: List[RequirementAtom]):
        if not atoms:
            return

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                for atom in atoms:
                    if not atom.requirement_id:
                        atom.requirement_id = f'REQ-{uuid.uuid4().hex[:8].upper()}'
                    embedding_text = self.build_embedding_text(atom)
                    vector = self.embedding_model.encode(embedding_text, normalize_embeddings=True).tolist()
                    payload = atom.model_dump()
                    payload['embedding_text'] = embedding_text
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f'{atom.doc_key}:{atom.requirement_id}'))
                    cur.execute(
                        f'''
                        INSERT INTO {self.table_name} (id, doc_key, requirement_id, embedding, payload)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET doc_key=EXCLUDED.doc_key,
                            requirement_id=EXCLUDED.requirement_id,
                            embedding=EXCLUDED.embedding,
                            payload=EXCLUDED.payload,
                            created_at=NOW()
                        ''',
                        (point_id, atom.doc_key, atom.requirement_id, vector, json.dumps(payload)),
                    )
            conn.commit()
        finally:
            conn.close()

    def _make_filter(self, filters: Optional[Dict[str, Any]] = None) -> str:
        if not filters:
            return ''
        clauses = []
        for key, value in filters.items():
            clauses.append(f"payload->>'{key}' = %s")
        return ' AND '.join(clauses)

    def search(self, query: str, limit: int = 20, filters: Optional[Dict[str, Any]] = None):
        vector = self.embedding_model.encode(query, normalize_embeddings=True).tolist()
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                where_clause = self._make_filter(filters)
                params = [vector, limit]
                if where_clause:
                    params = [vector] + list(filters.values()) + [limit]
                    sql = f'''SELECT payload FROM {self.table_name} WHERE {where_clause} ORDER BY embedding <=> %s LIMIT %s'''
                else:
                    sql = f'''SELECT payload FROM {self.table_name} ORDER BY embedding <=> %s LIMIT %s'''
                cur.execute(sql, params)
                return cur.fetchall()
        finally:
            conn.close()

    def search_atoms(self, query: str, limit: int = 20, filters: Optional[Dict[str, Any]] = None) -> List[RequirementAtom]:
        results = self.search(query=query, limit=limit, filters=filters)
        return [RequirementAtom(**json.loads(row[0])) for row in results if row and row[0]]

    def delete_atoms_by_doc_key(self, doc_key: str):
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f'DELETE FROM {self.table_name} WHERE doc_key = %s', (doc_key,))
            conn.commit()
        finally:
            conn.close()

    def scroll_atoms_by_doc_key(self, doc_key: str, limit: int = 500) -> List[RequirementAtom]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f'SELECT payload FROM {self.table_name} WHERE doc_key = %s LIMIT %s',
                    (doc_key, limit),
                )
                return [RequirementAtom(**json.loads(row[0])) for row in cur.fetchall() if row and row[0]]
        finally:
            conn.close()
