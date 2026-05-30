from typing import List
from pydantic import BaseModel, Field


class SemanticChunk(BaseModel):
    chunk_id: str
    doc_id: str
    source_file: str
    section_path: List[str]
    title: str
    text: str


class RequirementAtom(BaseModel):
    requirement_id: str = ""
    category: str = Field(default="기능")
    requirement_name: str = ""
    requirement_type: str = Field(default="기능요구사항")
    domain: str = ""
    feature: str = ""
    description: str = ""
    note: str = ""
    source_doc: str = ""
    source_chunk_id: str = ""
    source_section_path: List[str] = []
    raw_text: str = ""


class WBSItem(BaseModel):
    level: str = ""
    wbs_name: str = ""
    start_date: str = ""
    end_date: str = ""
    assignee: str = ""
    deliverable: str = ""
