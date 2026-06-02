# EN: Application configuration loaded from environment variables.
# KO: 환경 변수에서 로드되는 애플리케이션 설정입니다.

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 앱
    APP_ENV: str = "development"
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # AWS
    AWS_REGION: str = "ap-northeast-2"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # S3
    S3_BUCKET_NAME: str = "kbds-s3-finpm"
    S3_UPLOAD_PREFIX: str = "storage/upload_files"
    S3_TEMPLATE_PREFIX: str = "storage/template_files"
    S3_GENERATED_PREFIX: str = "storage/generated_files"

    # Bedrock
    BEDROCK_MODEL_ID: str = "anthropic.claude-sonnet-4-5"


    # PM artifact generation / RAG integration
    # 기존 분리 파일(app/core/pm_config.py)의 설정을 backend 표준 config로 흡수했습니다.
    MODEL_ID: str = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "pm_requirement_atoms"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    CHUNK_MAX_CHARS: int = 1200
    CHUNK_OVERLAP_CHARS: int = 150
    WBS_BATCH_SIZE: int = 10
    SCREEN_BATCH_SIZE: int = 10
    BEDROCK_READ_TIMEOUT: int = 300
    RECREATE_COLLECTION: bool = False
    PROJECT_NAME: str = "프로젝트명"
    AUTHOR_NAME: str = "작성자"
    REQUIREMENT_TEMPLATE_PATH: str = "template/탬플릿_요구사항명세서.xlsx"
    WBS_TEMPLATE_PATH: str = "template/탬플릿_WBS.xlsx"
    SCREEN_TEMPLATE_PATH: str = "template/탬플릿_화면설계서.pptx"
    OUTPUT_MAPPER_PATH: str = "template/output_mapper.json"

    # DB (Aurora PostgreSQL)
    DATABASE_URL: str = "sqlite+aiosqlite:///./finpm.db"  # 로컬 개발용 SQLite

    # Vector Store
    VECTOR_STORE_TYPE: str = "chroma"  # chroma | pgvector | opensearch

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: object) -> object:
        if isinstance(value, str) and value.lower() in {
            "release",
            "prod",
            "production",
        }:
            return False

        return value


settings = Settings()


# PM artifact generation compatibility aliases
# 기존 pm_config.py에 있던 상수를 backend 표준 Settings에서 노출합니다.
AWS_REGION = settings.AWS_REGION
MODEL_ID = settings.MODEL_ID
QDRANT_URL = settings.QDRANT_URL
QDRANT_COLLECTION = settings.QDRANT_COLLECTION
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
CHUNK_MAX_CHARS = settings.CHUNK_MAX_CHARS
CHUNK_OVERLAP_CHARS = settings.CHUNK_OVERLAP_CHARS
WBS_BATCH_SIZE = settings.WBS_BATCH_SIZE
SCREEN_BATCH_SIZE = settings.SCREEN_BATCH_SIZE
BEDROCK_READ_TIMEOUT = settings.BEDROCK_READ_TIMEOUT
RECREATE_COLLECTION = settings.RECREATE_COLLECTION
PROJECT_NAME = settings.PROJECT_NAME
AUTHOR_NAME = settings.AUTHOR_NAME
REQUIREMENT_TEMPLATE_PATH = settings.REQUIREMENT_TEMPLATE_PATH
WBS_TEMPLATE_PATH = settings.WBS_TEMPLATE_PATH
SCREEN_TEMPLATE_PATH = settings.SCREEN_TEMPLATE_PATH
OUTPUT_MAPPER_PATH = settings.OUTPUT_MAPPER_PATH
