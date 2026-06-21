"""Phase 1 -> Phase 2 data migration helpers."""

from datetime import datetime
from typing import Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.qlib_research.app.models.database import (
    User,
    Portfolio,
    Position,
    Order,
    Trade,
    PriceHistory,
)


def _as_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def _ensure_default_user_portfolio(db: Session) -> Portfolio:
    user = db.query(User).filter(User.username == "paper_trader").first()
    if user is None:
        user = User(
            username="paper_trader",
            email="paper_trader@local",
            password_hash="phase2-migration",
            full_name="Paper Trader",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id, Portfolio.name == "Main")
        .first()
    )
    if portfolio is None:
        portfolio = Portfolio(
            user_id=user.id,
            name="Main",
            initial_capital=100000.0,
            current_cash=100000.0,
            total_value=100000.0,
            portfolio_type="PAPER",
            benchmark_symbol="SPY",
            is_active=True,
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
    return portfolio


def migrate_phase1_to_phase2(db: Session) -> Dict[str, int]:
    """Migrate legacy phase-1 tables into phase-2 schema."""
    summary = {
        "positions_migrated": 0,
        "orders_migrated": 0,
        "trades_migrated": 0,
        "prices_migrated": 0,
    }
    portfolio = _ensure_default_user_portfolio(db)

    # Migrate legacy positions table if it exists (legacy columns: ticker, quantity, avg_cost, current_price).
    try:
        legacy_positions = db.execute(
            text("SELECT ticker, quantity, avg_cost, current_price FROM positions")
        ).fetchall()
    except Exception:
        legacy_positions = []

    for row in legacy_positions:
        symbol = str(row.ticker).upper()
        existing = (
            db.query(Position)
            .filter(Position.portfolio_id == portfolio.id, Position.symbol == symbol)
            .first()
        )
        if existing:
            continue
        db.add(
            Position(
                portfolio_id=portfolio.id,
                symbol=symbol,
                quantity=int(row.quantity or 0),
                entry_price=_as_float(row.avg_cost, 0.0),
                current_price=_as_float(row.current_price, _as_float(row.avg_cost, 0.0)),
                entry_date=datetime.utcnow(),
            )
        )
        summary["positions_migrated"] += 1

    # Migrate legacy orders table if it has ticker-based shape.
    try:
        legacy_orders = db.execute(
            text(
                "SELECT id, ticker, side, quantity, order_type, limit_price, average_fill_price, status, created_at, filled_at "
                "FROM orders"
            )
        ).fetchall()
    except Exception:
        legacy_orders = []

    for row in legacy_orders:
        # Skip if this order id already exists in new table namespace.
        already = db.query(Order).filter(Order.id == row.id).first()
        if already:
            continue
        db.add(
            Order(
                id=row.id,
                portfolio_id=portfolio.id,
                symbol=str(row.ticker).upper(),
                side=str(row.side).upper(),
                quantity=int(row.quantity or 0),
                order_price=_as_float(row.limit_price, 0.0) if row.limit_price is not None else None,
                fill_price=_as_float(row.average_fill_price, 0.0) if row.average_fill_price is not None else None,
                order_type=str(row.order_type).upper(),
                status=str(row.status).upper(),
                created_at=row.created_at or datetime.utcnow(),
                filled_at=row.filled_at,
            )
        )
        summary["orders_migrated"] += 1

    # Migrate cached OHLC data if legacy market_data_cache exists.
    try:
        legacy_prices = db.execute(
            text("SELECT ticker, open_price, high_price, low_price, close_price, volume, data_date FROM market_data_cache")
        ).fetchall()
    except Exception:
        legacy_prices = []

    for row in legacy_prices:
        dt = row.data_date.date() if hasattr(row.data_date, "date") else datetime.utcnow().date()
        existing = (
            db.query(PriceHistory)
            .filter(PriceHistory.symbol == str(row.ticker).upper(), PriceHistory.date == dt)
            .first()
        )
        if existing:
            continue
        db.add(
            PriceHistory(
                symbol=str(row.ticker).upper(),
                date=dt,
                open_price=_as_float(row.open_price, 0.0),
                high_price=_as_float(row.high_price, 0.0),
                low_price=_as_float(row.low_price, 0.0),
                close_price=_as_float(row.close_price, 0.0),
                volume=int(row.volume or 0),
            )
        )
        summary["prices_migrated"] += 1

    db.commit()
    return summary
