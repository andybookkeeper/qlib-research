# tests/unit/test_db_models.py
"""Unit tests for database models."""

import pytest
from datetime import datetime
from src.qlib_research.app.db.models import (
    Order, Position, Portfolio, OrderStatus, OrderSide, OrderType
)


def test_order_model():
    """Test Order model creation."""
    order = Order(
        id="order-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100
    )
    
    assert order.ticker == "AAPL"
    assert order.side == OrderSide.BUY
    assert order.status == OrderStatus.PENDING
    assert order.filled_quantity == 0


def test_position_model():
    """Test Position model creation."""
    pos = Position(
        id="pos-1",
        ticker="MSFT",
        quantity=50,
        avg_cost=300.0,
        current_price=310.0
    )
    
    assert pos.quantity == 50
    assert pos.unrealized_pnl == 500.0  # (310 - 300) * 50


def test_portfolio_model():
    """Test Portfolio model creation."""
    portfolio = Portfolio(
        id="main",
        cash_balance=100000.0,
        total_market_value=50000.0
    )
    
    assert portfolio.cash_balance == 100000.0
    assert portfolio.total_market_value == 50000.0
    assert portfolio.cash_balance + portfolio.total_market_value == 150000.0


def test_order_repr():
    """Test Order string representation."""
    order = Order(
        id="order-1",
        ticker="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=100,
        limit_price=150.0,
        status=OrderStatus.PENDING
    )
    
    repr_str = repr(order)
    assert "AAPL" in repr_str
    assert "buy" in repr_str
    assert "100" in repr_str
