"""Broker service API endpoints (database-backed)."""

import json
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.qlib_research.app.api.dependencies import (
    get_broker_adapter,
    get_broker_reconciliation_service,
    get_strategy_automation_service,
    get_current_active_user,
)
from src.qlib_research.app.api.schemas.broker import (
    ClosedTradeResponse,
    OrderRequest,
    OrderResponse,
    PortfolioResponse,
    PortfolioStatsResponse,
    PositionResponse,
    StrategyProposalExecuteRequest,
    StrategyProposalRequest,
)
from src.qlib_research.app.config import get_phase3_feature_flags
from src.qlib_research.app.models.database import User
from src.qlib_research.app.services.broker_adapter import BrokerAdapter
from src.qlib_research.app.services.broker_reconciliation_service import BrokerReconciliationService
from src.qlib_research.app.services.realtime_service import realtime_hub
from src.qlib_research.app.services.strategy_automation_service import StrategyAutomationService

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
        rejected_reason=order.rejected_reason,
        created_at=order.created_at.isoformat(),
    )


def _require_strategy_automation_enabled() -> dict[str, bool]:
    flags = get_phase3_feature_flags()
    if not flags["enable_strategy_automation"]:
        raise HTTPException(
            status_code=503,
            detail="Strategy automation is disabled. Set PHASE3_ENABLE_STRATEGY_AUTOMATION=true to enable.",
        )
    return flags


@router.post("/orders")
async def place_order(
    request: OrderRequest,
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
) -> OrderResponse:
    """Place an order and persist it."""
    order = broker.create_order(
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
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
) -> List[OrderResponse]:
    """Get recent orders for current user."""
    return [_order_response(order) for order in broker.get_orders(user_id=current_user.id)]


@router.post("/orders/{order_id}/execute")
async def execute_pending_order(
    order_id: str,
    current_price: float,
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
) -> OrderResponse:
    """Execute pending limit/stop order at current price."""
    try:
        order = broker.fill_order(int(order_id), current_price, user_id=current_user.id)
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
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
) -> OrderResponse:
    """Get order status by id."""
    order = broker.get_order(int(order_id), user_id=current_user.id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return _order_response(order)


@router.get("/portfolio")
async def get_portfolio(
    current_prices: Optional[str] = Query(default=None, description="JSON string map of symbol->price"),
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioResponse:
    """Get current portfolio state."""
    snapshot = broker.get_portfolio_snapshot(_parse_prices(current_prices), user_id=current_user.id)

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
            for trade in broker.get_trades(user_id=current_user.id)
        ],
    )


@router.get("/positions")
async def get_positions(
    current_prices: Optional[str] = Query(default=None, description="JSON string map of symbol->price"),
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
) -> List[PositionResponse]:
    """Get all open positions."""
    prices = _parse_prices(current_prices)
    positions = []
    for position in broker.get_positions(user_id=current_user.id):
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
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
) -> PositionResponse:
    """Get single position by ticker."""
    prices = _parse_prices(current_prices)
    position = broker.get_position(ticker, user_id=current_user.id)
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
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
) -> List[ClosedTradeResponse]:
    """Get all persisted trades."""
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
        for trade in broker.get_trades(user_id=current_user.id)
    ]


@router.get("/statistics")
async def get_statistics(
    current_prices: Optional[str] = Query(default=None, description="JSON string map of symbol->price"),
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
) -> PortfolioStatsResponse:
    """Get persisted portfolio statistics."""
    snapshot = broker.get_portfolio_snapshot(_parse_prices(current_prices), user_id=current_user.id)
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
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
):
    """Reset default portfolio and all associated trades/orders/positions."""
    broker.reset(user_id=current_user.id)
    await realtime_hub.broadcast(
        event_type="portfolio_reset",
        data={"message": "Portfolio reset"},
        user_id=current_user.id,
    )
    return {"message": "Portfolio reset"}


@router.get("/live/status")
async def get_live_adapter_status(
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
):
    """Get current broker adapter connectivity and execution mode status."""
    _ = current_user
    return broker.get_connection_status()


@router.get("/live/account")
async def get_live_account_snapshot(
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
):
    """Get broker account snapshot (read-only in Phase 3 skeleton mode)."""
    return broker.get_account_snapshot(user_id=current_user.id)


@router.post("/live/sync")
async def sync_live_account_snapshot(
    broker: BrokerAdapter = Depends(get_broker_adapter),
    current_user: User = Depends(get_current_active_user),
):
    """Run a safe account sync operation for adapter-level visibility."""
    return broker.sync_account_snapshot(user_id=current_user.id)


@router.get("/live/reconciliation")
async def get_live_reconciliation(
    broker: BrokerAdapter = Depends(get_broker_adapter),
    reconciliation: BrokerReconciliationService = Depends(get_broker_reconciliation_service),
    current_user: User = Depends(get_current_active_user),
):
    """Run backtest-live reconciliation when the feature flag is enabled."""
    flags = get_phase3_feature_flags()
    if not flags["enable_broker_reconciliation"]:
        raise HTTPException(
            status_code=503,
            detail="Broker reconciliation is disabled. Set PHASE3_ENABLE_BROKER_RECONCILIATION=true to enable.",
        )
    return reconciliation.reconcile(broker=broker, user_id=current_user.id)


@router.get("/live/reconciliation/history")
async def get_live_reconciliation_history(
    limit: int = Query(default=20, ge=1, le=100),
    reconciliation: BrokerReconciliationService = Depends(get_broker_reconciliation_service),
    current_user: User = Depends(get_current_active_user),
):
    """Get recent reconciliation snapshots for observability."""
    _ = current_user
    flags = get_phase3_feature_flags()
    if not flags["enable_broker_reconciliation"]:
        raise HTTPException(
            status_code=503,
            detail="Broker reconciliation is disabled. Set PHASE3_ENABLE_BROKER_RECONCILIATION=true to enable.",
        )
    return reconciliation.list_recent(limit=limit)


@router.post("/automation/proposals")
async def create_strategy_proposal(
    request: StrategyProposalRequest,
    automation: StrategyAutomationService = Depends(get_strategy_automation_service),
    current_user: User = Depends(get_current_active_user),
):
    """Create a strategy-generated proposal without executing a trade."""
    flags = _require_strategy_automation_enabled()
    proposal = automation.create_proposal(
        user_id=current_user.id,
        ticker=request.ticker,
        side=request.side,
        quantity=request.quantity,
        confidence=request.confidence,
        rationale=request.rationale,
        suggested_price=request.suggested_price,
    )
    proposal["manual_confirmation_required"] = bool(flags["enforce_manual_trade_confirmation"])
    return proposal


@router.get("/automation/proposals")
async def list_strategy_proposals(
    limit: int = Query(default=50, ge=1, le=100),
    automation: StrategyAutomationService = Depends(get_strategy_automation_service),
    current_user: User = Depends(get_current_active_user),
):
    """List strategy proposals for the current user."""
    _require_strategy_automation_enabled()
    return automation.list_proposals(user_id=current_user.id, limit=limit)


@router.post("/automation/proposals/{proposal_id}/execute")
async def execute_strategy_proposal(
    proposal_id: str,
    request: StrategyProposalExecuteRequest,
    broker: BrokerAdapter = Depends(get_broker_adapter),
    automation: StrategyAutomationService = Depends(get_strategy_automation_service),
    current_user: User = Depends(get_current_active_user),
):
    """Execute a proposal as an order with manual confirmation enforcement."""
    flags = _require_strategy_automation_enabled()
    proposal = automation.get_proposal(proposal_id=proposal_id, user_id=current_user.id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Strategy proposal not found")
    if proposal["status"] != "proposed":
        raise HTTPException(status_code=400, detail="Strategy proposal is not executable")

    if flags["enforce_manual_trade_confirmation"] and request.confirmation_text != "CONFIRM":
        raise HTTPException(
            status_code=400,
            detail="Manual confirmation required. Submit confirmation_text='CONFIRM' to execute.",
        )

    order = broker.create_order(
        ticker=str(proposal["ticker"]),
        side=str(proposal["side"]),
        quantity=float(proposal["quantity"]),
        order_type="market",
        current_price=request.current_price or proposal.get("suggested_price"),
        user_id=current_user.id,
    )
    updated = automation.mark_executed(proposal_id=proposal_id, user_id=current_user.id, order_id=str(order.id))
    return {
        "proposal": updated,
        "order": _order_response(order),
    }
