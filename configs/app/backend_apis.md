# Backend APIs Specification
# FastAPI routes, request/response schemas, error handling, and middleware

## Overview

The backend API layer provides:
1. **Market Data Endpoints**: Current prices, OHLC, market overview
2. **Analysis Endpoints**: Stock analysis, options chains, Greeks
3. **Trading Endpoints**: Manual order entry, order status, trade history
4. **Portfolio Endpoints**: Positions, P&L, risk metrics, Greeks
5. **Research Endpoints**: Qlib signals, backtests, model performance
6. **Settings Endpoints**: User preferences, risk limits
7. **System Endpoints**: Health, version, deployment info

**Architecture**: FastAPI + Pydantic for validation + dependency injection for service layer

## API Design Principles

1. **RESTful**: Standard HTTP methods (GET, POST, PUT, DELETE)
2. **Versioned**: `/api/v1/` prefix for future compatibility
3. **Documented**: Automatic OpenAPI/Swagger at `/docs`
4. **Validated**: Pydantic models for all inputs/outputs
5. **Paginated**: Large result sets use cursor or offset pagination
6. **Error Responses**: Consistent error format with codes and messages
7. **Async**: All endpoints async-ready with `async def`

## Project Structure

```
src/qlib_research/app/
├── api/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app and middleware setup
│   ├── dependencies.py          # Dependency injection functions
│   ├── exceptions.py            # Custom exception classes
│   ├── middleware.py            # Request/response middleware
│   ├── schemas/                 # Pydantic models
│   │   ├── market.py            # MarketDataRequest, etc.
│   │   ├── trading.py           # OrderRequest, TradeResponse, etc.
│   │   ├── portfolio.py         # PositionResponse, GreeksResponse, etc.
│   │   └── common.py            # Pagination, error responses
│   └── routes/
│       ├── market.py            # GET market data
│       ├── analysis.py          # GET analysis (stocks, options)
│       ├── trading.py           # POST orders, GET order status
│       ├── portfolio.py         # GET positions, Greeks, risk
│       ├── research.py          # GET Qlib signals, backtests
│       ├── settings.py          # GET/POST risk limits, preferences
│       └── health.py            # GET health, version
```

## FastAPI Application Setup

```python
# src/qlib_research/app/api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from src.qlib_research.app.api import routes
from src.qlib_research.app.api.exceptions import TradingError, ValidationError
from src.qlib_research.app.api.middleware import (
    add_request_tracking, add_error_handling, add_performance_logging
)

# App lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Startup and shutdown hooks.
    
    Startup: Initialize services, connect to databases, warm up caches
    Shutdown: Close connections, persist state, cleanup
    """
    # Startup
    print("Starting Qlib Trading App API...")
    
    # Initialize services (moved to dependencies.py)
    # app.state.market_data_service = MarketDataService()
    # app.state.broker_service = PaperBrokerService()
    # etc.
    
    yield  # App is running
    
    # Shutdown
    print("Shutting down Qlib Trading App API...")
    # Cleanup (close DB connections, etc.)

# Create FastAPI app
app = FastAPI(
    title="Qlib Trading API",
    description="Quantitative trading backend with paper trading",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (allow frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
add_request_tracking(app)      # Log request ID, timestamp
add_error_handling(app)         # Global exception handler
add_performance_logging(app)    # Track endpoint latency

# Exception handlers
@app.exception_handler(TradingError)
async def trading_error_handler(request, exc: TradingError):
    """Handle domain-specific errors"""
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "code": getattr(exc, "code", "TRADING_ERROR")
        }
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": str(exc),
            "details": getattr(exc, "details", [])
        }
    )

@app.exception_handler(Exception)
async def generic_error_handler(request, exc: Exception):
    """Catch all unhandled errors"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "type": exc.__class__.__name__
        }
    )

# Include routers
app.include_router(routes.market.router, prefix="/api/v1", tags=["market"])
app.include_router(routes.analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(routes.trading.router, prefix="/api/v1", tags=["trading"])
app.include_router(routes.portfolio.router, prefix="/api/v1", tags=["portfolio"])
app.include_router(routes.research.router, prefix="/api/v1", tags=["research"])
app.include_router(routes.settings.router, prefix="/api/v1", tags=["settings"])
app.include_router(routes.health.router, prefix="/api/v1", tags=["health"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Exception Hierarchy

```python
# src/qlib_research/app/api/exceptions.py

class TradingError(Exception):
    """Base exception for trading errors"""
    code = "TRADING_ERROR"
    status_code = 400

class ValidationError(TradingError):
    """Input validation failed"""
    code = "VALIDATION_ERROR"
    
    def __init__(self, message: str, details: list = None):
        super().__init__(message)
        self.details = details or []

class InsufficientBuyingPowerError(TradingError):
    """Account lacks buying power for trade"""
    code = "INSUFFICIENT_BUYING_POWER"

class RiskLimitExceededError(TradingError):
    """Trade would violate risk limits"""
    code = "RISK_LIMIT_EXCEEDED"

class OrderNotFoundError(TradingError):
    """Order ID does not exist"""
    code = "ORDER_NOT_FOUND"
    status_code = 404

class PositionNotFoundError(TradingError):
    """Position does not exist"""
    code = "POSITION_NOT_FOUND"
    status_code = 404

class DataFetchError(TradingError):
    """Failed to fetch data from provider"""
    code = "DATA_FETCH_ERROR"

class InvalidInstrumentError(TradingError):
    """Instrument not supported"""
    code = "INVALID_INSTRUMENT"
```

## Request/Response Schemas

### Common Schemas

```python
# src/qlib_research/app/api/schemas/common.py

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

class Pagination(BaseModel):
    """Pagination parameters"""
    offset: int = Field(0, ge=0, description="Items to skip")
    limit: int = Field(50, ge=1, le=100, description="Items per page")

class PaginatedResponse(BaseModel):
    """Response wrapper for paginated results"""
    total: int
    offset: int
    limit: int
    items: List[Any]

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    code: str
    timestamp: datetime
    request_id: Optional[str] = None

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthResponse(BaseModel):
    """System health check"""
    status: HealthStatus
    version: str
    timestamp: datetime
    services: dict  # {"market_data": "ok", "broker": "ok", ...}
```

### Market Data Schemas

```python
# src/qlib_research/app/api/schemas/market.py

from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List

class PriceData(BaseModel):
    """Current price snapshot"""
    ticker: str
    price: float
    bid: float
    ask: float
    volume: int
    timestamp: datetime

class OHLCData(BaseModel):
    """OHLC bar"""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None

class MarketOverviewRequest(BaseModel):
    """Request market overview"""
    tickers: List[str]
    include_technicals: bool = False

class MarketOverviewResponse(BaseModel):
    """Market overview response"""
    overview: List[PriceData]
    timestamp: datetime
    source: str = "market_data_service"

class HistoricalDataRequest(BaseModel):
    """Request historical OHLC data"""
    ticker: str
    start_date: date
    end_date: date
    interval: str = "daily"  # daily, weekly, monthly

class HistoricalDataResponse(BaseModel):
    """Historical OHLC response"""
    ticker: str
    bars: List[OHLCData]
    count: int
    start_date: date
    end_date: date
```

### Trading Schemas

```python
# src/qlib_research/app/api/schemas/trading.py

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
from enum import Enum

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class OrderRequest(BaseModel):
    """Create new order"""
    ticker: str = Field(..., min_length=1, max_length=10)
    side: OrderSide
    quantity: int = Field(..., gt=0)
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = Field(None, gt=0)  # For limit orders
    stop_price: Optional[float] = Field(None, gt=0)  # For stop orders
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v, info):
        """Limit orders must have price"""
        if info.data.get('order_type') in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if v is None:
                raise ValueError("price required for limit orders")
        return v

class OrderResponse(BaseModel):
    """Order response"""
    order_id: str
    ticker: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    price: Optional[float]
    status: OrderStatus
    filled_quantity: int = 0
    average_fill_price: Optional[float] = None
    created_at: datetime
    updated_at: datetime

class TradeRecord(BaseModel):
    """Realized trade from closed position"""
    trade_id: str
    ticker: str
    side: OrderSide
    quantity: int
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    commission: float = 0.0
    opened_at: datetime
    closed_at: datetime

class CancelOrderRequest(BaseModel):
    """Cancel existing order"""
    order_id: str
```

### Portfolio Schemas

```python
# src/qlib_research/app/api/schemas/portfolio.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class StockPositionResponse(BaseModel):
    """Stock position details"""
    ticker: str
    quantity: int
    entry_price: float
    current_price: float
    cost_basis: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    portfolio_pct: float

class OptionPositionResponse(BaseModel):
    """Option position details"""
    contract_symbol: str
    quantity: int
    contract_type: str  # call/put
    strike: float
    expiration: str  # YYYY-MM-DD
    entry_price: float
    current_price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    market_value: float
    unrealized_pnl: float

class PortfolioPositionsResponse(BaseModel):
    """All positions"""
    stocks: List[StockPositionResponse]
    options: List[OptionPositionResponse]
    cash_balance: float
    total_market_value: float
    gross_market_value: float
    net_market_value: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    total_pnl_pct: float

class GreeksResponse(BaseModel):
    """Portfolio Greeks"""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    delta_interpretation: str  # e.g., "Long 150 shares equiv."

class RiskMetricsResponse(BaseModel):
    """Portfolio risk snapshot"""
    pnl: dict  # {realized, unrealized, total, total_pct}
    var_95: float  # Value at Risk 95%
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    win_rate: Optional[float] = None
    concentration: dict  # Top positions by exposure %
    leverage: float
    buying_power: float
    margin_utilization_pct: float
```

## API Routes

### Market Data Routes

```python
# src/qlib_research/app/api/routes/market.py

from fastapi import APIRouter, Query, Depends, HTTPException
from src.qlib_research.app.api.schemas.market import (
    MarketOverviewRequest, MarketOverviewResponse, HistoricalDataRequest, HistoricalDataResponse
)
from src.qlib_research.app.api.dependencies import get_market_data_service

router = APIRouter(prefix="/market", tags=["market"])

@router.get("/overview")
async def market_overview(
    tickers: str = Query(..., description="Comma-separated tickers"),
    include_technicals: bool = Query(False),
    market_service=Depends(get_market_data_service)
):
    """
    Get current market prices for multiple tickers.
    
    Example: GET /api/v1/market/overview?tickers=AAPL,MSFT,GOOG
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    
    try:
        prices = market_service.get_bulk_prices(ticker_list)
        
        return MarketOverviewResponse(
            overview=[
                {
                    "ticker": p.ticker,
                    "price": p.current_price,
                    "bid": p.bid,
                    "ask": p.ask,
                    "volume": p.volume,
                    "timestamp": datetime.now()
                }
                for p in prices
            ],
            timestamp=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history/{ticker}")
async def historical_data(
    ticker: str,
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    interval: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    market_service=Depends(get_market_data_service)
):
    """
    Get historical OHLC data.
    
    Example: GET /api/v1/market/history/AAPL?start_date=2024-01-01&end_date=2024-01-31
    """
    from datetime import datetime as dt
    
    try:
        start = dt.strptime(start_date, "%Y-%m-%d").date()
        end = dt.strptime(end_date, "%Y-%m-%d").date()
        
        bars = market_service.get_ohlc_data(
            ticker=ticker.upper(),
            start_date=start,
            end_date=end
        )
        
        return HistoricalDataResponse(
            ticker=ticker.upper(),
            bars=[
                {
                    "date": bar.date,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "adjusted_close": bar.adjusted_close
                }
                for bar in bars
            ],
            count=len(bars),
            start_date=start,
            end_date=end
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Trading Routes

```python
# src/qlib_research/app/api/routes/trading.py

from fastapi import APIRouter, Depends, HTTPException, Path
from src.qlib_research.app.api.schemas.trading import (
    OrderRequest, OrderResponse, OrderStatus, CancelOrderRequest
)
from src.qlib_research.app.api.dependencies import get_broker_service, get_risk_validator

router = APIRouter(prefix="/orders", tags=["trading"])

@router.post("")
async def create_order(
    order_req: OrderRequest,
    broker_service=Depends(get_broker_service),
    risk_validator=Depends(get_risk_validator)
):
    """
    Submit a new order.
    
    Request:
    {
      "ticker": "AAPL",
      "side": "buy",
      "quantity": 100,
      "order_type": "market"
    }
    
    Response:
    {
      "order_id": "ord_123abc",
      "ticker": "AAPL",
      "side": "buy",
      "quantity": 100,
      "status": "filled",
      "filled_quantity": 100,
      "average_fill_price": 150.25,
      "created_at": "2024-01-19T14:30:00Z"
    }
    """
    try:
        # Validate risk limits
        current_positions = broker_service.get_portfolio()
        can_execute, violations = risk_validator.can_execute_trade(
            current_positions,
            order_req
        )
        
        if not can_execute:
            raise HTTPException(
                status_code=400,
                detail=f"Risk limit violations: {', '.join(violations)}"
            )
        
        # Execute order
        order = await broker_service.submit_order(
            ticker=order_req.ticker,
            side=order_req.side,
            quantity=order_req.quantity,
            order_type=order_req.order_type,
            price=order_req.price
        )
        
        return OrderResponse(
            order_id=order.id,
            ticker=order.ticker,
            side=order.side,
            quantity=order.quantity,
            order_type=order.order_type,
            price=order.price,
            status=order.status,
            filled_quantity=order.filled_quantity,
            average_fill_price=order.average_fill_price,
            created_at=order.created_at,
            updated_at=order.updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{order_id}")
async def get_order(
    order_id: str = Path(..., min_length=1),
    broker_service=Depends(get_broker_service)
):
    """Get order status"""
    order = broker_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse(**order.dict())

@router.delete("/{order_id}")
async def cancel_order(
    order_id: str = Path(..., min_length=1),
    broker_service=Depends(get_broker_service)
):
    """Cancel pending order"""
    try:
        result = await broker_service.cancel_order(order_id)
        return {"status": "cancelled", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Portfolio Routes

```python
# src/qlib_research/app/api/routes/portfolio.py

from fastapi import APIRouter, Depends
from src.qlib_research.app.api.schemas.portfolio import (
    PortfolioPositionsResponse, GreeksResponse, RiskMetricsResponse
)
from src.qlib_research.app.api.dependencies import (
    get_portfolio, get_portfolio_greeks, get_risk_metrics
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/positions")
async def get_positions(portfolio=Depends(get_portfolio)):
    """Get all open positions"""
    return PortfolioPositionsResponse(
        stocks=[...],  # Serialized stock positions
        options=[...],  # Serialized option positions
        cash_balance=portfolio.cash_balance,
        total_market_value=portfolio.total_market_value,
        realized_pnl=portfolio.realized_pnl,
        unrealized_pnl=portfolio.unrealized_pnl,
        total_pnl=portfolio.total_pnl,
        total_pnl_pct=portfolio.total_pnl_pct
    )

@router.get("/greeks")
async def get_greeks(greeks=Depends(get_portfolio_greeks)):
    """Get portfolio-level Greeks"""
    return GreeksResponse(**greeks)

@router.get("/risk")
async def get_risk(risk_metrics=Depends(get_risk_metrics)):
    """Get portfolio risk metrics"""
    return RiskMetricsResponse(**risk_metrics)
```

## Dependency Injection

```python
# src/qlib_research/app/api/dependencies.py

from fastapi import Depends
from typing import AsyncGenerator
from src.qlib_research.app.services.market_data_service import MarketDataService
from src.qlib_research.app.services.paper_broker import PaperBrokerService
from src.qlib_research.app.services.portfolio_greeks import PortfolioGreeksCalculator
from src.qlib_research.app.services.risk_calculator import RiskCalculator
from src.qlib_research.app.services.risk_validator import RiskValidator
from src.qlib_research.app.models.risk_limits import RiskLimits

# Singleton instances (in production, use app.state or dependency container)
_market_data_service = None
_broker_service = None
_risk_limits = None

async def get_market_data_service() -> MarketDataService:
    """Get or create market data service"""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service

async def get_broker_service() -> PaperBrokerService:
    """Get or create paper broker service"""
    global _broker_service
    if _broker_service is None:
        _broker_service = PaperBrokerService(initial_cash=100000)
    return _broker_service

async def get_portfolio(broker=Depends(get_broker_service)):
    """Get current portfolio state"""
    return broker.get_portfolio()

async def get_portfolio_greeks(portfolio=Depends(get_portfolio)):
    """Get portfolio Greeks"""
    return PortfolioGreeksCalculator.calculate_portfolio_greeks(portfolio)

async def get_risk_metrics(portfolio=Depends(get_portfolio)):
    """Get risk metrics"""
    pnl = RiskCalculator.calculate_pnl(portfolio)
    var = RiskCalculator.calculate_var(portfolio)
    concentration = RiskCalculator.calculate_concentration_risk(portfolio)
    
    return {
        "pnl": pnl,
        "var_95": var,
        "concentration": concentration
    }

async def get_risk_limits() -> RiskLimits:
    """Get current risk limits"""
    global _risk_limits
    if _risk_limits is None:
        _risk_limits = RiskLimits()
    return _risk_limits

async def get_risk_validator(limits=Depends(get_risk_limits)) -> RiskValidator:
    """Get risk validator"""
    return RiskValidator(limits)
```

## Middleware

```python
# src/qlib_research/app/api/middleware.py

import uuid
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Add request ID and timing to all requests"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.request_id = str(uuid.uuid4())
        request.state.start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - request.state.start_time
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Process-Time"] = str(duration)
        
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
        )
        
        return response

def add_request_tracking(app):
    """Register request tracking middleware"""
    app.add_middleware(RequestTrackingMiddleware)

def add_error_handling(app):
    """Error handling already in main.py"""
    pass

def add_performance_logging(app):
    """Track endpoint latency"""
    pass
```

## Testing

```python
# tests/integration/test_api_routes.py

import pytest
from fastapi.testclient import TestClient
from src.qlib_research.app.api.main import app

client = TestClient(app)

def test_market_overview():
    """Test market overview endpoint"""
    response = client.get("/api/v1/market/overview?tickers=AAPL,MSFT")
    assert response.status_code == 200
    data = response.json()
    assert "overview" in data
    assert len(data["overview"]) == 2

def test_create_order():
    """Test order creation"""
    response = client.post(
        "/api/v1/orders",
        json={
            "ticker": "AAPL",
            "side": "buy",
            "quantity": 100,
            "order_type": "market"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "order_id" in data
    assert data["status"] in ["filled", "submitted"]

def test_get_portfolio():
    """Test portfolio endpoint"""
    response = client.get("/api/v1/portfolio/positions")
    assert response.status_code == 200
    data = response.json()
    assert "stocks" in data
    assert "options" in data
    assert "total_pnl" in data
```

## Acceptance Criteria

- [ ] FastAPI app runs on port 8000
- [ ] All routes documented in Swagger (/docs)
- [ ] Pydantic validation on all inputs
- [ ] Error responses consistent format
- [ ] Market data endpoints return prices, OHLC
- [ ] Trading endpoints create/cancel orders
- [ ] Portfolio endpoints show positions, Greeks, risk
- [ ] Risk limits enforced on trades
- [ ] Dependency injection works (services reused)
- [ ] Middleware tracks request IDs and latency
- [ ] Integration tests pass
- [ ] Health check endpoint works

## Known Limitations (MVP)

- No authentication (single user)
- No database (in-memory state)
- No rate limiting
- No request logging to disk
- Sync only (no WebSocket for real-time updates)
- Pagination not fully implemented
