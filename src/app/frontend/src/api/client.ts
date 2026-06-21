const API_BASE_URL = 'http://localhost:8000/api'

export const apiClient = {
  // Market Data
  market: {
    getTickers: async (): Promise<string[]> => {
      const response = await fetch(`${API_BASE_URL}/market/tickers`)
      return response.json()
    },
    getPrice: async (ticker: string) => {
      const response = await fetch(`${API_BASE_URL}/market/price/${ticker}`)
      return response.json()
    },
    getPrices: async (tickers: string[]) => {
      const params = new URLSearchParams()
      tickers.forEach(t => params.append('tickers', t))
      const response = await fetch(`${API_BASE_URL}/market/prices?${params}`)
      return response.json()
    },
  },

  // Portfolio
  portfolio: {
    getOverview: async () => {
      const response = await fetch(`${API_BASE_URL}/portfolio/overview`)
      return response.json()
    },
    getDashboard: async () => {
      const response = await fetch(`${API_BASE_URL}/portfolio/dashboard`)
      return response.json()
    },
    getPerformance: async () => {
      const response = await fetch(`${API_BASE_URL}/portfolio/performance`)
      return response.json()
    },
  },

  // Risk
  risk: {
    getLimits: async () => {
      const response = await fetch(`${API_BASE_URL}/risk/limits`)
      return response.json()
    },
    calculateVaR: async (portfolioValue: number, confidence: number = 0.95) => {
      const response = await fetch(
        `${API_BASE_URL}/risk/var?portfolio_value=${portfolioValue}&confidence=${confidence}`,
        { method: 'POST' }
      )
      return response.json()
    },
  },

  // Broker
  broker: {
    getPositions: async () => {
      const response = await fetch(`${API_BASE_URL}/broker/positions`)
      return response.json()
    },
    getOrders: async () => {
      const response = await fetch(`${API_BASE_URL}/broker/orders`)
      return response.json()
    },
    getTrades: async () => {
      const response = await fetch(`${API_BASE_URL}/broker/trades`)
      return response.json()
    },
    placeOrder: async (order: any) => {
      const response = await fetch(`${API_BASE_URL}/broker/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(order),
      })
      return response.json()
    },
  },

  // Research
  research: {
    listModels: async () => {
      const response = await fetch(`${API_BASE_URL}/research/models`)
      return response.json()
    },
    predict: async (modelName: string, features: any) => {
      const response = await fetch(
        `${API_BASE_URL}/research/predict?model_name=${modelName}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(features),
        }
      )
      return response.json()
    },
    getBacktests: async () => {
      const response = await fetch(`${API_BASE_URL}/research/backtests`)
      return response.json()
    },
  },

  // Features
  features: {
    getIndicators: async () => {
      const response = await fetch(`${API_BASE_URL}/features/indicators`)
      return response.json()
    },
  },

  // Training
  training: {
    trainModel: async (config: any) => {
      const response = await fetch(`${API_BASE_URL}/training/train`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      return response.json()
    },
    listModels: async () => {
      const response = await fetch(`${API_BASE_URL}/training/models`)
      return response.json()
    },
  },
}
