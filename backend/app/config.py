"""Settings read from environment variables (or a local .env file)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    mongodb_uri: str = ""                 # empty -> auth endpoints report "database not configured"
    mongodb_db: str = "pathpilot"
    jwt_secret: str = ""                  # required for auth; empty disables token signing
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # one week
    cors_origins: str = "http://localhost:5173"  # comma-separated

    @property
    def cors_origin_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings():
    return Settings()
