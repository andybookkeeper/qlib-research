# src/qlib_research/app/api/routes/market.py
"""Market data API endpoints."""

from typing import List, Dict
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from src.qlib_research.app.api.schemas.market import (
    PriceSnapshot,
    CacheStatus,
    DataPipelineStats,
    RefreshSuggestion
)

router = APIRouter()

# In-memory cache for phase 1
_price_cache: Dict[str, Dict] = {}
_cache_stats = {"fetches": 0, "hits": 0, "misses": 0}


@router.get("/tickers")
async def get_available_tickers() -> List[str]:
    """Get available tickers for trading."""
    
    tickers = [
        "AAPL", "MSFT", "GOOGL", "TSLA", "NVDA",
        "JPM", "V", "JNJ", "WMT", "PG",
        "MA", "NFLX", "META", "AMZN", "MSTR"
    ]
    
    return tickers


@router.get("/price/{ticker}")
async def get_current_price(ticker: str) -> PriceSnapshot:
    """Get current price for ticker."""
    
    if ticker in _price_cache:
        _cache_stats["hits"] += 1
        data = _price_cache[ticker]
        return PriceSnapshot(
            ticker=ticker,
            price=data.get('price', 0),
            timestamp=data.get('timestamp', datetime.now()),
            volume=data.get('volume', 0),
            change_pct=data.get('change_pct', 0)
        )
    
    _cache_stats["misses"] += 1
    _cache_stats["fetches"] += 1
    
    # Return placeholder
    return PriceSnapshot(
        ticker=ticker,
        price=0,
        timestamp=datetime.now(),
        volume=0,
        change_pct=0
    )


@router.get("/prices")
async def get_prices(tickers: List[str] = Query(...)) -> List[PriceSnapshot]:
    """Get current prices for multiple tickers."""
    
    results = []
    
    for ticker in tickers:
        if ticker in _price_cache:
            _cache_stats["hits"] += 1
            data = _price_cache[ticker]
            results.append(PriceSnapshot(
                ticker=ticker,
                price=data.get('price', 0),
                timestamp=data.get('timestamp', datetime.now()),
                volume=data.get('volume', 0),
                change_pct=data.get('change_pct', 0)
            ))
        else:
            _cache_stats["misses"] += 1
    
    return results


@router.post("/cache/{ticker}")
async def set_price(ticker: str, price: float, volume: int = 0) -> Dict:
    """Set price in cache."""
    
    _price_cache[ticker] = {
        "price": price,
        "volume": volume,
        "timestamp": datetime.now(),
        "change_pct": 0
    }
    
    return {"status": "cached", "ticker": ticker, "price": price}


@router.get("/cache/status")
async def get_cache_status() -> CacheStatus:
    """Get cache status."""
    
    return CacheStatus(
        total_cached=len(_price_cache),
        cache_hits=_cache_stats["hits"],
        cache_misses=_cache_stats["misses"],
        total_fetches=_cache_stats["fetches"],
        last_updated=datetime.now()
    )


@router.get("/cache/missing")
async def get_missing_data() -> List[str]:
    """Get list of tickers with missing or stale data."""
    
    all_tickers = [
        "AAPL", "MSFT", "GOOGL", "TSLA", "NVDA",
        "JPM", "V", "JNJ", "WMT", "PG"
    ]
    
    missing = [t for t in all_tickers if t not in _price_cache]
    return missing


