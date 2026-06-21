"""Broker service API endpoints (database-backed)."""

import json
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.qlib_research.app.api.schemas.broker import (
    ClosedTradeResponse,
    OrderRequest,
    OrderResponse,
    PortfolioResponse,
    PortfolioStatsResponse,
    PositionResponse,
)
from src.qlib_research.app.db import get_db
from src.qlib_research.app.api.dependencies import get_current_active_user
from src.qlib_research.app.models.database import User
from src.qlib_research.app.services.broker_service import DatabaseBrokerService
from src.qlib_research.app.services.realtime_service import realtime_hub

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


def _order_response(order) -> OrderResponse:
    return OrderResponse(
        order_id=str(order.id),
        ticker=order.symbol,
        side=str(order.side).lower(),
        quantity=float(order.quantity),
        order_type=str(order.order_type).lower(),
        status=str(order.status).lower(),
        filled_quantity=float(order.quantity if str(order.status).upper() == "FILLED" else 0),
        filled_price=float(order.fill_price) if order.fill_price is not None else None,
        created_at=order.created_at.isoformat(),
    )


@router.post("/orders")
async def place_order(
    request: OrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderResponse:
    """Place an order and persist it."""
    service = DatabaseBrokerService(db)
    order = service.create_order(
        ticker=request.ticker,
        side=request.side,
        quantity=request.quantity,
        order_type=request.order_type,
        price=request.price,
        stop_price=request.stop_price,
        current_price=100.0 if request.order_type.lower() == "market" else None,
        user_id=current_user.id,
    )

    await realtime_hub.broadcast(
        event_type="order_update",
        data={
            "order_id": str(order.id),
            "ticker": order.symbol,
            "side": str(order.side).lower(),
            "order_type": str(order.order_type).lower(),
            "status": str(order.status).lower(),
            "filled_price": float(order.fill_price) if order.fill_price is not None else None,
            "filled_quantity": float(order.quantity if str(order.status).upper() == "FILLED" else 0),
        },
        ticker=order.symbol,
        user_id=current_user.id,
    )
    return _order_response(order)


@router.get("/orders")
async def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[OrderResponse]:
    """Get recent orders for current user."""
    service = DatabaseBrokerService(db)
    return [_order_response(order) for order in service.get_orders(user_id=current_user.id)]


@router.post("/orders/{order_id}/execute")
async def execute_pending_order(
    order_id: str,
    current_price: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderResponse:
    """Execute pending limit/stop order at current price."""
    service = DatabaseBrokerService(db)
    try:
        order = service.fill_order(int(order_id), current_price, user_id=current_user.id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Order not found")

    await realtime_hub.broadcast(
        event_type="order_update",
        data={
            "order_id": str(order.id),
            "ticker": order.symbol,
            "side": str(order.side).lower(),
            "order_type": str(order.order_type).lower(),
            "status": str(order.status).lower(),
            "filled_price": float(order.fill_price) if order.fill_price is not None else None,
            "filled_quantity": float(order.quantity if str(order.status).upper() == "FILLED" else 0),
        },
        ticker=order.symbol,
        user_id=current_user.id,
    )
    return _order_response(order)


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderResponse:
    """Get order status by id."""
    service = DatabaseBrokerService(db)
    order = service.get_order(int(order_id), user_id=current_user.id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_response(order)


@router.get("/portfolio")
async def get_portfolio(
    current_prices: Optional[str] = Query(default=None, description="JSON string map of symbol->price"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioResponse:
    """Get current portfolio state."""
    service = DatabaseBrokerService(db)
    snapshot = service.get_portfolio_snapshot(_parse_prices(current_prices), user_id=current_user.id)

    return PortfolioResponse(
        initial_cash=snapshot["initial_cash"],
        current_cash=snapshot["current_cash"],
        positions=[PositionResponse(**position) for position in snapshot["positions"]],
        statistics=PortfolioStatsResponse(
            initial_cash=snapshot["initial_cash"],
            current_cash=snapshot["current_cash"],
            portfolio_value=snapshot["portfolio_value"],
            position_value=snapshot["position_value"],
            total_pnl=snapshot["total_pnl"],
            total_return_pct=snapshot["total_return_pct"],
            realized_pnl=snapshot["realized_pnl"],
            unrealized_pnl=snapshot["unrealized_pnl"],
            total_trades=snapshot["total_trades"],
            winning_trades=snapshot["winning_trades"],
            losing_trades=snapshot["losing_trades"],
            win_rate=snapshot["win_rate"],
            avg_win=snapshot["avg_win"],
            avg_loss=snapshot["avg_loss"],
            profit_factor=snapshot["profit_factor"],
            avg_holding_days=snapshot["avg_holding_days"],
            open_positions=snapshot["open_positions"],
        ),
        closed_trades=[
            ClosedTradeResponse(
                trade_id=str(trade.id),
                ticker=trade.symbol,
                side="buy" if int(trade.quantity) > 0 else "sell",
                entry_date=trade.executed_at.isoformat() if trade.executed_at else "",
                entry_price=float(trade.execution_price),
                entry_quantity=float(abs(int(trade.quantity))),
                exit_date=trade.executed_at.isoformat() if trade.executed_at else "",
                exit_price=float(trade.execution_price),
                exit_quantity=float(abs(int(trade.quantity))),
                realized_pnl=float(trade.gross_pnl) if trade.gross_pnl is not None else 0.0,
                realized_pnl_pct=0.0,
                holding_days=0,
            )
            for trade in service.get_trades(user_id=current_user.id)
        ],
    )


@router.get("/positions")
async def get_positions(
    current_prices: Optional[str] = Query(default=None, description="JSON string map of symbol->price"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[PositionResponse]:
    """Get all open positions."""
    prices = _parse_prices(current_prices)
    service = DatabaseBrokerService(db)
    positions = []
    for position in service.get_positions(user_id=current_user.id):
        market_price = prices.get(position.symbol, float(position.current_price))
        entry = float(position.entry_price)
        quantity = int(position.quantity)
        pnl = (market_price - entry) * quantity
        pnl_pct = ((market_price - entry) / entry * 100.0) if entry else 0.0
        positions.append(
            PositionResponse(
                ticker=position.symbol,
                quantity=float(quantity),
                entry_price=entry,
                current_price=market_price,
                cost_basis=abs(entry * quantity),
                market_value=market_price * quantity,
                unrealized_pnl=pnl,
                unrealized_pnl_pct=pnl_pct,
                is_long=quantity > 0,
                is_short=quantity < 0,
            )
        )
    return positions


@router.get("/positions/{ticker}")
async def get_position(
    ticker: str,
    current_prices: Optional[str] = Query(default=None, description="JSON string map of symbol->price"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PositionResponse:
    """Get single position by ticker."""
    prices = _parse_prices(current_prices)
    service = DatabaseBrokerService(db)
    position = service.get_position(ticker, user_id=current_user.id)
    if position is None:
        raise HTTPException(status_code=404, detail=f"No position in {ticker}")
    market_price = prices.get(position.symbol, float(position.current_price))
    entry = float(position.entry_price)
    quantity = int(position.quantity)
    pnl = (market_price - entry) * quantity
    pnl_pct = ((market_price - entry) / entry * 100.0) if entry else 0.0
    return PositionResponse(
        ticker=position.symbol,
        quantity=float(quantity),
        entry_price=entry,
        current_price=market_price,
        cost_basis=abs(entry * quantity),
        market_value=market_price * quantity,
        unrealized_pnl=pnl,
        unrealized_pnl_pct=pnl_pct,
        is_long=quantity > 0,
        is_short=quantity < 0,
    )


@router.get("/trades/closed")
async def get_closed_trades(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[ClosedTradeResponse]:
    """Get all persisted trades."""
    service = DatabaseBrokerService(db)
    return [
        ClosedTradeResponse(
            trade_id=str(trade.id),
            ticker=trade.symbol,
            side="buy" if int(trade.quantity) > 0 else "sell",
            entry_date=trade.executed_at.isoformat() if trade.executed_at else "",
            entry_price=float(trade.execution_price),
            entry_quantity=float(abs(int(trade.quantity))),
            exit_date=trade.executed_at.isoformat() if trade.executed_at else "",
            exit_price=float(trade.execution_price),
            exit_quantity=float(abs(int(trade.quantity))),
            realized_pnl=float(trade.gross_pnl) if trade.gross_pnl is not None else 0.0,
            realized_pnl_pct=0.0,
            holding_days=0,
        )
        for trade in service.get_trades(user_id=current_user.id)
    ]


@router.get("/statistics")
async def get_statistics(
    current_prices: Optional[str] = Query(default=None, description="JSON string map of symbol->price"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioStatsResponse:
    """Get persisted portfolio statistics."""
    service = DatabaseBrokerService(db)
    snapshot = service.get_portfolio_snapshot(_parse_prices(current_prices), user_id=current_user.id)
    return PortfolioStatsResponse(
        initial_cash=snapshot["initial_cash"],
        current_cash=snapshot["current_cash"],
        portfolio_value=snapshot["portfolio_value"],
        position_value=snapshot["position_value"],
        total_pnl=snapshot["total_pnl"],
        total_return_pct=snapshot["total_return_pct"],
        realized_pnl=snapshot["realized_pnl"],
        unrealized_pnl=snapshot["unrealized_pnl"],
        total_trades=snapshot["total_trades"],
        winning_trades=snapshot["winning_trades"],
        losing_trades=snapshot["losing_trades"],
        win_rate=snapshot["win_rate"],
        avg_win=snapshot["avg_win"],
        avg_loss=snapshot["avg_loss"],
        profit_factor=snapshot["profit_factor"],
        avg_holding_days=snapshot["avg_holding_days"],
        open_positions=snapshot["open_positions"],
    )


@router.post("/reset")
async def reset_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reset default portfolio and all associated trades/orders/positions."""
    service = DatabaseBrokerService(db)
    service.reset(user_id=current_user.id)
    await realtime_hub.broadcast(
        event_type="portfolio_reset",
        data={"message": "Portfolio reset"},
        user_id=current_user.id,
    )
    return {"message": "Portfolio reset"}
