# Brokerage Stack Specification
# MVP: In-Memory Paper Trading Broker with Mock Order Execution

## Overview

The brokerage stack for MVP consists of:
1. **Paper Broker Service** — In-memory order execution and position management
2. **Portfolio State** — Tracks cash, positions, filled orders, and trade history
3. **Risk Engine** — Pre-trade and intra-day risk checks
4. **Order Matching Engine** — Simulates order fills at market price
5. **P&L Calculator** — Computes realized, unrealized, and portfolio-level P&L

This is a **single-user, paper-only** mock broker. No real orders are submitted to any exchange. Live broker integration comes in phase 2.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      FastAPI App                              │
│  - Routes: POST /orders, GET /positions, GET /portfolio       │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────┐
│                    Risk Engine                                 │
│  - Buying power validation                                     │
│  - Position limit checks                                       │
│  - Daily loss limits                                           │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────┐
│                 Paper Broker Service                           │
│  - Order queuing and execution                                 │
│  - Position tracking and updates                               │
│  - Trade history logging                                       │
└────────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────┐
│                  Portfolio State                               │
│  - Cash balance                                                │
│  - Positions (qty, avg_cost, current_price)                   │
│  - Open orders (status, fill details)                         │
│  - Trade history (all closed trades)                          │
└────────────────────────────────────────────────────────────────┘
```

## Paper Broker Service

### Core Responsibilities
1. Accept order requests from API
2. Pre-trade risk validation (via Risk Engine)
3. Execute orders (simulate immediate fills at market price)
4. Update positions and cash
5. Log trades to history
6. Provide position and portfolio snapshots to API

### Order Model

```python
class Order:
    """Represents a single order (buy or sell)"""
    order_id: str              # UUID
    ticker: str                # Stock symbol (e.g., "AAPL")
    side: str                  # "buy" or "sell"
    order_type: str            # "market" or "limit"
    quantity: int              # Number of shares
    price: float               # Market price at submission (for limit: user-specified price)
    limit_price: float | None  # Limit price if order_type == "limit"
    time_in_force: str         # "day" or "gtc"
    status: str                # "pending", "filled", "cancelled", "expired"
    filled_qty: int            # Quantity filled
    filled_price: float        # Average fill price
    commission: float          # Fee in USD
    total_value: float         # qty * filled_price (before commission)
    created_at: datetime       # Order submission timestamp
    filled_at: datetime | None # Fill timestamp
    cancelled_at: datetime | None
```

### Position Model

```python
class Position:
    """Represents a current holding"""
    ticker: str                # Stock symbol
    quantity: int              # Shares held
    avg_cost: float            # Average cost per share (for FIFO)
    current_price: float       # Last known market price
    current_value: float       # quantity * current_price
    unrealized_pnl: float      # current_value - (quantity * avg_cost)
    unrealized_pnl_pct: float  # unrealized_pnl / (quantity * avg_cost)
    last_updated: datetime     # Last price refresh time
```

### Trade Model (Closed Trade)

```python
class ClosedTrade:
    """Represents a completed round-trip trade (entry + exit or partial exits)"""
    trade_id: str              # UUID
    ticker: str
    entry_order_id: str        # Original buy order
    exit_orders: List[str]     # List of sell order IDs that closed this position
    entry_price: float         # Avg price of all buys
    entry_qty: int             # Total qty bought
    exit_price: float          # Avg price of sells
    exit_qty: int              # Total qty sold
    total_fees: float          # Sum of all commissions
    realized_pnl: float        # (exit_qty * exit_price) - (entry_qty * entry_price) - fees
    realized_pnl_pct: float    # realized_pnl / (entry_qty * entry_price)
    days_held: int             # Calendar days from entry to exit
    entry_date: datetime
    exit_date: datetime
```

### Portfolio State Model

```python
class PortfolioState:
    """Global state of the paper trading account"""
    account_id: str            # User identifier (single user in MVP)
    cash: float                # Available cash
    positions: Dict[str, Position]      # Current holdings
    open_orders: Dict[str, Order]       # Pending orders
    closed_trades: List[ClosedTrade]    # Historical trades
    trade_history: List[Order]          # All orders (filled + cancelled)
    
    # Computed properties
    @property
    def total_value(self) -> float:
        """Portfolio value = cash + sum of position values"""
        return self.cash + sum(p.current_value for p in self.positions.values())
    
    @property
    def unrealized_pnl(self) -> float:
        """Sum of unrealized P&L from all positions"""
        return sum(p.unrealized_pnl for p in self.positions.values())
    
    @property
    def realized_pnl(self) -> float:
        """Sum of P&L from all closed trades"""
        return sum(t.realized_pnl for t in self.closed_trades)
    
    @property
    def total_pnl(self) -> float:
        """Total P&L = realized + unrealized"""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def pnl_pct(self) -> float:
        """P&L as % of initial capital"""
        # Use initial capital from settings (default 100,000)
        return self.total_pnl / self.settings.initial_cash
```

## Order Execution Flow

### 1. User Submits Order (via UI)
```
POST /api/orders
{
  "ticker": "AAPL",
  "side": "buy",
  "quantity": 10,
  "order_type": "market",
  "time_in_force": "day",
  "limit_price": null
}
```

### 2. API Route Handler
```python
@router.post("/api/orders")
def create_order(request: OrderRequest, market_data: MarketDataService):
    # Fetch current price
    current_price = market_data.get_price(request.ticker)
    
    # Validate request
    validate_order_request(request)
    
    # Submit to broker
    order = broker.submit_order(
        ticker=request.ticker,
        side=request.side,
        quantity=request.quantity,
        order_type=request.order_type,
        limit_price=request.limit_price,
        time_in_force=request.time_in_force,
        current_price=current_price
    )
    
    return {"order_id": order.order_id, "status": order.status}
```

### 3. Risk Engine Validation
```python
def validate_order(order: Order, portfolio: PortfolioState, settings: Settings):
    """Pre-trade risk checks"""
    
    # Check 1: Buying Power (for buys only)
    if order.side == "buy":
        required_cash = order.quantity * order.price + estimate_commission(order)
        available_cash = portfolio.cash
        
        if required_cash > available_cash:
            raise InsufficientBuyingPowerError(
                f"Required: ${required_cash:.2f}, Available: ${available_cash:.2f}"
            )
    
    # Check 2: Position Limit (max % of portfolio)
    if order.side == "buy":
        proposed_position_value = order.quantity * order.price
        max_position_value = portfolio.total_value * settings.max_position_pct
        
        if proposed_position_value > max_position_value:
            raise PositionLimitExceededError(
                f"Position ${proposed_position_value:.2f} exceeds limit ${max_position_value:.2f}"
            )
    
    # Check 3: Daily Loss Limit
    if settings.max_daily_loss_pct > 0:
        daily_pnl = compute_daily_realized_pnl(portfolio)
        daily_loss_limit = portfolio.total_value * settings.max_daily_loss_pct
        
        if daily_pnl < -daily_loss_limit:
            raise DailyLossLimitExceededError(
                f"Today's loss ${-daily_pnl:.2f} exceeds limit ${daily_loss_limit:.2f}"
            )
    
    return True  # Validation passed
```

### 4. Order Execution (Paper Broker)
```python
def execute_order(order: Order, portfolio: PortfolioState, settings: Settings):
    """Simulate order fill immediately at market price"""
    
    # In MVP: all orders fill instantly at market price
    # (Future: add latency simulation, realistic slippage, order book)
    
    order.status = "filled"
    order.filled_qty = order.quantity
    order.filled_price = order.price  # Market price at submission
    order.filled_at = datetime.now()
    
    # Compute commission
    order.commission = order.quantity * order.price * settings.commission_rate
    order.total_value = order.quantity * order.filled_price
    
    # Update portfolio
    if order.side == "buy":
        update_position_on_buy(order, portfolio)
        portfolio.cash -= (order.total_value + order.commission)
    else:  # sell
        update_position_on_sell(order, portfolio)
        portfolio.cash += (order.total_value - order.commission)
    
    # Log trade
    portfolio.trade_history.append(order)
    
    return order
```

### 5. Position Update Logic

#### On Buy:
```python
def update_position_on_buy(order: Order, portfolio: PortfolioState):
    """Add to or create position using cost averaging"""
    ticker = order.ticker
    
    if ticker not in portfolio.positions:
        # Create new position
        position = Position(
            ticker=ticker,
            quantity=order.quantity,
            avg_cost=order.filled_price,
            current_price=order.filled_price
        )
        portfolio.positions[ticker] = position
    else:
        # Update existing position (FIFO cost averaging)
        pos = portfolio.positions[ticker]
        total_shares = pos.quantity + order.quantity
        total_cost = (pos.quantity * pos.avg_cost) + (order.quantity * order.filled_price)
        pos.avg_cost = total_cost / total_shares
        pos.quantity = total_shares
```

#### On Sell:
```python
def update_position_on_sell(order: Order, portfolio: PortfolioState):
    """Reduce or close position"""
    ticker = order.ticker
    
    if ticker not in portfolio.positions:
        raise PositionDoesNotExistError(f"No position to sell for {ticker}")
    
    pos = portfolio.positions[ticker]
    
    if order.quantity > pos.quantity:
        raise InsufficientPositionError(
            f"Trying to sell {order.quantity}, but only have {pos.quantity}"
        )
    
    # Record closed trade if this closes the position
    if order.quantity == pos.quantity:
        realized_pnl = (order.filled_price * order.quantity) - \
                       (pos.avg_cost * pos.quantity) - \
                       order.commission
        closed_trade = ClosedTrade(
            entry_price=pos.avg_cost,
            exit_price=order.filled_price,
            entry_qty=pos.quantity,
            exit_qty=order.quantity,
            realized_pnl=realized_pnl
        )
        portfolio.closed_trades.append(closed_trade)
        del portfolio.positions[ticker]
    else:
        # Partial sell: reduce position
        realized_pnl_partial = (order.filled_price * order.quantity) - \
                               (pos.avg_cost * order.quantity) - \
                               order.commission
        closed_trade = ClosedTrade(
            entry_price=pos.avg_cost,
            exit_price=order.filled_price,
            entry_qty=order.quantity,
            exit_qty=order.quantity,
            realized_pnl=realized_pnl_partial
        )
        portfolio.closed_trades.append(closed_trade)
        pos.quantity -= order.quantity
```

## P&L Calculation

### Realized P&L (Closed Trades)
```
For each closed trade:
  Realized P&L = (Exit Price × Exit Qty) - (Entry Price × Entry Qty) - Commissions
  
Total Realized = Sum of all closed trades' P&L
```

### Unrealized P&L (Open Positions)
```
For each position:
  Unrealized P&L = (Current Price - Avg Cost) × Quantity
  
Total Unrealized = Sum of all positions' unrealized P&L
```

### Portfolio P&L
```
Total P&L = Realized P&L + Unrealized P&L
P&L % = Total P&L / Initial Capital

Example:
  Initial Capital: $100,000
  Cash: $90,000
  Position (100 shares @ $100 avg, current $120): +$2,000 unrealized
  Closed trades (sum): +$500 realized
  
  Total Value = 90,000 + (100 * 120) = 102,000
  Total P&L = 500 (realized) + 2,000 (unrealized) = 2,500
  P&L % = 2,500 / 100,000 = 2.5%
```

## Settings & Configuration

```yaml
broker_config:
  initial_cash: 100000.0
  commission_rate: 0.001  # 0.1% per trade
  slippage_rate: 0.001   # 0.1% slippage (not used in MVP, instant fills)
  
position_limits:
  max_position_pct: 0.05   # Max 5% of portfolio per position
  max_sector_exposure_pct: 0.10  # Not enforced in MVP
  max_daily_loss_pct: 0.02  # Max 2% daily loss
  
order_execution:
  fill_latency_ms: 0      # Instant fills in MVP
  order_queue_latency_ms: 50
  
market_hours:
  market_open: "09:30"
  market_close: "16:00"
  timezone: "US/Eastern"
```

## API Endpoints (Brokerage Layer)

### Create Order
```
POST /api/orders
Request:
{
  "ticker": "AAPL",
  "side": "buy",  # or "sell"
  "quantity": 10,
  "order_type": "market",  # or "limit"
  "limit_price": 150.00,   # Only for limit orders
  "time_in_force": "day"   # or "gtc"
}

Response (201):
{
  "order_id": "uuid-xxx",
  "ticker": "AAPL",
  "side": "buy",
  "quantity": 10,
  "filled_qty": 10,
  "filled_price": 150.25,
  "commission": 15.03,
  "status": "filled",
  "created_at": "2024-01-15T14:30:00Z",
  "filled_at": "2024-01-15T14:30:00Z"
}
```

### Get Open Orders
```
GET /api/orders?status=open

Response (200):
{
  "orders": [
    {
      "order_id": "uuid-xxx",
      "ticker": "AAPL",
      "side": "buy",
      "quantity": 10,
      "status": "filled",
      "filled_price": 150.25,
      "created_at": "2024-01-15T14:30:00Z"
    }
  ]
}
```

### Cancel Order
```
DELETE /api/orders/{order_id}

Response (200):
{
  "order_id": "uuid-xxx",
  "status": "cancelled",
  "cancelled_at": "2024-01-15T14:31:00Z"
}
```

### Get Positions
```
GET /api/positions

Response (200):
{
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": 10,
      "avg_cost": 150.00,
      "current_price": 152.50,
      "current_value": 1525.00,
      "unrealized_pnl": 25.00,
      "unrealized_pnl_pct": 0.0167
    }
  ]
}
```

### Get Portfolio Summary
```
GET /api/portfolio

Response (200):
{
  "cash": 85000.00,
  "total_value": 102500.00,
  "positions_value": 17500.00,
  "realized_pnl": 500.00,
  "unrealized_pnl": 2500.00,
  "total_pnl": 3000.00,
  "total_pnl_pct": 0.03,
  "num_open_positions": 1,
  "num_open_orders": 0
}
```

### Get Trade History
```
GET /api/trade-history?limit=50&offset=0

Response (200):
{
  "trades": [
    {
      "trade_id": "uuid-xxx",
      "ticker": "AAPL",
      "side": "buy",
      "entry_price": 150.00,
      "entry_qty": 10,
      "exit_price": 152.50,
      "exit_qty": 10,
      "realized_pnl": 25.00,
      "entry_date": "2024-01-15T14:30:00Z",
      "exit_date": "2024-01-16T10:00:00Z"
    }
  ],
  "total": 5
}
```

## State Persistence (MVP)

### In-Memory Storage
- Portfolio state (positions, cash, orders) lives in Python memory
- On app restart, state is reset (no persistence)
- Acceptable for MVP; add SQLite or PostgreSQL in phase 2

### Data Export
- Trade history can be exported to CSV for external analysis
- Portfolio snapshots saved as JSON on-demand

## Testing Strategy

### Unit Tests
- [ ] Position update logic (buy, sell, partial sell)
- [ ] P&L calculations (realized, unrealized, total)
- [ ] Risk checks (buying power, position limits, daily loss)
- [ ] Commission calculations

### Integration Tests
- [ ] Full order flow (submit → validate → execute → update)
- [ ] Multiple orders on same ticker
- [ ] Buy then sell (round-trip P&L)
- [ ] Partial fills and closes

### E2E Tests (via UI)
- [ ] Dashboard shows correct portfolio value
- [ ] Place buy order → position appears
- [ ] Place sell order → position closes
- [ ] Portfolio P&L reflects trades

## Future Enhancements (Post-MVP)

1. **Realistic Order Matching**
   - Add order book simulation
   - Partial fills and slippage modeling
   - Order rejection scenarios

2. **Live Broker Integration**
   - Alpaca API adapter
   - Interactive Brokers API adapter
   - Order sync and reconciliation

3. **Persistence**
   - SQLite or PostgreSQL for order/trade history
   - Daily portfolio snapshots for analytics
   - Data warehouse for backtesting

4. **Advanced Risk Management**
   - Sector exposure limits
   - Portfolio Greeks (for options)
   - Dynamic margin requirements

5. **Multi-User Support**
   - User authentication
   - Per-user portfolio isolation
   - Shared model library

## Acceptance Criteria

- [ ] Paper broker accepts buy/sell orders via API
- [ ] Positions are created and updated correctly
- [ ] Cash balance is accurate after orders
- [ ] P&L calculations are correct (realized + unrealized)
- [ ] Risk checks prevent invalid orders (insufficient buying power, position limits)
- [ ] Order history is complete and auditable
- [ ] Portfolio state can be serialized to JSON
- [ ] All broker operations are logged for debugging
- [ ] No real orders submitted (mock only)
