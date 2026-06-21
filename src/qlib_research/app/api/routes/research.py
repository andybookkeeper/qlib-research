# src/qlib_research/app/api/routes/research_simple.py
"""Research and ML model endpoints."""

from fastapi import APIRouter, Query
from typing import Dict, List, Optional

router = APIRouter()


@router.get("/models")
async def list_models() -> Dict:
    """Get list of available trained models."""
    return {
        "count": 0,
        "models": []
    }


@router.post("/predict")
async def predict(
    model_name: str = Query(...),
    features: Optional[Dict] = None
) -> Dict:
    """Make predictions with a trained model."""
    return {
        "model_name": model_name,
        "prediction": 0.0,
        "confidence": 0.0
    }


@router.get("/backtests")
async def list_backtests() -> Dict:
    """Get backtest results."""
    return {
        "count": 0,
        "backtests": []
    }
