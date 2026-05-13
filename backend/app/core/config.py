from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    project_name: str = "Travel Agent Onboarding Hub"
    environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://username:password@localhost:5432/"
        "travel_agent_onboarding_hub"
    )
    jwt_secret_key: str = "change-this-before-real-use"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    frontend_url: str = "http://localhost:5173"
    upload_dir: Path = BACKEND_DIR / "uploads"
    max_upload_size_mb: int = 10
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    @property
    def cors_allowed_origins(self) -> list[str]:
        origins = {
            self.frontend_url,
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        }
        return sorted(origin for origin in origins if origin)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
