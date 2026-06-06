from pathlib import Path
from typing import Optional


def load_agent_instruction(path: Optional[str]) -> str:
    if not path:
        return ''
    p = Path(path)
    if not p.exists():
        return ''
    return p.read_text(encoding='utf-8').strip()
