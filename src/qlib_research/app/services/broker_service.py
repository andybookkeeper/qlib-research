# src/qlib_research/app/services/broker_service.py
"""Paper broker service for order execution and portfolio management."""

from datetime import datetime
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from src.qlib_research.app.models.database import (
    User as DBUser,
    Portfolio as DBPortfolio,
    Position as DBPosition,
    Order as DBOrder,
    Trade as DBTrade,
)


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


class DatabaseBrokerService:
    """Database-backed broker service for orders and portfolio tracking."""

    def __init__(self, db: Session, commission_rate: float = 0.001):
        self.db = db
        self.commission_rate = commission_rate

    @staticmethod
    def _as_float(value, default: float = 0.0) -> float:
        if value is None:
            return default
        return float(value)

    def _get_or_create_portfolio(self, user_id: Optional[int] = None) -> DBPortfolio:
        user = None
        if user_id is not None:
            user = self.db.query(DBUser).filter(DBUser.id == user_id).first()
        if user is None:
            user = (
                self.db.query(DBUser)
                .filter(DBUser.username == "paper_trader")
                .first()
            )
        if user is None:
            user = DBUser(
                username="paper_trader",
                email="paper_trader@local",
                password_hash="phase2-placeholder",
                full_name="Paper Trader",
                is_active=True,
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

        portfolio = (
            self.db.query(DBPortfolio)
            .filter(DBPortfolio.user_id == user.id, DBPortfolio.name == "Main")
            .first()
        )
        if portfolio is None:
            initial_cash = 100000.0
            portfolio = DBPortfolio(
                user_id=user.id,
                name="Main",
                description="Default paper trading portfolio",
                initial_capital=initial_cash,
                current_cash=initial_cash,
                total_value=initial_cash,
                portfolio_type="PAPER",
                benchmark_symbol="SPY",
                is_active=True,
            )
            self.db.add(portfolio)
            self.db.commit()
            self.db.refresh(portfolio)
        return portfolio

    def _portfolio_market_value(self, portfolio_id: int) -> float:
        positions = (
            self.db.query(DBPosition)
            .filter(DBPosition.portfolio_id == portfolio_id)
            .all()
        )
        return sum(
            self._as_float(position.current_price) * int(position.quantity)
            for position in positions
        )

    def _refresh_portfolio_totals(self, portfolio: DBPortfolio) -> None:
        market_value = self._portfolio_market_value(portfolio.id)
        portfolio.total_value = self._as_float(portfolio.current_cash) + market_value
        self.db.commit()

    def _apply_fill_to_position(self, portfolio: DBPortfolio, order: DBOrder, fill_price: float, commission: float) -> None:
        symbol = order.symbol.upper()
        side = order.side.upper()
        qty = int(order.quantity)
        signed_qty = qty if side == "BUY" else -qty

        position = (
            self.db.query(DBPosition)
            .filter(DBPosition.portfolio_id == portfolio.id, DBPosition.symbol == symbol)
            .first()
        )

        realized_pnl = 0.0
        if position is None:
            position = DBPosition(
                portfolio_id=portfolio.id,
                symbol=symbol,
                quantity=signed_qty,
                entry_price=fill_price,
                current_price=fill_price,
                entry_date=datetime.utcnow(),
            )
            self.db.add(position)
        else:
            old_qty = int(position.quantity)
            old_entry = self._as_float(position.entry_price)
            new_qty = old_qty + signed_qty

            if old_qty == 0 or (old_qty > 0 and signed_qty > 0) or (old_qty < 0 and signed_qty < 0):
                total_abs = abs(old_qty) + abs(signed_qty)
                if total_abs > 0:
                    weighted = (
                        (abs(old_qty) * old_entry) + (abs(signed_qty) * fill_price)
                    ) / total_abs
                    position.entry_price = weighted
                position.quantity = new_qty
            else:
                closed_qty = min(abs(old_qty), abs(signed_qty))
                if old_qty > 0 and signed_qty < 0:
                    realized_pnl = (fill_price - old_entry) * closed_qty
                elif old_qty < 0 and signed_qty > 0:
                    realized_pnl = (old_entry - fill_price) * closed_qty

                position.quantity = new_qty
                if new_qty == 0:
                    position.entry_price = fill_price
                elif (old_qty > 0 > new_qty) or (old_qty < 0 < new_qty):
                    position.entry_price = fill_price

            position.current_price = fill_price
            position.updated_at = datetime.utcnow()

        if side == "BUY":
            portfolio.current_cash = self._as_float(portfolio.current_cash) - (fill_price * qty) - commission
        else:
            portfolio.current_cash = self._as_float(portfolio.current_cash) + (fill_price * qty) - commission

        trade = DBTrade(
            order_id=order.id,
            portfolio_id=portfolio.id,
            symbol=symbol,
            quantity=qty,
            execution_price=fill_price,
            commission=commission,
            gross_pnl=realized_pnl if realized_pnl != 0 else None,
            net_pnl=(realized_pnl - commission) if realized_pnl != 0 else None,
            executed_at=datetime.utcnow(),
        )
        self.db.add(trade)
        self.db.commit()
        self._refresh_portfolio_totals(portfolio)

    def create_order(
        self,
        ticker: str,
        side: str,
        quantity: float,
        order_type: str,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        current_price: Optional[float] = None,
        user_id: Optional[int] = None,
    ) -> DBOrder:
        portfolio = self._get_or_create_portfolio(user_id=user_id)
        normalized_type = order_type.upper()
        normalized_side = side.upper()
        if normalized_type not in {"MARKET", "LIMIT", "STOP"}:
            normalized_type = "MARKET"
        if normalized_side not in {"BUY", "SELL"}:
            normalized_side = "BUY"

        order = DBOrder(
            portfolio_id=portfolio.id,
            symbol=ticker.upper(),
            side=normalized_side,
            quantity=int(quantity),
            order_type=normalized_type,
            order_price=price,
            stop_price=stop_price,
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        if normalized_type == "MARKET":
            fill_at = current_price if current_price is not None else 100.0
            self.fill_order(order.id, fill_at)
            self.db.refresh(order)

        return order

    def fill_order(self, order_id: int, current_price: float, user_id: Optional[int] = None) -> DBOrder:
        order = (
            self.db.query(DBOrder)
            .filter(DBOrder.id == order_id)
            .first()
        )
        if order is None:
            raise ValueError("Order not found")

        if user_id is not None:
            allowed = (
                self.db.query(DBPortfolio)
                .filter(DBPortfolio.id == order.portfolio_id, DBPortfolio.user_id == user_id)
                .first()
            )
            if allowed is None:
                raise ValueError("Order not found")

        if order.status in {"FILLED", "CANCELLED", "REJECTED"}:
            return order

        fill = False
        order_type = order.order_type.upper()
        side = order.side.upper()
        ref_price = self._as_float(order.order_price)
        ref_stop = self._as_float(order.stop_price)

        if order_type == "MARKET":
            fill = True
        elif order_type == "LIMIT":
            if side == "BUY" and current_price <= ref_price:
                fill = True
            if side == "SELL" and current_price >= ref_price:
                fill = True
        elif order_type == "STOP":
            if side == "BUY" and current_price >= ref_stop:
                fill = True
            if side == "SELL" and current_price <= ref_stop:
                fill = True

        if not fill:
            return order

        fill_price = current_price if order_type != "LIMIT" else ref_price
        commission = fill_price * int(order.quantity) * self.commission_rate

        order.fill_price = fill_price
        order.filled_at = datetime.utcnow()
        order.status = "FILLED"
        self.db.commit()

        portfolio = (
            self.db.query(DBPortfolio)
            .filter(DBPortfolio.id == order.portfolio_id)
            .first()
        )
        if portfolio is None:
            raise ValueError("Portfolio not found for order")

        self._apply_fill_to_position(portfolio, order, fill_price, commission)
        self.db.refresh(order)
        return order

    def get_order(self, order_id: int, user_id: Optional[int] = None) -> Optional[DBOrder]:
        query = (
            self.db.query(DBOrder)
            .join(DBPortfolio, DBPortfolio.id == DBOrder.portfolio_id)
            .filter(DBOrder.id == order_id)
        )
        if user_id is not None:
            query = query.filter(DBPortfolio.user_id == user_id)
        return query.first()

    def get_orders(self, user_id: Optional[int] = None, limit: int = 100) -> List[DBOrder]:
        query = (
            self.db.query(DBOrder)
            .join(DBPortfolio, DBPortfolio.id == DBOrder.portfolio_id)
        )
        if user_id is not None:
            query = query.filter(DBPortfolio.user_id == user_id)
        return query.order_by(DBOrder.created_at.desc()).limit(limit).all()

    def get_positions(self, user_id: Optional[int] = None) -> List[DBPosition]:
        portfolio = self._get_or_create_portfolio(user_id=user_id)
        return (
            self.db.query(DBPosition)
            .filter(DBPosition.portfolio_id == portfolio.id, DBPosition.quantity != 0)
            .all()
        )

    def get_position(self, symbol: str, user_id: Optional[int] = None) -> Optional[DBPosition]:
        portfolio = self._get_or_create_portfolio(user_id=user_id)
        return (
            self.db.query(DBPosition)
            .filter(
                DBPosition.portfolio_id == portfolio.id,
                DBPosition.symbol == symbol.upper(),
                DBPosition.quantity != 0,
            )
            .first()
        )

    def get_trades(self, user_id: Optional[int] = None) -> List[DBTrade]:
        portfolio = self._get_or_create_portfolio(user_id=user_id)
        return (
            self.db.query(DBTrade)
            .filter(DBTrade.portfolio_id == portfolio.id)
            .order_by(DBTrade.executed_at.desc())
            .all()
        )

    def get_portfolio_snapshot(self, current_prices: Optional[Dict[str, float]] = None, user_id: Optional[int] = None) -> Dict:
        current_prices = current_prices or {}
        portfolio = self._get_or_create_portfolio(user_id=user_id)
        positions = self.get_positions(user_id=user_id)

        realized = 0.0
        for trade in self.get_trades(user_id=user_id):
            if trade.gross_pnl is not None:
                realized += self._as_float(trade.gross_pnl)

        unrealized = 0.0
        position_payload = []
        for pos in positions:
            market_price = current_prices.get(pos.symbol, self._as_float(pos.current_price, self._as_float(pos.entry_price)))
            entry = self._as_float(pos.entry_price)
            qty = int(pos.quantity)
            pnl = (market_price - entry) * qty
            pnl_pct = ((market_price - entry) / entry * 100.0) if entry else 0.0
            unrealized += pnl
            position_payload.append(
                {
                    "ticker": pos.symbol,
                    "quantity": qty,
                    "entry_price": entry,
                    "current_price": market_price,
                    "cost_basis": abs(entry * qty),
                    "market_value": market_price * qty,
                    "unrealized_pnl": pnl,
                    "unrealized_pnl_pct": pnl_pct,
                    "is_long": qty > 0,
                    "is_short": qty < 0,
                }
            )

        total_pnl = realized + unrealized
        portfolio_value = self._as_float(portfolio.current_cash) + sum(item["market_value"] for item in position_payload)
        return_pct = (
            (total_pnl / self._as_float(portfolio.initial_capital) * 100.0)
            if self._as_float(portfolio.initial_capital) > 0
            else 0.0
        )

        trades = self.get_trades(user_id=user_id)
        pnl_values = [self._as_float(trade.gross_pnl) for trade in trades if trade.gross_pnl is not None]
        winning = [value for value in pnl_values if value > 0]
        losing = [value for value in pnl_values if value < 0]
        total_trades = len(pnl_values)
        avg_win = (sum(winning) / len(winning)) if winning else 0.0
        avg_loss = (sum(losing) / len(losing)) if losing else 0.0
        profit_factor = (abs(sum(winning)) / abs(sum(losing))) if losing else 0.0

        holding_days = []
        for trade in trades:
            if trade.executed_at and trade.order and trade.order.created_at:
                delta = (trade.executed_at - trade.order.created_at).days
                holding_days.append(max(delta, 1))

        return {
            "initial_cash": self._as_float(portfolio.initial_capital),
            "current_cash": self._as_float(portfolio.current_cash),
            "portfolio_value": portfolio_value,
            "position_value": sum(item["market_value"] for item in position_payload),
            "total_pnl": total_pnl,
            "total_return_pct": return_pct,
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
            "total_trades": total_trades,
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": (len(winning) / total_trades * 100.0) if total_trades else 0.0,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "avg_holding_days": float(np.mean(holding_days)) if holding_days else 0.0,
            "open_positions": len(position_payload),
            "positions": position_payload,
        }

    def reset(self, user_id: Optional[int] = None) -> None:
        portfolio = self._get_or_create_portfolio(user_id=user_id)
        self.db.query(DBTrade).filter(DBTrade.portfolio_id == portfolio.id).delete()
        self.db.query(DBOrder).filter(DBOrder.portfolio_id == portfolio.id).delete()
        self.db.query(DBPosition).filter(DBPosition.portfolio_id == portfolio.id).delete()
        portfolio.current_cash = portfolio.initial_capital
        portfolio.total_value = portfolio.initial_capital
        self.db.commit()
