"""
Database session management and connection handling.
Provides dependency injection for FastAPI routes.
"""

import os
from typing import Generator

from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/qlib_trading.db"  # Fallback to SQLite for development
)

# Check if using PostgreSQL
USING_POSTGRES = "postgresql" in DATABASE_URL

print(f"[DATABASE] Using: {'PostgreSQL' if USING_POSTGRES else 'SQLite'}")
print(f"[DATABASE] URL: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

# Create engine with appropriate settings
if USING_POSTGRES:
    # PostgreSQL-specific settings
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Test connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False,  # Set to True for SQL debugging
    )
else:
    # SQLite settings (simpler, no pooling)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys for SQLite"""
    if "sqlite" in DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for FastAPI routes.
    Provides a database session for the lifetime of a request.
    
    Usage:
        @router.get("/items/")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_sync() -> Session:
    """
    Synchronous database session getter (non-FastAPI use).
    Must be manually closed when done.
    
    Usage:
        db = get_db_sync()
        try:
            results = db.query(Item).all()
        finally:
            db.close()
    """
    return SessionLocal()


def init_db():
    """Initialize database tables (create if not exist)"""
    from src.qlib_research.app.models.database import Base
    Base.metadata.create_all(bind=engine)
    print("[DATABASE] Tables initialized")


def drop_all_tables():
    """Drop all tables (use with caution!)"""
    from src.qlib_research.app.models.database import Base
    Base.metadata.drop_all(bind=engine)
    print("[DATABASE] All tables dropped")


def verify_connection():
    """Verify database connection is working"""
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
            print("[DATABASE] Connection verified")
            return True
    except Exception as e:
        print(f"[DATABASE] Connection failed: {e}")
        return False
