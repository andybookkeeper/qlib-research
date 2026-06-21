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


def _parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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


def get_phase3_feature_flags() -> dict[str, bool]:
    """Resolve Phase 3 feature flags with safe defaults."""
    return {
        "enable_live_broker_adapter": _parse_bool(os.getenv("PHASE3_ENABLE_LIVE_BROKER_ADAPTER"), False),
        "enable_broker_reconciliation": _parse_bool(os.getenv("PHASE3_ENABLE_BROKER_RECONCILIATION"), False),
        "enable_strategy_automation": _parse_bool(os.getenv("PHASE3_ENABLE_STRATEGY_AUTOMATION"), False),
        "enforce_manual_trade_confirmation": _parse_bool(
            os.getenv("PHASE3_ENFORCE_MANUAL_TRADE_CONFIRMATION"), True
        ),
    }


def get_phase3_scope_stage() -> str:
    """Resolve Phase 3 rollout stage label."""
    return os.getenv("PHASE3_SCOPE_STAGE", "kickoff").strip().lower()


def validate_runtime_settings(logger: logging.Logger) -> None:
    """Validate required production settings and log effective runtime mode."""
    env = get_runtime_env()
    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/qlib_trading.db")
    secret_key = os.getenv("SECRET_KEY", "").strip()
    cors_origins = get_cors_origins()
    phase3_flags = get_phase3_feature_flags()

    logger.info("[CONFIG] Environment: %s", env)
    logger.info("[CONFIG] CORS origins: %s", ",".join(cors_origins))
    logger.info("[CONFIG] Phase 3 flags: %s", phase3_flags)

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
    if phase3_flags["enable_live_broker_adapter"] and not _parse_bool(os.getenv("ENABLE_LIVE_TRADING"), False):
        raise RuntimeError(
            "ENABLE_LIVE_TRADING must be true when PHASE3_ENABLE_LIVE_BROKER_ADAPTER is enabled."
        )
