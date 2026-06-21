# src/qlib_research/app/services/market_data_service.py
"""Market data caching and retrieval service."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
import pandas as pd

from src.qlib_research.app.services.qlib_service import QlibService
from src.qlib_research.app.db.operations import MarketDataOperations
from src.qlib_research.app.db.models import MarketDataCache

logger = logging.getLogger("qlib_trading.market_data_service")


class MarketDataService:
    """Market data with caching layer."""
    
    def __init__(self, db: Session, qlib_service: QlibService):
        """Initialize market data service."""
        self.db = db
        self.qlib = qlib_service
        self.cache = {}  # In-memory cache
        self.cache_ttl = 24 * 3600  # 24 hours
    
    async def get_latest_price(self, ticker: str) -> Optional[float]:
        """Get latest cached price for ticker."""
        
        # Check in-memory cache first
        if ticker in self.cache:
            cached_data, timestamp = self.cache[ticker]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                logger.debug(f"Using in-memory cache for {ticker}")
                return cached_data.get('close')
        
        # Check database cache
        db_cache = MarketDataOperations.get_market_data(self.db, ticker)
        if db_cache and not db_cache.is_stale():
            logger.debug(f"Using database cache for {ticker}")
            self.cache[ticker] = ({'close': db_cache.close_price}, datetime.now())
            return db_cache.close_price
        
        # Fetch fresh data
        return await self.refresh_price(ticker)
    
    async def refresh_price(self, ticker: str) -> Optional[float]:
        """Fetch and cache latest price."""
        
        try:
            snapshot = self.qlib.get_daily_snapshot([ticker])
            
            if ticker not in snapshot:
                logger.warning(f"No data from Qlib for {ticker}")
                return None
            
            data = snapshot[ticker]
            
            # Store in database
            MarketDataOperations.set_market_data(
                self.db,
                ticker=ticker,
                open_price=data['open'],
                high_price=data['high'],
                low_price=data['low'],
                close_price=data['close'],
                volume=data['volume'],
                data_date=data['timestamp']
            )
            
            # Store in memory
            self.cache[ticker] = (data, datetime.now())
            
            logger.info(f"✓ Refreshed price for {ticker}: ${data['close']:.2f}")
            return data['close']
            
        except Exception as e:
            logger.error(f"Failed to refresh price for {ticker}: {e}")
            return None
    
    async def get_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Get OHLCV history."""
        
        try:
            data = self.qlib.get_ohlcv(ticker, start_date, end_date)
            
            if data is None or data.empty:
                logger.warning(f"No OHLCV data for {ticker}")
                return None
            
            logger.info(f"✓ Got OHLCV for {ticker}: {len(data)} rows")
            return data
            
        except Exception as e:
            logger.error(f"OHLCV fetch error: {e}")
            return None
    
    async def refresh_all_prices(self, tickers: List[str]) -> Dict:
        """Refresh prices for all tickers."""
        
        results = {}
        for ticker in tickers:
            price = await self.refresh_price(ticker)
            results[ticker] = price
        
        logger.info(f"✓ Refreshed {len(results)} prices")
        return results
    
    def get_cached_price(self, ticker: str) -> Optional[float]:
        """Get price without fetching (may be stale)."""
        
        cache = MarketDataOperations.get_market_data(self.db, ticker)
        return cache.close_price if cache else None
    
    def __repr__(self):
        return f"<MarketDataService cache_size={len(self.cache)}>"
