"""Risk validation endpoints (database-backed)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.qlib_research.app.api.schemas.risk import RiskLimitsSchema
from src.qlib_research.app.api.dependencies import get_current_active_user
from src.qlib_research.app.db import get_db
from src.qlib_research.app.models.database import User
from src.qlib_research.app.services.broker_service import DatabaseBrokerService

router = APIRouter()


@router.get("/limits")
async def get_risk_limits() -> RiskLimitsSchema:
    """Get current risk limit configuration."""
    return RiskLimitsSchema(
        max_position_size=50000.0,
        max_concentration=0.25,
        max_portfolio_delta=2.0,
        max_portfolio_gamma=0.5,
        max_portfolio_theta=-500.0,
        max_portfolio_vega=1000.0,
        max_drawdown=0.20,
        min_sharpe_ratio=0.5,
    )


@router.post("/var")
async def calculate_var(
    portfolio_value: float = Query(...),
    confidence: float = Query(default=0.95),
) -> dict:
    """Calculate Value at Risk at provided confidence."""
    return {
        "var": abs(portfolio_value) * (1.0 - confidence),
        "confidence": confidence,
        "description": f"Maximum expected loss at {confidence*100:.0f}% confidence",
    }


@router.post("/sharpe")
async def calculate_sharpe(
    risk_free_rate: float = Query(default=0.02),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Calculate simplified Sharpe ratio from persisted PnL."""
    snapshot = DatabaseBrokerService(db).get_portfolio_snapshot(user_id=current_user.id)
    total_return = snapshot["total_return_pct"] / 100.0
    volatility = 0.20 if snapshot["total_trades"] > 0 else 0.0
    sharpe = ((total_return - risk_free_rate) / volatility) if volatility > 0 else 0.0
    return {
        "sharpe_ratio": sharpe,
        "interpretation": "Good risk-adjusted returns" if sharpe >= 1 else "Moderate risk-adjusted returns",
        "risk_free_rate": risk_free_rate,
    }


@router.get("/health")
async def health_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Risk validator health check."""
    snapshot = DatabaseBrokerService(db).get_portfolio_snapshot(user_id=current_user.id)
    return {
        "status": "healthy",
        "component": "risk_validator",
        "open_positions": snapshot["open_positions"],
    }
