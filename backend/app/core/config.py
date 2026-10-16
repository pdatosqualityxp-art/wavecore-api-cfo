from pathlib import Path

from pydantic import Field, StrictStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: StrictStr
    supabase_service_role_key: StrictStr
    gemini_api_key: StrictStr
    cors_allowed_origins: list[StrictStr] = Field(default_factory=list)
    gemini_agent_model: StrictStr = "gemini-3.5-flash-lite"
    gemini_fallback_model: StrictStr = "gemini-3.8-flash"
    gemini_embedding_model: StrictStr = "gemini-embedding-001"

    @field_validator("cors_allowed_origins")
    @classmethod
    def reject_wildcard_cors_origin(
        cls, origins: list[str]
    ) -> list[str]:
        if "*" in origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must not contain '*'")
        return origins


settings = Settings()
