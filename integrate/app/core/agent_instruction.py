from pathlib import Path


def load_agent_instruction(agent_file: str, md_filename: str = 'AGENT.md') -> str:
    """agent.py와 같은 폴더의 AGENT.md 내용을 읽는다.

    Agent별 역할/규칙은 코드가 아니라 Markdown으로 관리한다.
    파일이 없으면 빈 문자열을 반환해 기존 실행을 막지 않는다.
    """
    md_path = Path(agent_file).resolve().parent / md_filename
    if not md_path.exists():
        return ''
    return md_path.read_text(encoding='utf-8').strip()
