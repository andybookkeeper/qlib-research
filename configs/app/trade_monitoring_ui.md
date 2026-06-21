# Trade Monitoring UI Specification
# Real-time order status, fills, and trade history visualization

## Overview

Trade monitoring UI displays:
1. **Active Orders** — Pending, partially filled orders with cancel/modify
2. **Trade History** — Realized trades with entry/exit analysis
3. **Order Book** — Live bid/ask updates (if supported)
4. **Execution Details** — Full fills breakdown, average price, slippage

## Active Orders Dashboard

### Orders Table

```
┌────────────────────────────────────────────────────────────┐
│ Active Orders (3)                                          │
├────────────────────────────────────────────────────────────┤
│ ID    │Ticker│ Side │ Qty  │ Filled│ Avg Px │ Status │ Act │
├────────────────────────────────────────────────────────────┤
│12001  │ AAPL │ Buy  │ 100  │  75   │ 150.45 │ PARTIAL│ ⋮  │
│12002  │ MSFT │ Sell │ 50   │  0    │  —     │ PENDING│ ⋮  │
│12003  │ GOOG │ Buy  │ 200  │ 200   │ 139.82 │ FILLED │ ⋮  │
└────────────────────────────────────────────────────────────┘

Actions (per row):
⋮ → [View Fills] [Modify] [Cancel] [Close]
```

### Order Details Modal

When user clicks "View Fills" or order ID:

```
┌──────────────────────────────────────────────┐
│ Order Details: ORD_12001                      │
├──────────────────────────────────────────────┤
│
│ Summary:
│ • Ticker: AAPL
│ • Side: BUY
│ • Total Qty: 100 shares
│ • Filled: 75 (75%)
│ • Remaining: 25
│ • Avg Fill Price: $150.45
│ • Order Type: Limit $151.00
│ • Status: PARTIALLY FILLED
│ • Time in force: GTC (good-til-cancel)
│ • Created: 2024-01-19 14:30:15 UTC
│ • Last Updated: 2024-01-19 14:32:47 UTC
│
│ Fills Breakdown:
│ ┌────────────────────────────────────┐
│ │ Fill# │ Time       │ Qty │ Price  │
│ ├────────────────────────────────────┤
│ │ F1    │ 14:30:22   │ 50  │ 150.40 │
│ │ F2    │ 14:31:15   │ 25  │ 150.50 │
│ └────────────────────────────────────┘
│
│ P&L Impact (unrealized):
│ Cost: 75 × $150.45 = $11,283.75
│ Current Value: 75 × $151.20 = $11,340.00
│ Unrealized P&L: +$56.25 (+0.50%)
│
│ [Modify Limit Price] [Cancel Remaining] [Close]
└──────────────────────────────────────────────┘
```

### Real-Time Updates

**Refresh Strategy**:
- Auto-refresh active orders every **3 seconds** via polling
- Highlight newly filled quantities in green
- Sound notification on order fill (optional)
- Toast alert for status changes

**Components**:

```python
# src/components/Trading/OrdersTable.vue

<template>
  <table class="orders-table">
    <thead>
      <tr>
        <th>Order ID</th>
        <th>Ticker</th>
        <th>Side</th>
        <th>Qty</th>
        <th>Filled</th>
        <th>Avg Price</th>
        <th>Status</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="order in activeOrders" :key="order.id" 
          :class="{ 'newly-filled': order._isNew }">
        <td>{{ order.id }}</td>
        <td class="ticker-cell">{{ order.ticker }}</td>
        <td :class="order.side">{{ order.side }}</td>
        <td>{{ order.quantity }}</td>
        <td>
          <ProgressBar :value="order.filledQuantity / order.quantity * 100" />
          {{ order.filledQuantity }} / {{ order.quantity }}
        </td>
        <td>${{ order.averageFillPrice }}</td>
        <td><StatusBadge :status="order.status" /></td>
        <td>
          <DropdownMenu>
            <MenuItem @click="viewFills(order)">View Fills</MenuItem>
            <MenuItem @click="modifyOrder(order)">Modify</MenuItem>
            <MenuItem @click="cancelOrder(order)" class="danger">Cancel</MenuItem>
          </DropdownMenu>
        </td>
      </tr>
    </tbody>
  </table>
</template>

<script>
export default {
  props: ['activeOrders'],
  methods: {
    async viewFills(order) {
      const details = await this.$api.get(`/api/v1/orders/${order.id}`);
      this.$emit('show-details', details);
    },
    async cancelOrder(order) {
      const confirmed = await this.$confirm(
        `Cancel order ${order.id}?`
      );
      if (confirmed) {
        await this.$api.delete(`/api/v1/orders/${order.id}`);
        this.$toast.success(`Order ${order.id} cancelled`);
      }
    }
  }
}
</script>

<style scoped>
.newly-filled {
  background-color: rgba(76, 175, 80, 0.1);
  animation: highlight 2s ease-out;
}

@keyframes highlight {
  0% { background-color: rgba(76, 175, 80, 0.3); }
  100% { background-color: rgba(76, 175, 80, 0.1); }
}
</style>
```

## Trade History

### Realized Trades Table

```
┌──────────────────────────────────────────────────────────────┐
│ Trade History - Last 30 Days (12 trades)                    │
├──────────────────────────────────────────────────────────────┤
│Ticker│Entry Date │Entry  │Exit Date  │Exit   │Qty│ P&L    │ MDD │
├──────────────────────────────────────────────────────────────┤
│ GOOG │2024-01-15│139.82 │2024-01-18│141.25 │50 │ +$71.50│+1.0%│
│ NVDA │2024-01-10│485.20 │2024-01-17│482.50 │25 │ -$67.50│-2.1%│
│ AAPL │2024-01-12│150.00 │2024-01-19│151.20 │100│+$120.00│+1.2%│
└──────────────────────────────────────────────────────────────┘

Legend:
P&L: Realized profit/loss including commissions
MDD: Max drawdown during holding period
```

### Trade Analysis Modal

Click on trade row:

```
┌──────────────────────────────────────────────┐
│ Trade Analysis: GOOG (Entry 2024-01-15)      │
├──────────────────────────────────────────────┤
│
│ Entry:
│ • Date/Time: 2024-01-15 10:45:30 UTC
│ • Price: $139.82
│ • Qty: 50 shares
│ • Order ID: ORD_11998
│ • Commission: $5.00
│
│ Exit:
│ • Date/Time: 2024-01-18 14:22:15 UTC
│ • Price: $141.25
│ • Qty: 50 shares
│ • Order ID: ORD_12000
│ • Commission: $5.00
│
│ Performance:
│ • Holding Period: 3 days 3 hours 37 minutes
│ • Entry Cost: 50 × $139.82 + $5 = $6,991.00
│ • Exit Proceeds: 50 × $141.25 - $5 = $7,056.50
│ • Gross P&L: +$65.50
│ • Net P&L: +$71.50 (after commission)
│ • Return: +1.02%
│ • Max Drawdown: -$45.00 (-0.64%)
│ • Days Held: 3
│
│ 📊 Price Chart During Hold:
│ ┌────────────────────────────────────┐
│ │ Entry: $139.82 ────────●            │
│ │                       / \          │
│ │                      /   \         │
│ │              Exit: ●/$141.25        │
│ │                                    │
│ │ High: $143.20  Low: $138.50        │
│ └────────────────────────────────────┘
│
│ Signal Quality (Qlib):
│ • Entry Signal Confidence: 72%
│ • Exit Triggered By: Price target (1.2% gain)
│ • [View backtest for similar trades]
│
│ [Export] [Duplicate Trade] [Close]
└──────────────────────────────────────────────┘
```

## Trade Statistics Dashboard

```
┌──────────────────────────────────────────────────────────┐
│ Trade Statistics (Last 30 days)                          │
├──────────────────────────────────────────────────────────┤
│
│ Win Rate: 58% (7 wins, 5 losses)
│ Avg Win: +$156.25
│ Avg Loss: -$89.50
│ Profit Factor: 1.94 (total wins / total losses)
│ 
│ Best Trade: GOOG +$256.00 (+2.1%)
│ Worst Trade: NVDA -$234.00 (-1.8%)
│ Avg Trade Duration: 4.2 days
│
│ Cumulative Return: +$843.50 (+0.8% of portfolio)
│
│ Monthly Breakdown:
│ ┌─────────────────────────────┐
│ │ Month      │ Trades │ P&L   │
│ ├─────────────────────────────┤
│ │ 2024-01    │ 12     │+843.50│
│ │ 2023-12    │ 8      │+456.00│
│ │ 2023-11    │ 15     │-123.00│
│ └─────────────────────────────┘
│
│ [Export to CSV] [View Detailed Report] [Settings]
└──────────────────────────────────────────────────────────┘
```

## Components

### ActiveOrdersWidget

```python
# src/components/Trading/ActiveOrdersWidget.vue

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const activeOrders = ref([])
const refreshInterval = ref(null)

const fetchOrders = async () => {
  const response = await fetch('/api/v1/orders?status=pending,partially_filled')
  activeOrders.value = await response.json()
}

const cancelOrder = async (orderId) => {
  await fetch(`/api/v1/orders/${orderId}`, { method: 'DELETE' })
  await fetchOrders()
}

onMounted(() => {
  fetchOrders()
  refreshInterval.value = setInterval(fetchOrders, 3000)  // Poll every 3s
})

onBeforeUnmount(() => {
  clearInterval(refreshInterval.value)
})
</script>

<template>
  <div class="orders-widget">
    <h2>Active Orders ({{ activeOrders.length }})</h2>
    <OrdersTable 
      :orders="activeOrders"
      @cancel="cancelOrder"
      @view-fills="viewOrderDetails"
    />
    <p v-if="activeOrders.length === 0" class="no-orders">
      No active orders. All filled or cancelled.
    </p>
  </div>
</template>
```

### TradeHistoryWidget

```python
# src/components/Trading/TradeHistoryWidget.vue

<script setup>
import { ref, onMounted } from 'vue'

const trades = ref([])
const filteredTrades = ref([])
const daysFilter = ref(30)

const fetchTrades = async () => {
  const response = await fetch(
    `/api/v1/trades?days=${daysFilter.value}`
  )
  trades.value = await response.json()
  filteredTrades.value = trades.value
}

const calculateStats = () => {
  if (trades.value.length === 0) return {}
  
  const winningTrades = trades.value.filter(t => t.pnl > 0)
  const losingTrades = trades.value.filter(t => t.pnl < 0)
  
  return {
    totalTrades: trades.value.length,
    winRate: (winningTrades.length / trades.value.length * 100).toFixed(1),
    avgWin: (winningTrades.reduce((s, t) => s + t.pnl, 0) / winningTrades.length).toFixed(2),
    avgLoss: (losingTrades.reduce((s, t) => s + t.pnl, 0) / losingTrades.length).toFixed(2),
    totalPnL: trades.value.reduce((s, t) => s + t.pnl, 0).toFixed(2)
  }
}

onMounted(fetchTrades)
</script>

<template>
  <div class="trade-history-widget">
    <h2>Trade History</h2>
    
    <div class="filters">
      <label>Last <select v-model="daysFilter" @change="fetchTrades">
        <option value="7">7 days</option>
        <option value="30">30 days</option>
        <option value="90">90 days</option>
        <option value="365">1 year</option>
      </select></label>
    </div>
    
    <TradeStatsPanel :stats="calculateStats()" />
    
    <TradesTable 
      :trades="filteredTrades"
      @view-analysis="viewTradeDetails"
    />
    
    <p v-if="filteredTrades.length === 0" class="no-trades">
      No trades in this period.
    </p>
  </div>
</template>
```

## API Endpoints (Reference)

```python
# src/qlib_research/app/api/routes/trading.py (additions)

@router.get("/orders")
async def list_orders(
    status: Optional[str] = Query(None),  # pending, filled, cancelled
    ticker: Optional[str] = Query(None),
    days: int = Query(30),
    broker_service=Depends(get_broker_service)
):
    """List orders with optional filtering"""
    orders = broker_service.get_orders(
        status=status,
        ticker=ticker,
        days=days
    )
    return orders

@router.get("/trades")
async def list_trades(
    days: int = Query(30),
    broker_service=Depends(get_broker_service)
):
    """Get realized trades"""
    trades = broker_service.get_trades(days=days)
    return [
        {
            "ticker": t.ticker,
            "entry_date": t.opened_at,
            "entry_price": t.entry_price,
            "exit_date": t.closed_at,
            "exit_price": t.exit_price,
            "quantity": t.quantity,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "commission": t.commission,
            "duration_days": (t.closed_at - t.opened_at).days
        }
        for t in trades
    ]

@router.get("/orders/{order_id}/fills")
async def get_order_fills(
    order_id: str,
    broker_service=Depends(get_broker_service)
):
    """Get detailed fills for an order"""
    order = broker_service.get_order(order_id)
    return {
        "order_id": order.id,
        "ticker": order.ticker,
        "total_quantity": order.quantity,
        "total_filled": order.filled_quantity,
        "fills": [
            {
                "fill_id": f.id,
                "timestamp": f.timestamp,
                "quantity": f.quantity,
                "price": f.price
            }
            for f in order.fills
        ],
        "average_fill_price": order.average_fill_price
    }

@router.get("/trades/stats")
async def get_trade_stats(
    days: int = Query(30),
    broker_service=Depends(get_broker_service)
):
    """Get trading statistics"""
    trades = broker_service.get_trades(days=days)
    
    if not trades:
        return {"error": "No trades"}
    
    winning = [t for t in trades if t.pnl > 0]
    losing = [t for t in trades if t.pnl < 0]
    
    return {
        "total_trades": len(trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": len(winning) / len(trades) if trades else 0,
        "avg_win": sum(t.pnl for t in winning) / len(winning) if winning else 0,
        "avg_loss": sum(t.pnl for t in losing) / len(losing) if losing else 0,
        "best_trade": max(trades, key=lambda t: t.pnl).pnl if trades else 0,
        "worst_trade": min(trades, key=lambda t: t.pnl).pnl if trades else 0,
        "total_pnl": sum(t.pnl for t in trades),
        "avg_holding_days": sum(
            (t.closed_at - t.opened_at).days for t in trades
        ) / len(trades) if trades else 0
    }
```

## Styling

```css
/* src/components/Trading/OrdersTable.vue */

.orders-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.orders-table thead {
  background-color: #f5f5f5;
  border-bottom: 2px solid #ddd;
}

.orders-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
}

.orders-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #eee;
}

.orders-table tbody tr:hover {
  background-color: #f9f9f9;
}

.orders-table .buy {
  color: #4CAF50;
  font-weight: 600;
}

.orders-table .sell {
  color: #f44336;
  font-weight: 600;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.pending {
  background-color: #fff3cd;
  color: #856404;
}

.status-badge.filled {
  background-color: #d4edda;
  color: #155724;
}

.status-badge.cancelled {
  background-color: #f8d7da;
  color: #721c24;
}
```

## Acceptance Criteria

- [ ] Active orders table shows pending/partially filled
- [ ] Refresh every 3 seconds without freezing UI
- [ ] Order details modal shows all fills
- [ ] Cancel button works and updates immediately
- [ ] Trade history table shows realized trades
- [ ] Trade statistics calculated correctly
- [ ] Win rate, avg win/loss computed
- [ ] Export to CSV works (future)
- [ ] Mobile responsive on tablet

## Known Limitations (MVP)

- No WebSocket (polling only)
- No modify order (cancel + resubmit)
- No order templates/favorites
- No bracket orders (OCO)
- No notifications (popup only)
- No P&L chart overlay on price chart
