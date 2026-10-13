from pathlib import Path

from pydantic import StrictStr
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


settings = Settings()
