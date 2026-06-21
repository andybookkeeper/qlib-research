# src/qlib_research/app/services/broker_service.py
"""Paper broker service for order execution and portfolio management."""

from datetime import datetime
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

import pandas as pd
import numpy as np


class OrderType(Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order statuses."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(Enum):
    """Order sides."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """Single order."""
    order_id: str
    ticker: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    price: Optional[float] = None  # For limit orders
    stop_price: Optional[float] = None  # For stop orders
    limit_price: Optional[float] = None  # For stop-limit orders
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    commission: float = 0.0  # Filled quantity * filled_price * commission_rate
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'order_id': self.order_id,
            'ticker': self.ticker,
            'side': self.side.value,
            'quantity': self.quantity,
            'order_type': self.order_type.value,
            'price': self.price,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'filled_price': self.filled_price,
            'commission': self.commission,
            'created_at': self.created_at.isoformat(),
            'filled_at': self.filled_at.isoformat() if self.filled_at else None
        }


@dataclass
class Position:
    """Single position in portfolio."""
    ticker: str
    quantity: float  # Positive = long, negative = short
    entry_price: float
    entry_date: datetime
    
    @property
    def is_long(self) -> bool:
        """Is this a long position?"""
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        """Is this a short position?"""
        return self.quantity < 0
    
    @property
    def is_flat(self) -> bool:
        """Is position flat (zero quantity)?"""
        return abs(self.quantity) < 1e-6
    
    def get_cost_basis(self) -> float:
        """Total cost basis (entry_price * quantity)."""
        return abs(self.entry_price * self.quantity)
    
    def calculate_pnl(self, current_price: float) -> Tuple[float, float]:
        """
        Calculate unrealized P&L.
        
        Returns:
            (absolute_pnl, pnl_percent)
        """
        if self.is_flat:
            return 0.0, 0.0
        
        pnl = (current_price - self.entry_price) * self.quantity
        pnl_percent = ((current_price - self.entry_price) / self.entry_price) * 100
        
        return pnl, pnl_percent
    
    def to_dict(self, current_price: float) -> Dict:
        """Convert to dictionary."""
        pnl, pnl_pct = self.calculate_pnl(current_price)
        
        return {
            'ticker': self.ticker,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'entry_date': self.entry_date.isoformat(),
            'current_price': current_price,
            'cost_basis': self.get_cost_basis(),
            'market_value': current_price * self.quantity,
            'unrealized_pnl': pnl,
            'unrealized_pnl_pct': pnl_pct,
            'is_long': self.is_long,
            'is_short': self.is_short
        }


@dataclass
class ClosedTrade:
    """Closed trade (complete round trip)."""
    trade_id: str
    ticker: str
    entry_date: datetime
    entry_price: float
    entry_quantity: float
    exit_date: datetime
    exit_price: float
    exit_quantity: float
    side: OrderSide  # BUY for long, SELL for short
    realized_pnl: float
    realized_pnl_pct: float
    holding_days: int
    commission: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'trade_id': self.trade_id,
            'ticker': self.ticker,
            'side': self.side.value,
            'entry_date': self.entry_date.isoformat(),
            'entry_price': self.entry_price,
            'entry_quantity': self.entry_quantity,
            'exit_date': self.exit_date.isoformat(),
            'exit_price': self.exit_price,
            'exit_quantity': self.exit_quantity,
            'realized_pnl': self.realized_pnl,
            'realized_pnl_pct': self.realized_pnl_pct,
            'holding_days': self.holding_days,
            'commission': self.commission
        }


class OrderExecutor:
    """Executes orders (matches to market prices)."""
    
    def __init__(self, commission_rate: float = 0.001):  # 0.1% default
        self.commission_rate = commission_rate
        self.filled_orders: List[Order] = []
    
    def execute_market_order(
        self,
        order: Order,
        current_price: float
    ) -> Order:
        """
        Execute market order (instant fill at current price).
        
        Args:
            order: Order to fill
            current_price: Current market price
        
        Returns:
            Filled order
        """
        # Calculate commission
        commission = current_price * order.quantity * self.commission_rate
        
        # Fill order
        order.filled_price = current_price
        order.filled_quantity = order.quantity
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()
        order.commission = commission
        
        self.filled_orders.append(order)
        
        return order
    
    def execute_limit_order(
        self,
        order: Order,
        current_price: float
    ) -> Order:
        """
        Execute limit order (fill if price crosses limit).
        
        Args:
            order: Limit order
            current_price: Current market price
        
        Returns:
            Order (may still be pending)
        """
        if order.price is None:
            order.status = OrderStatus.REJECTED
            return order
        
        # Check if limit is hit
        can_fill = False
        
        if order.side == OrderSide.BUY and current_price <= order.price:
            can_fill = True
        elif order.side == OrderSide.SELL and current_price >= order.price:
            can_fill = True
        
        if can_fill:
            # Fill at limit price (better for trader)
            commission = order.price * order.quantity * self.commission_rate
            
            order.filled_price = order.price
            order.filled_quantity = order.quantity
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.now()
            order.commission = commission
            
            self.filled_orders.append(order)
        
        return order
    
    def execute_stop_order(
        self,
        order: Order,
        current_price: float
    ) -> Order:
        """
        Execute stop order (becomes market order if triggered).
        
        Args:
            order: Stop order
            current_price: Current market price
        
        Returns:
            Order (may still be pending)
        """
        if order.stop_price is None:
            order.status = OrderStatus.REJECTED
            return order
        
        # Check if stop is hit
        triggered = False
        
        # BUY stop: buy when price rises above stop
        if order.side == OrderSide.BUY and current_price >= order.stop_price:
            triggered = True
        # SELL stop: sell when price falls below stop
        elif order.side == OrderSide.SELL and current_price <= order.stop_price:
            triggered = True
        
        if triggered:
            # Convert to market order
            commission = current_price * order.quantity * self.commission_rate
            
            order.filled_price = current_price
            order.filled_quantity = order.quantity
            order.status = OrderStatus.FILLED
            order.filled_at = datetime.now()
            order.commission = commission
            
            self.filled_orders.append(order)
        
        return order


class PortfolioTracker:
    """Tracks positions and calculates portfolio metrics."""
    
    def __init__(self, initial_cash: float = 100000):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.closed_trades: List[ClosedTrade] = []
        self.trade_history: List[Order] = []
    
    def add_trade(self, order: Order, ticker: str) -> None:
        """
        Process filled order and update positions.
        
        Args:
            order: Filled order
            ticker: Ticker symbol
        """
        if order.status != OrderStatus.FILLED:
            return
        
        # Update cash
        trade_value = order.filled_price * order.filled_quantity
        if order.side == OrderSide.BUY:
            self.cash -= trade_value + order.commission
        else:  # SELL
            self.cash += trade_value - order.commission
        
        # Update position
        if ticker not in self.positions:
            # Open new position
            self.positions[ticker] = Position(
                ticker=ticker,
                quantity=order.filled_quantity if order.side == OrderSide.BUY else -order.filled_quantity,
                entry_price=order.filled_price,
                entry_date=order.filled_at or datetime.now()
            )
        else:
            # Modify existing position
            current_pos = self.positions[ticker]
            
            if order.side == OrderSide.BUY:
                # Buying
                if current_pos.is_long or current_pos.is_flat:
                    # Add to long position
                    avg_price = (current_pos.entry_price * abs(current_pos.quantity) + 
                                order.filled_price * order.filled_quantity) / (abs(current_pos.quantity) + order.filled_quantity)
                    current_pos.entry_price = avg_price
                    current_pos.quantity += order.filled_quantity
                else:
                    # Cover short position
                    closed_qty = min(abs(current_pos.quantity), order.filled_quantity)
                    exit_pnl = (current_pos.entry_price - order.filled_price) * closed_qty
                    exit_pnl_pct = ((current_pos.entry_price - order.filled_price) / current_pos.entry_price) * 100
                    holding_days = (order.filled_at - current_pos.entry_date).days
                    
                    # Record closed trade
                    trade = ClosedTrade(
                        trade_id=str(uuid.uuid4())[:8],
                        ticker=ticker,
                        entry_date=current_pos.entry_date,
                        entry_price=current_pos.entry_price,
                        entry_quantity=closed_qty,
                        exit_date=order.filled_at or datetime.now(),
                        exit_price=order.filled_price,
                        exit_quantity=closed_qty,
                        side=OrderSide.SELL,
                        realized_pnl=exit_pnl,
                        realized_pnl_pct=exit_pnl_pct,
                        holding_days=max(holding_days, 1),
                        commission=order.commission
                    )
                    self.closed_trades.append(trade)
                    
                    # Update position
                    current_pos.quantity += order.filled_quantity
                    if current_pos.quantity > 0:
                        # New long position from extra quantity
                        current_pos.entry_price = order.filled_price
                        current_pos.entry_date = order.filled_at or datetime.now()
            else:  # SELL
                # Selling
                if current_pos.is_short or current_pos.is_flat:
                    # Add to short position
                    if current_pos.is_flat:
                        current_pos.entry_price = order.filled_price
                    else:
                        avg_price = (current_pos.entry_price * abs(current_pos.quantity) + 
                                    order.filled_price * order.filled_quantity) / (abs(current_pos.quantity) + order.filled_quantity)
                        current_pos.entry_price = avg_price
                    current_pos.quantity -= order.filled_quantity
                else:
                    # Close long position
                    closed_qty = min(current_pos.quantity, order.filled_quantity)
                    exit_pnl = (order.filled_price - current_pos.entry_price) * closed_qty
                    exit_pnl_pct = ((order.filled_price - current_pos.entry_price) / current_pos.entry_price) * 100
                    holding_days = (order.filled_at - current_pos.entry_date).days
                    
                    # Record closed trade
                    trade = ClosedTrade(
                        trade_id=str(uuid.uuid4())[:8],
                        ticker=ticker,
                        entry_date=current_pos.entry_date,
                        entry_price=current_pos.entry_price,
                        entry_quantity=closed_qty,
                        exit_date=order.filled_at or datetime.now(),
                        exit_price=order.filled_price,
                        exit_quantity=closed_qty,
                        side=OrderSide.BUY,
                        realized_pnl=exit_pnl,
                        realized_pnl_pct=exit_pnl_pct,
                        holding_days=max(holding_days, 1),
                        commission=order.commission
                    )
                    self.closed_trades.append(trade)
                    
                    # Update position
                    current_pos.quantity -= order.filled_quantity
                    if current_pos.quantity < 0:
                        # New short position from extra quantity
                        current_pos.entry_price = order.filled_price
                        current_pos.entry_date = order.filled_at or datetime.now()
        
        self.trade_history.append(order)
    
    def get_position_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total position market value."""
        total = 0.0
        
        for ticker, position in self.positions.items():
            if ticker in current_prices:
                total += position.quantity * current_prices[ticker]
        
        return total
    
    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value (cash + positions)."""
        return self.cash + self.get_position_value(current_prices)
    
    def get_total_pnl(self, current_prices: Dict[str, float]) -> Dict:
        """
        Calculate total P&L (realized + unrealized).
        
        Returns:
            Dict with realized, unrealized, total P&L and percentages
        """
        # Realized P&L from closed trades
        realized_pnl = sum(trade.realized_pnl for trade in self.closed_trades)
        
        # Unrealized P&L from open positions
        unrealized_pnl = 0.0
        for ticker, position in self.positions.items():
            if not position.is_flat and ticker in current_prices:
                pnl, _ = position.calculate_pnl(current_prices[ticker])
                unrealized_pnl += pnl
        
        total_pnl = realized_pnl + unrealized_pnl
        portfolio_value = self.get_portfolio_value(current_prices)
        total_return_pct = (total_pnl / self.initial_cash) * 100 if self.initial_cash > 0 else 0
        
        return {
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': total_pnl,
            'total_return_pct': total_return_pct,
            'portfolio_value': portfolio_value,
            'cash': self.cash,
            'position_value': self.get_position_value(current_prices)
        }
    
    def get_statistics(self, current_prices: Dict[str, float]) -> Dict:
        """Calculate portfolio statistics."""
        pnl_dict = self.get_total_pnl(current_prices)
        
        # Trade statistics
        winning_trades = [t for t in self.closed_trades if t.realized_pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.realized_pnl < 0]
        
        total_trades = len(self.closed_trades)
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        
        avg_win = sum(t.realized_pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.realized_pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        profit_factor = abs(avg_win * len(winning_trades)) / abs(avg_loss * len(losing_trades)) if losing_trades and avg_loss != 0 else 0
        
        # Holding period
        avg_holding_days = np.mean([t.holding_days for t in self.closed_trades]) if self.closed_trades else 0
        
        return {
            **pnl_dict,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'avg_holding_days': avg_holding_days,
            'open_positions': len([p for p in self.positions.values() if not p.is_flat])
        }
    
    def to_dict(self, current_prices: Dict[str, float]) -> Dict:
        """Convert to dictionary."""
        return {
            'initial_cash': self.initial_cash,
            'current_cash': self.cash,
            'positions': {
                ticker: pos.to_dict(current_prices.get(ticker, pos.entry_price))
                for ticker, pos in self.positions.items()
                if not pos.is_flat
            },
            'statistics': self.get_statistics(current_prices),
            'closed_trades': [trade.to_dict() for trade in self.closed_trades]
        }
