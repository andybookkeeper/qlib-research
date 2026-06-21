# Data and Qlib Boundary
# This document clarifies responsibilities between the Qlib research layer and the app layer

## Overall Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer (FastAPI + UI)            │
│  - Dashboard, charting, order entry, position monitoring       │
│  - Manual order execution, paper broker simulation             │
│  - Risk checks, safeguards, P&L calculation                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ API boundary
┌─────────────────────────────────────────────────────────────────┐
│                    Qlib Research Layer                          │
│  - Market data ingestion, provider, data handlers              │
│  - Feature engineering, model training, backtesting            │
│  - Signal generation, online serving                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓ File boundary
┌─────────────────────────────────────────────────────────────────┐
│                    Data / External Services                     │
│  - Qlib data providers (Yahoo, CN data, custom)                │
│  - Market data files (data/qlib/...)                           │
│  - Experiment artifacts, MLflow records                        │
│  - Options chain API (external, not Qlib)                      │
└─────────────────────────────────────────────────────────────────┘
```

## Qlib Responsibilities (Research Layer)

### Data Ingestion & Storage
- **Owned**: Fetching and storing OHLC data for stocks
- **Tools**: Qlib data module, configured providers (Yahoo, CN data, etc.)
- **Storage**: `data/qlib/` directory or external provider URL
- **Frequency**: Daily (end-of-day) in MVP
- **Scope**: US stocks only (options data out of Qlib scope)

### Feature Engineering
- **Owned**: Computing price-based features (momentum, volatility, moving averages, etc.)
- **Tools**: Qlib expression engine, processors
- **Input**: Raw OHLC data
- **Output**: Feature matrices for model training
- **Responsibility**: Ensure features are forward-looking and not look-ahead biased

### Model Training & Backtesting
- **Owned**: Model selection, hyperparameter tuning, cross-validation
- **Tools**: Qlib LightGBM or RL modules
- **Input**: Feature matrices, targets (labels derived from forward price movements)
- **Output**: Trained models, backtest results (metrics, equity curves)
- **Responsibility**: Qlib handles rolling window backtesting; app layer does NOT re-backtest

### Signal Generation
- **Owned**: Real-time feature computation and model inference
- **Tools**: Qlib online serving (daily prediction refresh in MVP)
- **Input**: Latest market data
- **Output**: Buy/sell signals and confidence scores (0-1 range)
- **Responsibility**: Qlib ensures signals are aligned with backtest performance

### Experiment Management
- **Owned**: Tracking experiments, hyperparameters, model artifacts
- **Tools**: Qlib Recorder + MLflow integration
- **Storage**: `~/mlruns/` or configured MLflow backend
- **Output**: Experiment metadata, metrics, params, trained model pkl files

## App Layer Responsibilities (Execution & UI)

### Paper Broker Simulation
- **Owned**: Order execution, position tracking, P&L computation
- **Tools**: Custom in-memory broker service
- **Input**: Order requests from UI (qty, price, side)
- **Output**: Filled orders, positions, portfolio value
- **Responsibility**: App layer handles commission, slippage, buying power checks

### Risk Management & Safeguards
- **Owned**: Pre-trade and real-time risk checks
- **Checks**:
  - Buying power validation (cash sufficient for order)
  - Position limit checks (% portfolio, sector concentration)
  - Daily loss limits (if configured)
  - Kill switch on catastrophic error
- **Responsibility**: App layer enforces risk rules; Qlib signals are NOT risk-checked by Qlib

### Order Entry & Execution
- **Owned**: Manual order acceptance, preview, execution
- **Responsibility**: App layer is single point for order submission
- **Future**: Extend to Qlib signal-based automatic orders (with explicit user opt-in)

### UI & Charting
- **Owned**: All visual rendering, interactive charts, dashboards
- **Tools**: Jinja2 templates, JavaScript (minimal), Chart.js or similar
- **Data sources**:
  - Current prices: from Qlib market data (cached)
  - Historical prices: from Qlib (for charting)
  - Portfolio data: from paper broker
  - Qlib signals: from signal serving endpoint

### User Authentication & Settings
- **Owned**: User login (basic, session management), settings persistence
- **Responsibility**: App layer; not Qlib concern

## Data Flow Boundaries

### Daily Market Data Refresh (Morning)
1. **Qlib side**: Fetch latest OHLC data from provider, update data store
2. **App side**: Query Qlib for latest prices, cache locally
3. **App side**: Serve prices to UI dashboard

### Model Training (Offline, triggered manually or on schedule)
1. **Qlib side**: Pull feature matrix, compute targets, train model
2. **Qlib side**: Backtest model on historical data
3. **Qlib side**: Save trained model to experiment artifact store
4. **App side**: Poll experiment store for new models; if metrics pass threshold, mark model as "ready"
5. **App side**: Load ready model for online inference (optional in MVP)

### Signal Generation (Daily, after market close in MVP)
1. **Qlib side**: Load latest trained model
2. **Qlib side**: Compute features for today's data
3. **Qlib side**: Run inference; generate buy/sell signals
4. **Qlib side**: Store signals in time-series format (artifact or database)
5. **App side**: Query Qlib signals endpoint; display in "Signals Panel" on stock detail
6. **App side**: User reviews signal; optionally places manual order based on signal

### Order Execution (Intraday)
1. **App side**: User enters order via UI
2. **App side**: Check buying power and risk limits
3. **App side**: Submit to paper broker
4. **Paper broker**: Simulate fill (immediate at market price in MVP)
5. **App side**: Update position list, P&L
6. **App side**: Persist trade to history (SQLite or file)

### Backtesting & Performance Review (Offline)
1. **User**: Navigates to Research tab; selects model
2. **App side**: Fetch experiment metadata and backtest results from Qlib
3. **App side**: Render charts and metrics in UI
4. **App side**: User compares multiple runs, validates signals before approval

## API Contract Between Layers

### Qlib → App (Output Endpoints)
- `/qlib/market_data/{ticker}?start=2024-01-01&end=2024-01-31` - OHLC data
- `/qlib/signals/{ticker}?date=2024-01-31` - Latest buy/sell signal and confidence
- `/qlib/experiments/{model_id}` - Experiment metadata and backtest metrics
- `/qlib/features/{ticker}?date=2024-01-31` - Feature values (optional; for transparency)

### App → Qlib (Inputs)
- **Implicit**: Qlib is autonomous; no explicit API calls from app to Qlib
- **Exception**: App may trigger model retraining or data refresh (via CLI or Qlib Python API)

## What's NOT Qlib

### Explicitly Out of Scope
- **Options data & Greeks**: Qlib is equity-focused. Options chain and Greeks will be sourced externally.
- **Broker connectivity**: Qlib signals are abstract recommendations. App layer handles broker connections (future).
- **User authentication**: No auth in Qlib; handled entirely by app.
- **Order execution**: Qlib does not submit orders. App layer is single point of order entry.
- **Risk management rules**: Qlib does not enforce position limits or kill switches. App layer enforces risk policy.
- **Real-time market data**: Qlib in MVP uses end-of-day data. Real-time intraday requires external subscription.

### Options Data (Special Case)
- **Current plan**: Options chain will be fetched from external API (e.g., OptionChain, Alpha Vantage, or custom provider)
- **Future**: Qlib signal extension to include options-specific features (implied vol, Greeks) if needed
- **Responsibility**: App layer responsible for options data ingestion; Qlib provides equity signals only

## Deployment Boundaries

### Qlib Runtime Requirements
- Python 3.7+
- Qlib dependencies (pyqlib, pandas, numpy, lightgbm, etc.)
- Data storage (either local `data/qlib/` or cloud provider)
- Optional: MongoDB for task management (multi-model workflows)
- Optional: MLflow server (experiments, artifact store)

### App Runtime Requirements
- Python 3.7+
- FastAPI, Uvicorn, Jinja2
- SQLite or similar for orders/trades history
- No direct Qlib binary dependency; imports only the Python SDK

### Separation Benefit
- **Qlib can run independently** for research/backtesting (no app required)
- **App can serve signals** from pre-trained models without re-running Qlib
- **Easy to mock Qlib** in app tests using fixture signals

## Acceptance Criteria

- [ ] Qlib data ingestion is tested independently (e.g., data provider availability, data integrity)
- [ ] App layer never imports Qlib model training modules (only inference)
- [ ] Signals API contract is documented and tested
- [ ] Paper broker does not depend on Qlib; fully functional with mock signals
- [ ] Options chain sourced from external API; Qlib unaware of options
- [ ] Risk checks happen in app layer, not Qlib (safeguards are app responsibility)
- [ ] All order execution flows through paper broker (single point); no direct Qlib order submission
