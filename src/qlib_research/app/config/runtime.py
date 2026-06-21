"""Runtime environment configuration and safety checks."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

load_dotenv()

_PRODUCTION_ENVS = {"production", "prod"}
_INSECURE_SECRET_VALUES = {
    "",
    "change-me-in-production",
    "your-secret-key-change-this-in-production",
}
_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]


def get_runtime_env() -> str:
    """Resolve runtime environment value."""
    return os.getenv("FASTAPI_ENV", "development").strip().lower()


def get_cors_origins() -> list[str]:
    """Parse CORS origins from environment."""
    raw_value = os.getenv("CORS_ORIGINS")
    if raw_value is None:
        return list(_DEFAULT_CORS_ORIGINS)
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    if origins:
        return origins
    return list(_DEFAULT_CORS_ORIGINS)


def validate_runtime_settings(logger: logging.Logger) -> None:
    """Validate required production settings and log effective runtime mode."""
    env = get_runtime_env()
    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/qlib_trading.db")
    secret_key = os.getenv("SECRET_KEY", "").strip()
    cors_origins = get_cors_origins()

    logger.info("[CONFIG] Environment: %s", env)
    logger.info("[CONFIG] CORS origins: %s", ",".join(cors_origins))

    if env not in _PRODUCTION_ENVS:
        return

    if secret_key in _INSECURE_SECRET_VALUES:
        raise RuntimeError(
            "SECRET_KEY must be set to a strong non-default value in production."
        )
    if database_url.startswith("sqlite"):
        raise RuntimeError(
            "DATABASE_URL must use PostgreSQL in production (SQLite is development-only)."
        )
    if not cors_origins:
        raise RuntimeError("CORS_ORIGINS must contain at least one allowed origin in production.")

