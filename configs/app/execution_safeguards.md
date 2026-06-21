# Execution Safeguards Specification
# Risk controls, order validation, circuit breakers, and kill switches

## Overview

Execution safeguards prevent catastrophic losses through:
1. **Pre-Trade Validation** — Risk limit checks, buying power, position size
2. **Circuit Breakers** — Halt trading on max loss or volatility spike
3. **Price Bounds** — Reject orders outside normal trading range
4. **Kill Switches** — Manual pause/halt all trading
5. **Audit Trail** — Log all trades and risk decisions

## Pre-Trade Validation Pipeline

```
User submits order
         ↓
┌──────────────────────────────────┐
│ 1. Instrument Valid?             │ → Reject if not in supported assets
│    (ticker exists, tradeable)    │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ 2. Quantity Valid?               │ → Reject if qty <= 0 or > max
│    (positive, not NaN)           │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ 3. Price Valid? (limit orders)   │ → Reject if outside bounds
│    (positive, reasonable range)  │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ 4. Buying Power OK?              │ → Reject if insufficient cash
│    (cash >= order cost)          │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ 5. Risk Limits OK?               │ → Reject if violates limits
│    (position size, Greeks, etc)  │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ 6. Circuit Breaker OK?           │ → Halt if triggered
│    (max loss, volatility spike)  │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ 7. Execute Order                 │ → Fill at current market
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│ 8. Post-Trade Audit              │ → Log to audit trail
│    (record execution details)    │
└──────────────────────────────────┘
```

## Validation Rules

### Instrument Validation

```python
# src/qlib_research/app/services/execution_safeguards.py

class InstrumentValidator:
    """Validate that instrument is tradeable"""
    
    SUPPORTED_ASSETS = {"AAPL", "MSFT", "GOOG", "NVDA", ...}  # MVP: hardcoded
    
    def validate_instrument(self, ticker: str) -> tuple[bool, str]:
        """
        Check if ticker is supported.
        
        Returns:
            (is_valid, error_message)
        """
        ticker = ticker.upper()
        
        if not ticker or len(ticker) > 5:
            return False, "Invalid ticker format"
        
        if ticker not in self.SUPPORTED_ASSETS:
            return False, f"Ticker {ticker} not supported (MVP: {len(self.SUPPORTED_ASSETS)} assets)"
        
        # Future: check if market is open, halted, etc.
        
        return True, ""
```

### Quantity & Price Validation

```python
class OrderValidator:
    """Validate order parameters"""
    
    MIN_ORDER_SIZE = 1          # Minimum 1 share
    MAX_ORDER_SIZE = 10000      # Maximum 10,000 shares per order
    MAX_PRICE_SPIKE = 0.20      # Reject limit orders >20% away from last price
    
    def validate_quantity(self, qty: int, price: float = None) -> tuple[bool, str]:
        """Validate order quantity"""
        
        if not isinstance(qty, int) or qty <= 0:
            return False, f"Quantity must be positive integer, got {qty}"
        
        if qty < self.MIN_ORDER_SIZE:
            return False, f"Minimum order size is {self.MIN_ORDER_SIZE} shares"
        
        if qty > self.MAX_ORDER_SIZE:
            return False, f"Maximum order size is {self.MAX_ORDER_SIZE} shares"
        
        return True, ""
    
    def validate_limit_price(
        self, 
        limit_price: float, 
        current_price: float,
        side: str
    ) -> tuple[bool, str]:
        """Validate limit price isn't absurd"""
        
        if limit_price <= 0:
            return False, "Limit price must be positive"
        
        # Check price spike
        if side == "buy":
            # Buy limit price too high compared to current
            if limit_price > current_price * (1 + self.MAX_PRICE_SPIKE):
                return False, (
                    f"Buy limit ${limit_price} is {((limit_price/current_price - 1)*100):.1f}% "
                    f"above current price ${current_price} (max allowed: {self.MAX_PRICE_SPIKE*100}%)"
                )
        else:  # sell
            # Sell limit price too low
            if limit_price < current_price * (1 - self.MAX_PRICE_SPIKE):
                return False, (
                    f"Sell limit ${limit_price} is {((current_price/limit_price - 1)*100):.1f}% "
                    f"below current price ${current_price} (max allowed: {self.MAX_PRICE_SPIKE*100}%)"
                )
        
        return True, ""
```

### Buying Power Validation

```python
class BuyingPowerValidator:
    """Check if account has sufficient capital"""
    
    COMMISSION_PER_TRADE = 5.00  # $5 per order
    
    def validate_buying_power(
        self,
        order_side: str,
        order_qty: int,
        order_price: float,
        cash_balance: float,
        portfolio: 'PortfolioPosition'
    ) -> tuple[bool, str]:
        """Check if order can be afforded"""
        
        if order_side == "buy":
            # Estimate order cost
            cost = order_qty * order_price + self.COMMISSION_PER_TRADE
            
            if cash_balance < cost:
                shortfall = cost - cash_balance
                return False, (
                    f"Insufficient buying power. Need ${cost:,.2f} "
                    f"but only have ${cash_balance:,.2f} "
                    f"(short ${shortfall:,.2f})"
                )
        
        else:  # sell
            # Check if we have shares to sell
            if order_side == "sell":
                ticker = order_qty  # Placeholder
                position = portfolio.stock_positions.get(ticker)
                
                if not position or position.quantity < order_qty:
                    available = position.quantity if position else 0
                    return False, (
                        f"Cannot sell {order_qty} shares of {ticker}. "
                        f"Only {available} available."
                    )
        
        return True, ""
```

## Risk Limits Enforcement

```python
class RiskLimitValidator:
    """Check order against risk limits"""
    
    def validate_position_size(
        self,
        ticker: str,
        order_qty: int,
        order_price: float,
        portfolio_value: float,
        max_position_size_pct: float = 0.10
    ) -> tuple[bool, str]:
        """Check position doesn't exceed max % of portfolio"""
        
        # Calculate position value after order
        position_value = order_qty * order_price
        position_pct = position_value / portfolio_value if portfolio_value > 0 else 0
        
        if position_pct > max_position_size_pct:
            return False, (
                f"Position would be {position_pct*100:.1f}% of portfolio "
                f"(max: {max_position_size_pct*100:.1f}%)"
            )
        
        return True, ""
    
    def validate_portfolio_greeks(
        self,
        portfolio: 'PortfolioPosition',
        order: 'OrderRequest',
        greeks_after_trade: dict,
        limits: 'RiskLimits'
    ) -> tuple[bool, str]:
        """Check Greeks stay within limits"""
        
        if abs(greeks_after_trade['delta']) > limits.max_portfolio_delta:
            return False, (
                f"Portfolio delta would be {greeks_after_trade['delta']:+.2f} "
                f"(limit: ±{limits.max_portfolio_delta:.2f})"
            )
        
        if abs(greeks_after_trade['vega']) > limits.max_abs_vega:
            return False, (
                f"Portfolio vega would be {greeks_after_trade['vega']:+.2f} "
                f"(limit: ±{limits.max_abs_vega:.2f})"
            )
        
        return True, ""
```

## Circuit Breakers

### Daily Loss Limit

```python
class CircuitBreaker:
    """Automatic trading halt on risk thresholds"""
    
    def __init__(self):
        self.session_start_portfolio_value = None
        self.trades_today = []
        self.is_halted = False
        self.halt_reason = None
    
    def check_daily_loss_limit(
        self,
        current_portfolio_value: float,
        current_pnl: float,
        max_daily_loss_pct: float = 0.02,
        max_daily_loss_usd: float = 1000
    ) -> tuple[bool, str]:
        """Check if daily loss exceeds limit"""
        
        # Check percentage loss
        if self.session_start_portfolio_value:
            loss_pct = -current_pnl / self.session_start_portfolio_value
            
            if loss_pct > max_daily_loss_pct:
                self.is_halted = True
                self.halt_reason = f"Daily loss limit hit: {loss_pct*100:.2f}%"
                return False, self.halt_reason
        
        # Check dollar loss
        if current_pnl < -max_daily_loss_usd:
            self.is_halted = True
            self.halt_reason = f"Daily loss limit hit: ${-current_pnl:,.2f}"
            return False, self.halt_reason
        
        return True, ""
    
    def check_volatility_spike(
        self,
        current_volatility: float,
        normal_volatility: float = 0.20,
        spike_threshold: float = 2.0  # 2x normal vol
    ) -> tuple[bool, str]:
        """Halt trading if volatility spikes"""
        
        if current_volatility > normal_volatility * spike_threshold:
            self.is_halted = True
            self.halt_reason = f"Volatility spike: {current_volatility:.1%}"
            return False, self.halt_reason
        
        return True, ""
    
    def check_max_drawdown(
        self,
        pnl_history: list[float],
        max_drawdown_pct: float = 0.10
    ) -> tuple[bool, str]:
        """Check cumulative drawdown from peak"""
        
        import numpy as np
        
        if not pnl_history:
            return True, ""
        
        cumulative = np.cumsum(pnl_history)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_dd = np.min(drawdown) if len(drawdown) > 0 else 0
        
        dd_pct = abs(max_dd) / abs(running_max[0]) if running_max[0] != 0 else 0
        
        if dd_pct > max_drawdown_pct:
            self.is_halted = True
            self.halt_reason = f"Max drawdown hit: {dd_pct*100:.1f}%"
            return False, self.halt_reason
        
        return True, ""
```

### Manual Kill Switch

```python
class KillSwitch:
    """Emergency halt all trading"""
    
    def __init__(self):
        self.is_active = False
        self.activated_at = None
        self.reason = ""
    
    def activate(self, reason: str = "Manual halt"):
        """Emergency stop all trading"""
        self.is_active = True
        self.activated_at = datetime.now()
        self.reason = reason
        print(f"🛑 TRADING HALTED: {reason}")
    
    def deactivate(self):
        """Resume trading"""
        self.is_active = False
        self.activated_at = None
        print("✓ Trading resumed")
    
    def check_active(self) -> tuple[bool, str]:
        """Check if kill switch is on"""
        if self.is_active:
            return False, f"Trading halted: {self.reason}"
        return True, ""
```

## Execution Service

```python
class SafeExecutionService:
    """Execute trades with all safeguards"""
    
    def __init__(self):
        self.instrument_validator = InstrumentValidator()
        self.order_validator = OrderValidator()
        self.buying_power_validator = BuyingPowerValidator()
        self.risk_limit_validator = RiskLimitValidator()
        self.circuit_breaker = CircuitBreaker()
        self.kill_switch = KillSwitch()
        self.audit_trail = AuditTrail()
    
    async def execute_order(
        self,
        order_request: 'OrderRequest',
        portfolio: 'PortfolioPosition',
        risk_limits: 'RiskLimits'
    ) -> tuple['Order', list[str]]:
        """
        Execute order if all safeguards pass.
        
        Returns:
            (order_object, list_of_violations)
        """
        violations = []
        
        # 1. Kill switch
        ok, msg = self.kill_switch.check_active()
        if not ok:
            violations.append(msg)
            return None, violations
        
        # 2. Instrument valid
        ok, msg = self.instrument_validator.validate_instrument(order_request.ticker)
        if not ok:
            violations.append(msg)
            return None, violations
        
        # 3. Quantity valid
        ok, msg = self.order_validator.validate_quantity(order_request.quantity)
        if not ok:
            violations.append(msg)
            return None, violations
        
        # 4. Price valid (limit orders)
        if order_request.order_type == "limit" and order_request.price:
            current_price = await self._get_current_price(order_request.ticker)
            ok, msg = self.order_validator.validate_limit_price(
                order_request.price, current_price, order_request.side
            )
            if not ok:
                violations.append(msg)
                return None, violations
        
        # 5. Buying power
        ok, msg = self.buying_power_validator.validate_buying_power(
            order_request.side,
            order_request.quantity,
            await self._get_current_price(order_request.ticker),
            portfolio.cash_balance,
            portfolio
        )
        if not ok:
            violations.append(msg)
            return None, violations
        
        # 6. Risk limits
        ok, msg = self.risk_limit_validator.validate_position_size(
            order_request.ticker,
            order_request.quantity,
            await self._get_current_price(order_request.ticker),
            portfolio.total_market_value,
            risk_limits.max_position_size_pct
        )
        if not ok:
            violations.append(msg)
            return None, violations
        
        # 7. Circuit breaker
        ok, msg = self.circuit_breaker.check_daily_loss_limit(
            portfolio.total_market_value,
            portfolio.total_pnl,
            risk_limits.max_daily_loss_pct,
            risk_limits.max_daily_loss_usd
        )
        if not ok:
            violations.append(msg)
            return None, violations
        
        # All checks pass → execute
        order = await self._submit_order(order_request)
        
        # 8. Audit trail
        self.audit_trail.log_trade(
            order=order,
            portfolio=portfolio,
            violations=violations,
            timestamp=datetime.now()
        )
        
        return order, violations
```

## Audit Trail

```python
class AuditTrail:
    """Log all trading decisions"""
    
    def __init__(self, log_file: str = "data/audit.log"):
        self.log_file = log_file
    
    def log_trade(
        self,
        order: 'Order',
        portfolio: 'PortfolioPosition',
        violations: list[str],
        timestamp: datetime
    ):
        """Log executed trade"""
        
        entry = {
            "timestamp": timestamp.isoformat(),
            "event": "trade_executed",
            "order_id": order.id,
            "ticker": order.ticker,
            "side": order.side,
            "quantity": order.quantity,
            "price": order.price,
            "portfolio_value_before": portfolio.total_market_value,
            "cash_before": portfolio.cash_balance,
            "violations_checked": violations
        }
        
        self._append_log(entry)
    
    def log_rejection(
        self,
        order_request: 'OrderRequest',
        violations: list[str],
        timestamp: datetime
    ):
        """Log rejected order"""
        
        entry = {
            "timestamp": timestamp.isoformat(),
            "event": "order_rejected",
            "ticker": order_request.ticker,
            "side": order_request.side,
            "quantity": order_request.quantity,
            "violations": violations
        }
        
        self._append_log(entry)
    
    def _append_log(self, entry: dict):
        """Append entry to audit log"""
        import json
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
```

## API Endpoints

```python
# src/qlib_research/app/api/routes/safety.py

@router.post("/kill-switch/activate")
async def activate_kill_switch(
    reason: str = "Manual halt",
    kill_switch: KillSwitch = Depends(get_kill_switch)
):
    """Emergency halt trading"""
    kill_switch.activate(reason)
    return {"status": "halted", "reason": reason}

@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch(
    kill_switch: KillSwitch = Depends(get_kill_switch)
):
    """Resume trading"""
    kill_switch.deactivate()
    return {"status": "active"}

@router.get("/kill-switch/status")
async def kill_switch_status(
    kill_switch: KillSwitch = Depends(get_kill_switch)
):
    """Check kill switch status"""
    return {
        "is_halted": kill_switch.is_active,
        "reason": kill_switch.reason,
        "activated_at": kill_switch.activated_at
    }

@router.get("/circuit-breaker/status")
async def circuit_breaker_status(
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker)
):
    """Check circuit breaker status"""
    return {
        "is_halted": circuit_breaker.is_halted,
        "halt_reason": circuit_breaker.halt_reason
    }

@router.get("/audit-trail")
async def get_audit_trail(
    days: int = Query(1),
    event_type: str = Query(None)  # trade_executed, order_rejected
):
    """Get audit trail entries"""
    entries = AuditTrail().read_log(days=days, event_type=event_type)
    return {"entries": entries, "count": len(entries)}
```

## Testing

```python
# tests/unit/test_execution_safeguards.py

def test_reject_unsupported_ticker():
    """Reject order for unsupported ticker"""
    validator = InstrumentValidator()
    ok, msg = validator.validate_instrument("UNKNOWN_TICKER")
    assert not ok
    assert "not supported" in msg

def test_reject_negative_quantity():
    """Reject negative order quantity"""
    validator = OrderValidator()
    ok, msg = validator.validate_quantity(-100)
    assert not ok

def test_reject_insufficient_buying_power():
    """Reject order when not enough cash"""
    bpv = BuyingPowerValidator()
    ok, msg = bpv.validate_buying_power(
        "buy", 1000, 150.00, 100000, portfolio
    )
    assert not ok  # 1000 * 150 = $150k > $100k cash

def test_circuit_breaker_daily_loss():
    """Halt trading on daily loss limit"""
    cb = CircuitBreaker()
    ok, msg = cb.check_daily_loss_limit(
        current_portfolio_value=98000,
        current_pnl=-2500,
        max_daily_loss_pct=0.02,
        max_daily_loss_usd=2000
    )
    assert not ok
    assert "Daily loss limit" in msg
```

## Acceptance Criteria

- [ ] All 7 validation checks implemented
- [ ] Circuit breaker halts on max daily loss
- [ ] Kill switch can be activated/deactivated
- [ ] Audit trail logs all trades
- [ ] API endpoints for kill switch and circuit breaker
- [ ] Error messages clear and actionable
- [ ] Unit tests for each validator
- [ ] Rejection reasons returned to UI

## Known Limitations (MVP)

- No market hours checks (24/5 trading assumed)
- No liquidity validation (assume liquid)
- No slippage estimation
- No multi-leg order constraints
- No sector concentration (single asset concentration only)
