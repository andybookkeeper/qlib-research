# src/qlib_research/app/db/operations.py
"""Database operations and queries."""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from src.qlib_research.app.db.models import (
    Order, Position, ClosedTrade, Portfolio, MarketDataCache,
    BacktestRun, AuditLog, OrderStatus, OrderSide
)


class OrderOperations:
    """Order CRUD operations."""
    
    @staticmethod
    def create_order(
        db: Session,
        ticker: str,
        side: OrderSide,
        quantity: int,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        signal_id: Optional[str] = None
    ) -> Order:
        """Create new order."""
        order = Order(
            id=str(uuid4()),
            ticker=ticker,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            signal_id=signal_id
        )
        db.add(order)
        db.commit()
        return order
    
    @staticmethod
    def get_order(db: Session, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return db.query(Order).filter(Order.id == order_id).first()
    
    @staticmethod
    def get_active_orders(db: Session) -> List[Order]:
        """Get all pending/partial orders."""
        return db.query(Order).filter(
            Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL])
        ).order_by(desc(Order.created_at)).all()
    
    @staticmethod
    def update_order_status(
        db: Session,
        order_id: str,
        status: OrderStatus,
        filled_quantity: int = 0,
        average_fill_price: Optional[float] = None
    ) -> Order:
        """Update order status."""
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = status
            order.filled_quantity = filled_quantity
            order.average_fill_price = average_fill_price
            if status == OrderStatus.FILLED:
                order.filled_at = datetime.now()
            db.commit()
        return order


class PositionOperations:
    """Position CRUD operations."""
    
    @staticmethod
    def get_or_create_position(db: Session, ticker: str) -> Position:
        """Get position or create if doesn't exist."""
        pos = db.query(Position).filter(Position.ticker == ticker).first()
        if not pos:
            pos = Position(
                id=str(uuid4()),
                ticker=ticker,
                quantity=0,
                avg_cost=0.0
            )
            db.add(pos)
            db.commit()
        return pos
    
    @staticmethod
    def update_position(
        db: Session,
        ticker: str,
        quantity: int,
        avg_cost: float,
        current_price: float
    ) -> Position:
        """Update position (buy/sell)."""
        pos = PositionOperations.get_or_create_position(db, ticker)
        pos.quantity = quantity
        pos.avg_cost = avg_cost
        pos.current_price = current_price
        pos.last_update = datetime.now()
        pos.unrealized_pnl = (current_price - avg_cost) * quantity
        db.commit()
        return pos
    
    @staticmethod
    def get_all_positions(db: Session) -> List[Position]:
        """Get all open positions."""
        return db.query(Position).filter(Position.quantity > 0).all()
    
    @staticmethod
    def close_position(db: Session, ticker: str) -> Position:
        """Close position (set quantity to 0)."""
        pos = db.query(Position).filter(Position.ticker == ticker).first()
        if pos:
            pos.quantity = 0
            pos.closed_at = datetime.now()
            db.commit()
        return pos


class PortfolioOperations:
    """Portfolio CRUD operations."""
    
    @staticmethod
    def get_portfolio(db: Session) -> Portfolio:
        """Get main portfolio."""
        portfolio = db.query(Portfolio).filter(Portfolio.id == "main").first()
        if not portfolio:
            portfolio = Portfolio(
                id="main",
                cash_balance=100000.0,
                total_market_value=0.0
            )
            db.add(portfolio)
            db.commit()
        return portfolio
    
    @staticmethod
    def update_portfolio_values(
        db: Session,
        cash: float,
        market_value: float,
        daily_pnl: float = 0.0
    ) -> Portfolio:
        """Update portfolio balances."""
        portfolio = PortfolioOperations.get_portfolio(db)
        portfolio.cash_balance = cash
        portfolio.total_market_value = market_value
        portfolio.daily_pnl = daily_pnl
        portfolio.daily_return_pct = daily_pnl / (cash + market_value) if (cash + market_value) > 0 else 0
        portfolio.updated_at = datetime.now()
        db.commit()
        return portfolio
    
    @staticmethod
    def update_portfolio_metrics(
        db: Session,
        realized_pnl: float,
        unrealized_pnl: float,
        sharpe: float,
        max_dd: float,
        win_rate: float,
        winning_trades: int,
        total_trades: int
    ) -> Portfolio:
        """Update performance metrics."""
        portfolio = PortfolioOperations.get_portfolio(db)
        portfolio.realized_pnl = realized_pnl
        portfolio.unrealized_pnl = unrealized_pnl
        portfolio.sharpe_ratio = sharpe
        portfolio.max_drawdown = max_dd
        portfolio.win_rate = win_rate
        portfolio.winning_trades = winning_trades
        portfolio.losing_trades = total_trades - winning_trades
        portfolio.total_trades = total_trades
        db.commit()
        return portfolio


class ClosedTradeOperations:
    """Closed trade CRUD operations."""
    
    @staticmethod
    def create_closed_trade(
        db: Session,
        ticker: str,
        entry_side: OrderSide,
        entry_price: float,
        entry_quantity: int,
        entry_order_id: str,
        opened_at: datetime,
        exit_price: float,
        exit_quantity: int,
        exit_order_id: str,
        closed_at: datetime,
        signal_id: Optional[str] = None
    ) -> ClosedTrade:
        """Record closed trade."""
        gross_pnl = (exit_price - entry_price) * exit_quantity if entry_side == OrderSide.BUY else (entry_price - exit_price) * exit_quantity
        commission = exit_quantity * 0.001  # 0.1% commission
        net_pnl = gross_pnl - commission
        return_pct = (exit_price / entry_price - 1) if entry_side == OrderSide.BUY else (1 - exit_price / entry_price)
        holding_days = (closed_at - opened_at).days
        
        trade = ClosedTrade(
            id=str(uuid4()),
            ticker=ticker,
            entry_side=entry_side,
            entry_price=entry_price,
            entry_quantity=entry_quantity,
            entry_order_id=entry_order_id,
            opened_at=opened_at,
            exit_price=exit_price,
            exit_quantity=exit_quantity,
            exit_order_id=exit_order_id,
            closed_at=closed_at,
            gross_pnl=gross_pnl,
            commission=commission,
            net_pnl=net_pnl,
            return_pct=return_pct,
            holding_days=holding_days,
            signal_id=signal_id
        )
        db.add(trade)
        db.commit()
        return trade
    
    @staticmethod
    def get_recent_trades(db: Session, days: int = 30) -> List[ClosedTrade]:
        """Get closed trades from last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        return db.query(ClosedTrade).filter(
            ClosedTrade.closed_at >= cutoff
        ).order_by(desc(ClosedTrade.closed_at)).all()


class MarketDataOperations:
    """Market data cache operations."""
    
    @staticmethod
    def set_market_data(
        db: Session,
        ticker: str,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: int,
        data_date: datetime,
        source: str = "yahoo"
    ) -> MarketDataCache:
        """Cache market data."""
        cache = db.query(MarketDataCache).filter(
            MarketDataCache.ticker == ticker
        ).first()
        
        change_pct = ((close_price - open_price) / open_price * 100) if open_price > 0 else 0
        
        if cache:
            cache.open_price = open_price
            cache.high_price = high_price
            cache.low_price = low_price
            cache.close_price = close_price
            cache.volume = volume
            cache.change_pct = change_pct
            cache.data_date = data_date
            cache.cached_at = datetime.now()
        else:
            cache = MarketDataCache(
                id=str(uuid4()),
                ticker=ticker,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                change_pct=change_pct,
                data_date=data_date,
                source=source
            )
            db.add(cache)
        
        db.commit()
        return cache
    
    @staticmethod
    def get_market_data(db: Session, ticker: str) -> Optional[MarketDataCache]:
        """Get cached market data."""
        return db.query(MarketDataCache).filter(
            MarketDataCache.ticker == ticker
        ).first()
    
    @staticmethod
    def get_all_market_data(db: Session) -> List[MarketDataCache]:
        """Get all cached market data."""
        return db.query(MarketDataCache).all()


class AuditOperations:
    """Audit log operations."""
    
    @staticmethod
    def log_event(
        db: Session,
        event_type: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None
    ) -> AuditLog:
        """Log audit event."""
        log = AuditLog(
            id=str(uuid4()),
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value
        )
        db.add(log)
        db.commit()
        return log
