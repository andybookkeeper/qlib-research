# src/qlib_research/app/db/models.py
"""SQLAlchemy ORM models for paper trading."""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class OrderStatus(str, Enum):
    """Order status enum."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderSide(str, Enum):
    """Order side enum."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enum."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class Order(Base):
    """Order model."""
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True)  # UUID
    ticker = Column(String(10), nullable=False, index=True)
    side = Column(SQLEnum(OrderSide), nullable=False)
    order_type = Column(SQLEnum(OrderType), nullable=False, default=OrderType.MARKET)
    quantity = Column(Integer, nullable=False)
    filled_quantity = Column(Integer, default=0)
    
    # Pricing
    limit_price = Column(Float, nullable=True)  # For limit orders
    average_fill_price = Column(Float, nullable=True)
    
    # Status
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    
    # Timing
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    filled_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Metadata
    signal_id = Column(String(100), nullable=True)  # Link to Qlib signal
    notes = Column(String(500), nullable=True)
    
    def __repr__(self):
        return (
            f"<Order {self.ticker} {self.side.value} {self.quantity} "
            f"@ ${self.average_fill_price or self.limit_price or 'mkt'} "
            f"({self.status.value})>"
        )


class Position(Base):
    """Position model."""
    __tablename__ = "positions"

    id = Column(String(36), primary_key=True)
    ticker = Column(String(10), nullable=False, unique=True, index=True)
    
    # Quantity and cost basis
    quantity = Column(Integer, nullable=False, default=0)
    avg_cost = Column(Float, nullable=False, default=0.0)
    
    # Current market data
    current_price = Column(Float, nullable=False, default=0.0)
    last_update = Column(DateTime, default=datetime.now)
    
    # P&L (updated daily)
    unrealized_pnl = Column(Float, nullable=False, default=0.0)
    realized_pnl = Column(Float, nullable=False, default=0.0)
    
    # Greeks (for tracking)
    delta = Column(Float, nullable=True)
    gamma = Column(Float, nullable=True)
    theta = Column(Float, nullable=True)
    vega = Column(Float, nullable=True)
    
    # Timestamps
    opened_at = Column(DateTime, default=datetime.now)
    closed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return (
            f"<Position {self.ticker} {self.quantity} shares "
            f"@ ${self.avg_cost:.2f} (P&L: ${self.unrealized_pnl:.2f})>"
        )


class ClosedTrade(Base):
    """Closed trade (for P&L tracking)."""
    __tablename__ = "closed_trades"

    id = Column(String(36), primary_key=True)
    ticker = Column(String(10), nullable=False, index=True)
    
    # Entry
    entry_side = Column(SQLEnum(OrderSide), nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_quantity = Column(Integer, nullable=False)
    entry_order_id = Column(String(36), nullable=False)
    opened_at = Column(DateTime, nullable=False)
    
    # Exit
    exit_price = Column(Float, nullable=False)
    exit_quantity = Column(Integer, nullable=False)
    exit_order_id = Column(String(36), nullable=False)
    closed_at = Column(DateTime, nullable=False, index=True)
    
    # P&L
    gross_pnl = Column(Float, nullable=False)
    commission = Column(Float, default=0.0)
    net_pnl = Column(Float, nullable=False)
    return_pct = Column(Float, nullable=False)
    
    # Metadata
    holding_days = Column(Integer, nullable=False)
    signal_id = Column(String(100), nullable=True)
    
    def __repr__(self):
        return (
            f"<ClosedTrade {self.ticker} "
            f"{self.entry_quantity}@${self.entry_price:.2f}-${self.exit_price:.2f} "
            f"P&L: ${self.net_pnl:.2f}>"
        )


class Portfolio(Base):
    """Portfolio summary (updated daily)."""
    __tablename__ = "portfolio"

    id = Column(String(36), primary_key=True, default="main")
    
    # Balances
    cash_balance = Column(Float, nullable=False, default=100000.0)
    total_market_value = Column(Float, nullable=False, default=0.0)
    
    # P&L (cumulative)
    realized_pnl = Column(Float, nullable=False, default=0.0)
    unrealized_pnl = Column(Float, nullable=False, default=0.0)
    
    # Performance metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    
    # Daily P&L
    daily_pnl = Column(Float, default=0.0)
    daily_return_pct = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return (
            f"<Portfolio cash=${self.cash_balance:.2f} "
            f"market=${self.total_market_value:.2f} "
            f"total=${self.total_market_value + self.cash_balance:.2f}>"
        )


class MarketDataCache(Base):
    """Cached market data for quick access."""
    __tablename__ = "market_data_cache"

    id = Column(String(36), primary_key=True)
    ticker = Column(String(10), nullable=False, unique=True, index=True)
    
    # OHLCV data
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float)
    volume = Column(Integer)
    
    # Computed
    change_pct = Column(Float)
    market_cap = Column(Float, nullable=True)
    
    # Source
    source = Column(String(20), default="yahoo")
    data_date = Column(DateTime, nullable=False, index=True)
    cached_at = Column(DateTime, default=datetime.now)
    ttl_hours = Column(Integer, default=24)
    
    def is_stale(self) -> bool:
        """Check if cache is stale."""
        age = datetime.now() - self.cached_at
        return age.total_seconds() > (self.ttl_hours * 3600)
    
    def __repr__(self):
        return (
            f"<MarketData {self.ticker} ${self.close_price:.2f} "
            f"({self.change_pct:+.2f}%) {self.data_date.date()}>"
        )


class BacktestRun(Base):
    """Backtest execution record."""
    __tablename__ = "backtest_runs"

    id = Column(String(36), primary_key=True)
    model_name = Column(String(50), nullable=False, index=True)
    
    # Backtest parameters
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_capital = Column(Float, default=100000.0)
    
    # Results
    final_portfolio_value = Column(Float, nullable=False)
    total_return_pct = Column(Float, nullable=False)
    annualized_return_pct = Column(Float, nullable=False)
    
    # Risk metrics
    sharpe_ratio = Column(Float, nullable=False)
    max_drawdown_pct = Column(Float, nullable=False)
    win_rate = Column(Float, nullable=False)
    profit_factor = Column(Float, nullable=False)
    
    # Trade stats
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    avg_win = Column(Float, nullable=False)
    avg_loss = Column(Float, nullable=False)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    
    def __repr__(self):
        return (
            f"<BacktestRun {self.model_name} "
            f"Sharpe={self.sharpe_ratio:.2f} Win={self.win_rate:.0%}>"
        )


class AuditLog(Base):
    """Audit trail for all actions."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=True, index=True)
    
    # Change details
    old_value = Column(String(500), nullable=True)
    new_value = Column(String(500), nullable=True)
    
    # Context
    user_agent = Column(String(200), nullable=True)
    ip_address = Column(String(50), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.now, index=True)
    
    def __repr__(self):
        return (
            f"<AuditLog {self.event_type} "
            f"{self.entity_type}:{self.entity_id} {self.created_at}>"
        )
