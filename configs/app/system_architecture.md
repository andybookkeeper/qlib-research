# System Architecture Specification
# FastAPI + Qlib + Paper Broker Integration

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser / UI                             │
│  (Jinja2 HTML + minimal JavaScript)                            │
└─────────────────────────────────────────────────────────────────┘
                              ↑↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Web Server                         │
│  - Static file serving (HTML, CSS, JS)                         │
│  - REST API endpoints (orders, positions, market data)         │
│  - WebSocket for real-time updates (optional)                 │
│  Port: 8000                                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────┬──────────────────────┬────────────────┐
│   Paper Broker         │   Market Data        │  Qlib Signal   │
│   Service              │   Service            │  Service       │
│  (In-memory)           │  (Qlib provider)     │  (Qlib model)  │
└────────────────────────┴──────────────────────┴────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                      Qlib Research Layer                         │
│  - Data ingestion (Yahoo, custom provider)                      │
│  - Feature engineering                                           │
│  - Model training & backtesting                                 │
│  - Signal generation & serving                                  │
│  - Experiment tracking (MLflow)                                 │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    External Data Sources                         │
│  - Yahoo Finance (via Qlib)                                     │
│  - Options data API (external provider, TBD)                   │
│  - MLflow artifact store                                        │
└──────────────────────────────────────────────────────────────────┘
```

## Package Structure

```
my-qlib-research/
├── src/
│   └── qlib_research/
│       ├── __init__.py
│       ├── app/
│       │   ├── __init__.py
│       │   ├── main.py                    # FastAPI app factory, startup logic
│       │   ├── config.py                  # App settings (env vars, defaults)
│       │   ├── api/
│       │   │   ├── __init__.py
│       │   │   ├── routes/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── orders.py          # POST/GET/DELETE /orders
│       │   │   │   ├── positions.py       # GET /positions
│       │   │   │   ├── portfolio.py       # GET /portfolio
│       │   │   │   ├── market_data.py     # GET /market_data/{ticker}
│       │   │   │   ├── signals.py         # GET /signals/{ticker}
│       │   │   │   ├── experiments.py     # GET /experiments
│       │   │   │   └── trade_history.py   # GET /trade-history
│       │   │   ├── schemas.py             # Pydantic models for validation
│       │   │   └── dependencies.py        # FastAPI dependency injection
│       │   ├── services/
│       │   │   ├── __init__.py
│       │   │   ├── broker_service.py      # Paper broker logic
│       │   │   ├── market_data_service.py # Qlib data fetching
│       │   │   ├── signals_service.py     # Qlib signal serving
│       │   │   ├── risk_engine.py         # Pre-trade validation
│       │   │   ├── pnl_calculator.py      # P&L computation
│       │   │   └── experiments_service.py # Experiment fetching
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   ├── order.py               # Order domain model
│       │   │   ├── position.py            # Position domain model
│       │   │   ├── trade.py               # ClosedTrade domain model
│       │   │   ├── portfolio.py           # PortfolioState domain model
│       │   │   └── settings.py            # App settings model
│       │   ├── static/
│       │   │   ├── css/
│       │   │   │   └── style.css          # Main stylesheet
│       │   │   ├── js/
│       │   │   │   ├── app.js             # Main app logic
│       │   │   │   ├── chart.js           # Charting utilities (Chart.js)
│       │   │   │   └── websocket.js       # WS client (optional)
│       │   │   └── images/
│       │   ├── templates/
│       │   │   ├── base.html              # Base layout
│       │   │   ├── dashboard.html         # Dashboard view
│       │   │   ├── stock_detail.html      # Stock analysis view
│       │   │   ├── options_chain.html     # Options view
│       │   │   ├── order_entry.html       # Order form (modal)
│       │   │   ├── positions.html         # Holdings view
│       │   │   ├── trade_history.html     # Trade list view
│       │   │   ├── research.html          # Backtest results view
│       │   │   └── settings.html          # Settings view
│       │   ├── utils/
│       │   │   ├── __init__.py
│       │   │   ├── logger.py              # Logging configuration
│       │   │   ├── errors.py              # Custom exception classes
│       │   │   └── helpers.py             # Utility functions
│       │   └── middleware/
│       │       ├── __init__.py
│       │       ├── error_handler.py       # Global error handling
│       │       └── cors.py                # CORS configuration
│       ├── qlib_research/
│       │   ├── __init__.py
│       │   ├── init_qlib.py               # Qlib initialization
│       │   ├── data_provider.py           # Data ingestion
│       │   ├── features.py                # Feature engineering
│       │   ├── models.py                  # Model definitions (LightGBM, RL)
│       │   ├── backtest.py                # Backtesting logic
│       │   └── signals.py                 # Signal computation
│       └── __init__.py
├── configs/
│   ├── app/
│   │   ├── research_goals.md
│   │   ├── supported_assets.yaml
│   │   ├── user_flows.yaml
│   │   ├── data_and_qlib_boundary.md
│   │   ├── acceptance_criteria.md
│   │   ├── brokerage_stack_spec.md
│   │   ├── system_architecture.md         # This file
│   │   ├── settings.yaml                  # Default app config
│   │   └── qlib_config.yaml               # Qlib-specific config
│   └── deployment/
│       ├── docker/
│       │   └── Dockerfile                 # Docker image definition
│       ├── k8s/                           # Kubernetes manifests (future)
│       └── env.example                    # Environment variables template
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_broker_service.py
│   │   ├── test_pnl_calculator.py
│   │   ├── test_risk_engine.py
│   │   └── ...
│   ├── integration/
│   │   ├── test_order_flow.py
│   │   ├── test_market_data.py
│   │   └── ...
│   └── e2e/
│       ├── test_dashboard.py              # Selenium/Playwright tests
│       ├── test_order_entry.py
│       └── ...
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_training.ipynb
│   ├── 04_backtest_analysis.ipynb
│   └── ...
├── data/
│   └── qlib/
│       ├── cn_data/                       # (placeholder for Qlib data)
│       └── cache/
│           └── market_data.pickle         # Local cache
├── .env.example                           # Environment template
├── README.md                              # Setup & usage
├── requirements.txt                       # Python dependencies
├── setup.py                               # Package setup
└── docker-compose.yml                     # Local dev environment
```

## Core Modules & Responsibilities

### 1. FastAPI Application (`src/qlib_research/app/main.py`)

```python
# Responsibilities:
# - Initialize FastAPI app
# - Register routes and middleware
# - Setup error handling
# - Load configuration
# - Start Qlib and broker services
# - Manage app lifecycle (startup/shutdown events)

async def lifespan(app: FastAPI):
    # Startup: initialize services
    broker_service = PaperBrokerService()
    market_data_service = MarketDataService()
    qlib_service = QlibSignalService()
    
    app.state.broker = broker_service
    app.state.market_data = market_data_service
    app.state.signals = qlib_service
    
    yield
    
    # Shutdown: cleanup
    broker_service.save_state()
    market_data_service.close()
```

### 2. Broker Service (`src/qlib_research/app/services/broker_service.py`)

```python
class PaperBrokerService:
    """Manages order execution and portfolio state"""
    
    portfolio: PortfolioState
    settings: BrokerSettings
    
    def __init__(self, initial_cash=100000.0):
        self.portfolio = PortfolioState(cash=initial_cash)
        self.settings = load_broker_settings()
    
    def submit_order(self, order_request: OrderRequest) -> Order:
        """Validate and execute order"""
        # 1. Validate request
        # 2. Risk checks
        # 3. Execute (simulate fill)
        # 4. Update portfolio
        # 5. Return filled order
    
    def get_positions(self) -> List[Position]:
        """Return current positions"""
    
    def get_portfolio_summary(self) -> dict:
        """Return portfolio snapshot"""
    
    def cancel_order(self, order_id: str) -> Order:
        """Cancel pending order"""
    
    def save_state(self) -> None:
        """Export state to JSON (for recovery/backup)"""
```

### 3. Market Data Service (`src/qlib_research/app/services/market_data_service.py`)

```python
class MarketDataService:
    """Fetches current and historical prices from Qlib"""
    
    qlib_provider: QlibDataProvider
    cache: Dict[str, PriceData]
    
    def __init__(self):
        self.qlib_provider = init_qlib()
        self.cache = {}
    
    def get_current_price(self, ticker: str) -> float:
        """Return latest close price for ticker"""
        # 1. Check cache (if < 1 hour old)
        # 2. Query Qlib data provider
        # 3. Cache result
        # 4. Return price
    
    def get_ohlc_data(self, ticker: str, start_date, end_date) -> pd.DataFrame:
        """Return historical OHLC data"""
    
    def refresh_prices(self, tickers: List[str]) -> None:
        """Refresh cache for list of tickers"""
    
    def close(self) -> None:
        """Cleanup resources"""
```

### 4. Signals Service (`src/qlib_research/app/services/signals_service.py`)

```python
class QlibSignalService:
    """Generates and serves trading signals from Qlib models"""
    
    qlib_provider: QlibProvider
    loaded_models: Dict[str, Any]
    
    def __init__(self):
        self.qlib_provider = init_qlib()
        self.loaded_models = {}
    
    def get_signal(self, ticker: str, model_id: str = "default") -> Signal:
        """Get latest buy/sell signal for ticker"""
        # 1. Load model if not cached
        # 2. Compute features
        # 3. Run inference
        # 4. Return signal (buy/sell/hold, confidence)
    
    def list_models(self) -> List[dict]:
        """Return available models and their metadata"""
    
    def get_model_backtest_results(self, model_id: str) -> dict:
        """Fetch backtest metrics from Qlib experiment"""
```

### 5. Risk Engine (`src/qlib_research/app/services/risk_engine.py`)

```python
class RiskEngine:
    """Pre-trade validation and safeguards"""
    
    def validate_order(self, order_request: OrderRequest, 
                      portfolio: PortfolioState, 
                      settings: AppSettings) -> bool:
        """Check buying power, position limits, daily loss"""
        # 1. Buying power validation
        # 2. Position limit check
        # 3. Daily loss limit check
        # 4. Return True if all pass, raise exception otherwise
```

### 6. P&L Calculator (`src/qlib_research/app/services/pnl_calculator.py`)

```python
class PnlCalculator:
    """Computes realized, unrealized, and total P&L"""
    
    def compute_realized_pnl(self, closed_trades: List[ClosedTrade]) -> float:
        """Sum P&L from all closed trades"""
    
    def compute_unrealized_pnl(self, positions: Dict[str, Position]) -> float:
        """Sum unrealized P&L from open positions"""
    
    def compute_daily_realized_pnl(self, trade_history: List[Order], 
                                   date: datetime) -> float:
        """P&L from trades closed today"""
```

## Data Flow Diagrams

### Order Placement Flow
```
User clicks "Buy" on stock
         ↓
Browser POSTs /api/orders
         ↓
API Route Handler (orders.py)
  - Validate request (Pydantic schema)
         ↓
Risk Engine
  - Check buying power
  - Check position limits
  - Check daily loss limit
         ↓
Paper Broker Service
  - Create Order object
  - Simulate fill at market price
  - Update Position(s)
  - Deduct cash
         ↓
P&L Calculator
  - Recalculate portfolio totals
         ↓
Response to Browser
  - Order ID, fill details, new portfolio value
         ↓
Browser updates UI
  - Confirm modal, refresh positions list, update dashboard
```

### Signal Generation Flow (Daily, After Market Close)
```
Scheduled Task (e.g., 5 PM daily)
         ↓
Qlib Signal Service
  - Load latest trained model
  - Fetch latest market data from Qlib
  - Compute features
  - Run inference
         ↓
Save signals to artifact store
  (e.g., MLflow or local file)
         ↓
Browser (next day)
  - Stock detail page requests signals
         ↓
Signals Service
  - Load cached signals
  - Return latest signals
         ↓
Browser displays signal on stock detail page
```

## Configuration Management

### Environment Variables
```bash
# .env file (not committed to git)
QLIB_PROVIDER_URI=yahoo  # or path to local data
QLIB_REGION=US
INITIAL_CASH=100000
COMMISSION_RATE=0.001
MAX_POSITION_PCT=0.05
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000"]
```

### YAML Configuration Files
```yaml
# configs/app/settings.yaml
broker:
  initial_cash: 100000
  commission_rate: 0.001
  
market_data:
  provider: yahoo
  cache_ttl_hours: 24
  
signals:
  default_model: lgb_classifier_v1
  confidence_threshold: 0.6
  
logging:
  level: INFO
  format: json
```

## Error Handling Strategy

### Exception Hierarchy
```python
class TradingError(Exception):
    """Base exception for all trading errors"""
    pass

class InsufficientBuyingPowerError(TradingError):
    """Raised when order exceeds available cash"""
    pass

class PositionLimitExceededError(TradingError):
    """Raised when position would exceed limits"""
    pass

class DailyLossLimitExceededError(TradingError):
    """Raised when daily loss limit would be breached"""
    pass

class QlibDataError(TradingError):
    """Raised when Qlib data fetch fails"""
    pass

class OrderExecutionError(TradingError):
    """Raised during order execution"""
    pass
```

### Error Response Format
```python
# Global error handler middleware
@app.exception_handler(TradingError)
async def trading_error_handler(request: Request, exc: TradingError):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )
```

## Logging & Monitoring

### Logging Strategy
```python
# utils/logger.py
import logging
import json

logger = logging.getLogger(__name__)

def log_order_submission(order: Order):
    """Log order submission for audit trail"""
    logger.info(json.dumps({
        "event": "order_submitted",
        "order_id": order.order_id,
        "ticker": order.ticker,
        "side": order.side,
        "quantity": order.quantity,
        "timestamp": datetime.now().isoformat()
    }))

def log_order_filled(order: Order):
    """Log order fill for audit trail"""
    logger.info(json.dumps({
        "event": "order_filled",
        "order_id": order.order_id,
        "filled_price": order.filled_price,
        "total_value": order.total_value,
        "commission": order.commission,
        "timestamp": order.filled_at.isoformat()
    }))
```

### Metrics to Track
- Orders submitted / filled / cancelled (daily)
- Portfolio value over time
- P&L (realized, unrealized, total)
- Error rates (failed validations, execution errors)
- API latency (by endpoint)
- Qlib signal hit rate (% of signals that were profitable)

## Dependency Injection

FastAPI uses `Depends()` for service injection:

```python
# api/dependencies.py
from fastapi import Depends

def get_broker_service(request: Request) -> PaperBrokerService:
    return request.app.state.broker

def get_market_data_service(request: Request) -> MarketDataService:
    return request.app.state.market_data

def get_signals_service(request: Request) -> QlibSignalService:
    return request.app.state.signals

# In route handler:
@router.get("/api/portfolio")
def get_portfolio(broker: PaperBrokerService = Depends(get_broker_service)):
    return broker.get_portfolio_summary()
```

## Testing Boundaries

### Unit Tests (No External Dependencies)
- Broker service logic (buying power, position updates, P&L)
- Risk engine validation
- P&L calculations

### Integration Tests (Services + Qlib Mock)
- Order flow (submit → validate → execute → update)
- Market data caching
- Signal generation (with mock model)

### E2E Tests (Full Stack)
- Dashboard rendering
- Order entry and execution
- Portfolio updates reflected in UI

## Deployment Architecture

### Single Container (Development)
```bash
docker run -p 8000:8000 \
  -e QLIB_PROVIDER_URI=yahoo \
  -e INITIAL_CASH=100000 \
  qlib-trading-app
```

### Multi-Container (Future, Production)
```yaml
# docker-compose.yml
version: '3'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - QLIB_PROVIDER_URI=http://data-service:5000
      - MLFLOW_TRACKING_URI=http://mlflow:5000
    depends_on:
      - data-service
      - mlflow
  
  data-service:
    image: qlib-data-provider:latest
    ports:
      - "5000:5000"
  
  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    ports:
      - "5001:5000"
```

## Startup Sequence

```
1. Load environment variables
2. Initialize logger
3. Load app configuration from YAML + env overrides
4. Initialize Qlib (data provider, models)
5. Initialize Paper Broker Service
6. Initialize Market Data Service
7. Initialize Signals Service
8. Register routes
9. Setup middleware (error handler, CORS)
10. Start FastAPI server on port 8000
11. Log startup complete
```

## Shutdown Sequence

```
1. Stop accepting new requests
2. Drain in-flight requests (timeout: 30s)
3. Broker service: save portfolio state to JSON
4. Market data service: clear cache
5. Qlib: unload models from memory
6. Close database connections (if applicable)
7. Flush logs
8. Exit
```

## Acceptance Criteria

- [ ] All modules follow single responsibility principle
- [ ] Broker service is independent of FastAPI (testable in isolation)
- [ ] Qlib integration is isolated in dedicated service
- [ ] Error handling is consistent across all routes
- [ ] Logging captures all critical events (orders, fills, errors)
- [ ] Configuration can be set via environment variables
- [ ] Startup/shutdown are graceful (no data loss, no crashes)
- [ ] All external dependencies are injected (no globals)
- [ ] Code is organized by feature/responsibility, not layer
