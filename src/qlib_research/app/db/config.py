# src/qlib_research/app/db/config.py
"""Database configuration and initialization."""

import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.qlib_research.app.db.models import Base

# Database paths
DB_DIR = Path(os.getenv("DATA_PATH", "./data"))
DB_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_DIR}/qlib_trading.db"

# Engine configuration
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# SQLite pragma settings for better performance
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys and other SQLite optimizations."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    print(f"✓ Database initialized at {DATABASE_URL}")


def drop_db():
    """Drop all tables (for testing)."""
    Base.metadata.drop_all(bind=engine)
    print("✓ Database dropped")


def get_db() -> Session:
    """Dependency injection for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db():
    """Reset database (drop and recreate)."""
    drop_db()
    init_db()
