from pathlib import Path
from typing import Any, Dict, List

from app.core.agent_instruction import load_agent_instruction


class MarkdownSummaryAgent:
    """분석 결과 요약 Markdown을 생성하는 출력 Agent."""

    def __init__(self):
        self.instruction = load_agent_instruction(__file__)

    def run(self, output_path: str, project_name: str, core_data: Dict[str, Any]):
        requirements: List[Any] = core_data.get('requirements', []) or []
        wbs_items: List[Any] = core_data.get('wbs_items', []) or []
        screen_items: List[Any] = core_data.get('screen_items', []) or []

        lines = [
            f'# {project_name} 분석 요약',
            '',
            f'- 요구사항: {len(requirements)}건',
            f'- WBS: {len(wbs_items)}건',
            f'- 화면기획: {len(screen_items)}건',
            '',
            '## 요구사항 목록',
        ]
        for atom in requirements[:50]:
            lines.append(f'- {getattr(atom, "requirement_id", "")}: {getattr(atom, "requirement_name", "")}')

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text('\n'.join(lines), encoding='utf-8')
