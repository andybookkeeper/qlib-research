# tests/unit/test_db_operations.py
"""Unit tests for database operations."""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.qlib_research.app.db.models import Base, OrderSide, OrderType, OrderStatus
from src.qlib_research.app.db.operations import (
    OrderOperations,
    PositionOperations,
    PortfolioOperations
)


@pytest.fixture
def db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()


def test_create_order(db):
    """Test creating an order."""
    order = OrderOperations.create_order(
        db,
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=100,
        order_type=OrderType.MARKET
    )
    
    assert order.id is not None
    assert order.ticker == "AAPL"
    assert order.quantity == 100
    assert order.status == OrderStatus.PENDING


def test_get_active_orders(db):
    """Test fetching active orders."""
    # Create multiple orders
    OrderOperations.create_order(db, "AAPL", OrderSide.BUY, 100)
    OrderOperations.create_order(db, "MSFT", OrderSide.SELL, 50)
    
    active = OrderOperations.get_active_orders(db)
    
    assert len(active) == 2
    assert all(o.status == OrderStatus.PENDING for o in active)


def test_update_order_status(db):
    """Test updating order status."""
    order = OrderOperations.create_order(
        db, "AAPL", OrderSide.BUY, 100, OrderType.MARKET
    )
    
    updated = OrderOperations.update_order_status(
        db,
        order.id,
        OrderStatus.FILLED,
        filled_quantity=100,
        average_fill_price=150.0
    )
    
    assert updated.status == OrderStatus.FILLED
    assert updated.average_fill_price == 150.0


def test_position_operations(db):
    """Test position creation and update."""
    pos = PositionOperations.get_or_create_position(db, "AAPL")
    
    assert pos.ticker == "AAPL"
    assert pos.quantity == 0
    
    # Update position
    updated = PositionOperations.update_position(
        db, "AAPL", quantity=100, avg_cost=150.0, current_price=155.0
    )
    
    assert updated.quantity == 100
    assert updated.avg_cost == 150.0
    assert updated.unrealized_pnl == 500.0


def test_portfolio_operations(db):
    """Test portfolio operations."""
    portfolio = PortfolioOperations.get_portfolio(db)
    
    assert portfolio.id == "main"
    assert portfolio.cash_balance == 100000.0
    
    # Update portfolio
    updated = PortfolioOperations.update_portfolio_values(
        db, cash=90000.0, market_value=15000.0
    )
    
    assert updated.cash_balance == 90000.0
    assert updated.total_market_value == 15000.0
