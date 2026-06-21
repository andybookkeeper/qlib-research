"""Unified portfolio view endpoints (database-backed)."""

import json
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.qlib_research.app.api.dependencies import get_current_active_user
from src.qlib_research.app.db import get_db
from src.qlib_research.app.models.database import User
from src.qlib_research.app.services.broker_service import DatabaseBrokerService

router = APIRouter()


def _parse_prices(current_prices: Optional[str]) -> Dict[str, float]:
    if not current_prices:
        return {}
    try:
        payload = json.loads(current_prices)
        if isinstance(payload, dict):
            return {str(k).upper(): float(v) for k, v in payload.items()}
    except Exception:
        return {}
    return {}


@router.get("/overview")
async def get_portfolio_overview(
    current_prices: Optional[str] = Query(default=None, description="JSON string map of symbol->price"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict:
    """Get complete portfolio overview."""
    snapshot = DatabaseBrokerService(db).get_portfolio_snapshot(_parse_prices(current_prices), user_id=current_user.id)
    return {
        "portfolio_value": snapshot["portfolio_value"],
        "cash": snapshot["current_cash"],
        "gross_value": snapshot["position_value"],
        "net_value": snapshot["portfolio_value"],
        "realized_pnl": snapshot["realized_pnl"],
        "unrealized_pnl": snapshot["unrealized_pnl"],
        "total_pnl": snapshot["total_pnl"],
        "total_pnl_pct": snapshot["total_return_pct"],
        "open_positions": snapshot["open_positions"],
        "total_trades": snapshot["total_trades"],
    }


@router.get("/dashboard")
async def get_dashboard(
    current_prices: Optional[str] = Query(default=None, description="JSON string map of symbol->price"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict:
    """Get full dashboard with all metrics."""
    snapshot = DatabaseBrokerService(db).get_portfolio_snapshot(_parse_prices(current_prices), user_id=current_user.id)
    return {
        "portfolio_value": snapshot["portfolio_value"],
        "cash": snapshot["current_cash"],
        "var_95": abs(snapshot["portfolio_value"]) * 0.05,
        "max_drawdown": 0.0,
        "sharpe_ratio": 0.0,
        "positions": snapshot["positions"],
        "risk_warnings": [],
    }


@router.get("/performance")
async def get_performance(
    current_prices: Optional[str] = Query(default=None, description="JSON string map of symbol->price"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict:
    """Get performance metrics."""
    snapshot = DatabaseBrokerService(db).get_portfolio_snapshot(_parse_prices(current_prices), user_id=current_user.id)
    return {
        "daily_returns": [],
        "cumulative_returns": snapshot["total_return_pct"] / 100.0,
        "volatility": 0.0,
        "risk_free_rate": 0.02,
    }
