const defaultApiBaseUrl =
  typeof window !== 'undefined' &&
  ['localhost', '127.0.0.1'].includes(window.location.hostname)
    ? 'http://127.0.0.1:8000/api'
    : 'https://qlib-api.onrender.com/api'

const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl
export const API_BASE_URL = String(rawApiBaseUrl).replace(/\/+$/, '')
const AUTH_TOKEN_KEY = 'qlib_auth_token'

function getAuthToken(): string | null {
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

async function request<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAuthToken()
  const headers = new Headers(init.headers || {})

  if (!headers.has('Content-Type') && init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const detail = payload?.detail || `Request failed (${response.status})`
    throw new Error(detail)
  }
  return response.json()
}

export function createRealtimeWebSocket(): WebSocket {
  const token = getAuthToken()
  const query = token ? `?token=${encodeURIComponent(token)}` : ''
  const configuredWsBase = import.meta.env.VITE_WS_BASE_URL
  let wsBase = ''
  if (configuredWsBase) {
    wsBase = String(configuredWsBase).replace(/\/+$/, '')
  } else {
    const apiUrl = new URL(API_BASE_URL)
    wsBase = apiUrl.origin.replace(/^http/, 'ws')
  }
  return new WebSocket(`${wsBase}/api/realtime/ws${query}`)
}

export const apiClient = {
  auth: {
    signup: async (payload: {
      username: string
      email: string
      password: string
      full_name?: string
    }) => request('/auth/signup', { method: 'POST', body: JSON.stringify(payload) }),
    login: async (username: string, password: string) =>
      request<{ access_token: string; token_type: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }),
    me: async () => request('/auth/me'),
  },
  market: {
    getTickers: async (): Promise<string[]> => request('/market/tickers'),
    getPrice: async (ticker: string) => request(`/market/price/${ticker}`),
    getPrices: async (tickers: string[]) => {
      const params = new URLSearchParams()
      tickers.forEach((t) => params.append('tickers', t))
      return request(`/market/prices?${params.toString()}`)
    },
  },
  portfolio: {
    getOverview: async () => request('/portfolio/overview'),
    getDashboard: async () => request('/portfolio/dashboard'),
    getPerformance: async () => request('/portfolio/performance'),
  },
  risk: {
    getLimits: async () => request('/risk/limits'),
    calculateVaR: async (portfolioValue: number, confidence = 0.95) =>
      request(`/risk/var?portfolio_value=${portfolioValue}&confidence=${confidence}`, {
        method: 'POST',
      }),
  },
  broker: {
    getPositions: async () => request('/broker/positions'),
    getOrders: async () => request('/broker/orders'),
    getTrades: async () => request('/broker/trades/closed'),
    placeOrder: async (order: {
      symbol: string
      side: 'BUY' | 'SELL'
      quantity: number
      orderType: 'MARKET' | 'LIMIT' | 'STOP'
      limitPrice?: number
      stopPrice?: number
    }) =>
      request('/broker/orders', {
        method: 'POST',
        body: JSON.stringify({
          ticker: order.symbol,
          side: order.side,
          quantity: order.quantity,
          order_type: order.orderType,
          limit_price: order.orderType === 'LIMIT' ? order.limitPrice : undefined,
          stop_price: order.orderType === 'STOP' ? order.stopPrice : undefined,
        }),
      }),
  },
  research: {
    listModels: async () => request('/research/models'),
    predict: async (modelName: string, features: unknown) =>
      request(`/research/predict?model_name=${encodeURIComponent(modelName)}`, {
        method: 'POST',
        body: JSON.stringify(features),
      }),
    getBacktests: async () => request('/research/backtests'),
    getSignals: async (tickers?: string[]) => {
      const qs = tickers ? `?tickers=${tickers.join(',')}` : ''
      return request(`/research/signals${qs}`)
    },
  },
  features: {
    getIndicators: async () => request('/features/indicators'),
  },
  training: {
    trainModel: async (config: unknown) =>
      request('/training/train', {
        method: 'POST',
        body: JSON.stringify(config),
      }),
    listModels: async () => request('/training/models'),
  },
}
