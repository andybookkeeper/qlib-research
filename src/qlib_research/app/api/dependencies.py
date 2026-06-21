# src/qlib_research/app/api/dependencies.py
"""FastAPI dependency injection for services and authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.qlib_research.app.config import get_phase3_feature_flags
from src.qlib_research.app.db import SessionLocal, get_db
from src.qlib_research.app.models.database import User
from src.qlib_research.app.services.broker_adapter import BrokerAdapter, create_broker_adapter
from src.qlib_research.app.services.qlib_service import QlibService
from src.qlib_research.app.services.market_data_service import MarketDataService
from src.qlib_research.app.services.data_pipeline import DataPipeline, CacheManager
from src.qlib_research.app.services.auth_service import decode_access_token
from src.qlib_research.app.services.broker_reconciliation_service import BrokerReconciliationService
from src.qlib_research.app.services.strategy_automation_service import StrategyAutomationService
from src.qlib_research.app.services.training_runtime_service import TrainingRuntimeService


# Singleton services (initialized once)
_qlib_service: QlibService = None
_market_data_service: MarketDataService = None
_training_runtime_service: TrainingRuntimeService = None
_broker_reconciliation_service: BrokerReconciliationService = None
_strategy_automation_service: StrategyAutomationService = None
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


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


def get_training_runtime_service() -> TrainingRuntimeService:
    """Get or create runtime training service."""
    global _training_runtime_service
    if _training_runtime_service is None:
        _training_runtime_service = TrainingRuntimeService()
    return _training_runtime_service


def get_broker_adapter(db: Session = Depends(get_db)) -> BrokerAdapter:
    """Resolve broker adapter (paper by default, live path feature-flagged)."""
    flags = get_phase3_feature_flags()
    return create_broker_adapter(
        db=db,
        enable_live_broker_adapter=flags["enable_live_broker_adapter"],
    )


def get_broker_reconciliation_service() -> BrokerReconciliationService:
    """Get or create broker reconciliation service."""
    global _broker_reconciliation_service
    if _broker_reconciliation_service is None:
        _broker_reconciliation_service = BrokerReconciliationService()
    return _broker_reconciliation_service


def get_strategy_automation_service() -> StrategyAutomationService:
    """Get or create strategy automation service."""
    global _strategy_automation_service
    if _strategy_automation_service is None:
        _strategy_automation_service = StrategyAutomationService()
    return _strategy_automation_service


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve and validate current user from bearer token."""
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    return current_user
