# src/qlib_research/app/api/schemas/market.py
"""Pydantic schemas for market data."""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class PriceSnapshot(BaseModel):
    """Current price snapshot."""
    ticker: str
    price: float
    timestamp: datetime
    volume: Optional[int] = None
    change_pct: Optional[float] = None


class OHLCVData(BaseModel):
    """OHLCV bar."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_pct: Optional[float] = None


class MarketDataCache(BaseModel):
    """Cached market data."""
    ticker: str
    close_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    data_date: datetime
    cached_at: datetime
    is_stale: bool


class CacheStatus(BaseModel):
    """Cache status summary."""
    total: int
    fresh: int
    stale: int
    coverage_pct: float


class DataPipelineStats(BaseModel):
    """Data pipeline statistics."""
    fetched: int
    cached: int
    failed: int
    validated: int
    error_count: int
    errors: List[str] = []


class RefreshSuggestion(BaseModel):
    """Suggested tickers to refresh."""
    refresh_urgent: List[str]
    refresh_soon: List[str]
    message: str
