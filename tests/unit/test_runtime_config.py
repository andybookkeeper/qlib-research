"""Unit tests for runtime configuration safety checks."""

import logging

import pytest

from src.qlib_research.app.config.runtime import (
    get_cors_origins,
    get_phase3_feature_flags,
    get_phase3_scope_stage,
    validate_runtime_settings,
)


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


def test_phase3_feature_flags_default_safe(monkeypatch):
    monkeypatch.delenv("PHASE3_ENABLE_LIVE_BROKER_ADAPTER", raising=False)
    monkeypatch.delenv("PHASE3_ENABLE_BROKER_RECONCILIATION", raising=False)
    monkeypatch.delenv("PHASE3_ENABLE_STRATEGY_AUTOMATION", raising=False)
    monkeypatch.delenv("PHASE3_ENFORCE_MANUAL_TRADE_CONFIRMATION", raising=False)
    flags = get_phase3_feature_flags()
    assert flags["enable_live_broker_adapter"] is False
    assert flags["enable_broker_reconciliation"] is False
    assert flags["enable_strategy_automation"] is False
    assert flags["enforce_manual_trade_confirmation"] is True


def test_phase3_scope_stage(monkeypatch):
    monkeypatch.setenv("PHASE3_SCOPE_STAGE", "pilot")
    assert get_phase3_scope_stage() == "pilot"


def test_production_live_adapter_requires_live_trading_enabled(monkeypatch):
    monkeypatch.setenv("FASTAPI_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "super-secret-and-random-value")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/qlib")
    monkeypatch.setenv("PHASE3_ENABLE_LIVE_BROKER_ADAPTER", "true")
    monkeypatch.setenv("ENABLE_LIVE_TRADING", "false")
    with pytest.raises(RuntimeError, match="ENABLE_LIVE_TRADING"):
        validate_runtime_settings(logging.getLogger("test"))
