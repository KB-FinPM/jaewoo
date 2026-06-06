import json
from typing import List

from modules.schemas import SemanticChunk, RequirementAtom
from modules.bedrock_client import invoke_bedrock
from modules.json_utils import clean_json_response, safe_json_loads, repair_json_array
from modules.version_manager import DocumentVersionInfo
from modules.agent_instruction import load_agent_instruction
from modules.project_profile import get_profile_instruction


EXTRACTION_SYSTEM_PROMPT = '''
너는 PM Agent의 구축요건정의서 분석기다.
입력 chunk에서 요구사항명세서에 들어갈 요구사항 atom을 추출하라.
반드시 JSON 배열만 반환한다.
각 항목 schema:
[
  {"category":"기능 | 비기능 | 인터페이스 | 데이터 | 정책 | 인프라 | 보안 | 운영","biz_requirement_id":"Biz요건ID 또는 빈 문자열","biz_requirement_name":"Biz요건명 또는 업무영역","requirement_name":"요구사항명","requirement_type":"기능요구사항 | 비기능요구사항","domain":"업무영역","feature":"기능명 또는 구축항목","description":"요구사항 설명","note":"검토의견 또는 비고"}
]
규칙:
- 문서에 없는 내용은 추측하지 않는다.
- 하나의 요구사항은 하나의 atom으로 분리한다.
- 중복 요구사항은 최대한 만들지 않는다.
- Biz요건명은 실제 요구사항명세서/WBS 그룹핑의 기준이 되므로 명확히 작성한다.
- 인프라 구축 프로젝트에서는 OCP, Kafka, EFK, CDC, API Gateway, Service Mesh, Monitoring, Logging, DB, 보안, 백업 등을 Biz요건명 후보로 본다.
- 개발 프로젝트에서는 업무, 화면, 기능, 인터페이스, 데이터, 권한, 배치 등을 Biz요건명 후보로 본다.
- 기능 구현과 직접 관련 있으면 기능요구사항으로 분류한다.
- 성능, 보안, 권한, 로그, 접근성, 운영, 백업, 장애대응은 비기능요구사항으로 분류한다.
- 한 번의 응답에서 최대 10개 요구사항만 추출한다.
- 각 description은 120자 이내로 요약한다.
- note는 50자 이내로 작성한다.
- JSON 외의 설명 문장은 절대 출력하지 않는다.
'''


def extract_requirement_atoms(
    chunk: SemanticChunk,
    doc_info: DocumentVersionInfo,
    project_type: str = 'auto',
    instruction_md: str = '',
) -> List[RequirementAtom]:
    agent_instruction = load_agent_instruction(instruction_md)
    system_prompt = f"""{EXTRACTION_SYSTEM_PROMPT}\n\n{get_profile_instruction(project_type)}\n\n{agent_instruction}""".strip()
    prompt = f'''
문서명: {chunk.source_file}
문서버전: {doc_info.version}
프로젝트유형: {project_type}
섹션: {' > '.join(chunk.section_path)}
제목: {chunk.title}
chunk_id: {chunk.chunk_id}

내용:
{chunk.text}
'''
    raw = invoke_bedrock(system_prompt=system_prompt, user_prompt=prompt, max_tokens=6000).strip()
    raw = clean_json_response(raw)
    try:
        items = safe_json_loads(raw, '요구사항')
    except json.JSONDecodeError:
        # JSON 복구는 Bedrock 유료 호출이지만, 파싱 안정성을 위해 토큰 제한을 걸지 않는다.
        items = repair_json_array(raw, '요구사항', max_tokens=4000)
    atoms = []
    for item in items:
        try:
            item.setdefault('biz_requirement_name', item.get('domain') or item.get('category') or '공통')
            item.setdefault('domain', item.get('biz_requirement_name') or '공통')
            atoms.append(RequirementAtom(**item, source_doc=chunk.source_file, source_chunk_id=chunk.chunk_id, source_section_path=chunk.section_path, raw_text=chunk.text, doc_key=doc_info.doc_key, doc_version=doc_info.version))
        except Exception as e:
            print(f'요구사항 item 변환 실패, skip: {e}')
    return atoms
