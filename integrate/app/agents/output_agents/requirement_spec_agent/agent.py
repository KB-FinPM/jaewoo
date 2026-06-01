from typing import Any, Dict, List

from app.core.agent_instruction import load_agent_instruction
from app.storage.excel_writer import save_requirement_excel


class RequirementSpecOutputAgent:
    """요구사항명세서 Excel 산출물 생성 Agent."""

    def __init__(self):
        self.instruction = load_agent_instruction(__file__)

    def run(self, atoms: List[Any], template_path: str, output_path: str, project_name: str, author: str, mapper: Dict[str, Any]):
        save_requirement_excel(
            atoms=atoms,
            template_path=template_path,
            output_path=output_path,
            project_name=project_name,
            author=author,
            mapper=mapper,
        )
        return output_path
