from typing import Any, Dict, List

from app.core.agent_instruction import load_agent_instruction
from app.storage.excel_writer import save_wbs_excel


class WBSOutputAgent:
    """WBS Excel 산출물 생성 Agent."""

    def __init__(self):
        self.instruction = load_agent_instruction(__file__)

    def run(self, items: List[Any], template_path: str, output_path: str, mapper: Dict[str, Any]):
        save_wbs_excel(
            items=items,
            template_path=template_path,
            output_path=output_path,
            mapper=mapper,
        )
        return output_path
