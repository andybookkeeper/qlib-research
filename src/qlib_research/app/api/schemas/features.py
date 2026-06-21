# src/qlib_research/app/api/schemas/features.py
"""Pydantic schemas for feature engineering."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class FeatureConfigSchema(BaseModel):
    """Feature configuration."""
    sma_periods: List[int] = Field(default=[5, 10, 20, 50])
    ema_periods: List[int] = Field(default=[12, 26])
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std_dev: int = 2
    atr_period: int = 14
    forward_returns_periods: List[int] = Field(default=[1, 5, 20])
    classification_threshold: float = 0.01


class FeatureStats(BaseModel):
    """Feature engineering statistics."""
    features_created: int
    targets_created: int
    error_count: int
    errors: List[str] = []


class FeatureMatrix(BaseModel):
    """Feature matrix response."""
    ticker: str
    rows: int
    columns: int
    start_date: str
    end_date: str
    stats: FeatureStats
    columns_list: List[str] = []
    sample_data: Optional[Dict] = None


class TargetResponse(BaseModel):
    """Target variables response."""
    ticker: str
    rows: int
    targets: List[str]
    sample: Optional[Dict] = None


class IndicatorLibrary(BaseModel):
    """Available indicators."""
    trend_indicators: List[str]
    momentum_indicators: List[str]
    volatility_indicators: List[str]
    volume_indicators: List[str]
