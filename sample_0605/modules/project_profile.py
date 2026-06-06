from typing import Dict, Iterable, List

from modules.schemas import RequirementAtom

INFRA_KEYWORDS = ['OCP', 'OpenShift', 'PaaS', 'Kafka', 'EFK', 'Elastic', 'Kibana', 'CDC', 'Service Mesh', '클러스터', '서버', '인프라', 'Gateway', '모니터링', '백업', 'DB동기화']
DEV_KEYWORDS = ['화면', 'UI', 'UX', 'API', '업무', '기능', '관리', '조회', '등록', '수정', '삭제', '승인', '결재', '배치', '프론트엔드', '백엔드']


def classify_project_type(text: str = '', atoms: Iterable[RequirementAtom] = (), configured: str = 'auto') -> str:
    if configured and configured != 'auto':
        return configured
    corpus = text or ''
    for atom in atoms or []:
        corpus += f' {atom.category} {atom.domain} {atom.feature} {atom.requirement_name} {atom.description}'
    infra_score = sum(1 for kw in INFRA_KEYWORDS if kw.lower() in corpus.lower())
    dev_score = sum(1 for kw in DEV_KEYWORDS if kw.lower() in corpus.lower())
    if infra_score >= 3 and dev_score >= 3:
        return 'hybrid'
    if infra_score > dev_score:
        return 'infra'
    if dev_score > 0:
        return 'development'
    return 'hybrid'


def get_phase_names(project_type: str) -> List[str]:
    if project_type == 'infra':
        return ['분석', '설계', '개발환경 구축', '스테이징 구축', '운영 구축']
    if project_type == 'development':
        return ['분석', '설계', '개발', '테스트', '운영 이행']
    return ['분석', '설계', '개발/구축', '스테이징 검증', '운영 이행']


def get_profile_instruction(project_type: str) -> str:
    if project_type == 'infra':
        return '프로젝트 유형은 인프라 구축이다. 기능 화면보다 아키텍처, 서버, 플랫폼, 미들웨어, 보안, 운영 요건을 우선 고려한다.'
    if project_type == 'development':
        return '프로젝트 유형은 애플리케이션 개발이다. 업무 기능, 화면, 인터페이스, 데이터, 권한, 테스트 요건을 우선 고려한다.'
    return '프로젝트 유형은 하이브리드이다. 인프라 구축 요건과 애플리케이션 개발 요건을 모두 구분해 고려한다.'
