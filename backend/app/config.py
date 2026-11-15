"""Configuration for the local MARSIGHT API service.

Secrets come from the process environment. Uvicorn can load the repository's
ignored .env file with its --env-file option during local development.
"""

from dataclasses import dataclass
import os


DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    allowed_origins: list[str]
    claude_enabled: bool
    claude_project_cap_usd: int
    anthropic_api_key_configured: bool


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    origins = os.getenv("MARSIGHT_ALLOWED_ORIGINS", DEFAULT_ORIGINS)
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    return Settings(
        app_name="MARSIGHT Platform API",
        app_version="0.1.0",
        allowed_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        # AI stays off until a later, deliberate implementation and review.
        claude_enabled=_as_bool(os.getenv("MARSIGHT_CLAUDE_ENABLED", "false")),
        claude_project_cap_usd=int(os.getenv("MARSIGHT_CLAUDE_PROJECT_CAP_USD", "25")),
        anthropic_api_key_configured=bool(api_key),
    )
