from typing import List, Dict

from modules.qdrant_store import QdrantRequirementStore
from modules.schemas import RequirementAtom


def unique_domains(atoms: List[RequirementAtom]) -> List[str]:
    domains = []
    seen = set()
    for atom in atoms:
        domain = (atom.domain or '공통').strip() or '공통'
        if domain not in seen:
            seen.add(domain)
            domains.append(domain)
    return domains or ['전체']


def fallback_domain_atoms(atoms: List[RequirementAtom], domain: str, limit: int = 25) -> List[RequirementAtom]:
    matched = [a for a in atoms if (a.domain or '공통').strip() == domain]
    return matched[:limit] if matched else atoms[:limit]


def retrieve_atoms_for_domain(store: QdrantRequirementStore, all_atoms: List[RequirementAtom], doc_key: str, domain: str, purpose: str, limit: int = 25) -> List[RequirementAtom]:
    query = f'{domain} {purpose} 요구사항 화면 기능 비기능 정책 데이터'
    try:
        retrieved = store.search_atoms(query=query, limit=limit, filters={'doc_key': doc_key})
    except Exception:
        retrieved = []
    if retrieved:
        return retrieved
    return fallback_domain_atoms(all_atoms, domain, limit=limit)


def build_domain_contexts(store: QdrantRequirementStore, all_atoms: List[RequirementAtom], doc_key: str, purpose: str, limit_per_domain: int = 25) -> Dict[str, List[RequirementAtom]]:
    contexts = {}
    for domain in unique_domains(all_atoms):
        contexts[domain] = retrieve_atoms_for_domain(store, all_atoms, doc_key, domain, purpose, limit_per_domain)
    return contexts
