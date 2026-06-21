"""Research and ML model endpoints."""

from typing import Any, Dict, Optional

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
