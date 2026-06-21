"""Backtest-live reconciliation helpers for Phase 3 broker readiness."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.qlib_research.app.services.broker_adapter import BrokerAdapter


class BrokerReconciliationService:
    """Compute and persist lightweight reconciliation snapshots."""

    def __init__(self) -> None:
        mlruns_path = Path(os.getenv("MLRUNS_PATH", "./mlruns"))
        self._runs_dir = mlruns_path / "runs"
        self._audit_dir = mlruns_path / "reconciliation"
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._comparison_window_days = int(os.getenv("PHASE3_RECONCILIATION_WINDOW_DAYS", "30"))
        self._thresholds = {
            "win_rate_delta": float(os.getenv("PHASE3_RECONCILIATION_WIN_RATE_DELTA", "-0.05")),
            "sharpe_delta": float(os.getenv("PHASE3_RECONCILIATION_SHARPE_DELTA", "-0.15")),
            "total_return_delta": float(os.getenv("PHASE3_RECONCILIATION_RETURN_DELTA", "-0.10")),
        }

    def _load_latest_backtest_baseline(self) -> Optional[Dict[str, Any]]:
        if not self._runs_dir.exists():
            return None
        for run_file in sorted(self._runs_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True):
            payload = json.loads(run_file.read_text(encoding="utf-8"))
            backtest = payload.get("backtest")
            if not isinstance(backtest, dict):
                continue
            metrics = payload.get("metrics", {})
            return {
                "model_id": payload.get("model_id"),
                "trained_at": payload.get("created_at"),
                "ticker": payload.get("ticker"),
                "win_rate": float(metrics.get("accuracy", 0.0) or 0.0),
                "sharpe_ratio": float(backtest.get("sharpe_ratio", 0.0) or 0.0),
                "total_return": float(backtest.get("total_return", 0.0) or 0.0),
                "max_drawdown": float(backtest.get("max_drawdown", 0.0) or 0.0),
            }
        return None

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _build_live_metrics(self, broker: BrokerAdapter, user_id: int) -> Dict[str, Any]:
        account = broker.get_account_snapshot(user_id=user_id)
        now = datetime.utcnow()
        window_start = now - timedelta(days=self._comparison_window_days)
        trades = broker.get_trades(user_id=user_id)

        window_trades = []
        for trade in trades:
            executed_at = getattr(trade, "executed_at", None)
            if executed_at is None or executed_at < window_start:
                continue
            window_trades.append(trade)

        pnl_values = [self._float(getattr(trade, "gross_pnl", 0.0), 0.0) for trade in window_trades]
        total_trades = len(window_trades)
        winning = len([pnl for pnl in pnl_values if pnl > 0.0])
        returns = []
        portfolio_value = max(self._float(account.get("portfolio_value"), 0.0), 1.0)
        for pnl in pnl_values:
            returns.append(pnl / portfolio_value)

        mean_return = (sum(returns) / len(returns)) if returns else 0.0
        variance = (sum((r - mean_return) ** 2 for r in returns) / len(returns)) if returns else 0.0
        std_dev = variance ** 0.5
        sharpe = ((mean_return * 252) / (std_dev * (252**0.5))) if std_dev > 0 else 0.0
        total_return = sum(returns)

        return {
            "period_start": window_start.date().isoformat(),
            "period_end": now.date().isoformat(),
            "total_trades": total_trades,
            "winning_trades": winning,
            "win_rate": (winning / total_trades) if total_trades else 0.0,
            "sharpe_ratio": sharpe,
            "total_return": total_return,
            "gross_pnl": sum(pnl_values),
            "portfolio_value": self._float(account.get("portfolio_value"), 0.0),
            "cash": self._float(account.get("cash"), 0.0),
            "open_positions": int(account.get("open_positions", 0) or 0),
            "source": str(account.get("source", "unknown")),
        }

    def _build_alerts(self, deltas: Dict[str, float]) -> List[str]:
        alerts: List[str] = []
        if deltas["win_rate"] < self._thresholds["win_rate_delta"]:
            alerts.append("Live win rate is below backtest tolerance.")
        if deltas["sharpe_ratio"] < self._thresholds["sharpe_delta"]:
            alerts.append("Live Sharpe ratio is below backtest tolerance.")
        if deltas["total_return"] < self._thresholds["total_return_delta"]:
            alerts.append("Live total return is below backtest tolerance.")
        return alerts

    def _persist_result(self, result: Dict[str, Any], user_id: int) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        output = self._audit_dir / f"reconciliation_{user_id}_{timestamp}.json"
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    def reconcile(self, broker: BrokerAdapter, user_id: int) -> Dict[str, Any]:
        baseline = self._load_latest_backtest_baseline()
        if baseline is None:
            result = {
                "reconciled_at": datetime.utcnow().isoformat(),
                "status": "baseline_missing",
                "is_aligned": False,
                "alerts": ["No backtest baseline found in mlruns/runs."],
                "recommendations": ["Run at least one training/backtest flow before reconciliation."],
                "backtest": None,
                "live": self._build_live_metrics(broker, user_id),
                "deltas": None,
            }
            self._persist_result(result, user_id=user_id)
            return result

        live = self._build_live_metrics(broker, user_id)
        deltas = {
            "win_rate": live["win_rate"] - baseline["win_rate"],
            "sharpe_ratio": live["sharpe_ratio"] - baseline["sharpe_ratio"],
            "total_return": live["total_return"] - baseline["total_return"],
        }
        alerts = self._build_alerts(deltas)
        result = {
            "reconciled_at": datetime.utcnow().isoformat(),
            "status": "ok",
            "is_aligned": len(alerts) == 0,
            "alerts": alerts,
            "recommendations": (
                []
                if not alerts
                else ["Review strategy assumptions, market regime, and risk controls before enabling automation."]
            ),
            "backtest": baseline,
            "live": live,
            "deltas": deltas,
        }
        self._persist_result(result, user_id=user_id)
        return result

    def list_recent(self, limit: int = 20) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        for path in sorted(self._audit_dir.glob("reconciliation_*.json"), reverse=True)[: max(limit, 1)]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["artifact"] = path.name
            results.append(payload)
        return {"count": len(results), "results": results}
