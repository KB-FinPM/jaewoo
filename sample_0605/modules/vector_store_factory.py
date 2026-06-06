from modules.pgvector_store import PgVectorRequirementStore


def create_requirement_store():
    """PgVector 저장소를 생성한다."""
    return PgVectorRequirementStore()
