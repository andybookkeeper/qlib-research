# Market Data Pipeline Specification
# Qlib-based data ingestion, caching, and serving

## Overview

The market data pipeline is responsible for:
1. **Ingestion**: Fetching OHLC data from external providers (Yahoo Finance)
2. **Storage**: Storing data in Qlib's format and local caches
3. **Serving**: Providing prices to the app via API
4. **Refresh**: Updating prices daily and maintaining cache freshness
5. **Reliability**: Handling provider failures gracefully

MVP focuses on **daily end-of-day data** (no intraday). US stocks only.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    External Providers                        │
│  - Yahoo Finance (free, limited data)                       │
│  - Qlib data service (if configured)                        │
│  - Custom provider (future)                                 │
└──────────────────────────────────────────────────────────────┘
                           ↓ (Daily fetch)
┌──────────────────────────────────────────────────────────────┐
│                  Qlib Data Provider                          │
│  - Handle provider initialization                           │
│  - Manage data storage                                      │
│  - Fetch historical data                                    │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                   Data Storage Layer                         │
│  - Local cache (SQLite, pickle)                             │
│  - Qlib data directory (data/qlib/...)                      │
│  - MLflow artifacts (experiment data)                       │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                 Market Data Service                          │
│  - Query and cache prices                                   │
│  - Serve via API endpoints                                  │
│  - Handle cache expiration                                  │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              FastAPI Endpoints                               │
│  - GET /api/market_data/{ticker}                            │
│  - GET /api/ohlc?ticker=AAPL&start=...&end=...             │
│  - GET /api/market_data/bulk?tickers=AAPL,MSFT             │
└──────────────────────────────────────────────────────────────┘
```

## Qlib Initialization

### 1. Qlib Provider Configuration

```python
# src/qlib_research/init_qlib.py

import os
from qlib.data import D
from qlib.data import init as qlib_init

def init_qlib(provider_uri: str = None, region: str = "US"):
    """
    Initialize Qlib with specified provider.
    
    Args:
        provider_uri: Path or URL to data provider
                     - "yahoo" for Yahoo Finance (requires qlib-data fetch)
                     - "/path/to/data" for local directory
                     - "http://server:5000" for remote Qlib service
        region: Data region ("US" or "CN")
    
    Returns:
        Initialized Qlib provider
    
    Example:
        # Use default (Yahoo via qlib)
        qlib_init(provider_uri="yahoo", region="US")
        
        # Use local data
        qlib_init(provider_uri="~/qlib-data", region="US")
        
        # Use remote Qlib server
        qlib_init(provider_uri="http://localhost:5000", region="US")
    """
    
    # Resolve provider URI from env → arg → default
    provider_uri = provider_uri or os.getenv("QLIB_PROVIDER_URI", "yahoo")
    region = region or os.getenv("QLIB_REGION", "US")
    
    # Expand home directory
    if provider_uri.startswith("~"):
        provider_uri = os.path.expanduser(provider_uri)
    
    # Initialize Qlib
    try:
        qlib_init(
            provider_uri=provider_uri,
            region=region,
            expression_cache=None,  # Disable expression caching for MVP
            calendar_cache=None
        )
        print(f"✓ Qlib initialized with provider={provider_uri}, region={region}")
        return D  # Return Qlib data accessor
    except Exception as e:
        print(f"✗ Qlib initialization failed: {e}")
        raise

# Call at app startup
if __name__ == "__main__":
    provider = init_qlib()
    # Now can use: D.features(["AAPL"], ["close", "high", "low"])
```

### 2. Provider Options for MVP

#### Option A: Yahoo Finance (Recommended for MVP)
- **Pros**: Free, easy setup, no local data storage needed
- **Cons**: Limited historical data (Yahoo has ~20 years), rate-limited
- **Setup**:
  ```bash
  # Download Qlib data from Yahoo
  python -c "from qlib.data import init; init(provider_uri='yahoo', region='US')"
  
  # Or let Qlib auto-fetch on first use
  ```

#### Option B: Local Data Directory
- **Pros**: Full control, fast, no network dependency
- **Cons**: Must maintain data files, manual updates
- **Setup**:
  ```
  data/qlib/
  ├── cn_data/           # (if using CN region)
  └── us_data/
      ├── stock_data.csv
      └── calendars.csv
  ```

#### Option C: Remote Qlib Service (Future)
- For multi-user deployments
- Requires separate Qlib data server

**MVP decision**: Use Yahoo Finance via Qlib auto-fetch. No manual data management required.

## Data Fetching

### 1. Fetch Latest Prices

```python
# src/qlib_research/app/services/market_data_service.py

import pandas as pd
from qlib.data import D
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class MarketDataService:
    """Fetches and caches market data from Qlib"""
    
    def __init__(self, cache_ttl_hours: int = 24):
        """
        Args:
            cache_ttl_hours: Time-to-live for price cache (hours)
        """
        self.cache: Dict[str, dict] = {}  # {ticker: {price, timestamp}}
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
    
    def get_current_price(self, ticker: str) -> float:
        """
        Get latest close price for a ticker.
        
        Returns:
            float: Latest close price
            
        Raises:
            DataFetchError: If ticker not found or fetch fails
        """
        # Check cache first
        if self._is_cached(ticker):
            return self.cache[ticker]["price"]
        
        # Fetch from Qlib
        try:
            # Get last trading day's close
            df = D.features(
                instruments=[ticker],
                fields=["close"],
                start_time="2024-01-01",  # Arbitrary start
                end_time=datetime.now().strftime("%Y-%m-%d")
            )
            
            if df.empty:
                raise DataFetchError(f"No data found for {ticker}")
            
            price = float(df.iloc[-1]["close"])  # Last row = today
            
            # Cache result
            self.cache[ticker] = {
                "price": price,
                "timestamp": datetime.now(),
                "ticker": ticker
            }
            
            return price
            
        except Exception as e:
            raise DataFetchError(f"Failed to fetch price for {ticker}: {e}")
    
    def _is_cached(self, ticker: str) -> bool:
        """Check if ticker is in cache and not expired"""
        if ticker not in self.cache:
            return False
        
        age = datetime.now() - self.cache[ticker]["timestamp"]
        return age < self.cache_ttl
    
    def get_ohlc_data(
        self, 
        ticker: str, 
        start_date: str, 
        end_date: str,
        fields: List[str] = None
    ) -> pd.DataFrame:
        """
        Get historical OHLC data for a ticker.
        
        Args:
            ticker: Stock symbol (e.g., "AAPL")
            start_date: ISO format (e.g., "2023-01-01")
            end_date: ISO format (e.g., "2024-01-31")
            fields: Columns to fetch (default: ["open", "high", "low", "close", "volume"])
        
        Returns:
            pd.DataFrame: OHLC data with date as index
        """
        if fields is None:
            fields = ["open", "high", "low", "close", "volume"]
        
        try:
            df = D.features(
                instruments=[ticker],
                fields=fields,
                start_time=start_date,
                end_time=end_date
            )
            
            if df.empty:
                raise DataFetchError(f"No data found for {ticker} in range {start_date}:{end_date}")
            
            # Clean up index (Qlib returns multi-index)
            df = df.reset_index()
            df.columns = ["date"] + fields
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            
            return df
            
        except Exception as e:
            raise DataFetchError(f"Failed to fetch OHLC for {ticker}: {e}")
    
    def get_bulk_prices(self, tickers: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple tickers.
        
        Returns:
            {ticker: price}
        """
        prices = {}
        for ticker in tickers:
            try:
                prices[ticker] = self.get_current_price(ticker)
            except DataFetchError as e:
                # Log but don't fail entire batch
                print(f"Warning: {e}")
                prices[ticker] = None
        
        return prices
    
    def refresh_cache(self, tickers: List[str]) -> None:
        """Force refresh cache for specified tickers"""
        for ticker in tickers:
            if ticker in self.cache:
                del self.cache[ticker]
            # Next call will refetch
    
    def clear_cache(self) -> None:
        """Clear all cached prices"""
        self.cache.clear()
```

### 2. Data Validation

```python
# Validate fetched data quality

def validate_ohlc_data(df: pd.DataFrame) -> bool:
    """
    Validate OHLC data integrity.
    
    Checks:
    - No NaN values
    - high >= low
    - high >= close >= low
    - volume >= 0
    """
    assert not df.isnull().any().any(), "Data contains NaN values"
    assert (df["high"] >= df["low"]).all(), "Invalid OHLC: high < low"
    assert (df["high"] >= df["close"]).all(), "Invalid OHLC: close > high"
    assert (df["close"] >= df["low"]).all(), "Invalid OHLC: close < low"
    assert (df["volume"] >= 0).all(), "Invalid volume (negative)"
    return True
```

## API Endpoints

### 1. Get Current Price

```python
# src/qlib_research/app/api/routes/market_data.py

from fastapi import APIRouter, Depends, HTTPException
from src.qlib_research.app.services.market_data_service import MarketDataService
from src.qlib_research.app.api.dependencies import get_market_data_service

router = APIRouter(prefix="/api/market_data", tags=["market_data"])

@router.get("/{ticker}")
def get_current_price(
    ticker: str,
    market_data: MarketDataService = Depends(get_market_data_service)
):
    """
    Get latest close price and daily change for a ticker.
    
    Example: GET /api/market_data/AAPL
    
    Response:
    {
      "ticker": "AAPL",
      "price": 150.25,
      "open": 148.50,
      "high": 151.00,
      "low": 148.25,
      "volume": 52000000,
      "daily_change": 1.75,
      "daily_change_pct": 1.17,
      "timestamp": "2024-01-15T16:00:00Z"
    }
    """
    try:
        # Get today's OHLC
        today = datetime.now().strftime("%Y-%m-%d")
        df = market_data.get_ohlc_data(ticker, today, today)
        
        row = df.iloc[0]
        price = float(row["close"])
        open_price = float(row["open"])
        
        return {
            "ticker": ticker.upper(),
            "price": price,
            "open": open_price,
            "high": float(row["high"]),
            "low": float(row["low"]),
            "volume": int(row["volume"]),
            "daily_change": price - open_price,
            "daily_change_pct": ((price - open_price) / open_price * 100) if open_price else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch price for {ticker}: {str(e)}")
```

### 2. Get Historical OHLC

```python
@router.get("/ohlc")
def get_ohlc(
    ticker: str,
    start_date: str,
    end_date: str,
    market_data: MarketDataService = Depends(get_market_data_service)
):
    """
    Get historical OHLC data.
    
    Example: GET /api/market_data/ohlc?ticker=AAPL&start_date=2023-01-01&end_date=2024-01-31
    
    Response:
    {
      "ticker": "AAPL",
      "data": [
        {
          "date": "2024-01-15",
          "open": 148.50,
          "high": 151.00,
          "low": 148.25,
          "close": 150.25,
          "volume": 52000000
        }
      ]
    }
    """
    try:
        df = market_data.get_ohlc_data(ticker, start_date, end_date)
        
        # Convert to list of dicts
        data = []
        for date, row in df.iterrows():
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"])
            })
        
        return {
            "ticker": ticker.upper(),
            "start_date": start_date,
            "end_date": end_date,
            "data": data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### 3. Get Bulk Prices

```python
@router.post("/bulk")
def get_bulk_prices(
    tickers: List[str],
    market_data: MarketDataService = Depends(get_market_data_service)
):
    """
    Get current prices for multiple tickers in one request.
    
    Request body:
    {
      "tickers": ["AAPL", "MSFT", "GOOGL"]
    }
    
    Response:
    {
      "prices": {
        "AAPL": 150.25,
        "MSFT": 380.50,
        "GOOGL": 140.75
      },
      "timestamp": "2024-01-15T16:00:00Z"
    }
    """
    prices = market_data.get_bulk_prices(tickers)
    return {
        "prices": prices,
        "timestamp": datetime.now().isoformat()
    }
```

## Caching Strategy

### 1. In-Memory Cache (MVP)

```python
class CacheEntry:
    price: float
    timestamp: datetime
    ttl: timedelta

# Check cache before fetching
if ticker in cache and cache[ticker].timestamp + cache[ticker].ttl > now:
    return cache[ticker].price

# Fetch from Qlib and cache
price = fetch_from_qlib(ticker)
cache[ticker] = CacheEntry(price, now, ttl=24h)
```

### 2. Cache Invalidation

```python
# Automatic: Time-based (24 hour TTL)
# Manual: API endpoint to force refresh
# Scheduled: Daily refresh at market close (4 PM ET)

@router.post("/cache/refresh")
def refresh_cache(
    tickers: List[str] = None,
    market_data: MarketDataService = Depends(get_market_data_service)
):
    """Force refresh cache for specified tickers (or all if tickers is null)"""
    if tickers:
        market_data.refresh_cache(tickers)
    else:
        market_data.clear_cache()
    
    return {"status": "refreshed", "tickers": tickers or "all"}
```

## Error Handling

### Custom Exceptions

```python
# src/qlib_research/app/utils/errors.py

class DataFetchError(Exception):
    """Raised when data fetch fails"""
    pass

class InvalidTickerError(DataFetchError):
    """Raised when ticker symbol is invalid"""
    pass

class NoDataError(DataFetchError):
    """Raised when no data available for date range"""
    pass

class ProviderError(DataFetchError):
    """Raised when provider is unavailable"""
    pass
```

### Fallback Strategy

```python
def get_current_price_with_fallback(ticker: str, market_data: MarketDataService):
    """
    Get price with fallback to cache.
    
    1. Try fresh fetch
    2. Fall back to stale cache (if available)
    3. Raise error
    """
    try:
        return market_data.get_current_price(ticker, force_refresh=True)
    except ProviderError:
        # Provider down, use stale cache
        if ticker in market_data.cache:
            print(f"Warning: Using stale price for {ticker}")
            return market_data.cache[ticker]["price"]
        else:
            raise NoDataError(f"No data available for {ticker} (provider offline)")
```

## Daily Refresh Job

### Scheduled Task (Optional for MVP)

```python
# src/qlib_research/app/background_tasks.py

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time

def refresh_market_data(market_data_service: MarketDataService):
    """Refresh price cache daily at market close (4 PM ET)"""
    try:
        # List of main stocks to pre-cache
        main_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        market_data_service.refresh_cache(main_tickers)
        print(f"✓ Market data refreshed at {datetime.now()}")
    except Exception as e:
        print(f"✗ Market data refresh failed: {e}")

def setup_background_jobs(app: FastAPI):
    """Setup scheduled background tasks"""
    scheduler = BackgroundScheduler()
    
    # Refresh prices daily at 4:00 PM ET
    scheduler.add_job(
        func=lambda: refresh_market_data(app.state.market_data),
        trigger="cron",
        hour=16,
        minute=0,
        timezone="US/Eastern",
        id="refresh_market_data"
    )
    
    scheduler.start()
    
    # Shutdown job on app shutdown
    def shutdown_scheduler():
        scheduler.shutdown()
    
    app.add_event_handler("shutdown", shutdown_scheduler)
```

## Data Quality Monitoring

### Log Fetch Operations

```python
def log_data_fetch(ticker: str, source: str, success: bool, duration_ms: int):
    """Log all data fetch operations for monitoring"""
    logger.info(json.dumps({
        "event": "data_fetch",
        "ticker": ticker,
        "source": source,
        "success": success,
        "duration_ms": duration_ms,
        "timestamp": datetime.now().isoformat()
    }))
```

### Track Metrics

- Fetch success rate (% successful)
- Fetch latency (average, p99)
- Cache hit rate (% served from cache)
- Provider availability (uptime)

## Testing

### Unit Tests

```python
# tests/unit/test_market_data_service.py

import pytest
from unittest.mock import Mock, patch
from src.qlib_research.app.services.market_data_service import MarketDataService

@pytest.fixture
def service():
    return MarketDataService(cache_ttl_hours=24)

def test_get_current_price_cache_hit(service):
    """Test that cached prices are returned without refetch"""
    service.cache["AAPL"] = {
        "price": 150.25,
        "timestamp": datetime.now(),
        "ticker": "AAPL"
    }
    
    price = service.get_current_price("AAPL")
    assert price == 150.25

def test_get_current_price_fetch(service):
    """Test that price is fetched from Qlib when not cached"""
    with patch("src.qlib_research.app.services.market_data_service.D.features") as mock:
        # Mock Qlib response
        mock_df = Mock()
        mock_df.empty = False
        mock_df.iloc.__getitem__.return_value = Mock(close=150.25)
        mock.return_value = mock_df
        
        price = service.get_current_price("AAPL")
        assert price == 150.25
        assert "AAPL" in service.cache

def test_ohlc_data_validation():
    """Test that invalid OHLC data raises error"""
    invalid_df = pd.DataFrame({
        "open": [100],
        "high": [90],  # Invalid: high < low
        "low": [80],
        "close": [95],
        "volume": [1000000]
    })
    
    with pytest.raises(AssertionError):
        validate_ohlc_data(invalid_df)
```

### Integration Tests

```python
# tests/integration/test_market_data_api.py

def test_get_current_price_endpoint(client):
    """Test /api/market_data/{ticker} endpoint"""
    response = client.get("/api/market_data/AAPL")
    
    assert response.status_code == 200
    data = response.json()
    assert "ticker" in data
    assert "price" in data
    assert "daily_change" in data

def test_get_ohlc_endpoint(client):
    """Test /api/market_data/ohlc endpoint"""
    response = client.get(
        "/api/market_data/ohlc",
        params={
            "ticker": "AAPL",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert len(data["data"]) > 0
```

## Acceptance Criteria

- [ ] Qlib initialized successfully with Yahoo data provider
- [ ] Can fetch current price for any valid US stock ticker
- [ ] Can fetch historical OHLC data for any date range
- [ ] Price cache works (24-hour TTL, manual refresh)
- [ ] API endpoints return proper JSON responses
- [ ] Data validation catches malformed OHLC data
- [ ] Error handling works (invalid ticker, no data, provider offline)
- [ ] Bulk price fetch returns results for multiple tickers
- [ ] All market data operations logged
- [ ] Unit tests pass (cache, validation, error cases)
- [ ] Integration tests pass (API endpoints with mock Qlib)
- [ ] No rate limiting issues (Yahoo allows ~2000 requests/hour)

## Configuration

```yaml
# configs/app/settings.yaml

market_data:
  provider: "yahoo"  # or path to local data
  region: "US"
  cache_ttl_hours: 24
  
  # Fallback strategy if provider offline
  fallback_to_cache: true
  cache_stale_warning_hours: 72
  
  # Daily refresh job
  refresh_schedule:
    enabled: true
    time: "16:00"  # 4 PM ET (market close)
    timezone: "US/Eastern"
    main_tickers: ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
```

## Known Limitations (MVP)

- **Daily data only**: No intraday / real-time quotes
- **US stocks only**: No international markets
- **Yahoo data**: Limited to ~20 years of history
- **No options data**: Options prices sourced from external API (future)
- **Single cache instance**: No distributed caching (acceptable for single-user MVP)
