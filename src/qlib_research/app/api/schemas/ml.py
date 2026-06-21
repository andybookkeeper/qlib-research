# src/qlib_research/app/api/schemas/ml.py
"""Pydantic schemas for ML training."""

from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field


class ModelConfigSchema(BaseModel):
    """Model configuration."""
    model_family: str = Field("lightgbm", description="lightgbm, random_forest, or extra_trees")
    task: str = Field("classification", description="classification, multiclass, or regression")
    target_column: Optional[str] = None
    forecast_horizon: int = Field(1, ge=1, le=252)
    test_size: float = Field(0.2, gt=0.05, lt=0.5)
    n_splits: int = 5
    n_estimators: int = 100
    learning_rate: float = 0.05
    max_depth: int = 7
    num_leaves: int = 31
    early_stopping_rounds: int = 20


class TrainingRequest(BaseModel):
    """Training request."""
    model_name: Optional[str] = None
    ticker: str
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    config: Optional[ModelConfigSchema] = None


class TrainingResult(BaseModel):
    """Training result."""
    ticker: str
    task: str
    n_estimators: int
    training_date: str
    model_id: str
    feature_count: int
    top_features: List[Tuple[str, float]]


class CVResult(BaseModel):
    """Cross-validation result."""
    n_folds: int
    mean_accuracy: Optional[float] = None
    std_accuracy: Optional[float] = None
    mean_f1: Optional[float] = None
    std_f1: Optional[float] = None
    mean_mae: Optional[float] = None
    std_mae: Optional[float] = None
    results_per_fold: List[Dict]


class BacktestResult(BaseModel):
    """Backtest result."""
    model_id: str
    ticker: str
    total_return: float
    buy_hold_return: float
    excess_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    final_equity: float


class PredictionResponse(BaseModel):
    """Prediction response."""
    ticker: str
    date: str
    close_price: float
    prediction: int
    prediction_proba: Optional[List[float]] = None
    confidence: float
