# Signal-to-Trade Bridge Specification
# Connect Qlib signals to paper trading execution

## Overview

The signal-to-trade bridge:
1. **Polls Qlib signals** — Daily signal generation from trained models
2. **Validates signals** — Check signal quality, timing
3. **Maps to trades** — Convert signal to order with sizing
4. **Executes** — Submit to paper broker with safeguards
5. **Tracks** — Link signal to trade for analysis

## Architecture

```
Qlib Models (Signals)
         ↓
┌──────────────────────────────┐
│ Signal Validator             │ ← Check confidence, timing
└──────────────────────────────┘
         ↓
┌──────────────────────────────┐
│ Position Sizer               │ ← Determine qty based on Kelly/fixed%
└──────────────────────────────┘
         ↓
┌──────────────────────────────┐
│ Order Factory                │ ← Create OrderRequest
└──────────────────────────────┘
         ↓
┌──────────────────────────────┐
│ Risk Validator               │ ← Pre-trade checks
└──────────────────────────────┘
         ↓
┌──────────────────────────────┐
│ Execution Engine             │ ← Submit to broker
└──────────────────────────────┘
         ↓
Paper Broker (Filled)
```

## Implementation

```python
# src/qlib_research/app/services/signal_to_trade_bridge.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger("qlib_trading.signal_bridge")

@dataclass
class QlibSignal:
    """Signal from Qlib model"""
    ticker: str
    action: str              # BUY, SELL, HOLD
    confidence: float        # 0.0-1.0
    expected_return: float   # 0.05 = 5%
    model_name: str
    backtest_sharpe: float
    generated_at: datetime

@dataclass
class SignalTrade:
    """Trade linked to signal"""
    signal_id: str
    order_id: str
    ticker: str
    side: str
    quantity: int
    entry_price: float
    created_at: datetime
    signal: QlibSignal

class SignalToTradeBridge:
    """Convert Qlib signals to trades"""
    
    def __init__(
        self,
        qlib_service,
        broker_service,
        risk_validator,
        min_confidence: float = 0.60,
        position_sizing_method: str = "fixed_pct"  # fixed_pct, kelly, max_loss
    ):
        self.qlib = qlib_service
        self.broker = broker_service
        self.risk_validator = risk_validator
        self.min_confidence = min_confidence
        self.position_sizing_method = position_sizing_method
        self.signal_trades = {}  # signal_id -> trade
    
    async def process_daily_signals(self) -> dict:
        """Process today's signals and execute trades"""
        
        results = {
            "processed": 0,
            "executed": 0,
            "rejected": 0,
            "errors": []
        }
        
        try:
            # 1. Get signals from Qlib
            signals = self.qlib.get_daily_signals(date=datetime.now().date())
            
            logger.info(f"Received {len(signals)} signals from Qlib")
            results["processed"] = len(signals)
            
            portfolio = self.broker.get_portfolio()
            
            for signal in signals:
                try:
                    # 2. Validate signal
                    if not self._validate_signal(signal):
                        results["rejected"] += 1
                        logger.info(f"Rejected signal: {signal.ticker} (confidence {signal.confidence:.0%})")
                        continue
                    
                    # 3. Size position
                    quantity = self._size_position(
                        signal=signal,
                        portfolio=portfolio
                    )
                    
                    if quantity == 0:
                        logger.warning(f"Position size=0 for {signal.ticker}, skipping")
                        results["rejected"] += 1
                        continue
                    
                    # 4. Create trade
                    trade = await self._create_and_execute_trade(
                        signal=signal,
                        quantity=quantity,
                        portfolio=portfolio
                    )
                    
                    if trade:
                        self.signal_trades[signal.ticker] = trade
                        results["executed"] += 1
                        logger.info(f"Executed trade: {signal.ticker} {signal.action} {quantity}")
                    else:
                        results["rejected"] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing signal {signal.ticker}: {e}")
                    results["errors"].append(str(e))
                    results["rejected"] += 1
            
            logger.info(f"Signal processing complete: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error in signal processing loop: {e}")
            results["errors"].append(str(e))
            return results
    
    def _validate_signal(self, signal: QlibSignal) -> bool:
        """Check signal is valid"""
        
        # Confidence check
        if signal.confidence < self.min_confidence:
            logger.debug(f"Signal {signal.ticker} confidence too low: {signal.confidence:.0%}")
            return False
        
        # Action check
        if signal.action not in ["BUY", "SELL", "HOLD"]:
            logger.warning(f"Unknown action: {signal.action}")
            return False
        
        # Skip holds
        if signal.action == "HOLD":
            return False
        
        # Timing check (signal shouldn't be too old)
        age = datetime.now() - signal.generated_at
        if age.days > 0:
            logger.info(f"Signal {signal.ticker} is {age.days} day(s) old, skipping")
            return False
        
        # Backtest quality check
        if signal.backtest_sharpe < 0.5:  # Sharpe too low
            logger.debug(f"Signal {signal.ticker} backtest Sharpe low: {signal.backtest_sharpe:.2f}")
            return False
        
        return True
    
    def _size_position(
        self,
        signal: QlibSignal,
        portfolio: 'PortfolioPosition'
    ) -> int:
        """Determine order quantity"""
        
        current_price = self.broker.get_current_price(signal.ticker)
        portfolio_value = portfolio.total_market_value + portfolio.cash_balance
        
        if self.position_sizing_method == "fixed_pct":
            # Fixed 5% position size
            position_value = portfolio_value * 0.05
            quantity = int(position_value / current_price)
        
        elif self.position_sizing_method == "kelly":
            # Kelly criterion: f = (p * b - q) / b
            # f = optimal fraction of capital
            # p = win probability, b = payoff ratio, q = 1-p
            # Simplified: Kelly = confidence * (expected_return / avg_loss)
            # Use conservative half-Kelly
            
            expected_return = signal.expected_return
            assumed_loss = 0.02  # Assume max 2% loss on bad trade
            
            win_prob = signal.confidence
            payoff_ratio = abs(expected_return / assumed_loss) if assumed_loss > 0 else 1
            
            kelly = ((win_prob * payoff_ratio) - (1 - win_prob)) / payoff_ratio
            kelly = max(0, min(kelly, 0.5))  # Cap at 50%, use half-Kelly
            
            position_value = portfolio_value * kelly * 0.5  # 0.5 = half-Kelly
            quantity = int(position_value / current_price)
        
        elif self.position_sizing_method == "max_loss":
            # Size so max loss = 1% of portfolio
            max_loss_pct = 0.01
            max_loss_usd = portfolio_value * max_loss_pct
            
            # Assume 2% move against us
            stop_loss_pct = 0.02
            quantity = int(max_loss_usd / (current_price * stop_loss_pct))
        
        else:
            quantity = 100  # Default 100 shares
        
        # Respect max position limit
        max_position_pct = 0.10  # 10% per trade
        max_quantity = int((portfolio_value * max_position_pct) / current_price)
        
        quantity = min(quantity, max_quantity)
        quantity = max(1, quantity)  # At least 1 share
        
        return quantity
    
    async def _create_and_execute_trade(
        self,
        signal: QlibSignal,
        quantity: int,
        portfolio: 'PortfolioPosition'
    ) -> Optional[SignalTrade]:
        """Execute trade based on signal"""
        
        try:
            # Map signal to order
            order_request = self._signal_to_order(signal, quantity)
            
            # Pre-flight risk checks
            can_execute, violations = self.risk_validator.can_execute_trade(
                portfolio,
                order_request
            )
            
            if not can_execute:
                logger.warning(
                    f"Trade blocked for {signal.ticker}: {', '.join(violations)}"
                )
                return None
            
            # Execute
            order = await self.broker.submit_order(
                ticker=order_request.ticker,
                side=order_request.side,
                quantity=order_request.quantity,
                order_type="market"
            )
            
            # Link signal to trade
            trade = SignalTrade(
                signal_id=f"SIG_{signal.ticker}_{signal.generated_at.timestamp()}",
                order_id=order.id,
                ticker=signal.ticker,
                side=order_request.side,
                quantity=quantity,
                entry_price=order.average_fill_price or self.broker.get_current_price(signal.ticker),
                created_at=datetime.now(),
                signal=signal
            )
            
            logger.info(
                f"Executed signal trade: {signal.ticker} {order_request.side} "
                f"{quantity} @ {trade.entry_price} (confidence {signal.confidence:.0%})"
            )
            
            return trade
            
        except Exception as e:
            logger.error(f"Error executing trade for {signal.ticker}: {e}")
            return None
    
    def _signal_to_order(
        self,
        signal: QlibSignal,
        quantity: int
    ) -> 'OrderRequest':
        """Convert signal to order"""
        
        from src.qlib_research.app.api.schemas.trading import OrderRequest, OrderSide
        
        side = OrderSide.BUY if signal.action == "BUY" else OrderSide.SELL
        
        return OrderRequest(
            ticker=signal.ticker,
            side=side,
            quantity=quantity,
            order_type="market"
        )
    
    def get_signal_trade_history(self, days: int = 7) -> list[SignalTrade]:
        """Get recent signal-based trades"""
        return list(self.signal_trades.values())[-100:]  # Last 100 trades
    
    def backtest_signals(
        self,
        start_date: str,
        end_date: str
    ) -> dict:
        """Backtest signal-to-trade execution"""
        
        logger.info(f"Backtesting signals from {start_date} to {end_date}")
        
        results = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "trades": []
        }
        
        # Would iterate through date range, fetch signals, execute, track P&L
        
        return results
```

## Scheduled Signal Processing

```python
# src/qlib_research/app/services/scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
import logging

logger = logging.getLogger("qlib_trading.scheduler")

class SignalScheduler:
    """Schedule daily signal processing"""
    
    def __init__(self, signal_bridge: SignalToTradeBridge):
        self.bridge = signal_bridge
        self.scheduler = BackgroundScheduler()
    
    def start(self):
        """Start scheduler"""
        
        # Process signals daily at market close (4 PM ET = 21:00 UTC)
        self.scheduler.add_job(
            self._daily_signal_job,
            'cron',
            hour=21,
            minute=0,
            id='daily_signal_processing'
        )
        
        # Health check every 5 minutes
        self.scheduler.add_job(
            self._health_check_job,
            'interval',
            minutes=5,
            id='health_check'
        )
        
        self.scheduler.start()
        logger.info("Signal scheduler started")
    
    async def _daily_signal_job(self):
        """Daily signal processing job"""
        logger.info("Running daily signal processing...")
        
        results = await self.bridge.process_daily_signals()
        
        logger.info(f"Signal processing complete: {results}")
    
    async def _health_check_job(self):
        """Periodic health check"""
        # Check broker connectivity, market data freshness, etc.
        pass
    
    def stop(self):
        """Stop scheduler"""
        self.scheduler.shutdown()
        logger.info("Signal scheduler stopped")
```

## API Endpoints

```python
# src/qlib_research/app/api/routes/signals.py

@router.get("/signals/today")
async def get_today_signals(bridge=Depends(get_signal_bridge)):
    """Get today's Qlib signals"""
    signals = bridge.qlib.get_daily_signals(date=datetime.now().date())
    
    return {
        "date": datetime.now().date().isoformat(),
        "signals": [
            {
                "ticker": s.ticker,
                "action": s.action,
                "confidence": s.confidence,
                "expected_return": s.expected_return,
                "backtest_sharpe": s.backtest_sharpe
            }
            for s in signals
        ]
    }

@router.get("/signal-trades")
async def get_signal_trades(
    days: int = Query(7),
    bridge=Depends(get_signal_bridge)
):
    """Get trades executed from signals"""
    trades = bridge.get_signal_trade_history(days=days)
    
    return {
        "trades": [
            {
                "signal_id": t.signal_id,
                "order_id": t.order_id,
                "ticker": t.ticker,
                "side": t.side,
                "quantity": t.quantity,
                "entry_price": t.entry_price,
                "created_at": t.created_at.isoformat()
            }
            for t in trades
        ],
        "count": len(trades)
    }

@router.post("/signals/process-now")
async def process_signals_now(bridge=Depends(get_signal_bridge)):
    """Manually trigger signal processing"""
    results = await bridge.process_daily_signals()
    return results
```

## Testing

```python
# tests/integration/test_signal_to_trade.py

@pytest.mark.asyncio
async def test_valid_signal_execution(bridge_fixture):
    """Execute valid high-confidence signal"""
    
    # Create signal
    signal = QlibSignal(
        ticker="AAPL",
        action="BUY",
        confidence=0.80,
        expected_return=0.05,
        model_name="LightGBM-v2",
        backtest_sharpe=1.8,
        generated_at=datetime.now()
    )
    
    # Execute
    trade = await bridge_fixture._create_and_execute_trade(
        signal=signal,
        quantity=100,
        portfolio=portfolio_fixture
    )
    
    assert trade is not None
    assert trade.ticker == "AAPL"
    assert trade.side == "buy"
    assert trade.order_id is not None

def test_low_confidence_signal_rejected(bridge_fixture):
    """Reject low-confidence signals"""
    
    signal = QlibSignal(
        ticker="MSFT",
        action="SELL",
        confidence=0.45,  # Too low
        expected_return=0.02,
        model_name="LightGBM-v2",
        backtest_sharpe=0.8,
        generated_at=datetime.now()
    )
    
    assert not bridge_fixture._validate_signal(signal)

def test_kelly_position_sizing():
    """Kelly criterion sizing works"""
    bridge = SignalToTradeBridge(
        qlib=mock_qlib,
        broker=mock_broker,
        risk_validator=mock_validator,
        position_sizing_method="kelly"
    )
    
    quantity = bridge._size_position(
        signal=signal_fixture,
        portfolio=portfolio_fixture
    )
    
    assert 1 <= quantity <= 1000  # Reasonable range
```

## Acceptance Criteria

- [ ] Signals fetched from Qlib daily
- [ ] Low-confidence signals filtered
- [ ] Position sizing works (fixed %, Kelly, max loss)
- [ ] Trades executed with risk checks
- [ ] Signal-to-trade linkage recorded
- [ ] Scheduler runs at specified time
- [ ] API endpoints for signals and trades
- [ ] Backtest signal performance
- [ ] Integration tests pass
- [ ] Signals logged to audit trail

## Known Limitations (MVP)

- No ML model retraining (manual retrain only)
- No dynamic confidence thresholds
- Kelly criterion simplified (no covariance)
- No multi-signal strategies
- No hedging or partial exits
