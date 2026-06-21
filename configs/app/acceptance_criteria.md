# Acceptance Criteria for MVP
# Definition of "done" for the minimum viable product (paper trading app with Qlib signal serving)

## Scope: Stocks Only (Options Read-Only in MVP)
- [x] Application can display US equity stocks
- [x] Paper trading simulates stock buys and sells
- [ ] Options chain viewable but order entry disabled until external data source is integrated
- [ ] App clearly indicates "Paper Trading Mode" in UI

## Qlib Integration
- [ ] Qlib is initialized and market data is fetched (daily end-of-day)
- [ ] At least one trained LightGBM model exists (dummy model acceptable for MVP)
- [ ] Qlib signals (buy/sell predictions) can be retrieved and displayed in stock detail page
- [ ] Backtest results are accessible in Research tab
- [ ] Model backtest shows Sharpe ratio, max drawdown, cumulative returns, win rate
- [ ] Data and Qlib boundary is clearly enforced (no order submission via Qlib)

## FastAPI Backend
- [ ] FastAPI app starts on `http://localhost:8000`
- [ ] All endpoints respond with <500ms latency
- [ ] Market data endpoint (`/api/market_data/{ticker}`) returns current price and daily change
- [ ] Signals endpoint (`/api/signals/{ticker}`) returns latest signal and confidence
- [ ] Experiments endpoint (`/api/experiments`) returns list of trained models with metrics

## Paper Trading / Paper Broker
- [ ] User can place market orders from UI
- [ ] Buying power is checked (cash sufficient for order size)
- [ ] Orders are filled instantly at current market price (no latency simulation in MVP)
- [ ] Portfolio positions are tracked correctly (qty, avg cost, current value, P&L)
- [ ] Realized P&L matches sum of closed trade P&L
- [ ] Unrealized P&L = (current price - avg cost) × qty for each position

## User Interface (Jinja2 + HTML + Minimal JavaScript)
- [ ] Dashboard displays portfolio summary (cash, positions, total value, P&L %)
- [ ] Watchlist widget shows stocks, current prices, daily change
- [ ] Stock search works (search by ticker or name; results in <1s)
- [ ] Stock detail page displays:
      - Historical price chart (last 252 trading days)
      - Current price, daily change, 52-week high/low
      - Qlib signal (if available) with model name and confidence
      - Technical indicators (20d MA, RSI, optional)
- [ ] Options chain table displays (read-only):
      - Underlying stock info
      - Calls and puts by expiration and strike
      - Greeks (delta, gamma, theta, vega)
      - Note: "Order entry disabled until data source active"
- [ ] Order entry modal supports:
      - Buy/sell selection
      - Quantity input
      - Order type (market, limit)
      - Time in force (day, GTC)
- [ ] Order preview modal shows:
      - Qty, price, total cost/proceeds
      - Estimated commission
      - Available buying power after order
- [ ] Open orders list shows pending orders with status
- [ ] Positions list shows current holdings with P&L detail
- [ ] Position detail modal shows all fills and transactions
- [ ] Portfolio history chart shows portfolio value over time (paper trading period)

## Manual Trade Execution
- [ ] User can click "Buy" or "Sell" on any stock from dashboard or stock detail
- [ ] Order entry form validates quantity (positive number, within buying power)
- [ ] Order confirmation shows order ID, fill details, fees
- [ ] Cancel button on open order removes it from pending list
- [ ] All trades are logged to trade history

## Risk Safeguards (Paper Trading Phase)
- [ ] Buying power check prevents over-leveraging (quantity * price ≤ available cash)
- [ ] Position limit enforced (max 5% of portfolio per position) with warning/reject
- [ ] Daily loss limit can be set in settings (optional in MVP)
- [ ] All safeguards are configurable (not hardcoded)

## Settings & Configuration
- [ ] Settings page allows user to:
      - Set initial portfolio cash (default 100,000 USD)
      - Set commission rate (default 0.1%)
      - Set slippage (default 0.1%)
      - Set position size limit (default 5%)
      - Confirm/reset paper broker state
- [ ] Settings persist across app restarts
- [ ] Paper broker uses updated settings for new orders

## Testing & Validation
- [ ] All primary flows have passing end-to-end tests (using Selenium or Playwright)
- [ ] Unit tests cover paper broker logic (buying power, P&L calculation, position tracking)
- [ ] API endpoints have passing integration tests
- [ ] No hardcoded secrets or credentials in code (config via env vars)
- [ ] README includes step-by-step setup and running instructions

## Documentation
- [ ] README.md includes:
      - Project overview (Qlib + FastAPI app)
      - Setup instructions (venv, requirements, Qlib init)
      - How to start the app (`python -m src.qlib_research.app.main`)
      - How to access UI (`http://localhost:8000`)
      - Qlib data location and refresh instructions
      - Known limitations (paper trading, options read-only, etc.)
- [ ] configs/app/ directory has all scope docs:
      - research_goals.yaml
      - supported_assets.yaml
      - user_flows.yaml
      - data_and_qlib_boundary.md
      - acceptance_criteria.md (this file)
- [ ] API documentation (Swagger) is auto-generated at `/docs`

## Performance & Reliability
- [ ] Dashboard loads within 2 seconds
- [ ] Stock search returns results in <1 second
- [ ] Order placement completes in <500ms
- [ ] No memory leaks in paper broker (tested with 100+ orders)
- [ ] App handles graceful shutdown (Ctrl+C) without data loss

## Deployment Readiness (MVP)
- [ ] App runs on Windows, macOS, Linux (tested on at least one)
- [ ] All dependencies specified in `requirements.txt`
- [ ] App can be started with single command: `python -m src.qlib_research.app.main`
- [ ] Logs are written to console and optionally to file
- [ ] Config is environment-based (no hardcoded paths except defaults)

## Known Limitations (Documented in README)
- Paper trading only (no live broker connection)
- Options chain is read-only (no order entry)
- Data is daily end-of-day (no intraday / real-time data)
- Single user (no multi-user auth)
- In-memory paper broker state (no persistence to DB)
- Qlib signals are pre-computed daily (no real-time inference)

## Future Work (Post-MVP)
- Live broker integration (Alpaca, Interactive Brokers, etc.)
- Real-time options data and order entry
- Intraday data and charting
- Multi-user authentication and workspace separation
- RD-Agent automated factor discovery
- Drift monitoring and model retraining orchestration

## Sign-Off
- [ ] Product owner (User) approves scope
- [ ] All acceptance criteria verified before deployment
- [ ] Performance testing completed (latency, memory, concurrency)
- [ ] Security review completed (no secrets in code, input validation, CORS configured)
