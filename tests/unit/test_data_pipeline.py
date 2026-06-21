# tests/unit/test_data_pipeline.py
"""Unit tests for data pipeline."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.qlib_research.app.db.models import Base
from src.qlib_research.app.services.data_pipeline import DataValidator, DataPipeline, CacheManager


class TestDataValidator:
    """Test data validation."""
    
    def test_valid_ohlcv(self):
        """Test validation of valid OHLCV data."""
        
        data = pd.DataFrame({
            'open': [100.0, 101.0, 102.0],
            'high': [101.0, 102.0, 103.0],
            'low': [99.0, 100.0, 101.0],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000000, 1100000, 900000]
        })
        
        is_valid, issues = DataValidator.validate_ohlcv(data)
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_invalid_ohlcv_high_low(self):
        """Test validation with invalid high/low."""
        
        data = pd.DataFrame({
            'open': [100.0, 101.0],
            'high': [98.0, 99.0],  # High < Open (invalid)
            'low': [99.0, 100.0],
            'close': [100.5, 101.5],
            'volume': [1000000, 1100000]
        })
        
        is_valid, issues = DataValidator.validate_ohlcv(data)
        
        assert is_valid is False
        assert any("Invalid high" in issue for issue in issues)
    
    def test_validate_prices(self):
        """Test price validation."""
        
        prices = {
            'AAPL': 150.0,
            'MSFT': 300.0,
            'GOOGL': 100.0
        }
        
        is_valid, issues = DataValidator.validate_prices(prices)
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_validate_prices_invalid(self):
        """Test price validation with invalid prices."""
        
        prices = {
            'AAPL': 150.0,
            'MSFT': -100.0,  # Negative price
            'GOOGL': None    # None price
        }
        
        is_valid, issues = DataValidator.validate_prices(prices)
        
        assert is_valid is False
        assert len(issues) >= 2


class TestCacheManager:
    """Test cache manager."""
    
    @pytest.fixture
    def db(self):
        """Create in-memory database."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        yield session
        session.close()
    
    def test_get_cache_status_empty(self, db):
        """Test cache status with no data."""
        
        manager = CacheManager(db)
        status = manager.get_cache_status()
        
        assert status['total'] == 0
        assert status['fresh'] == 0
        assert status['stale'] == 0
        assert status['coverage_pct'] == 0.0
    
    def test_get_missing_tickers(self, db):
        """Test identifying missing tickers."""
        
        manager = CacheManager(db)
        required = ["AAPL", "MSFT", "GOOGL"]
        
        missing = manager.get_missing_tickers(required)
        
        assert len(missing) == 3  # All missing since DB is empty
    
    def test_suggest_refresh(self, db):
        """Test refresh suggestions."""
        
        manager = CacheManager(db)
        suggestion = manager.suggest_refresh()
        
        assert 'refresh_urgent' in suggestion
        assert 'refresh_soon' in suggestion
        assert 'message' in suggestion
