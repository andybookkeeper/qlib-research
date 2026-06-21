# src/qlib_research/app/services/data_pipeline.py
"""Complete market data pipeline with validation and error handling."""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from src.qlib_research.app.db.operations import MarketDataOperations
from src.qlib_research.app.db.models import MarketDataCache

logger = logging.getLogger("qlib_trading.data_pipeline")


class DataValidator:
    """Validate market data quality."""
    
    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate OHLCV data for quality issues."""
        
        issues = []
        
        if df is None or df.empty:
            issues.append("Empty dataset")
            return False, issues
        
        required_columns = {'open', 'high', 'low', 'close', 'volume'}
        missing = required_columns - set(df.columns)
        if missing:
            issues.append(f"Missing columns: {missing}")
            return False, issues
        
        # Check for NaN values
        nan_pct = df[list(required_columns)].isna().sum().sum() / (len(df) * len(required_columns))
        if nan_pct > 0.05:
            issues.append(f"High NaN percentage: {nan_pct:.1%}")
        
        # Check OHLC logic (high >= open, close, low)
        invalid_high = (df['high'] < df[['open', 'close']].max(axis=1)).sum()
        if invalid_high > 0:
            issues.append(f"Invalid high prices: {invalid_high} rows")
        
        # Check for negative prices
        negative = (df[['open', 'high', 'low', 'close']] < 0).any().any()
        if negative:
            issues.append("Negative prices detected")
        
        # Check volume (should be > 0)
        zero_volume = (df['volume'] == 0).sum()
        if zero_volume > len(df) * 0.1:
            issues.append(f"High zero-volume bars: {zero_volume}")
        
        # Check for extreme moves (> 20% in one day)
        returns = df['close'].pct_change().abs()
        extreme_moves = (returns > 0.20).sum()
        if extreme_moves > len(df) * 0.05:
            issues.append(f"Extreme price moves: {extreme_moves} days")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_prices(prices: Dict[str, float]) -> Tuple[bool, List[str]]:
        """Validate current price snapshot."""
        
        issues = []
        
        for ticker, price in prices.items():
            if price is None or price <= 0:
                issues.append(f"{ticker}: invalid price {price}")
            elif price > 1e6:
                issues.append(f"{ticker}: unrealistic price {price}")
        
        return len(issues) == 0, issues


class DataPipeline:
    """Complete data pipeline: fetch → validate → cache."""
    
    def __init__(self, db: Session, market_data_service):
        """Initialize pipeline."""
        self.db = db
        self.market_data_service = market_data_service
        self.validator = DataValidator()
        self.stats = {
            'fetched': 0,
            'cached': 0,
            'failed': 0,
            'validated': 0,
            'errors': []
        }
    
    async def fetch_and_cache_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV, validate, and cache."""
        
        logger.info(f"Fetching OHLCV for {ticker} ({start_date} to {end_date})")
        
        try:
            # Fetch data
            data = await self.market_data_service.get_ohlcv(
                ticker, start_date, end_date
            )
            
            if data is None:
                self.stats['failed'] += 1
                logger.warning(f"No data for {ticker}")
                return None
            
            self.stats['fetched'] += 1
            
            # Validate data quality
            is_valid, issues = self.validator.validate_ohlcv(data)
            self.stats['validated'] += 1
            
            if not is_valid:
                logger.warning(f"Validation issues for {ticker}: {issues}")
                self.stats['errors'].extend(issues)
                # Still proceed but log warnings
            
            # Cache latest close
            if not data.empty:
                latest = data.iloc[-1]
                MarketDataOperations.set_market_data(
                    self.db,
                    ticker=ticker,
                    open_price=float(latest['open']),
                    high_price=float(latest['high']),
                    low_price=float(latest['low']),
                    close_price=float(latest['close']),
                    volume=int(latest['volume']),
                    data_date=data.index[-1] if hasattr(data.index[-1], '__str__') else datetime.now()
                )
                self.stats['cached'] += 1
                logger.info(f"✓ Cached {ticker}: ${latest['close']:.2f}")
            
            return data
            
        except Exception as e:
            logger.error(f"Error in pipeline for {ticker}: {e}")
            self.stats['failed'] += 1
            self.stats['errors'].append(str(e))
            return None
    
    async def fetch_and_cache_snapshot(
        self,
        tickers: List[str],
        force_refresh: bool = False
    ) -> Dict[str, float]:
        """Fetch current prices for multiple tickers."""
        
        logger.info(f"Fetching snapshot for {len(tickers)} tickers")
        
        results = {}
        
        for ticker in tickers:
            try:
                price = await self.market_data_service.get_latest_price(ticker)
                
                if price is not None:
                    results[ticker] = price
                    self.stats['cached'] += 1
                else:
                    self.stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to fetch {ticker}: {e}")
                self.stats['failed'] += 1
                self.stats['errors'].append(f"{ticker}: {e}")
        
        # Validate
        is_valid, issues = self.validator.validate_prices(results)
        if not is_valid:
            logger.warning(f"Price validation issues: {issues}")
            self.stats['errors'].extend(issues)
        
        logger.info(f"✓ Got prices for {len(results)}/{len(tickers)} tickers")
        return results
    
    async def refresh_all_data(self, tickers: List[str]) -> Dict:
        """Refresh all data (prices + OHLCV)."""
        
        logger.info(f"Full refresh for {len(tickers)} tickers")
        
        # Refresh prices
        prices = await self.fetch_and_cache_snapshot(tickers)
        
        # Refresh OHLCV for recent period (last 100 days)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        
        ohlcv_results = {}
        for ticker in tickers:
            data = await self.fetch_and_cache_ohlcv(
                ticker, start_date, end_date
            )
            ohlcv_results[ticker] = len(data) if data is not None else 0
        
        return {
            'prices': prices,
            'ohlcv_rows': ohlcv_results,
            'stats': self.stats
        }
    
    def get_cached_data(self, ticker: str) -> Optional[MarketDataCache]:
        """Get cached data for ticker."""
        
        cache = MarketDataOperations.get_market_data(self.db, ticker)
        
        if cache and cache.is_stale():
            logger.warning(f"Cache stale for {ticker} ({cache.ttl_hours}h)")
            return None
        
        return cache
    
    def get_all_cached_data(self) -> List[MarketDataCache]:
        """Get all cached data."""
        return MarketDataOperations.get_all_market_data(self.db)
    
    def clear_stale_cache(self) -> int:
        """Clear stale cache entries."""
        
        all_cache = self.get_all_cached_data()
        stale_count = 0
        
        for cache in all_cache:
            if cache.is_stale():
                # In real implementation, delete from DB
                stale_count += 1
        
        logger.info(f"Stale cache entries: {stale_count}")
        return stale_count
    
    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        return {
            'fetched': self.stats['fetched'],
            'cached': self.stats['cached'],
            'failed': self.stats['failed'],
            'validated': self.stats['validated'],
            'error_count': len(self.stats['errors']),
            'errors': self.stats['errors'][-10:]  # Last 10 errors
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'fetched': 0,
            'cached': 0,
            'failed': 0,
            'validated': 0,
            'errors': []
        }


class CacheManager:
    """Manage data cache lifecycle."""
    
    def __init__(self, db: Session, ttl_hours: int = 24):
        """Initialize cache manager."""
        self.db = db
        self.ttl_hours = ttl_hours
    
    def get_cache_status(self) -> Dict:
        """Get cache statistics."""
        
        all_cache = MarketDataOperations.get_all_market_data(self.db)
        
        fresh_count = 0
        stale_count = 0
        
        for cache in all_cache:
            if cache.is_stale():
                stale_count += 1
            else:
                fresh_count += 1
        
        return {
            'total': len(all_cache),
            'fresh': fresh_count,
            'stale': stale_count,
            'coverage_pct': (fresh_count / max(len(all_cache), 1)) * 100
        }
    
    def get_missing_tickers(
        self,
        required_tickers: List[str]
    ) -> List[str]:
        """Identify tickers without fresh cache."""
        
        missing = []
        
        for ticker in required_tickers:
            cache = MarketDataOperations.get_market_data(self.db, ticker)
            if cache is None or cache.is_stale():
                missing.append(ticker)
        
        return missing
    
    def suggest_refresh(self) -> Dict:
        """Suggest which data to refresh."""
        
        all_cache = MarketDataOperations.get_all_market_data(self.db)
        
        refresh_soon = []
        refresh_urgent = []
        
        now = datetime.now()
        
        for cache in all_cache:
            age_hours = (now - cache.cached_at).total_seconds() / 3600
            
            if age_hours > self.ttl_hours:
                refresh_urgent.append(cache.ticker)
            elif age_hours > self.ttl_hours * 0.75:
                refresh_soon.append(cache.ticker)
        
        return {
            'refresh_urgent': refresh_urgent,
            'refresh_soon': refresh_soon,
            'message': f"Refresh {len(refresh_urgent)} urgent + {len(refresh_soon)} soon"
        }
