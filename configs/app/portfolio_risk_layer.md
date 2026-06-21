# Portfolio Risk Layer Specification
# Position tracking, Greeks aggregation, risk limits, and P&L at portfolio level

## Overview

The portfolio risk layer provides:
1. **Position Tracking**: Current holdings across all securities
2. **Greeks Aggregation**: Portfolio-level directional (delta), convexity (gamma), time decay (theta), volatility (vega) exposure
3. **Risk Metrics**: VaR, maximum drawdown, Sharpe ratio, concentration risk
4. **Risk Limits**: Enforce position limits, Greeks boundaries, and exposure caps
5. **Real-Time P&L**: Mark-to-market valuation and realized gains
6. **Margin & Buying Power**: Track available capital for new positions

## Architecture

```
┌────────────────────────────────────────────────────────┐
│            Market Data Service                         │
│  - Current prices, OHLC, Greeks                       │
└────────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│         Position Manager                               │
│  - Track open positions (stocks + options)            │
│  - Manage cost basis, entry price, qty               │
└────────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│      Portfolio Greeks Aggregator                       │
│  - Sum Greeks across all holdings                     │
│  - Compute portfolio delta, gamma, theta, vega       │
└────────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│      Risk Calculator                                   │
│  - P&L (realized + unrealized)                        │
│  - VaR, max drawdown, Sharpe                          │
│  - Margin usage, buying power                         │
└────────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│      Risk Limits Validator                             │
│  - Check position size, Greeks, exposure              │
│  - Block or warn on violations                        │
└────────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│      API Endpoints                                     │
│  - GET /api/portfolio/positions                       │
│  - GET /api/portfolio/risk                            │
│  - GET /api/portfolio/greeks                          │
│  - GET /api/portfolio/limits                          │
│  - POST /api/portfolio/limits                         │
└────────────────────────────────────────────────────────┘
```

## Data Models

### Position

```python
# src/qlib_research/app/models/position.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_CLOSED = "partially_closed"

@dataclass
class StockPosition:
    """Single stock position"""
    
    ticker: str
    quantity: float              # Positive = long, negative = short
    entry_price: float           # Average cost basis
    current_price: float
    
    # Greeks (for understanding risk)
    delta: float = 1.0           # Stock delta = 1.0 (per share)
    
    # Metadata
    opened_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def cost_basis(self) -> float:
        """Total amount invested"""
        return self.quantity * self.entry_price
    
    @property
    def market_value(self) -> float:
        """Current market value"""
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        """Profit/loss on open position"""
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """Profit/loss as percentage"""
        if self.cost_basis == 0:
            return 0
        return self.unrealized_pnl / abs(self.cost_basis)
    
    @property
    def portfolio_value_exposure(self) -> float:
        """How much of portfolio is this position (as %)"""
        # Will be set by portfolio; used for concentration risk
        return 0.0

@dataclass
class OptionPosition:
    """Single option contract holding"""
    
    contract: 'OptionContract'    # From options_analytics.md
    quantity: int                 # Contracts (1 contract = 100 shares underlying)
    entry_price: float            # Price paid per contract
    
    # Greeks
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    
    # Metadata
    opened_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def cost_basis(self) -> float:
        """Total cost (contracts * price * 100 per contract)"""
        return self.quantity * self.entry_price * 100
    
    @property
    def market_value(self) -> float:
        """Current market value"""
        return self.quantity * self.contract.current_price * 100
    
    @property
    def unrealized_pnl(self) -> float:
        """Profit/loss"""
        return self.market_value - self.cost_basis
    
    @property
    def shares_equivalent(self) -> float:
        """Delta-adjusted exposure to underlying stock"""
        return self.quantity * 100 * self.delta  # 100 shares per contract

@dataclass
class PortfolioPosition:
    """Aggregated position across all holdings"""
    
    total_market_value: float
    cash_balance: float
    
    stock_positions: dict[str, StockPosition]    # ticker -> position
    option_positions: dict[str, OptionPosition]  # contract_symbol -> position
    
    # Aggregated Greeks
    portfolio_delta: float = 0.0
    portfolio_gamma: float = 0.0
    portfolio_theta: float = 0.0
    portfolio_vega: float = 0.0
    portfolio_rho: float = 0.0
    
    # P&L
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def gross_market_value(self) -> float:
        """Sum of all long positions"""
        stocks_value = sum(p.market_value for p in self.stock_positions.values() if p.quantity > 0)
        options_value = sum(p.market_value for p in self.option_positions.values() if p.quantity > 0)
        return stocks_value + options_value
    
    @property
    def net_market_value(self) -> float:
        """Long positions - short positions"""
        stocks_value = sum(p.market_value for p in self.stock_positions.values())
        options_value = sum(p.market_value for p in self.option_positions.values())
        return stocks_value + options_value
    
    @property
    def total_pnl(self) -> float:
        """Realized + unrealized"""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def total_pnl_pct(self) -> float:
        """P&L as % of total account value"""
        total_value = self.total_market_value + self.cash_balance
        if total_value == 0:
            return 0
        return self.total_pnl / total_value
```

## Portfolio Greeks Calculation

### Greeks Aggregation

```python
# src/qlib_research/app/services/portfolio_greeks.py

from typing import List, Dict
from src.qlib_research.app.models.position import (
    StockPosition, OptionPosition, PortfolioPosition
)

class PortfolioGreeksCalculator:
    """Compute portfolio-level Greeks"""
    
    @staticmethod
    def calculate_portfolio_greeks(positions: PortfolioPosition) -> Dict[str, float]:
        """
        Aggregate Greeks from all holdings.
        
        Returns:
            dict with keys: delta, gamma, theta, vega, rho
        """
        
        # Stock positions contribution
        stock_delta = sum(
            p.quantity for p in positions.stock_positions.values()
        )  # 1 share = 1 delta
        
        # Option positions contribution
        option_delta = sum(
            p.quantity * 100 * p.delta for p in positions.option_positions.values()
        )  # Contracts * 100 shares * delta per share
        
        option_gamma = sum(
            p.quantity * 100 * p.gamma for p in positions.option_positions.values()
        )
        
        option_theta = sum(
            p.quantity * 100 * p.theta for p in positions.option_positions.values()
        )
        
        option_vega = sum(
            p.quantity * p.vega for p in positions.option_positions.values()
        )
        
        option_rho = sum(
            p.quantity * p.rho for p in positions.option_positions.values()
        )
        
        return {
            "delta": stock_delta + option_delta,
            "gamma": option_gamma,
            "theta": option_theta,
            "vega": option_vega,
            "rho": option_rho
        }
    
    @staticmethod
    def get_greeks_exposure_summary(positions: PortfolioPosition) -> str:
        """
        Human-readable Greeks summary.
        
        Returns:
            String like "Portfolio delta: +150 (long 150 shares equivalent)\n..."
        """
        greeks = PortfolioGreeksCalculator.calculate_portfolio_greeks(positions)
        
        summary = f"""
Portfolio Greeks Summary:
  Delta: {greeks['delta']:+.2f}  (directional exposure, ±1 per share)
  Gamma: {greeks['gamma']:+.4f}  (delta acceleration, positive = convex)
  Theta: {greeks['theta']:+.2f}  (daily time decay, ±$ per day)
  Vega:  {greeks['vega']:+.2f}  (IV sensitivity, ±$ per 1% IV)
  Rho:   {greeks['rho']:+.2f}  (interest rate, ±$ per 1% rate)

Interpretation:
  Delta = {greeks['delta']:+.0f}: Equivalent to {greeks['delta']:+.0f} shares of stock
  Theta = {greeks['theta']:+.2f}/day: Time decay earning/costing ${-greeks['theta']:,.2f} per day
  Vega = {greeks['vega']:+.2f}: If IV rises 1%, P&L ${greeks['vega']:+,.2f}
"""
        return summary
```

### Greeks Interpretation for Portfolio

```
Portfolio Delta:
  Positive (e.g., +150): Portfolio acts like owning 150 shares
  Negative (e.g., -100): Portfolio acts like being short 100 shares
  How to neutralize: Sell/short to bring delta to 0 (delta-neutral)

Portfolio Gamma:
  Positive: Delta increases if market rises (convex payoff)
  Negative: Delta decreases if market rises (concave payoff)
  High positive gamma: Portfolio profits from big moves in either direction
  High negative gamma: Portfolio loses from big moves

Portfolio Theta:
  Positive: Portfolio gains money each day (usually from short options)
  Negative: Portfolio loses money each day (usually from long options)
  Interpretation: $ per day you make/lose from time passage alone

Portfolio Vega:
  Positive: Portfolio gains if IV rises (benefits from volatility spike)
  Negative: Portfolio loses if IV drops (hurt by volatility drop)
  Interpretation: $ change per 1% change in implied volatility
```

## Risk Metrics

### P&L Calculation

```python
# src/qlib_research/app/services/risk_calculator.py

import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict

class RiskCalculator:
    """Compute portfolio risk metrics"""
    
    @staticmethod
    def calculate_pnl(positions: PortfolioPosition) -> Dict[str, float]:
        """Current P&L snapshot"""
        return {
            "realized_pnl": positions.realized_pnl,
            "unrealized_pnl": positions.unrealized_pnl,
            "total_pnl": positions.total_pnl,
            "total_pnl_pct": positions.total_pnl_pct
        }
    
    @staticmethod
    def calculate_var(
        positions: PortfolioPosition,
        confidence: float = 0.95,  # 95% VaR
        lookback_days: int = 252   # 1 year
    ) -> float:
        """
        Value at Risk: Worst expected loss at given confidence level.
        
        Example: 95% VaR of $5000 means "95% of the time, losses won't exceed $5000"
        
        Simplified implementation using historical returns:
        """
        # Placeholder: Would calculate from historical position returns
        # For MVP: Return approximate based on portfolio Greeks and volatility
        
        portfolio_delta = positions.portfolio_delta
        portfolio_vega = positions.portfolio_vega
        
        # Assume 20% annualized volatility
        daily_vol = 0.20 / np.sqrt(252)
        
        # Approximate portfolio daily volatility from delta
        portfolio_daily_vol = abs(portfolio_delta) * daily_vol
        
        # Z-score for 95% confidence
        z_score = 1.645
        
        # VaR = z_score * portfolio_vol * portfolio_value
        portfolio_value = positions.total_market_value + positions.cash_balance
        var = z_score * portfolio_daily_vol * portfolio_value
        
        return var
    
    @staticmethod
    def calculate_sharpe_ratio(
        positions: PortfolioPosition,
        pnl_history: List[float],  # Daily P&L history
        risk_free_rate: float = 0.0  # Annual rate
    ) -> float:
        """
        Sharpe Ratio = (Return - Risk-Free Rate) / Volatility
        
        Higher is better (>1 is good, >2 is excellent)
        """
        if not pnl_history or len(pnl_history) < 2:
            return 0.0
        
        returns = np.array(pnl_history)
        daily_return = np.mean(returns)
        daily_vol = np.std(returns)
        
        if daily_vol == 0:
            return 0.0
        
        # Annualize (252 trading days)
        annual_return = daily_return * 252
        annual_vol = daily_vol * np.sqrt(252)
        
        # Adjust for risk-free rate
        excess_return = annual_return - risk_free_rate
        
        sharpe = excess_return / annual_vol if annual_vol > 0 else 0
        return sharpe
    
    @staticmethod
    def calculate_max_drawdown(pnl_history: List[float]) -> float:
        """
        Maximum consecutive decline from peak.
        
        Example: If max cumulative return was $10k and dropped to $7k, drawdown is $3k.
        """
        if not pnl_history or len(pnl_history) < 2:
            return 0.0
        
        cumulative = np.cumsum(pnl_history)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        max_drawdown = np.min(drawdown)  # Most negative value
        
        return abs(max_drawdown)
    
    @staticmethod
    def calculate_win_rate(pnl_history: List[float]) -> float:
        """Percentage of profitable days"""
        if not pnl_history or len(pnl_history) == 0:
            return 0.0
        
        winning_days = sum(1 for p in pnl_history if p > 0)
        return winning_days / len(pnl_history)
    
    @staticmethod
    def calculate_concentration_risk(positions: PortfolioPosition) -> Dict[str, float]:
        """
        Concentration risk: Is portfolio too exposed to single positions?
        
        Returns:
            dict with top positions by exposure
        """
        total_value = positions.total_market_value
        
        if total_value == 0:
            return {}
        
        exposure = {}
        
        for ticker, pos in positions.stock_positions.items():
            exposure[ticker] = (pos.market_value / total_value) * 100
        
        for contract_sym, pos in positions.option_positions.items():
            exposure[contract_sym] = (pos.market_value / total_value) * 100
        
        # Return top 5 positions
        return dict(sorted(exposure.items(), key=lambda x: abs(x[1]), reverse=True)[:5])
    
    @staticmethod
    def calculate_margin(
        positions: PortfolioPosition,
        initial_margin_pct: float = 0.30,  # 30% for stocks
        maintenance_margin_pct: float = 0.25  # 25% for maintenance
    ) -> Dict[str, float]:
        """
        Calculate margin requirements and buying power.
        
        Paper trading simplified: No actual margin. Just track hypothetical.
        """
        short_value = sum(
            abs(p.market_value) for p in positions.stock_positions.values()
            if p.quantity < 0
        )
        
        initial_margin_required = short_value * initial_margin_pct
        maintenance_margin_required = short_value * maintenance_margin_pct
        
        cash_available = positions.cash_balance
        buying_power = (cash_available / initial_margin_pct) if initial_margin_pct > 0 else cash_available
        
        return {
            "initial_margin_required": initial_margin_required,
            "maintenance_margin_required": maintenance_margin_required,
            "cash_available": cash_available,
            "buying_power": buying_power,
            "margin_utilization_pct": (initial_margin_required / buying_power * 100) if buying_power > 0 else 0
        }
```

## Risk Limits

### Risk Limit Model

```python
# src/qlib_research/app/models/risk_limits.py

from dataclasses import dataclass

@dataclass
class RiskLimits:
    """Risk control parameters"""
    
    # Position sizing
    max_position_size_pct: float = 0.10      # Max 10% of portfolio in single stock
    max_sector_exposure_pct: float = 0.30    # Max 30% in single sector
    
    # Greeks limits
    max_portfolio_delta: float = 1.5         # Portfolio can be long equiv. of 1.5x portfolio value
    min_portfolio_delta: float = -1.5        # Or short equiv. of 1.5x
    max_abs_gamma: float = 0.05              # Gamma (as % of portfolio) limits
    max_abs_vega: float = 5000               # Vega ($ per 1% IV) limits
    
    # P&L limits
    max_daily_loss_pct: float = 0.02         # Stop if lose 2% in a day
    max_daily_loss_usd: float = 1000         # Or $1000
    max_drawdown_pct: float = 0.10           # Max 10% drawdown
    
    # Leverage
    max_leverage: float = 2.0                # Max 2x leverage
    
    # Options specifics
    max_options_portfolio_pct: float = 0.30  # Max 30% in options
    max_single_expiration_pct: float = 0.15  # Max 15% in single expiration
    
    def validate(self, positions: PortfolioPosition) -> List[str]:
        """Check limits and return violations"""
        violations = []
        
        # Check position size
        total_value = positions.total_market_value
        for ticker, pos in positions.stock_positions.items():
            pct = abs(pos.market_value) / total_value if total_value > 0 else 0
            if pct > self.max_position_size_pct:
                violations.append(
                    f"Position {ticker} is {pct*100:.1f}% of portfolio (limit: {self.max_position_size_pct*100:.1f}%)"
                )
        
        # Check Greeks
        if abs(positions.portfolio_delta) > self.max_portfolio_delta:
            violations.append(
                f"Portfolio delta {positions.portfolio_delta:+.2f} exceeds limit ±{self.max_portfolio_delta:.2f}"
            )
        
        # Check leverage
        gross_value = positions.gross_market_value
        leverage = gross_value / total_value if total_value > 0 else 0
        if leverage > self.max_leverage:
            violations.append(
                f"Leverage {leverage:.2f}x exceeds limit {self.max_leverage:.2f}x"
            )
        
        return violations
```

### Risk Limit Validator

```python
# src/qlib_research/app/services/risk_validator.py

class RiskValidator:
    """Enforce risk limits on trades"""
    
    def __init__(self, limits: RiskLimits):
        self.limits = limits
    
    def can_execute_trade(
        self,
        current_positions: PortfolioPosition,
        proposed_trade: 'TradeOrder'  # Order to execute
    ) -> tuple[bool, List[str]]:
        """
        Check if proposed trade would violate limits.
        
        Returns:
            (can_execute, list_of_violations)
        """
        violations = []
        
        # Simulate position after trade
        simulated_positions = self._simulate_trade(current_positions, proposed_trade)
        
        # Validate simulated state
        violations = self.limits.validate(simulated_positions)
        
        return len(violations) == 0, violations
    
    def _simulate_trade(
        self,
        positions: PortfolioPosition,
        trade: 'TradeOrder'
    ) -> PortfolioPosition:
        """Create copy of positions with proposed trade applied"""
        # Deep copy positions
        import copy
        simulated = copy.deepcopy(positions)
        
        # Apply trade (simplified)
        if trade.instrument_type == "stock":
            if trade.ticker not in simulated.stock_positions:
                simulated.stock_positions[trade.ticker] = StockPosition(
                    ticker=trade.ticker,
                    quantity=trade.quantity,
                    entry_price=trade.price,
                    current_price=trade.price
                )
            else:
                pos = simulated.stock_positions[trade.ticker]
                pos.quantity += trade.quantity
        
        # Recalculate Greeks
        greeks = PortfolioGreeksCalculator.calculate_portfolio_greeks(simulated)
        simulated.portfolio_delta = greeks["delta"]
        simulated.portfolio_gamma = greeks["gamma"]
        simulated.portfolio_theta = greeks["theta"]
        simulated.portfolio_vega = greeks["vega"]
        simulated.portfolio_rho = greeks["rho"]
        
        return simulated
```

## API Endpoints

### Get Portfolio Positions

```python
# src/qlib_research/app/api/routes/portfolio.py

from fastapi import APIRouter, Depends
from src.qlib_research.app.services.portfolio_greeks import PortfolioGreeksCalculator
from src.qlib_research.app.services.risk_calculator import RiskCalculator
from src.qlib_research.app.api.dependencies import get_portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

@router.get("/positions")
def get_positions(portfolio: PortfolioPosition = Depends(get_portfolio)):
    """
    Get current positions.
    
    Response:
    {
      "stocks": [
        {
          "ticker": "AAPL",
          "quantity": 100,
          "entry_price": 150.50,
          "current_price": 151.00,
          "cost_basis": 15050.00,
          "market_value": 15100.00,
          "unrealized_pnl": 50.00,
          "unrealized_pnl_pct": 0.33
        }
      ],
      "options": [
        {
          "contract": "AAPL 2024-01-19 C150",
          "quantity": 5,
          "delta": 0.52,
          "theta": -0.08,
          "market_value": 750.00,
          "unrealized_pnl": 50.00
        }
      ],
      "cash": 10000.00,
      "total_market_value": 25100.00
    }
    """
    return {
        "stocks": [
            {
                "ticker": pos.ticker,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "cost_basis": pos.cost_basis,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct
            }
            for pos in portfolio.stock_positions.values()
        ],
        "options": [
            {
                "contract": f"{pos.contract.ticker} {pos.contract.expiration_date.date()} {pos.contract.contract_type[0].upper()}{pos.contract.strike_price:.2f}",
                "quantity": pos.quantity,
                "delta": pos.delta,
                "gamma": pos.gamma,
                "theta": pos.theta,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl
            }
            for pos in portfolio.option_positions.values()
        ],
        "cash": portfolio.cash_balance,
        "total_market_value": portfolio.total_market_value
    }

@router.get("/greeks")
def get_greeks(portfolio: PortfolioPosition = Depends(get_portfolio)):
    """Get portfolio Greeks"""
    greeks = PortfolioGreeksCalculator.calculate_portfolio_greeks(portfolio)
    return {
        "delta": round(greeks["delta"], 2),
        "gamma": round(greeks["gamma"], 4),
        "theta": round(greeks["theta"], 2),
        "vega": round(greeks["vega"], 2),
        "rho": round(greeks["rho"], 2),
        "summary": PortfolioGreeksCalculator.get_greeks_exposure_summary(portfolio)
    }

@router.get("/risk")
def get_risk_metrics(portfolio: PortfolioPosition = Depends(get_portfolio)):
    """Get portfolio risk metrics"""
    pnl = RiskCalculator.calculate_pnl(portfolio)
    var = RiskCalculator.calculate_var(portfolio)
    concentration = RiskCalculator.calculate_concentration_risk(portfolio)
    
    return {
        "pnl": pnl,
        "var_95": var,
        "concentration": concentration
    }

@router.get("/limits")
def get_limits(limits: RiskLimits = Depends(get_risk_limits)):
    """Get current risk limits"""
    return {
        "max_position_size_pct": limits.max_position_size_pct * 100,
        "max_portfolio_delta": limits.max_portfolio_delta,
        "max_abs_vega": limits.max_abs_vega,
        "max_daily_loss_pct": limits.max_daily_loss_pct * 100,
        "max_drawdown_pct": limits.max_drawdown_pct * 100,
        "max_leverage": limits.max_leverage
    }

@router.post("/limits")
def update_limits(new_limits: RiskLimits):
    """Update risk limits (admin only)"""
    # TODO: Add auth check
    return {"status": "limits_updated", "limits": new_limits}
```

## Testing

```python
# tests/unit/test_portfolio_greeks.py

def test_portfolio_delta_calculation():
    """Test portfolio delta aggregation"""
    positions = PortfolioPosition(
        total_market_value=100000,
        cash_balance=0,
        stock_positions={
            "AAPL": StockPosition(ticker="AAPL", quantity=100, entry_price=150, current_price=150),
            "MSFT": StockPosition(ticker="MSFT", quantity=-50, entry_price=300, current_price=300)
        },
        option_positions={}
    )
    
    greeks = PortfolioGreeksCalculator.calculate_portfolio_greeks(positions)
    
    # 100 shares AAPL delta = 100, -50 shares MSFT delta = -50
    assert greeks["delta"] == 50

def test_risk_limits_violation():
    """Test risk limit validation"""
    positions = PortfolioPosition(
        total_market_value=100000,
        cash_balance=0,
        stock_positions={
            "AAPL": StockPosition(ticker="AAPL", quantity=1000, entry_price=150, current_price=150)
        },
        option_positions={}
    )
    
    limits = RiskLimits(max_position_size_pct=0.10)  # Max 10%
    violations = limits.validate(positions)
    
    # AAPL is now 150% of portfolio—should violate
    assert len(violations) > 0
```

## Acceptance Criteria

- [ ] Portfolio position tracking (stocks + options)
- [ ] Greeks aggregation (delta, gamma, theta, vega, rho)
- [ ] P&L calculation (realized, unrealized, total)
- [ ] VaR and max drawdown calculation
- [ ] Sharpe ratio and win rate
- [ ] Concentration risk analysis
- [ ] Risk limits definition and enforcement
- [ ] API endpoints for positions, Greeks, risk metrics
- [ ] Risk validator blocks trades violating limits
- [ ] Unit tests for Greeks calculation
- [ ] Unit tests for risk limit validation

## Known Limitations (MVP)

- No real margin (paper trading only)
- Greeks calculation uses simplified Black-Scholes (no local vol)
- No sector or industry classification (concentration risk simplified)
- No multi-currency support
- No position hedging recommendations
- No stress testing or scenario analysis
