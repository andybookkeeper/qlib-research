"""Unit tests for reconciliation scheduler."""

import asyncio

from src.qlib_research.app.services.reconciliation_scheduler import ReconciliationScheduler


def test_scheduler_skips_when_feature_disabled(monkeypatch):
    monkeypatch.setenv("PHASE3_ENABLE_BROKER_RECONCILIATION", "false")
    scheduler = ReconciliationScheduler()
    result = asyncio.run(scheduler._run_once())

    assert result["status"] == "skipped"
    assert result["reason"] == "feature_disabled"
