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
from src.qlib_research.app.services.realtime_service import realtime_hub

router = APIRouter()

# In-memory cache for phase 1
_price_cache: Dict[str, Dict] = {}
_cache_stats = {"fetches": 0, "hits": 0, "misses": 0}
_default_tickers = [
    "AAPL", "MSFT", "GOOGL", "TSLA", "NVDA",
    "JPM", "V", "JNJ", "WMT", "PG",
]


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

    await realtime_hub.broadcast_price_update(
        ticker=ticker.upper(),
        price=price,
        volume=volume,
        change_pct=0,
    )

    return {"status": "cached", "ticker": ticker, "price": price}


@router.get("/cache/status")
async def get_cache_status() -> CacheStatus:
    """Get cache status."""
    total = len(_default_tickers)
    fresh = sum(1 for ticker in _default_tickers if ticker in _price_cache)
    stale = 0
    coverage_pct = (fresh / total * 100.0) if total else 0.0

    return CacheStatus(
        total=total,
        fresh=fresh,
        stale=stale,
        coverage_pct=coverage_pct,
    )


@router.get("/cache/missing")
async def get_missing_data() -> List[str]:
    """Get list of tickers with missing or stale data."""

    missing = [t for t in _default_tickers if t not in _price_cache]
    return missing


@router.get("/cache/refresh-suggestion")
async def get_refresh_suggestion() -> RefreshSuggestion:
    """Suggest which tickers should be refreshed first."""
    missing = [t for t in _default_tickers if t not in _price_cache]
    refresh_urgent = missing[:5]
    refresh_soon = missing[5:]
    if not missing:
        message = "Cache coverage is good. No urgent refresh needed."
    else:
        message = "Refresh urgent tickers first, then refresh the remaining soon list."
    return RefreshSuggestion(
        refresh_urgent=refresh_urgent,
        refresh_soon=refresh_soon,
        message=message,
    )
