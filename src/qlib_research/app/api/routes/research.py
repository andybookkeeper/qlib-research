"""Research and ML model endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.qlib_research.app.api.dependencies import get_training_runtime_service
from src.qlib_research.app.services.training_runtime_service import TrainingRuntimeService

router = APIRouter()


@router.get("/models")
async def list_models(
    runtime: TrainingRuntimeService = Depends(get_training_runtime_service),
) -> Dict[str, Any]:
    """Get list of available trained models."""
    return runtime.list_models()


@router.post("/predict")
async def predict(
    model_name: str = Query(...),
    features: Optional[Dict[str, Any]] = None,
    runtime: TrainingRuntimeService = Depends(get_training_runtime_service),
) -> Dict[str, Any]:
    """Make predictions with a trained model."""
    try:
        return runtime.predict(model_name, features)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/backtests")
async def list_backtests(
    runtime: TrainingRuntimeService = Depends(get_training_runtime_service),
) -> Dict[str, Any]:
    """Get backtest results."""
    return runtime.list_backtests()


@router.get("/signals")
async def get_signals(
    tickers: Optional[str] = Query(None, description="Comma-separated tickers to filter, e.g. AAPL,MSFT"),
    runtime: TrainingRuntimeService = Depends(get_training_runtime_service),
) -> Dict[str, Any]:
    """Run all trained models on latest market data and return BUY/SELL/HOLD signals."""
    ticker_list: Optional[List[str]] = [t.strip().upper() for t in tickers.split(",")] if tickers else None
    signals = runtime.generate_signals(tickers=ticker_list)
    return {"count": len(signals), "signals": signals}
