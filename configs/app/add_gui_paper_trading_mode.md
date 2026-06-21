# GUI Paper Trading Mode Specification
# Real-time simulation of live trading in browser UI

## Overview

MVP GUI features:
1. **Live paper portfolio** — Cash, positions, unrealized P&L
2. **Manual order entry** — Buy/sell with size and duration
3. **Order book** — Active and filled orders
4. **Position view** — Holdings with mark-to-market
5. **P&L dashboard** — Daily/monthly/total returns

## React Components (TypeScript)

```typescript
// src/app/components/PaperTradingUI/index.tsx

import React, { useState, useEffect } from 'react';
import { PortfolioCard } from './PortfolioCard';
import { OrderEntryForm } from './OrderEntryForm';
import { ActiveOrdersTable } from './ActiveOrdersTable';
import { PositionsTable } from './PositionsTable';
import { PnLChart } from './PnLChart';
import { usePortfolioStore } from '../../stores/portfolioStore';

export interface OrderRequest {
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
  order_type: 'market' | 'limit';
  limit_price?: number;
}

interface PortfolioState {
  cash_balance: number;
  total_market_value: number;
  total_portfolio_value: number;
  positions: Position[];
  orders: Order[];
  daily_pnl: number;
  daily_return_pct: number;
}

const PaperTradingUI: React.FC = () => {
  const [portfolio, setPortfolio] = useState<PortfolioState>({
    cash_balance: 0,
    total_market_value: 0,
    total_portfolio_value: 0,
    positions: [],
    orders: [],
    daily_pnl: 0,
    daily_return_pct: 0
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch portfolio every 5 seconds
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch('/api/trading/portfolio');
        const data = await response.json();
        setPortfolio(data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch portfolio');
      }
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleOrderSubmit = async (order: OrderRequest) => {
    setLoading(true);
    try {
      const response = await fetch('/api/trading/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(order)
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const newOrder = await response.json();
      setPortfolio(prev => ({
        ...prev,
        orders: [newOrder, ...prev.orders]
      }));

      setError(null);
    } catch (err) {
      setError(`Order failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelOrder = async (orderId: string) => {
    try {
      await fetch(`/api/trading/orders/${orderId}`, { method: 'DELETE' });
      
      setPortfolio(prev => ({
        ...prev,
        orders: prev.orders.filter(o => o.id !== orderId)
      }));
    } catch (err) {
      setError(`Cancel failed: ${err.message}`);
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>Paper Trading Dashboard</h1>

      {error && <div style={{ color: 'red', marginBottom: '20px' }}>{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        {/* Portfolio Summary */}
        <PortfolioCard
          cashBalance={portfolio.cash_balance}
          marketValue={portfolio.total_market_value}
          totalValue={portfolio.total_portfolio_value}
          dailyPnL={portfolio.daily_pnl}
          dailyReturnPct={portfolio.daily_return_pct}
        />

        {/* Quick Stats */}
        <div style={{ padding: '15px', border: '1px solid #ccc', borderRadius: '8px' }}>
          <h3>Stats</h3>
          <p>Open Positions: {portfolio.positions.length}</p>
          <p>Active Orders: {portfolio.orders.filter(o => o.status === 'pending').length}</p>
          <p>Buying Power: ${(portfolio.cash_balance * 0.99).toFixed(2)}</p>
        </div>
      </div>

      {/* Order Entry */}
      <OrderEntryForm
        onSubmit={handleOrderSubmit}
        loading={loading}
        cashBalance={portfolio.cash_balance}
      />

      {/* P&L Chart */}
      <div style={{ marginBottom: '20px' }}>
        <PnLChart />
      </div>

      {/* Active Orders */}
      <div style={{ marginBottom: '20px' }}>
        <h2>Active Orders</h2>
        <ActiveOrdersTable
          orders={portfolio.orders.filter(o => o.status === 'pending')}
          onCancel={handleCancelOrder}
        />
      </div>

      {/* Positions */}
      <div>
        <h2>Positions</h2>
        <PositionsTable positions={portfolio.positions} />
      </div>
    </div>
  );
};

export default PaperTradingUI;
```

```typescript
// src/app/components/PaperTradingUI/OrderEntryForm.tsx

import React, { useState } from 'react';

interface Props {
  onSubmit: (order: OrderRequest) => Promise<void>;
  loading: boolean;
  cashBalance: number;
}

export const OrderEntryForm: React.FC<Props> = ({
  onSubmit,
  loading,
  cashBalance
}) => {
  const [ticker, setTicker] = useState('');
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [quantity, setQuantity] = useState(0);
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [limitPrice, setLimitPrice] = useState(0);
  const [preview, setPreview] = useState(0);

  const handleQuantityChange = (qty: number) => {
    setQuantity(qty);
    // Estimate cost (would fetch real price)
    setPreview(qty * limitPrice);
  };

  const handleSubmit = async () => {
    if (!ticker || quantity <= 0) {
      alert('Invalid input');
      return;
    }

    await onSubmit({
      ticker: ticker.toUpperCase(),
      side,
      quantity,
      order_type: orderType,
      limit_price: orderType === 'limit' ? limitPrice : undefined
    });

    // Reset
    setTicker('');
    setQuantity(0);
    setLimitPrice(0);
  };

  return (
    <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', marginBottom: '20px' }}>
      <h2>Place Order</h2>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '10px', marginBottom: '10px' }}>
        {/* Ticker */}
        <div>
          <label>Ticker</label>
          <input
            type="text"
            placeholder="e.g., AAPL"
            value={ticker}
            onChange={e => setTicker(e.target.value)}
            disabled={loading}
          />
        </div>

        {/* Side */}
        <div>
          <label>Side</label>
          <select
            value={side}
            onChange={e => setSide(e.target.value as 'buy' | 'sell')}
            disabled={loading}
          >
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
          </select>
        </div>

        {/* Quantity */}
        <div>
          <label>Quantity</label>
          <input
            type="number"
            placeholder="100"
            value={quantity}
            onChange={e => handleQuantityChange(parseInt(e.target.value))}
            disabled={loading}
          />
        </div>

        {/* Order Type */}
        <div>
          <label>Type</label>
          <select
            value={orderType}
            onChange={e => setOrderType(e.target.value as 'market' | 'limit')}
            disabled={loading}
          >
            <option value="market">Market</option>
            <option value="limit">Limit</option>
          </select>
        </div>
      </div>

      {/* Limit Price (conditional) */}
      {orderType === 'limit' && (
        <div style={{ marginBottom: '10px' }}>
          <label>Limit Price</label>
          <input
            type="number"
            placeholder="150.00"
            value={limitPrice}
            onChange={e => setLimitPrice(parseFloat(e.target.value))}
            disabled={loading}
          />
        </div>
      )}

      {/* Preview */}
      <div style={{ backgroundColor: '#f0f0f0', padding: '10px', marginBottom: '10px', borderRadius: '4px' }}>
        <p>Est. Cost: ${preview.toFixed(2)} | Available Cash: ${cashBalance.toFixed(2)}</p>
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading || !ticker || quantity <= 0}
        style={{
          padding: '10px 20px',
          backgroundColor: side === 'buy' ? '#4CAF50' : '#f44336',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: loading ? 'not-allowed' : 'pointer',
          opacity: loading ? 0.5 : 1
        }}
      >
        {loading ? 'Submitting...' : 'Submit Order'}
      </button>
    </div>
  );
};
```

## Backend Integration

```python
# src/qlib_research/app/api/routes/trading.py

@router.get("/trading/portfolio")
async def get_portfolio(broker=Depends(get_broker)):
    """Get current portfolio state"""
    
    portfolio = broker.get_portfolio()
    
    return {
        "cash_balance": portfolio.cash_balance,
        "total_market_value": portfolio.total_market_value,
        "total_portfolio_value": portfolio.total_portfolio_value,
        "positions": [
            {
                "ticker": p.ticker,
                "quantity": p.quantity,
                "avg_cost": p.avg_cost,
                "current_price": broker.get_current_price(p.ticker),
                "unrealized_pnl": p.unrealized_pnl(broker),
                "unrealized_pnl_pct": p.unrealized_pnl_pct(broker)
            }
            for p in portfolio.positions
        ],
        "orders": [
            {
                "id": o.id,
                "ticker": o.ticker,
                "side": o.side,
                "quantity": o.quantity,
                "filled_quantity": o.filled_quantity,
                "status": o.status,
                "created_at": o.created_at.isoformat()
            }
            for o in broker.get_active_orders()
        ],
        "daily_pnl": portfolio.daily_pnl,
        "daily_return_pct": portfolio.daily_return_pct
    }

@router.post("/trading/orders")
async def submit_order(
    order: OrderRequest,
    broker=Depends(get_broker),
    risk_validator=Depends(get_risk_validator)
):
    """Submit buy/sell order"""
    
    # Validate
    portfolio = broker.get_portfolio()
    can_trade, violations = risk_validator.can_execute_trade(portfolio, order)
    
    if not can_trade:
        raise HTTPException(
            status_code=400,
            detail=f"Risk check failed: {', '.join(violations)}"
        )
    
    # Execute
    result = await broker.submit_order(
        ticker=order.ticker,
        side=order.side,
        quantity=order.quantity,
        order_type=order.order_type,
        limit_price=order.limit_price
    )
    
    return result
```

## Acceptance Criteria

- [ ] Portfolio display (cash, positions, P&L)
- [ ] Order entry form (buy/sell)
- [ ] Market and limit order types
- [ ] Active orders table
- [ ] Positions table with mark-to-market
- [ ] P&L chart (daily, cumulative)
- [ ] Real-time refresh (5-second polling)
- [ ] Cancel order functionality
- [ ] Risk check validation
- [ ] UI tests pass
