# EN: Shared document, artifact, template, and generation flow schemas.
# KO: 문서, 산출물, 템플릿, 생성 흐름에 대한 공통 스키마입니다.

from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    CONSTRUCTION_REQUIREMENT_DEFINITION = "CONSTRUCTION_REQUIREMENT_DEFINITION"
    REQUIREMENT_SPEC = "REQUIREMENT_SPEC"
    MEETING_NOTES = "MEETING_NOTES"
    UNKNOWN = "UNKNOWN"


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PARSED = "PARSED"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class ArtifactStatus(StrEnum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    EXPORTED = "EXPORTED"
    FAILED = "FAILED"


class ArtifactType(StrEnum):
    REQUIREMENT_SPEC = "REQUIREMENT_SPEC"
    SCREEN_DESIGN = "SCREEN_DESIGN"
    WBS = "WBS"
    ACTION_ITEMS = "ACTION_ITEMS"


class TemplateReference(BaseModel):
    template_id: Optional[str] = Field(
        None,
        description="Template ID from admin UI or built-in template registry",
    )
    template_version: Optional[str] = Field(
        None,
        description="Template version to use for generation",
    )


class GenerationFlow(BaseModel):
    source_document_type: Optional[DocumentType] = Field(
        None,
        description="Type of source document used to generate the artifact",
    )
    target_artifact_type: ArtifactType = Field(
        ...,
        description="Type of artifact to generate",
    )
    template: TemplateReference = Field(
        default_factory=TemplateReference,
        description="Template selection for the generated artifact",
    )


class DocumentMetadata(BaseModel):
    document_id: str = Field(..., description="Document ID")
    project_id: str = Field(..., description="Project ID")
    document_type: DocumentType = Field(..., description="Uploaded document type")
    file_name: str = Field(..., description="Original uploaded file name")
    storage_path: str = Field(..., description="Object storage path")
    status: DocumentStatus = Field(
        DocumentStatus.UPLOADED,
        description="Current document processing status",
    )


class ArtifactMetadata(BaseModel):
    artifact_id: str = Field(..., description="Artifact ID")
    project_id: str = Field(..., description="Project ID")
    artifact_type: ArtifactType = Field(..., description="Generated artifact type")
    name: str = Field(..., description="Artifact display name")
    version: int = Field(1, description="Artifact version")
    source_document_ids: list[str] = Field(
        default_factory=list,
        description="Source document IDs used to generate the artifact",
    )
    template_id: Optional[str] = Field(None, description="Template ID")
    template_version: Optional[str] = Field(None, description="Template version")
    result_json: dict = Field(default_factory=dict, description="Artifact result JSON")
    storage_path: Optional[str] = Field(None, description="Exported artifact path")
    status: ArtifactStatus = Field(
        ArtifactStatus.CREATED,
        description="Current artifact status",
    )


# PM artifact generation schemas
# 기존 app/schemas/pm_artifacts.py의 모델을 backend 표준 artifact schema에 통합했습니다.
class SemanticChunk(BaseModel):
    chunk_id: str
    doc_id: str
    source_file: str
    section_path: List[str]
    title: str
    text: str


class RequirementAtom(BaseModel):
    requirement_id: str = ''
    category: str = Field(default='기능')
    requirement_name: str = ''
    requirement_type: str = Field(default='기능요구사항')
    domain: str = ''
    feature: str = ''
    description: str = ''
    note: str = ''
    source_doc: str = ''
    source_chunk_id: str = ''
    source_section_path: List[str] = []
    raw_text: str = ''
    doc_key: str = ''
    doc_version: str = ''


class WBSItem(BaseModel):
    level: str = ''
    wbs_name: str = ''
    start_date: str = ''
    end_date: str = ''
    assignee: str = ''
    deliverable: str = ''


class ScreenDisplayItem(BaseModel):
    item_name: str = ''
    description: str = ''


class ScreenPlanItem(BaseModel):
    requirement_id: str = ''
    screen_id: str = ''
    screen_no: str = ''
    screen_name: str = ''
    screen_summary: str = ''
    display_items: List[ScreenDisplayItem] = []
