# src/qlib_research/app/api/dependencies.py
"""FastAPI dependency injection for services."""

from functools import lru_cache
from sqlalchemy.orm import Session

from src.qlib_research.app.db.config import SessionLocal, get_db
from src.qlib_research.app.services.qlib_service import QlibService
from src.qlib_research.app.services.market_data_service import MarketDataService
from src.qlib_research.app.services.data_pipeline import DataPipeline, CacheManager


# Singleton services (initialized once)
_qlib_service: QlibService = None
_market_data_service: MarketDataService = None


def get_qlib_service() -> QlibService:
    """Get or create Qlib service."""
    global _qlib_service
    
    if _qlib_service is None:
        _qlib_service = QlibService(region="US")
        _qlib_service.initialize()
    
    return _qlib_service


def get_market_data_service(db: Session = None) -> MarketDataService:
    """Get or create market data service."""
    global _market_data_service
    
    if _market_data_service is None:
        if db is None:
            db = SessionLocal()
        
        qlib = get_qlib_service()
        _market_data_service = MarketDataService(db, qlib)
    
    return _market_data_service


def get_data_pipeline(db: Session) -> DataPipeline:
    """Create data pipeline instance."""
    market_data = get_market_data_service(db)
    return DataPipeline(db, market_data)


def get_cache_manager(db: Session) -> CacheManager:
    """Create cache manager instance."""
    return CacheManager(db, ttl_hours=24)
