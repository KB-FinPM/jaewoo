from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.core.pm_config import AUTHOR_NAME, OUTPUT_MAPPER_PATH, PROJECT_NAME, RECREATE_COLLECTION
from app.orchestrator.pm_pipeline import run_pipeline

router = APIRouter()


class PMArtifactGenerationRequest(BaseModel):
    docx_path: str | None = Field(default=None, description="분석할 DOCX 경로. None이면 input/구축요건정의서.v.#.docx 중 최신 버전 사용")
    output_dir: str = "output"
    recreate_collection: bool = RECREATE_COLLECTION
    project_name: str = PROJECT_NAME
    author: str = AUTHOR_NAME
    mapper_path: str = OUTPUT_MAPPER_PATH
    process_path: str = "process.json"


@router.post("/pm-artifacts")
def generate_pm_artifacts(request: PMArtifactGenerationRequest):
    generated = run_pipeline(
        docx_path=request.docx_path,
        output_dir=request.output_dir,
        recreate_collection=request.recreate_collection,
        project_name=request.project_name,
        author=request.author,
        mapper_path=request.mapper_path,
        process_path=request.process_path,
    )
    return {"success": True, "generated": generated}
