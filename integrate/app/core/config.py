# EN: Application configuration loaded from environment variables.
# KO: 환경 변수에서 로드되는 애플리케이션 설정입니다.

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):

    model_id: str = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "pm_requirement_atoms"
    embedding_model: str = "BAAI/bge-m3"

    chunk_max_chars: int = 1200
    chunk_overlap_chars: int = 150

    wbs_batch_size: int = 10
    screen_batch_size: int = 10

    bedrock_read_timeout: int = 300
    recreate_collection: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

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
