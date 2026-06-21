"""SQLAlchemy ORM Models for Qlib Trading Platform - Phase 2-01"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey,
    Text, JSON, Index, UniqueConstraint, CheckConstraint, Float, Date
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_users_email_active", "email", "is_active"),
    )


class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    initial_capital = Column(Numeric(15, 2), nullable=False)
    current_cash = Column(Numeric(15, 2), nullable=False)
    total_value = Column(Numeric(15, 2), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    portfolio_type = Column(String(20), default="PAPER", nullable=False)
    benchmark_symbol = Column(String(20), default="SPY", nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    user = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="portfolio", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="portfolio", cascade="all, delete-orphan")
    risk_limits = relationship("RiskLimit", back_populates="portfolio", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="portfolio", cascade="all, delete-orphan")
    backtest_results = relationship("BacktestResult", back_populates="portfolio", cascade="all, delete-orphan")
    portfolio_snapshots = relationship("PortfolioSnapshot", back_populates="portfolio", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_portfolio_user_name"),
        Index("idx_portfolio_user_active", "user_id", "is_active"),
        Index("idx_portfolio_updated", "updated_at"),
    )


class Position(Base):
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Numeric(15, 4), nullable=False)
    current_price = Column(Numeric(15, 4), nullable=False)
    entry_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    
    portfolio = relationship("Portfolio", back_populates="positions")
    
    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol", name="uq_position_portfolio_symbol"),
        Index("idx_position_portfolio_symbol", "portfolio_id", "symbol"),
    )


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    order_price = Column(Numeric(15, 4), nullable=True)
    fill_price = Column(Numeric(15, 4), nullable=True)
    order_type = Column(String(20), nullable=False, index=True)
    status = Column(String(20), default="PENDING", nullable=False, index=True)
    stop_price = Column(Numeric(15, 4), nullable=True)
    rejected_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    filled_at = Column(DateTime, nullable=True, index=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    portfolio = relationship("Portfolio", back_populates="orders")
    trades = relationship("Trade", back_populates="order", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_order_portfolio_status", "portfolio_id", "status"),
        Index("idx_order_portfolio_symbol", "portfolio_id", "symbol"),
    )


class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    execution_price = Column(Numeric(15, 4), nullable=False)
    commission = Column(Numeric(15, 4), nullable=False)
    gross_pnl = Column(Numeric(15, 2), nullable=True)
    net_pnl = Column(Numeric(15, 2), nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    order = relationship("Order", back_populates="trades")
    portfolio = relationship("Portfolio", back_populates="trades")
    
    __table_args__ = (
        Index("idx_trade_portfolio_symbol", "portfolio_id", "symbol"),
    )


class PriceHistory(Base):
    """Time-series OHLCV data"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open_price = Column(Numeric(15, 4), nullable=False)
    high_price = Column(Numeric(15, 4), nullable=False)
    low_price = Column(Numeric(15, 4), nullable=False)
    close_price = Column(Numeric(15, 4), nullable=False)
    volume = Column(Integer, nullable=False)
    adjusted_close = Column(Numeric(15, 4), nullable=True)
    dividend = Column(Numeric(15, 4), nullable=True)
    split_ratio = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_price_symbol_date"),
        Index("idx_price_symbol_date", "symbol", "date"),
        Index("idx_price_date", "date"),
    )


class FeatureData(Base):
    """Time-series technical indicators & features"""
    __tablename__ = "feature_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # Moving averages
    sma_20 = Column(Numeric(15, 4), nullable=True)
    sma_50 = Column(Numeric(15, 4), nullable=True)
    sma_200 = Column(Numeric(15, 4), nullable=True)
    ema_12 = Column(Numeric(15, 4), nullable=True)
    ema_26 = Column(Numeric(15, 4), nullable=True)
    
    # Momentum
    rsi_14 = Column(Numeric(5, 2), nullable=True)
    macd = Column(Numeric(15, 4), nullable=True)
    macd_signal = Column(Numeric(15, 4), nullable=True)
    momentum = Column(Numeric(15, 4), nullable=True)
    roc = Column(Numeric(15, 4), nullable=True)
    
    # Volatility & Bands
    bollinger_upper = Column(Numeric(15, 4), nullable=True)
    bollinger_lower = Column(Numeric(15, 4), nullable=True)
    atr = Column(Numeric(15, 4), nullable=True)
    volatility = Column(Numeric(10, 6), nullable=True)
    
    # Stochastic
    stochastic_k = Column(Numeric(5, 2), nullable=True)
    stochastic_d = Column(Numeric(5, 2), nullable=True)
    
    # Volume
    obv = Column(Numeric(20, 0), nullable=True)
    ad_line = Column(Numeric(20, 0), nullable=True)
    cmf = Column(Numeric(5, 2), nullable=True)
    
    # Returns
    daily_return = Column(Numeric(10, 6), nullable=True)
    log_return = Column(Numeric(10, 6), nullable=True)
    
    # Extensible
    custom_features = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_feature_symbol_date"),
        Index("idx_feature_symbol_date", "symbol", "date"),
    )


class BacktestResult(Base):
    """Backtest execution & performance metrics"""
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    strategy_name = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    parameters = Column(JSON, nullable=False)
    
    # Performance
    total_return = Column(Numeric(10, 4), nullable=False)
    annual_return = Column(Numeric(10, 4), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    sortino_ratio = Column(Numeric(10, 4), nullable=True)
    calmar_ratio = Column(Numeric(10, 4), nullable=True)
    max_drawdown = Column(Numeric(10, 4), nullable=True)
    win_rate = Column(Numeric(5, 2), nullable=True)
    profit_factor = Column(Numeric(10, 4), nullable=True)
    
    # Trade stats
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    avg_win = Column(Numeric(15, 2), nullable=True)
    avg_loss = Column(Numeric(15, 2), nullable=True)
    
    # Results
    daily_returns = Column(JSON, nullable=True)
    equity_curve = Column(JSON, nullable=True)
    trade_log = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    portfolio = relationship("Portfolio", back_populates="backtest_results")
    
    __table_args__ = (
        Index("idx_backtest_portfolio", "portfolio_id"),
    )


class PortfolioSnapshot(Base):
    """Daily portfolio state for analytics"""
    __tablename__ = "portfolio_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    
    total_value = Column(Numeric(15, 2), nullable=False)
    cash = Column(Numeric(15, 2), nullable=False)
    positions_value = Column(Numeric(15, 2), nullable=False)
    daily_pnl = Column(Numeric(15, 2), nullable=False)
    cumulative_pnl = Column(Numeric(15, 2), nullable=False)
    total_return = Column(Numeric(10, 4), nullable=False)
    daily_return = Column(Numeric(10, 6), nullable=False)
    
    var_95 = Column(Numeric(15, 2), nullable=True)
    var_99 = Column(Numeric(15, 2), nullable=True)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    
    positions = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    portfolio = relationship("Portfolio", back_populates="portfolio_snapshots")
    
    __table_args__ = (
        UniqueConstraint("portfolio_id", "snapshot_date", name="uq_snapshot_portfolio_date"),
        Index("idx_snapshot_portfolio_date", "portfolio_id", "snapshot_date"),
    )


class RiskLimit(Base):
    """User-configured risk limits"""
    __tablename__ = "risk_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    limit_type = Column(String(50), nullable=False, index=True)
    limit_value = Column(Numeric(15, 4), nullable=False)
    unit = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    portfolio = relationship("Portfolio", back_populates="risk_limits")
    
    __table_args__ = (
        UniqueConstraint("portfolio_id", "limit_type", name="uq_risklimit_portfolio_type"),
        Index("idx_risklimit_portfolio", "portfolio_id"),
    )


class Alert(Base):
    """System and risk alerts"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    severity = Column(String(20), default="INFO", nullable=False)
    acknowledged = Column(Boolean, default=False, index=True)
    context = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    portfolio = relationship("Portfolio", back_populates="alerts")
    
    __table_args__ = (
        Index("idx_alert_portfolio_acknowledged", "portfolio_id", "acknowledged"),
    )


class AuditLog(Base):
    """Audit trail for compliance"""
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    status = Column(String(20), default="SUCCESS", nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index("idx_audit_user_portfolio", "user_id", "portfolio_id"),
        Index("idx_audit_action", "action"),
    )
