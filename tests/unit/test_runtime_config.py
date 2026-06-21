"""Unit tests for runtime configuration safety checks."""

import logging

import pytest

from src.qlib_research.app.config.runtime import get_cors_origins, validate_runtime_settings


def test_get_cors_origins_from_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com, https://admin.example.com")
    assert get_cors_origins() == ["https://app.example.com", "https://admin.example.com"]


def test_validate_runtime_settings_allows_development_defaults(monkeypatch):
    monkeypatch.setenv("FASTAPI_ENV", "development")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    validate_runtime_settings(logging.getLogger("test"))


def test_validate_runtime_settings_blocks_insecure_production_secret(monkeypatch):
    monkeypatch.setenv("FASTAPI_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "change-me-in-production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/qlib")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_runtime_settings(logging.getLogger("test"))


def test_validate_runtime_settings_blocks_sqlite_in_production(monkeypatch):
    monkeypatch.setenv("FASTAPI_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "super-secret-and-random-value")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/qlib_trading.db")

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        validate_runtime_settings(logging.getLogger("test"))

