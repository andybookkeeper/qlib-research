# UI/UX Flows Specification
# User interactions, wireframes, and component design patterns

## Overview

This specification defines all user interactions, screen layouts, navigation flows, and component behavior for the trading app UI. The app is **single-user, browser-based (React/Vue)** with FastAPI backend.

**Key principle**: UI is a thin client that calls FastAPI backend. All business logic resides on server.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  React/Vue SPA                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Components: Market, Analysis, Trading, Portfolio  │  │
│  │ State Management: Pinia (Vue) or Zustand (React)  │  │
│  │ HTTP Client: axios with interceptors             │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                       ↓ HTTP REST
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (/api/v1)                  │
│  Market Data, Trading, Portfolio, Research, Settings    │
└─────────────────────────────────────────────────────────┘
```

## App Layout

### Main Shell (Always Visible)

```
┌──────────────────────────────────────────────────────────┐
│  Logo  |  Qlib Trading Platform  |  Portfolio: +2.5%    │
├──────────────────────────────────────────────────────────┤
│  ▸ Market    ▸ Analysis  ▸ Trading  ▸ Portfolio  ▸ ...  │
├────────────────────┬─────────────────────────────────────┤
│                    │                                     │
│  Sidebar           │   Main Content Area                │
│  (Context)         │   (Router outlet)                   │
│                    │                                     │
│                    │                                     │
└────────────────────┴─────────────────────────────────────┘
```

### Navigation Tabs

- **Market**: Market overview, watchlist
- **Analysis**: Stock analysis, options chain
- **Trading**: Manual order entry, order history
- **Portfolio**: Current positions, P&L, Greeks
- **Research**: Qlib signals, backtests
- **Settings**: Risk limits, preferences

## Screen Flows

### 1. Market Overview (Home)

**URL**: `/`

**Purpose**: Quick market snapshot for decision-making

**Layout**:
```
┌─────────────────────────────────┐
│ Market Overview                 │
├─────────────────────────────────┤
│ 📊 Watchlist                    │
│ ┌───────────────────────────────┐
│ │ Ticker │ Price │ Change │ Vol  │
│ ├───────────────────────────────┤
│ │ AAPL   │ 151.2 │ +0.5%  │ 50M  │
│ │ MSFT   │ 340.8 │ -1.2%  │ 28M  │
│ │ GOOG   │ 139.5 │ +0.8%  │ 22M  │
│ └───────────────────────────────┘
│
│ 📈 Market Indicators            │
│ ├─ VIX: 14.5 (low volatility)   │
│ ├─ S&P 500: +0.3%               │
│ ├─ Nasdaq: +0.7%                │
│ └─ Yield (10Y): 4.25%           │
│
│ [+ Add to Watchlist] [Refresh]  │
└─────────────────────────────────┘
```

**Components**:
- `WatchlistTable` — Display tickers, prices, % change, volume
- `MarketIndicators` — VIX, index levels, bond yields
- `RefreshButton` — Manual refresh market data
- `AddTickerInput` — Search and add to watchlist

**Data Flow**:
1. User loads page → Fetch watchlist tickers from localStorage
2. Call `GET /api/v1/market/overview?tickers=AAPL,MSFT,...`
3. Update component state with prices
4. Auto-refresh every 30 seconds (configurable)

**Interactions**:
- Click on ticker row → Navigate to stock analysis
- Click price → Copy to clipboard
- Drag to reorder watchlist
- Right-click → Remove from watchlist

### 2. Stock Analysis

**URL**: `/analysis/stock/{ticker}`

**Purpose**: Deep dive into single stock with technicals and signals

**Layout**:
```
┌─────────────────────────────────────────────────────┐
│ Stock Analysis: AAPL                                │
├─────────────────────────────────────────────────────┤
│
│ 📊 Price Chart (50px height)                        │
│ [52W High: 195.0] [52W Low: 125.5] [Today: 151.2]  │
│ ┌─────────────────────────────────────────────────┐
│ │                                                  │
│ │              Interactive Chart                   │
│ │              (TradingView Lite)                  │
│ │                                                  │
│ └─────────────────────────────────────────────────┘
│
│ 📈 Technicals (Below chart)                        │
│ ├─ MA50: 150.5 (0.5% above current)               │
│ ├─ RSI: 65 (overbought)                           │
│ ├─ MACD: Bullish                                   │
│ ├─ Bollinger: Close to upper band                  │
│ └─ Volume: 48M shares (above avg)                  │
│
│ 🎯 Qlib Signals                                    │
│ ├─ Signal: STRONG BUY (Confidence: 78%)           │
│ ├─ Reason: Mean reversion + vol expansion         │
│ ├─ Expected Return: +2.3% (5 days)                │
│ ├─ Sharpe (backtest): 1.8                         │
│ └─ Last Updated: 2024-01-19 16:00 UTC             │
│
│ 💰 Options Chain                                   │
│ [View Options] → Go to options analysis           │
│
│ [Buy AAPL] [Sell AAPL] [Add to Watchlist]        │
└─────────────────────────────────────────────────────┘
```

**Components**:
- `PriceChart` — OHLC candles + moving averages (lightweight chart library)
- `TechnicalIndicators` — RSI, MACD, Bollinger, etc.
- `QlibSignal` — Signal, confidence, backtest metrics
- `OptionsChainPreview` — Quick link to options
- `ActionButtons` — Buy, Sell, Add to watchlist

**Data Flow**:
1. User navigates to `/analysis/stock/AAPL`
2. Fetch `GET /api/v1/analysis/stock/AAPL`
3. Response: {price, ohlc_data, technicals, qlib_signal, ...}
4. Render chart and metrics
5. Poll signal every 5 minutes

**Interactions**:
- Hover on chart → Show bar details (OHLC, date)
- Click "View Options" → Navigate to options chain
- Click "Buy AAPL" → Open order ticket

### 3. Options Chain Analysis

**URL**: `/analysis/options/{ticker}`

**Purpose**: View options chain with Greeks, place read-only analysis (MVP)

**Layout**:
```
┌────────────────────────────────────────────────┐
│ Options Analysis: AAPL                         │
├────────────────────────────────────────────────┤
│ Underlying: AAPL @ $151.20                     │
│
│ Expiration: [2024-01-19 ▼] [2024-01-26]       │
│            [2024-02-02]   [2024-02-16]         │
│
│ Strike Range: [±10% of current ▼]             │
│
│ 📞 CALLS                                       │
│ ┌──────────────────────────────────────────┐
│ │Stk │ Bid  │ Ask  │ Vol │ OI  │Δ  │Θ   │Γ│
│ ├──────────────────────────────────────────┤
│ │145 │ 6.80 │ 6.90 │ 124 │2500│0.8│-0.5│..
│ │150 │ 2.25 │ 2.35 │ 892 │8100│0.5│-0.6│..
│ │155 │ 0.75 │ 0.85 │1156 │5200│0.2│-0.3│..
│ └──────────────────────────────────────────┘
│
│ 📌 PUTS                                       │
│ ┌──────────────────────────────────────────┐
│ │Stk │ Bid  │ Ask  │ Vol │ OI  │Δ  │Θ   │Γ│
│ ├──────────────────────────────────────────┤
│ │145 │ 0.02 │ 0.05 │  12 │  500│-0.0│-0.1│..
│ │150 │ 0.22 │ 0.28 │ 245 │3200│-0.1│-0.2│..
│ │155 │ 1.50 │ 1.60 │ 789 │6800│-0.4│-0.5│..
│ └──────────────────────────────────────────┘
│
│ 📊 Greeks Guide (Always visible):             │
│ Δ = Directional (0.5 = 50% ITM prob)         │
│ Θ = Time decay ($ per day)                   │
│ Γ = Delta acceleration                       │
│
│ [View detailed Greeks] [Historical IV]       │
└────────────────────────────────────────────────┘
```

**Components**:
- `ExpirationSelector` — Dropdown to switch expirations
- `StrikeRangeFilter` — ±X% filter
- `CallsTable` — Tabular view with sortable columns
- `PutsTable` — Same for puts
- `GreeksLegend` — Tooltips explaining each Greek
- `HistoricalIVChart` — (Optional) IV term structure

**Data Flow**:
1. User selects ticker + expiration
2. Call `GET /api/v1/options/chain/AAPL?expiration=2024-01-19`
3. Response: {calls: [...], puts: [...], underlying_price, ...}
4. Render tables with sortable columns
5. Refresh every 10 minutes or on manual refresh

**Interactions**:
- Click column header → Sort by that column
- Hover on strike → Highlight row, show Greeks breakdown
- Hover on Greek (Δ, Θ, etc.) → Tooltip explanation
- Click strike → (Future) Open options order ticket
- Scroll → Sticky header

### 4. Manual Order Entry (Trading Ticket)

**URL**: `/trading/order`

**Purpose**: Create buy/sell orders with risk checks

**Layout**:
```
┌────────────────────────────────────────┐
│ New Order                              │
├────────────────────────────────────────┤
│
│ Instrument: [Ticker Search ▼]          │
│             (Typeahead: AAPL, MSFT...) │
│
│ Side: ◉ Buy  ○ Sell                   │
│
│ Quantity: [____] shares                │
│
│ Order Type: ◉ Market  ○ Limit         │
│
│ Price (Limit only): [____]             │
│
│ ────────────────────────────────────── │
│ Est. Cost (Market):  $151,200          │
│ Buying Power Left:   $948,800          │
│ Risk (% of portfolio): 0.45%           │
│
│ ⚠️  Risk Check:                        │
│ ✓ Position size OK                    │
│ ✓ Greeks within limits                │
│ ✓ Margin OK                           │
│
│ Preview P&L scenarios:                │
│ If price → +2%:  +$3,024 (+0.2%)      │
│ If price → -2%:  -$3,024 (-0.2%)      │
│
│ [Preview]  [Place Order]  [Cancel]    │
└────────────────────────────────────────┘
```

**Components**:
- `TickerSearch` — Typeahead with recent tickers
- `SideSelector` — Buy/Sell radio buttons
- `QuantityInput` — Numeric input with validation
- `OrderTypeSelector` — Market/Limit/Stop
- `PriceInput` — For limit orders
- `CostEstimate` — Real-time calculation
- `RiskChecklist` — Show limit violations
- `PreviewButton` — Open confirmation modal

**Data Flow**:
1. User enters ticker → Call `GET /api/v1/market/overview?tickers=AAPL`
2. Get current price, calculate order cost
3. User enters quantity → Calculate portfolio impact, Greeks change
4. Call `POST /api/v1/portfolio/validate-trade` (optional preview)
5. Check response for risk violations
6. If no violations → Enable "Place Order" button
7. On click → `POST /api/v1/orders`

**Interactions**:
- Ticker search → Real-time typeahead
- Quantity change → Recalculate cost, margin, risk
- Order type change → Show/hide price input
- Hover on warning → Explain risk violation
- "Place Order" → Confirmation modal

### 5. Order History & Trade Monitoring

**URL**: `/trading/orders`

**Purpose**: View pending and historical orders

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Orders & Trades                             │
├─────────────────────────────────────────────┤
│ Active Orders: 2                            │
│ ┌─────────────────────────────────────────┐
│ │ ID    │ Ticker │ Side │ Qty │ Type │ St │
│ ├─────────────────────────────────────────┤
│ │ 12345 │ AAPL   │ Buy  │ 100 │ Limit│ PND
│ │ 12346 │ MSFT   │ Sell │  50 │ Mkt  │ FLD
│ └─────────────────────────────────────────┘
│
│ Recent Trades: Last 30 days                │
│ ┌─────────────────────────────────────────┐
│ │ Ticker │ Entry  │ Exit   │ Qty │ P&L   │
│ ├─────────────────────────────────────────┤
│ │ GOOG   │ 138.50 │ 139.80 │ 50  │ +$65  │
│ │ NVDA   │ 485.20 │ 482.50 │ 25  │ -$68  │
│ └─────────────────────────────────────────┘
└─────────────────────────────────────────────┘
```

**Components**:
- `ActiveOrdersTable` — Pending, partially filled orders
- `TradesHistoryTable` — Realized trades with P&L
- `CancelButton` — Per-order cancel
- `Pagination` — Last 30/60/90/all trades

**Data Flow**:
1. Load page → `GET /api/v1/orders?status=pending,filled`
2. Render active orders and recent trades
3. Auto-refresh every 5 seconds
4. On cancel click → `DELETE /api/v1/orders/{order_id}`

### 6. Portfolio Dashboard

**URL**: `/portfolio`

**Purpose**: Real-time P&L, positions, Greeks, risk summary

**Layout**:
```
┌──────────────────────────────────────────────┐
│ Portfolio Summary                            │
├──────────────────────────────────────────────┤
│
│ 💰 Account Value: $102,450 (+2.45%)          │
│ Invested: $100,000 → Current: $102,450      │
│ Realized P&L: +$1,200  Unrealized: +$1,250  │
│
│ ⚖️  Allocation                               │
│ Stocks: 78% ($80,000)  Options: 22% ($22K)  │
│
│ 📊 Greeks (Portfolio-Level)                 │
│ Δ: +125 (long ~125 shares)                  │
│ Γ: +0.0045 (positive = profitable on moves) │
│ Θ: -$45/day (losing time decay)             │
│ ν: +$2,100 (gain if IV rises 1%)            │
│
│ 📍 Open Positions (5)                        │
│ ┌──────────────────────────────────────────┐
│ │ Ticker │ Qty │ Avg Cost │ Current │ P&L   │
│ ├──────────────────────────────────────────┤
│ │ AAPL   │ 100 │ 150.50   │ 151.20  │ +$70  │
│ │ MSFT   │  50 │ 340.00   │ 340.80  │ +$40  │
│ │ GOOG C │  10 │ 2.50     │ 2.80    │ +$30  │
│ └──────────────────────────────────────────┘
│
│ ⚠️  Risk Status                              │
│ ✓ All limits OK                            │
│ • Max daily loss: -$2,050 (limit: $2,500)  │
│ • Leverage: 1.0x (limit: 2.0x)             │
│ • Largest position: AAPL 7.8% (limit: 10%) │
│
│ [Edit Limits] [Close Position] [More Info]  │
└──────────────────────────────────────────────┘
```

**Components**:
- `AccountValue` — Total, invested, P&L cards
- `AllocationChart` — Pie chart stocks/options
- `GreeksPanel` — Portfolio δ, γ, θ, ν
- `PositionsTable` — All holdings with P&L
- `RiskStatus` — Indicator lights for limits
- `DetailButtons` — Drill-down actions

**Data Flow**:
1. Load → `GET /api/v1/portfolio/positions` + `/portfolio/greeks` + `/portfolio/risk`
2. Render summary cards
3. Auto-refresh every 10 seconds
4. On position click → Drill into stock analysis

### 7. Research Dashboard (Qlib Signals)

**URL**: `/research`

**Purpose**: View Qlib-generated signals and backtest results

**Layout**:
```
┌─────────────────────────────────────────────┐
│ Research & Signals                          │
├─────────────────────────────────────────────┤
│
│ 🎯 Today's Signals (Generated @ 16:00 UTC)  │
│ ┌──────────────────────────────────────────┐
│ │ Ticker │ Signal │ Conf │ Expected Return │
│ ├──────────────────────────────────────────┤
│ │ AAPL   │ BUY    │ 78%  │ +2.3% (5d)     │
│ │ MSFT   │ HOLD   │ 62%  │ +0.8% (5d)     │
│ │ NVDA   │ SELL   │ 85%  │ -1.5% (5d)     │
│ └──────────────────────────────────────────┘
│
│ 📈 Backtest Performance                     │
│ Model: "LightGBM-v2.1"                      │
│ Sharpe: 1.8  | Win Rate: 52%  | DD: -8%   │
│ [View backtest details]                     │
│
│ 🔄 Qlib Status                              │
│ Last trained: 2024-01-15 22:00 UTC          │
│ Next training: 2024-01-22 22:00 UTC         │
│ Training time: ~45 minutes                  │
│
│ [Retrain Now] [View Model] [Settings]      │
└─────────────────────────────────────────────┘
```

**Components**:
- `SignalsTable` — Tickers, signals, confidence, expected return
- `BacktestMetrics` — Sharpe, win rate, max DD
- `QlibStatus` — Training schedule, last run
- `RetainButton` — Trigger model retraining

**Data Flow**:
1. Load → `GET /api/v1/research/signals`
2. Render signal table
3. Load → `GET /api/v1/research/backtest-latest`
4. Show performance metrics
5. Display Qlib status (from backend)

### 8. Settings

**URL**: `/settings`

**Purpose**: Configure risk limits, preferences

**Layout**:
```
┌────────────────────────────────────────┐
│ Settings                               │
├────────────────────────────────────────┤
│
│ 🛡️  Risk Limits                        │
│ ├─ Max Position Size: [10]%            │
│ ├─ Max Portfolio Delta: [±1.5]         │
│ ├─ Max Daily Loss: [2]%                │
│ ├─ Max Leverage: [2.0]x                │
│ └─ Max Drawdown: [10]%                 │
│
│ 📊 Display Preferences                 │
│ ├─ Refresh Rate: [30] seconds          │
│ ├─ Chart Type: ◉ Candles  ○ Line      │
│ ├─ Decimal Places: [2] decimals        │
│ └─ Dark Mode: [Toggle] ON              │
│
│ 🔔 Notifications                       │
│ ├─ Order fills: ✓ Email                │
│ ├─ Risk limit violations: ✓ Alert      │
│ └─ Signal changes: ○ Disabled          │
│
│ [Save] [Reset] [Export Settings]       │
└────────────────────────────────────────┘
```

**Components**:
- `RiskLimitInputs` — Numeric inputs for each limit
- `DisplayPreferences` — Checkboxes and dropdowns
- `SaveButton` — POST to `/api/v1/settings`

**Data Flow**:
1. Load → `GET /api/v1/settings`
2. Populate form with current values
3. On save → `POST /api/v1/settings` with new limits
4. Show success/error toast

## Component Library

### Reusable Components

```
src/components/
├── Common/
│   ├── Card.vue             -- Bordered container
│   ├── Button.vue           -- Action button (primary, secondary, danger)
│   ├── Input.vue            -- Text, number inputs
│   ├── Select.vue           -- Dropdown selector
│   ├── Table.vue            -- Sortable, paginated table
│   ├── Modal.vue            -- Dialog
│   ├── Toast.vue            -- Notification
│   └── Loading.vue          -- Spinner
├── Market/
│   ├── PriceChart.vue       -- OHLC chart (TradingView Lite)
│   ├── Technicals.vue       -- RSI, MACD indicators
│   └── WatchlistTable.vue   -- Market overview table
├── Trading/
│   ├── OrderTicket.vue      -- Order form
│   ├── OrderHistory.vue     -- Orders and trades
│   └── ConfirmDialog.vue    -- Order confirmation
└── Portfolio/
    ├── GreeksPanel.vue      -- Portfolio Greeks display
    ├── PositionsTable.vue   -- Holdings list
    └── RiskStatus.vue       -- Risk limits indicator
```

## State Management

```javascript
// src/store/market.js (Pinia or Zustand)
{
  watchlist: ["AAPL", "MSFT", ...],
  prices: { AAPL: 151.20, MSFT: 340.80, ... },
  technicals: { AAPL: {rsi: 65, macd: ...}, ... },
  lastUpdate: timestamp
}

// src/store/portfolio.js
{
  positions: [...],
  portfolio: {totalValue, cash, realizedPnL, ...},
  greeks: {delta, gamma, theta, ...},
  riskStatus: {violations: []},
  lastUpdate: timestamp
}

// src/store/trading.js
{
  orders: [{id, ticker, side, qty, status, ...}],
  selectedOrder: null,
  orderForm: {ticker, side, qty, type, price, ...}
}
```

## Error Handling

**Network Errors**:
- 401 Unauthorized → Redirect to login (future)
- 400 Bad Request → Toast error message
- 500 Server Error → Toast "Server error, try again"
- Connection timeout → Retry with exponential backoff

**Validation Errors**:
- Empty ticker → Inline field error
- Invalid quantity → Show min/max
- Risk violation → Modal with explanation

## Acceptance Criteria

- [ ] All 8 screens render without errors
- [ ] Navigation between tabs works
- [ ] Market data auto-refreshes
- [ ] Order entry validates inputs
- [ ] Portfolio displays real-time positions
- [ ] Greeks panel shows correct values
- [ ] Risk limits display and update
- [ ] Settings save/load work
- [ ] All API calls use dependency-injected clients
- [ ] Responsive on 1920x1080 (desktop) and 768x1024 (tablet)
- [ ] Dark mode toggles all colors
- [ ] Loading states show spinner

## Known Limitations (MVP)

- No mobile layout (<768px)
- No WebSocket (polling only)
- No drag-and-drop customization
- No export to CSV/PDF
- No real-time alerts (polling)
- No chart interactivity (pan, zoom deferred)
- Single language (English)
