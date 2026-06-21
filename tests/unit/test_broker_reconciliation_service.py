"""Unit tests for broker reconciliation service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from src.qlib_research.app.services.broker_reconciliation_service import BrokerReconciliationService


@dataclass
class _Trade:
    gross_pnl: float
    executed_at: datetime


class _StubBroker:
    def __init__(self, trades):
        self._trades = trades

    def get_account_snapshot(self, user_id=None):
        return {
            "portfolio_value": 100000.0,
            "cash": 25000.0,
            "open_positions": 2,
            "source": "paper",
        }

    def get_trades(self, user_id=None):
        return list(self._trades)


def test_reconciliation_returns_baseline_missing_without_backtest(monkeypatch, tmp_path):
    monkeypatch.setenv("MLRUNS_PATH", str(tmp_path))
    service = BrokerReconciliationService()
    result = service.reconcile(broker=_StubBroker([]), user_id=1)

    assert result["status"] == "baseline_missing"
    assert result["backtest"] is None
    assert result["is_aligned"] is False


def test_reconciliation_compares_against_latest_backtest(monkeypatch, tmp_path):
    monkeypatch.setenv("MLRUNS_PATH", str(tmp_path))
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_payload = {
        "model_id": "m1",
        "created_at": datetime.utcnow().isoformat(),
        "ticker": "AAPL",
        "metrics": {"accuracy": 0.60},
        "backtest": {"sharpe_ratio": 1.2, "total_return": 0.15, "max_drawdown": -0.08},
    }
    (runs_dir / "run_1.json").write_text(json.dumps(run_payload), encoding="utf-8")

    trades = [
        _Trade(gross_pnl=100.0, executed_at=datetime.utcnow()),
        _Trade(gross_pnl=-50.0, executed_at=datetime.utcnow()),
    ]
    service = BrokerReconciliationService()
    result = service.reconcile(broker=_StubBroker(trades), user_id=2)

    assert result["status"] == "ok"
    assert result["backtest"]["model_id"] == "m1"
    assert "win_rate" in result["deltas"]
    assert "sharpe_ratio" in result["deltas"]
    assert "total_return" in result["deltas"]
