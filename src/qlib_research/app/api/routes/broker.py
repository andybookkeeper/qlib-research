# src/qlib_research/app/api/routes/broker.py
"""Broker service API endpoints."""

from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException

from src.qlib_research.app.api.schemas.broker import (
    OrderRequest,
    OrderResponse,
    PositionResponse,
    PortfolioResponse,
    PortfolioStatsResponse,
    ClosedTradeResponse
)
from src.qlib_research.app.services.broker_service import (
    OrderExecutor,
    PortfolioTracker,
    Order,
    OrderSide,
    OrderType,
    OrderStatus
)
import uuid

router = APIRouter()

# In-memory portfolio (in production: use database)
portfolio = PortfolioTracker(initial_cash=100000)
executor = OrderExecutor(commission_rate=0.001)

# In-memory order book
pending_orders: Dict[str, Order] = {}


@router.post("/orders")
async def place_order(
    request: OrderRequest
) -> OrderResponse:
    """
    Place an order (market, limit, or stop).
    
    For market orders: Fills immediately
    For limit orders: Queued until price hit
    For stop orders: Triggered on stop price
    """
    
    # Create order
    order = Order(
        order_id=str(uuid.uuid4())[:8],
        ticker=request.ticker,
        side=OrderSide[request.side.upper()],
        quantity=request.quantity,
        order_type=OrderType[request.order_type.upper()],
        price=request.price,
        stop_price=request.stop_price,
        limit_price=request.limit_price
    )
    
    # Execute based on type
    if order.order_type == OrderType.MARKET:
        # Market orders need current price
        # For now, assume it's filled at a mock price
        current_price = 100.0  # Mock price - should come from market data
        order = executor.execute_market_order(order, current_price)
        
        if order.status == OrderStatus.FILLED:
            portfolio.add_trade(order, request.ticker)
    
    else:
        # Queue limit/stop orders
        pending_orders[order.order_id] = order
    
    return OrderResponse(
        order_id=order.order_id,
        ticker=order.ticker,
        side=order.side.value,
        quantity=order.quantity,
        order_type=order.order_type.value,
        status=order.status.value,
        filled_quantity=order.filled_quantity,
        filled_price=order.filled_price,
        created_at=order.created_at.isoformat()
    )


@router.post("/orders/{order_id}/execute")
async def execute_pending_order(
    order_id: str,
    current_price: float
) -> OrderResponse:
    """
    Execute pending limit/stop order at current price.
    """
    
    if order_id not in pending_orders:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = pending_orders[order_id]
    
    if order.order_type == OrderType.LIMIT:
        order = executor.execute_limit_order(order, current_price)
    elif order.order_type == OrderType.STOP:
        order = executor.execute_stop_order(order, current_price)
    
    if order.status == OrderStatus.FILLED:
        portfolio.add_trade(order, order.ticker)
        del pending_orders[order_id]
    
    return OrderResponse(
        order_id=order.order_id,
        ticker=order.ticker,
        side=order.side.value,
        quantity=order.quantity,
        order_type=order.order_type.value,
        status=order.status.value,
        filled_quantity=order.filled_quantity,
        filled_price=order.filled_price,
        created_at=order.created_at.isoformat()
    )


@router.get("/orders/{order_id}")
async def get_order(order_id: str) -> OrderResponse:
    """Get order status."""
    
    # Check filled orders
    for order in executor.filled_orders:
        if order.order_id == order_id:
            return OrderResponse(
                order_id=order.order_id,
                ticker=order.ticker,
                side=order.side.value,
                quantity=order.quantity,
                order_type=order.order_type.value,
                status=order.status.value,
                filled_quantity=order.filled_quantity,
                filled_price=order.filled_price,
                created_at=order.created_at.isoformat()
            )
    
    # Check pending orders
    if order_id in pending_orders:
        order = pending_orders[order_id]
        return OrderResponse(
            order_id=order.order_id,
            ticker=order.ticker,
            side=order.side.value,
            quantity=order.quantity,
            order_type=order.order_type.value,
            status=order.status.value,
            filled_quantity=order.filled_quantity,
            filled_price=order.filled_price,
            created_at=order.created_at.isoformat()
        )
    
    raise HTTPException(status_code=404, detail="Order not found")


@router.get("/portfolio")
async def get_portfolio(
    current_prices: Dict[str, float] = None
) -> PortfolioResponse:
    """Get current portfolio state."""
    
    if current_prices is None:
        current_prices = {}
    
    stats = portfolio.get_statistics(current_prices)
    
    return PortfolioResponse(
        initial_cash=portfolio.initial_cash,
        current_cash=portfolio.cash,
        positions=[
            PositionResponse(
                ticker=ticker,
                quantity=pos.quantity,
                entry_price=pos.entry_price,
                current_price=current_prices.get(ticker, pos.entry_price),
                cost_basis=pos.get_cost_basis(),
                market_value=pos.quantity * current_prices.get(ticker, pos.entry_price),
                unrealized_pnl=pos.calculate_pnl(current_prices.get(ticker, pos.entry_price))[0],
                unrealized_pnl_pct=pos.calculate_pnl(current_prices.get(ticker, pos.entry_price))[1],
                is_long=pos.is_long,
                is_short=pos.is_short
            )
            for ticker, pos in portfolio.positions.items()
            if not pos.is_flat
        ],
        statistics=PortfolioStatsResponse(**stats),
        closed_trades=[
            ClosedTradeResponse(**trade.to_dict())
            for trade in portfolio.closed_trades
        ]
    )


@router.get("/positions")
async def get_positions(
    current_prices: Dict[str, float] = None
) -> List[PositionResponse]:
    """Get all open positions."""
    
    if current_prices is None:
        current_prices = {}
    
    positions = []
    for ticker, pos in portfolio.positions.items():
        if not pos.is_flat:
            current_price = current_prices.get(ticker, pos.entry_price)
            pnl, pnl_pct = pos.calculate_pnl(current_price)
            
            positions.append(PositionResponse(
                ticker=ticker,
                quantity=pos.quantity,
                entry_price=pos.entry_price,
                current_price=current_price,
                cost_basis=pos.get_cost_basis(),
                market_value=pos.quantity * current_price,
                unrealized_pnl=pnl,
                unrealized_pnl_pct=pnl_pct,
                is_long=pos.is_long,
                is_short=pos.is_short
            ))
    
    return positions


@router.get("/positions/{ticker}")
async def get_position(
    ticker: str,
    current_prices: Dict[str, float] = None
) -> PositionResponse:
    """Get single position."""
    
    if ticker not in portfolio.positions or portfolio.positions[ticker].is_flat:
        raise HTTPException(status_code=404, detail=f"No position in {ticker}")
    
    if current_prices is None:
        current_prices = {}
    
    pos = portfolio.positions[ticker]
    current_price = current_prices.get(ticker, pos.entry_price)
    pnl, pnl_pct = pos.calculate_pnl(current_price)
    
    return PositionResponse(
        ticker=ticker,
        quantity=pos.quantity,
        entry_price=pos.entry_price,
        current_price=current_price,
        cost_basis=pos.get_cost_basis(),
        market_value=pos.quantity * current_price,
        unrealized_pnl=pnl,
        unrealized_pnl_pct=pnl_pct,
        is_long=pos.is_long,
        is_short=pos.is_short
    )


@router.get("/trades/closed")
async def get_closed_trades() -> List[ClosedTradeResponse]:
    """Get all closed trades."""
    
    return [
        ClosedTradeResponse(**trade.to_dict())
        for trade in portfolio.closed_trades
    ]


@router.get("/statistics")
async def get_statistics(
    current_prices: Dict[str, float] = None
) -> PortfolioStatsResponse:
    """Get portfolio statistics."""
    
    if current_prices is None:
        current_prices = {}
    
    stats = portfolio.get_statistics(current_prices)
    
    return PortfolioStatsResponse(**stats)


@router.post("/reset")
async def reset_portfolio():
    """Reset portfolio to initial state (for testing)."""
    
    global portfolio, executor
    
    portfolio = PortfolioTracker(initial_cash=100000)
    executor = OrderExecutor(commission_rate=0.001)
    
    return {"message": "Portfolio reset"}

