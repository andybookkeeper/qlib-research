# src/qlib_research/app/services/qlib_service.py
"""Qlib integration service."""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger("qlib_trading.qlib_service")


class QlibService:
    """Qlib market data and signal service."""
    
    def __init__(self, region: str = "US", provider_uri: str = "data/qlib/qlib_data"):
        """Initialize Qlib service."""
        self.region = region
        self.provider_uri = provider_uri
        self.qlib = None
        self.initialized = False
        self.cache = {}
        self.cache_ttl = 24 * 3600  # 24 hours
    
    def initialize(self) -> bool:
        """Initialize Qlib with market data provider."""
        try:
            import qlib
            from qlib.constant import REG_US, REG_CN
            
            # Region config
            region_code = REG_US if self.region.upper() == "US" else REG_CN
            
            # Initialize Qlib
            qlib.init(
                provider_uri=self.provider_uri,
                region=region_code,
                expression_provider="custom"
            )
            
            self.qlib = qlib
            self.initialized = True
            logger.info(f"✓ Qlib initialized: region={self.region}, provider={self.provider_uri}")
            return True
            
        except ImportError:
            logger.error("Qlib not installed. Install with: pip install qlib-stock")
            return False
        except Exception as e:
            logger.error(f"Qlib initialization failed: {e}")
            return False
    
    def get_ohlcv(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        frequency: str = "day"
    ) -> Optional[pd.DataFrame]:
        """Get OHLCV data from Qlib."""
        
        if not self.initialized:
            logger.warning("Qlib not initialized")
            return None
        
        try:
            # Get market data from Qlib
            # Format: ticker format like 'SH600000' or 'AAPL' depending on region
            
            # For US market, use Yahoo Finance provider (fallback)
            if self.region.upper() == "US":
                return self._get_ohlcv_yahoo(ticker, start_date, end_date)
            
            # For CN market, use Qlib
            qlib_ticker = f"SH{ticker}" if not ticker.startswith("SH") and not ticker.startswith("SZ") else ticker
            
            fields = ["$open", "$high", "$low", "$close", "$volume"]
            data = self.qlib.D.features(
                [qlib_ticker],
                fields,
                start_time=start_date,
                end_time=end_date,
                freq=frequency
            )
            
            logger.info(f"✓ Got {len(data)} rows of {ticker} data")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get OHLCV for {ticker}: {e}")
            return None
    
    def _get_ohlcv_yahoo(
        self,
        ticker: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """Get OHLCV from Yahoo Finance (US market fallback)."""
        
        try:
            import yfinance as yf
            
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False
            )
            
            if data is None or data.empty:
                logger.warning(f"No data from Yahoo for {ticker}")
                return None
            
            # Normalize column names
            data = data.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume',
                'Adj Close': 'adj_close'
            })
            
            logger.info(f"✓ Got {len(data)} rows from Yahoo for {ticker}")
            return data[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            logger.error(f"Yahoo Finance error: {e}")
            return None
    
    def get_daily_snapshot(self, tickers: List[str]) -> Dict:
        """Get latest price snapshot for tickers."""
        
        try:
            import yfinance as yf
            
            snapshot = {}
            for ticker in tickers:
                data = yf.download(ticker, period="1d", progress=False)
                
                if data is not None and not data.empty:
                    snapshot[ticker] = {
                        'open': float(data['Open'].iloc[-1]),
                        'high': float(data['High'].iloc[-1]),
                        'low': float(data['Low'].iloc[-1]),
                        'close': float(data['Close'].iloc[-1]),
                        'volume': int(data['Volume'].iloc[-1]),
                        'timestamp': data.index[-1]
                    }
            
            logger.info(f"✓ Got snapshot for {len(snapshot)}/{len(tickers)} tickers")
            return snapshot
            
        except Exception as e:
            logger.error(f"Snapshot fetch error: {e}")
            return {}
    
    def get_available_tickers(self, market: str = "us") -> List[str]:
        """Get available tickers for market."""
        
        # US market tickers (sample)
        us_tickers = [
            "AAPL", "MSFT", "GOOGL", "TSLA", "NVDA",
            "JPM", "V", "JNJ", "WMT", "PG",
            "MA", "NFLX", "META", "AMZN", "MSTR"
        ]
        
        # Can extend with more tickers
        return us_tickers if market.lower() == "us" else []
    
    def __repr__(self):
        return f"<QlibService region={self.region} initialized={self.initialized}>"
