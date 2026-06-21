// API Types
export interface PriceSnapshot {
  ticker: string
  price: number
  timestamp: string
  volume: number
  change_pct: number
}

export interface PortfolioOverview {
  portfolio_value: number
  cash: number
  gross_value: number
  net_value: number
  realized_pnl: number
  unrealized_pnl: number
  total_pnl: number
  total_pnl_pct: number
  open_positions: number
  total_trades: number
}

export interface DashboardData extends PortfolioOverview {
  var_95: number
  max_drawdown: number
  sharpe_ratio: number
  positions: Position[]
  risk_warnings: string[]
}

export interface Position {
  symbol: string
  quantity: number
  entry_price: number
  current_price: number
  market_value: number
  pnl: number
  pnl_pct: number
}

export interface Order {
  order_id: string
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  price: number
  status: 'PENDING' | 'FILLED' | 'CANCELLED'
  timestamp: string
}

export interface RiskLimits {
  max_position_size: number
  max_concentration: number
  max_portfolio_delta: number
  max_portfolio_gamma: number
  max_portfolio_theta: number
  max_portfolio_vega: number
  max_drawdown: number
  min_sharpe_ratio: number
}

export interface Greeks {
  delta: number
  gamma: number
  theta: number
  vega: number
  rho: number
}

export interface Model {
  name: string
  type: string
  trained_at: string
  train_loss: number
  test_loss: number
  train_samples: number
  test_samples: number
  features: string[]
}

export interface Ticker {
  symbol: string
  name: string
  lastPrice?: number
  change?: number
  changePercent?: number
}
