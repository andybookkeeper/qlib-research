# src/qlib_research/app/db/seed.py
"""Database seeding with initial data."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.qlib_research.app.db.config import SessionLocal
from src.qlib_research.app.db.models import Portfolio, MarketDataCache
from src.qlib_research.app.db.operations import (
    PortfolioOperations,
    MarketDataOperations,
    AuditOperations
)


def seed_initial_data():
    """Seed database with initial data."""
    db = SessionLocal()
    
    try:
        # Ensure portfolio exists
        portfolio = PortfolioOperations.get_portfolio(db)
        print(f"✓ Portfolio initialized: {portfolio}")
        
        # Seed some market data
        sample_tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
        for ticker in sample_tickers:
            MarketDataOperations.set_market_data(
                db,
                ticker=ticker,
                open_price=150.0 + len(ticker),
                high_price=155.0 + len(ticker),
                low_price=145.0 + len(ticker),
                close_price=152.0 + len(ticker),
                volume=1000000,
                data_date=datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
            )
        
        print(f"✓ Seeded {len(sample_tickers)} market data caches")
        
        # Log seed event
        AuditOperations.log_event(
            db,
            event_type="DATABASE_SEEDED",
            entity_type="system",
            new_value="Initial data loaded"
        )
        
        print("✓ Database seeding complete")
        
    finally:
        db.close()


if __name__ == "__main__":
    seed_initial_data()
