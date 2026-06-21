# tests/unit/test_broker_service.py
"""Unit tests for broker service."""

import pytest
from datetime import datetime, timedelta

from src.qlib_research.app.services.broker_service import (
    Order,
    OrderType,
    OrderSide,
    OrderStatus,
    Position,
    ClosedTrade,
    OrderExecutor,
    PortfolioTracker
)


class TestOrder:
    """Test order model."""
    
    def test_order_creation(self):
        """Test order creation."""
        order = Order(
            order_id="order1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        assert order.order_id == "order1"
        assert order.ticker == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.status == OrderStatus.PENDING
    
    def test_order_to_dict(self):
        """Test order serialization."""
        order = Order(
            order_id="order1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            filled_quantity=100,
            filled_price=150.0,
            status=OrderStatus.FILLED
        )
        
        d = order.to_dict()
        
        assert d['order_id'] == "order1"
        assert d['ticker'] == "AAPL"
        assert d['filled_price'] == 150.0


class TestPosition:
    """Test position model."""
    
    def test_long_position(self):
        """Test long position."""
        pos = Position(
            ticker="AAPL",
            quantity=100,
            entry_price=150.0,
            entry_date=datetime.now()
        )
        
        assert pos.is_long
        assert not pos.is_short
        assert not pos.is_flat
    
    def test_short_position(self):
        """Test short position."""
        pos = Position(
            ticker="AAPL",
            quantity=-50,
            entry_price=150.0,
            entry_date=datetime.now()
        )
        
        assert not pos.is_long
        assert pos.is_short
        assert not pos.is_flat
    
    def test_flat_position(self):
        """Test flat position."""
        pos = Position(
            ticker="AAPL",
            quantity=0,
            entry_price=150.0,
            entry_date=datetime.now()
        )
        
        assert not pos.is_long
        assert not pos.is_short
        assert pos.is_flat
    
    def test_cost_basis(self):
        """Test cost basis calculation."""
        pos = Position(
            ticker="AAPL",
            quantity=100,
            entry_price=150.0,
            entry_date=datetime.now()
        )
        
        assert pos.get_cost_basis() == 15000.0
    
    def test_pnl_calculation_long(self):
        """Test P&L calculation for long position."""
        pos = Position(
            ticker="AAPL",
            quantity=100,
            entry_price=150.0,
            entry_date=datetime.now()
        )
        
        pnl, pnl_pct = pos.calculate_pnl(160.0)
        
        assert pnl == 1000.0  # (160 - 150) * 100
        assert abs(pnl_pct - 6.67) < 0.1
    
    def test_pnl_calculation_short(self):
        """Test P&L calculation for short position."""
        pos = Position(
            ticker="AAPL",
            quantity=-100,
            entry_price=160.0,
            entry_date=datetime.now()
        )
        
        pnl, pnl_pct = pos.calculate_pnl(150.0)
        
        assert pnl == 1000.0  # (150 - 160) * -100 = 1000
        # pnl_pct = ((150 - 160) / 160) * 100 = -6.25%
        assert abs(pnl_pct - (-6.25)) < 1.0


class TestOrderExecutor:
    """Test order execution."""
    
    def test_execute_market_order(self):
        """Test market order execution."""
        executor = OrderExecutor()
        
        order = Order(
            order_id="order1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        filled_order = executor.execute_market_order(order, 150.0)
        
        assert filled_order.status == OrderStatus.FILLED
        assert filled_order.filled_price == 150.0
        assert filled_order.filled_quantity == 100
        assert filled_order.commission > 0  # Commission calculated
    
    def test_execute_limit_order_buy_hit(self):
        """Test limit buy order execution."""
        executor = OrderExecutor()
        
        order = Order(
            order_id="order1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=150.0
        )
        
        filled_order = executor.execute_limit_order(order, 145.0)
        
        assert filled_order.status == OrderStatus.FILLED
        assert filled_order.filled_price == 150.0
    
    def test_execute_limit_order_buy_not_hit(self):
        """Test limit buy order not filled."""
        executor = OrderExecutor()
        
        order = Order(
            order_id="order1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=150.0
        )
        
        filled_order = executor.execute_limit_order(order, 155.0)
        
        assert filled_order.status == OrderStatus.PENDING
    
    def test_execute_stop_order_sell_hit(self):
        """Test stop sell order execution."""
        executor = OrderExecutor()
        
        order = Order(
            order_id="order1",
            ticker="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            order_type=OrderType.STOP,
            stop_price=145.0
        )
        
        # For SELL stop order, triggers when price falls below stop
        filled_order = executor.execute_stop_order(order, 144.0)
        
        assert filled_order.status == OrderStatus.FILLED
        assert filled_order.filled_price == 144.0


class TestPortfolioTracker:
    """Test portfolio tracking."""
    
    def test_initial_state(self):
        """Test initial portfolio state."""
        tracker = PortfolioTracker(initial_cash=100000)
        
        assert tracker.cash == 100000
        assert len(tracker.positions) == 0
        assert len(tracker.closed_trades) == 0
    
    def test_add_long_trade(self):
        """Test adding long position."""
        tracker = PortfolioTracker(initial_cash=100000)
        executor = OrderExecutor()
        
        # Buy 100 shares at 150
        order = Order(
            order_id="order1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        filled = executor.execute_market_order(order, 150.0)
        tracker.add_trade(filled, "AAPL")
        
        assert "AAPL" in tracker.positions
        assert tracker.positions["AAPL"].quantity == 100
        assert tracker.positions["AAPL"].entry_price == 150.0
        assert tracker.cash < 100000  # Cash reduced by purchase
    
    def test_close_long_trade(self):
        """Test closing long position."""
        tracker = PortfolioTracker(initial_cash=100000)
        executor = OrderExecutor()
        
        # Buy 100 shares
        buy_order = Order(
            order_id="order1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        filled_buy = executor.execute_market_order(buy_order, 150.0)
        tracker.add_trade(filled_buy, "AAPL")
        
        # Sell 100 shares at 160
        sell_order = Order(
            order_id="order2",
            ticker="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            order_type=OrderType.MARKET
        )
        filled_sell = executor.execute_market_order(sell_order, 160.0)
        tracker.add_trade(filled_sell, "AAPL")
        
        # Position should be closed
        assert tracker.positions["AAPL"].is_flat
        
        # Trade should be recorded
        assert len(tracker.closed_trades) > 0
        assert tracker.closed_trades[0].realized_pnl > 0
    
    def test_portfolio_value(self):
        """Test portfolio value calculation."""
        tracker = PortfolioTracker(initial_cash=100000)
        executor = OrderExecutor()
        
        # Buy 100 shares at 150
        order = Order(
            order_id="order1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        filled = executor.execute_market_order(order, 150.0)
        tracker.add_trade(filled, "AAPL")
        
        current_prices = {"AAPL": 160.0}
        
        value = tracker.get_portfolio_value(current_prices)
        
        # Should be: remaining cash + position value
        assert value > 0
    
    def test_statistics(self):
        """Test portfolio statistics."""
        tracker = PortfolioTracker(initial_cash=100000)
        executor = OrderExecutor()
        
        # Buy and sell for profit
        buy_order = Order(
            order_id="order1",
            ticker="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        filled_buy = executor.execute_market_order(buy_order, 150.0)
        tracker.add_trade(filled_buy, "AAPL")
        
        sell_order = Order(
            order_id="order2",
            ticker="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            order_type=OrderType.MARKET
        )
        filled_sell = executor.execute_market_order(sell_order, 160.0)
        tracker.add_trade(filled_sell, "AAPL")
        
        current_prices = {}
        stats = tracker.get_statistics(current_prices)
        
        assert stats['total_trades'] == 1
        assert stats['winning_trades'] == 1
        assert stats['realized_pnl'] > 0
