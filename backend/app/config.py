"""Application configuration."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.db.url import normalize_database_url

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://USER:PASSWORD@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require"
    )
    db_schema: str = "benchmarking"
    google_api_key: str = ""
    llm_model: str = "gemini-2.5-pro"
    cors_origins: str = "http://localhost:3000"
    cors_origin_regex: str = ""
    edit_password: str = ""
    session_secret: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value


settings = Settings()
