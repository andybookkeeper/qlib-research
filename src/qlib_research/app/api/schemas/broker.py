# src/qlib_research/app/api/schemas/broker.py
"""Pydantic schemas for broker service."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    """Order request."""
    ticker: str
    side: str = Field(..., description="buy or sell")
    quantity: float = Field(..., gt=0)
    order_type: str = Field("market", description="market, limit, stop, stop_limit")
    price: Optional[float] = None
    stop_price: Optional[float] = None
    limit_price: Optional[float] = None


class OrderResponse(BaseModel):
    """Order response."""
    order_id: str
    ticker: str
    side: str
    quantity: float
    order_type: str
    status: str
    filled_quantity: float
    filled_price: Optional[float]
    created_at: str


class PositionResponse(BaseModel):
    """Position response."""
    ticker: str
    quantity: float
    entry_price: float
    current_price: float
    cost_basis: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    is_long: bool
    is_short: bool


class ClosedTradeResponse(BaseModel):
    """Closed trade response."""
    trade_id: str
    ticker: str
    side: str
    entry_date: str
    entry_price: float
    entry_quantity: float
    exit_date: str
    exit_price: float
    exit_quantity: float
    realized_pnl: float
    realized_pnl_pct: float
    holding_days: int


class PortfolioStatsResponse(BaseModel):
    """Portfolio statistics."""
    initial_cash: float
    current_cash: float
    portfolio_value: float
    position_value: float
    total_pnl: float
    total_return_pct: float
    realized_pnl: float
    unrealized_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    avg_holding_days: float
    open_positions: int


class PortfolioResponse(BaseModel):
    """Complete portfolio response."""
    initial_cash: float
    current_cash: float
    positions: List[PositionResponse]
    statistics: PortfolioStatsResponse
    closed_trades: List[ClosedTradeResponse]
