# Backtest-Live Reconciliation Specification
# Ensure live trading matches backtest expectations

## Overview

Validate that live trading performance matches backtest simulation:
1. **Backtest baseline** — Historical benchmark
2. **Live metrics** — Current execution stats
3. **Reconciliation** — Compare and alert
4. **Root cause analysis** — Why divergence occurred
5. **Adjustment** — Tune model/config if needed

## Metrics Compared

```
Backtest (Historical)          Live (Current)
├─ Win rate: 52%     ←→ Win rate: 51%
├─ Sharpe: 1.4       ←→ Sharpe: 1.3
├─ Max DD: -8%       ←→ Max DD: -7.5%
├─ Trades/month: 25  ←→ Trades/month: 23
├─ Avg hold time: 5d ←→ Avg hold time: 6d
└─ Cost basis: 0.2%  ←→ Cost basis: 0.2%
```

## Reconciliation Engine

```python
# src/qlib_research/app/services/backtest_live_reconciliation.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger("qlib_trading.reconciliation")

@dataclass
class BacktestRun:
    """Historical backtest results"""
    model_name: str
    backtest_period: str        # "2023-01-01 to 2024-01-01"
    win_rate: float             # 0.52
    sharpe_ratio: float         # 1.4
    max_drawdown: float         # -0.08
    total_return: float         # 0.15
    avg_trade_duration: int     # days
    trades_per_month: float
    transaction_costs_pct: float
    
    generated_at: datetime = field(default_factory=datetime.now)

@dataclass
class LiveMetrics:
    """Current live trading stats"""
    start_date: datetime
    end_date: datetime
    
    # Cumulative stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Return stats
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    transaction_costs: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    
    # Trade stats
    avg_trade_duration: int = 0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    profit_factor: float = 0.0  # Gross wins / Gross losses
    
    # Current state
    open_positions: int = 0
    current_drawdown: float = 0.0
    portfolio_value: float = 100000.0

@dataclass
class ReconciliationResult:
    """Comparison between backtest and live"""
    
    backtest: BacktestRun
    live: LiveMetrics
    
    # Deltas (live - backtest)
    win_rate_delta: float = 0.0        # -0.02 = 2% worse
    sharpe_delta: float = 0.0          # -0.1
    max_dd_delta: float = 0.0          # -0.005 = 0.5% worse
    
    # Status
    is_aligned: bool = False           # Within tolerance?
    alerts: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    
    reconciled_at: datetime = field(default_factory=datetime.now)

class ReconciliationEngine:
    """Compare backtest to live trading"""
    
    def __init__(
        self,
        broker_service,
        backtest_storage_path: str = "~/mlruns/backtest_results",
        comparison_window_days: int = 30,
        tolerance_thresholds: dict = None
    ):
        self.broker = broker_service
        self.backtest_path = backtest_storage_path
        self.window_days = comparison_window_days
        
        # Tolerance for divergence (live slightly underperforms expected)
        self.thresholds = tolerance_thresholds or {
            "win_rate_delta": -0.05,      # Up to 5% lower
            "sharpe_delta": -0.15,        # Sharpe can drop 0.15
            "max_dd_delta": -0.03,        # Max DD can increase by 3%
            "trade_count_delta_pct": -0.2  # 20% fewer trades ok
        }
    
    async def reconcile(self) -> ReconciliationResult:
        """Run reconciliation"""
        
        logger.info("Starting backtest-live reconciliation...")
        
        try:
            # 1. Load latest backtest
            backtest = self._load_latest_backtest()
            
            if not backtest:
                logger.warning("No backtest baseline found")
                return ReconciliationResult(
                    backtest=None,
                    live=None,
                    alerts=["No baseline backtest to compare against"]
                )
            
            # 2. Calculate live metrics
            live = self._calculate_live_metrics()
            
            # 3. Compare
            result = self._compare(backtest, live)
            
            # 4. Generate alerts
            result = self._generate_alerts(result)
            
            logger.info(f"Reconciliation complete: aligned={result.is_aligned}")
            return result
            
        except Exception as e:
            logger.error(f"Reconciliation error: {e}")
            raise
    
    def _load_latest_backtest(self) -> Optional[BacktestRun]:
        """Load most recent backtest results"""
        
        import json
        from pathlib import Path
        
        backtest_dir = Path(self.backtest_path).expanduser()
        
        if not backtest_dir.exists():
            return None
        
        # Find latest backtest.json
        backtest_files = sorted(
            backtest_dir.glob("**/backtest.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not backtest_files:
            return None
        
        latest = backtest_files[0]
        
        with open(latest) as f:
            data = json.load(f)
        
        return BacktestRun(
            model_name=data.get("model_name", "unknown"),
            backtest_period=data.get("period", ""),
            win_rate=data.get("win_rate", 0.0),
            sharpe_ratio=data.get("sharpe_ratio", 0.0),
            max_drawdown=data.get("max_drawdown", 0.0),
            total_return=data.get("total_return", 0.0),
            avg_trade_duration=data.get("avg_hold_days", 5),
            trades_per_month=data.get("trades_per_month", 0.0),
            transaction_costs_pct=data.get("transaction_costs_pct", 0.002),
            generated_at=datetime.fromisoformat(
                data.get("generated_at", datetime.now().isoformat())
            )
        )
    
    def _calculate_live_metrics(self) -> LiveMetrics:
        """Calculate live trading stats"""
        
        now = datetime.now()
        start = now - timedelta(days=self.window_days)
        
        # Get all closed trades in window
        closed_trades = self.broker.get_closed_trades(
            start_date=start,
            end_date=now
        )
        
        # Get all open positions
        portfolio = self.broker.get_portfolio()
        open_positions = portfolio.positions
        
        # Calculate stats
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl <= 0]
        
        total_trades = len(closed_trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        gross_wins = sum(t.pnl for t in winning_trades)
        gross_losses = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0.0
        
        avg_winner = (gross_wins / len(winning_trades)) if winning_trades else 0.0
        avg_loser = (gross_losses / len(losing_trades)) if losing_trades else 0.0
        
        gross_pnl = gross_wins + gross_losses  # Losses are negative
        transaction_costs = total_trades * portfolio.total_market_value * 0.001  # ~0.1% per trade
        net_pnl = gross_pnl - transaction_costs
        
        # Sharpe (annualized)
        if closed_trades:
            returns = [t.pnl / portfolio.total_market_value for t in closed_trades]
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            
            if std_dev > 0:
                sharpe = (mean_return * 252) / (std_dev * (252 ** 0.5))
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0
        
        # Drawdown (simple: max loss from peak)
        cumulative_pnl = 0.0
        peak = 0.0
        max_drawdown = 0.0
        current_drawdown = 0.0
        
        for trade in sorted(closed_trades, key=lambda t: t.closed_at):
            cumulative_pnl += trade.pnl
            
            if cumulative_pnl > peak:
                peak = cumulative_pnl
                current_drawdown = 0.0
            else:
                current_drawdown = (cumulative_pnl - peak) / max(peak, 1.0)
                max_drawdown = min(max_drawdown, current_drawdown)
        
        avg_hold = (
            sum((t.closed_at - t.opened_at).days for t in closed_trades) / len(closed_trades)
            if closed_trades else 0
        )
        
        trades_per_month = total_trades / max(self.window_days / 30, 1)
        
        return LiveMetrics(
            start_date=start,
            end_date=now,
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            transaction_costs=transaction_costs,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown,
            avg_trade_duration=avg_hold,
            avg_winner=avg_winner,
            avg_loser=avg_loser,
            profit_factor=profit_factor,
            open_positions=len(open_positions),
            current_drawdown=current_drawdown,
            portfolio_value=portfolio.total_market_value + portfolio.cash_balance
        )
    
    def _compare(
        self,
        backtest: BacktestRun,
        live: LiveMetrics
    ) -> ReconciliationResult:
        """Compare backtest vs live"""
        
        result = ReconciliationResult(
            backtest=backtest,
            live=live,
            win_rate_delta=live.win_rate - backtest.win_rate,
            sharpe_delta=live.sharpe_ratio - backtest.sharpe_ratio,
            max_dd_delta=live.max_drawdown - backtest.max_drawdown
        )
        
        # Check if within tolerance
        is_aligned = (
            result.win_rate_delta >= self.thresholds["win_rate_delta"] and
            result.sharpe_delta >= self.thresholds["sharpe_delta"] and
            result.max_dd_delta >= self.thresholds["max_dd_delta"]
        )
        
        result.is_aligned = is_aligned
        
        return result
    
    def _generate_alerts(
        self,
        result: ReconciliationResult
    ) -> ReconciliationResult:
        """Generate alerts for divergence"""
        
        alerts = []
        recommendations = []
        
        # Win rate divergence
        if result.win_rate_delta < self.thresholds["win_rate_delta"]:
            delta_pct = result.win_rate_delta * 100
            alerts.append(
                f"Win rate {delta_pct:.1f}% below backtest "
                f"({result.live.win_rate:.0%} vs {result.backtest.win_rate:.0%})"
            )
            recommendations.append(
                "Check for market regime change or model degradation"
            )
        
        # Sharpe divergence
        if result.sharpe_delta < self.thresholds["sharpe_delta"]:
            alerts.append(
                f"Sharpe ratio {result.sharpe_delta:.2f} below backtest "
                f"({result.live.sharpe_ratio:.2f} vs {result.backtest.sharpe_ratio:.2f})"
            )
            recommendations.append(
                "Consider retraining model or adjusting signal confidence thresholds"
            )
        
        # Drawdown divergence
        if result.max_dd_delta < self.thresholds["max_dd_delta"]:
            delta_pct = result.max_dd_delta * 100
            alerts.append(
                f"Max drawdown {delta_pct:.1f}% worse than backtest "
                f"({result.live.max_drawdown:.0%} vs {result.backtest.max_drawdown:.0%})"
            )
            recommendations.append(
                "Reduce position size or add stop-loss protection"
            )
        
        # Trade count divergence
        expected_trades = result.backtest.trades_per_month * (result.live.start_date - result.live.end_date).days / 30
        trade_delta_pct = (result.live.total_trades - expected_trades) / max(expected_trades, 1)
        
        if trade_delta_pct < self.thresholds["trade_count_delta_pct"]:
            alerts.append(
                f"Trade frequency {trade_delta_pct:.0%} below backtest "
                f"({result.live.total_trades} vs {expected_trades:.0f} expected)"
            )
            recommendations.append(
                "Check signal generation frequency or data freshness"
            )
        
        # Profit factor
        if result.live.profit_factor < 1.0:
            alerts.append("Profit factor below 1.0 (losing money overall)")
            recommendations.append("Halt trading and investigate root cause")
        
        result.alerts = alerts
        result.recommendations = recommendations
        
        if alerts:
            logger.warning(f"Reconciliation alerts: {len(alerts)} issues found")
            for alert in alerts:
                logger.warning(f"  - {alert}")
        
        return result
```

## API Endpoint

```python
# src/qlib_research/app/api/routes/monitoring.py

@router.get("/reconciliation")
async def get_reconciliation(
    engine=Depends(get_reconciliation_engine)
) -> dict:
    """Run backtest-live reconciliation"""
    
    result = await engine.reconcile()
    
    return {
        "reconciled_at": result.reconciled_at.isoformat(),
        "is_aligned": result.is_aligned,
        "deltas": {
            "win_rate": f"{result.win_rate_delta:+.1%}",
            "sharpe": f"{result.sharpe_delta:+.2f}",
            "max_drawdown": f"{result.max_dd_delta:+.1%}"
        },
        "alerts": result.alerts,
        "recommendations": result.recommendations,
        "backtest": {
            "model": result.backtest.model_name,
            "period": result.backtest.backtest_period,
            "win_rate": f"{result.backtest.win_rate:.1%}",
            "sharpe": f"{result.backtest.sharpe_ratio:.2f}"
        },
        "live": {
            "period": f"{result.live.start_date.date()} to {result.live.end_date.date()}",
            "trades": result.live.total_trades,
            "win_rate": f"{result.live.win_rate:.1%}",
            "sharpe": f"{result.live.sharpe_ratio:.2f}",
            "pnl": f"${result.live.net_pnl:,.0f}"
        }
    }
```

## Acceptance Criteria

- [ ] Load latest backtest results from MLflow
- [ ] Calculate live trading metrics (win rate, Sharpe, DD)
- [ ] Compare backtest vs live with configurable tolerance
- [ ] Generate alerts for significant divergence
- [ ] Provide root cause recommendations
- [ ] API endpoint working
- [ ] Scheduled reconciliation (daily)
- [ ] Audit trail of all reconciliations
- [ ] Tests pass

## Known Limitations (MVP)

- Simple max drawdown (no underwater plot)
- No market regime detection
- No automatic model retraining
- No feedback loop to adjust thresholds
