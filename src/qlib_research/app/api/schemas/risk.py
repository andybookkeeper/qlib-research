# src/qlib_research/app/api/schemas/risk.py
"""Risk validation schemas."""

from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime


class GreeksSchema(BaseModel):
    """Portfolio Greeks."""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class PortfolioRiskSchema(BaseModel):
    """Portfolio risk metrics."""
    total_value: float
    cash: float
    gross_value: float
    net_value: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    total_pnl_pct: float
    var_95: float
    max_drawdown: float
    sharpe_ratio: float
    greeks: GreeksSchema
    leverage: float


class RiskViolationSchema(BaseModel):
    """Risk limit violation."""
    limit_name: str
    current_value: float
    limit_value: float
    severity: str  # warning, error
    message: str


class RiskValidationResponseSchema(BaseModel):
    """Risk validation response."""
    risk: PortfolioRiskSchema
    violations: List[RiskViolationSchema]
    is_compliant: bool  # True if no error violations


class RiskLimitsSchema(BaseModel):
    """Risk limits configuration."""
    max_position_size: float = 50000.0
    max_concentration: float = 0.25
    max_portfolio_delta: float = 2.0
    max_portfolio_gamma: float = 0.5
    max_portfolio_theta: float = -500.0
    max_portfolio_vega: float = 1000.0
    max_drawdown: float = 0.20
    min_sharpe_ratio: float = 0.5
