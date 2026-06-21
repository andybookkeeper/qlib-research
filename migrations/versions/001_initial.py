"""Initial database schema creation

Revision ID: 001_initial
Revises: 
Create Date: 2026-06-20 21:00:00.000000

"""

from sqlalchemy import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all database tables"""
    
    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('idx_users_email_active', 'users', ['email', 'is_active'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    
    # Portfolios table
    op.create_table('portfolios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('initial_capital', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('current_cash', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('total_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('portfolio_type', sa.String(length=20), nullable=False, server_default='PAPER'),
        sa.Column('benchmark_symbol', sa.String(length=20), nullable=True, server_default='SPY'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_portfolio_user_name'),
    )
    op.create_index('idx_portfolios_user_id', 'portfolios', ['user_id'])
    op.create_index('idx_portfolio_user_active', 'portfolios', ['user_id', 'is_active'])
    op.create_index('idx_portfolio_updated', 'portfolios', ['updated_at'])
    
    # Positions table
    op.create_table('positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('entry_price', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('current_price', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('entry_date', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('portfolio_id', 'symbol', name='uq_position_portfolio_symbol'),
    )
    op.create_index('idx_positions_portfolio_id', 'positions', ['portfolio_id'])
    op.create_index('idx_position_portfolio_symbol', 'positions', ['portfolio_id', 'symbol'])
    op.create_index('idx_position_updated', 'positions', ['updated_at'])
    
    # Orders table
    op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('order_price', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('fill_price', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('order_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('stop_price', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('rejected_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('filled_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_orders_portfolio_id', 'orders', ['portfolio_id'])
    op.create_index('idx_orders_symbol', 'orders', ['symbol'])
    op.create_index('idx_order_portfolio_status', 'orders', ['portfolio_id', 'status'])
    op.create_index('idx_order_portfolio_symbol', 'orders', ['portfolio_id', 'symbol'])
    op.create_index('idx_order_created', 'orders', ['created_at'])
    op.create_index('idx_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_order_type', 'orders', ['order_type'])
    op.create_index('idx_orders_filled_at', 'orders', ['filled_at'])
    
    # Trades table
    op.create_table('trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('execution_price', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('commission', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('gross_pnl', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('net_pnl', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_trades_order_id', 'trades', ['order_id'])
    op.create_index('idx_trades_portfolio_id', 'trades', ['portfolio_id'])
    op.create_index('idx_trade_portfolio_symbol', 'trades', ['portfolio_id', 'symbol'])
    op.create_index('idx_trade_executed', 'trades', ['executed_at'])
    
    # Price History table (time-series)
    op.create_table('price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open_price', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('high_price', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('low_price', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('close_price', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('volume', sa.Integer(), nullable=False),
        sa.Column('adjusted_close', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('dividend', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('split_ratio', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'date', name='uq_price_symbol_date'),
    )
    op.create_index('idx_price_symbol', 'price_history', ['symbol'])
    op.create_index('idx_price_date', 'price_history', ['date'])
    op.create_index('idx_price_symbol_date', 'price_history', ['symbol', 'date'])
    
    # Feature Data table (time-series)
    op.create_table('feature_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('sma_20', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('sma_50', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('sma_200', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('ema_12', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('ema_26', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('rsi_14', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('macd', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('macd_signal', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('bollinger_upper', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('bollinger_lower', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('atr', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('momentum', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('roc', sa.Numeric(precision=15, scale=4), nullable=True),
        sa.Column('stochastic_k', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('stochastic_d', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('obv', sa.Numeric(precision=20, scale=0), nullable=True),
        sa.Column('ad_line', sa.Numeric(precision=20, scale=0), nullable=True),
        sa.Column('cmf', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('daily_return', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('log_return', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('volatility', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('custom_features', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'date', name='uq_feature_symbol_date'),
    )
    op.create_index('idx_feature_symbol', 'feature_data', ['symbol'])
    op.create_index('idx_feature_date', 'feature_data', ['date'])
    op.create_index('idx_feature_symbol_date', 'feature_data', ['symbol', 'date'])
    
    # Backtest Results table
    op.create_table('backtest_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('strategy_name', sa.String(length=255), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('total_return', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('annual_return', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('calmar_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('win_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('profit_factor', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('losing_trades', sa.Integer(), nullable=False),
        sa.Column('avg_win', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('avg_loss', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('daily_returns', sa.JSON(), nullable=True),
        sa.Column('equity_curve', sa.JSON(), nullable=True),
        sa.Column('trade_log', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_backtest_portfolio', 'backtest_results', ['portfolio_id'])
    op.create_index('idx_backtest_created', 'backtest_results', ['created_at'])
    
    # Portfolio Snapshots table (daily time-series)
    op.create_table('portfolio_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('total_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('cash', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('positions_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('daily_pnl', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('cumulative_pnl', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('total_return', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('daily_return', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('var_95', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('var_99', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('positions', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('portfolio_id', 'snapshot_date', name='uq_snapshot_portfolio_date'),
    )
    op.create_index('idx_snapshot_portfolio_date', 'portfolio_snapshots', ['portfolio_id', 'snapshot_date'])
    op.create_index('idx_snapshot_date', 'portfolio_snapshots', ['snapshot_date'])
    
    # Risk Limits table
    op.create_table('risk_limits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('limit_type', sa.String(length=50), nullable=False),
        sa.Column('limit_value', sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('portfolio_id', 'limit_type', name='uq_risklimit_portfolio_type'),
    )
    op.create_index('idx_risklimit_portfolio', 'risk_limits', ['portfolio_id'])
    op.create_index('idx_risklimit_limit_type', 'risk_limits', ['limit_type'])
    
    # Alerts table
    op.create_table('alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='INFO'),
        sa.Column('acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_alerts_portfolio_id', 'alerts', ['portfolio_id'])
    op.create_index('idx_alert_portfolio_acknowledged', 'alerts', ['portfolio_id', 'acknowledged'])
    op.create_index('idx_alert_created', 'alerts', ['created_at'])
    op.create_index('idx_alert_severity', 'alerts', ['severity'])
    
    # Audit Log table
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='SUCCESS'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_audit_log_user_id', 'audit_log', ['user_id'])
    op.create_index('idx_audit_log_portfolio', 'audit_log', ['portfolio_id'])
    op.create_index('idx_audit_user_portfolio', 'audit_log', ['user_id', 'portfolio_id'])
    op.create_index('idx_audit_log_action', 'audit_log', ['action'])
    op.create_index('idx_audit_log_created_at', 'audit_log', ['created_at'])
    op.create_index('idx_audit_entity', 'audit_log', ['entity_type', 'entity_id'])


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table('audit_log')
    op.drop_table('alerts')
    op.drop_table('risk_limits')
    op.drop_table('portfolio_snapshots')
    op.drop_table('backtest_results')
    op.drop_table('feature_data')
    op.drop_table('price_history')
    op.drop_table('trades')
    op.drop_table('orders')
    op.drop_table('positions')
    op.drop_table('portfolios')
    op.drop_table('users')
