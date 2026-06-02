import json
from typing import List

from app.core.agent_instruction import load_agent_instruction
from app.core.bedrock_client import invoke_bedrock
from app.core.json_utils import clean_json_response, repair_json_array, safe_json_loads
from app.schemas.artifact import RequirementAtom, SemanticChunk
from app.storage.version_manager import DocumentVersionInfo


BASE_SYSTEM_PROMPT = '너는 PM Agent의 구축요건정의서 분석기다.'


def system_prompt() -> str:
    guide = load_agent_instruction(__file__)
    return f'{BASE_SYSTEM_PROMPT}\n\n{guide}'.strip()


def extract_requirement_atoms(chunk: SemanticChunk, doc_info: DocumentVersionInfo) -> List[RequirementAtom]:
    prompt = f'''
문서명: {chunk.source_file}
문서버전: {doc_info.version}
섹션: {' > '.join(chunk.section_path)}
제목: {chunk.title}
chunk_id: {chunk.chunk_id}

내용:
{chunk.text}
'''
    raw = invoke_bedrock(system_prompt=system_prompt(), user_prompt=prompt, max_tokens=6000).strip()
    raw = clean_json_response(raw)
    try:
        items = safe_json_loads(raw, '요구사항')
    except json.JSONDecodeError:
        items = repair_json_array(raw, '요구사항', max_tokens=4000)

    atoms = []
    for item in items:
        try:
            atoms.append(
                RequirementAtom(
                    **item,
                    source_doc=chunk.source_file,
                    source_chunk_id=chunk.chunk_id,
                    source_section_path=chunk.section_path,
                    raw_text=chunk.text,
                    doc_key=doc_info.doc_key,
                    doc_version=doc_info.version,
                )
            )
        except Exception as e:
            print(f'요구사항 item 변환 실패, skip: {e}')
    return atoms
