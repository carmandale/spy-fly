const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003'

interface HealthResponse {
  status: string
  timestamp: string
  version: string
  environment: string
}

interface QuoteResponse {
  ticker: string
  price: number
  bid?: number
  ask?: number
  bid_size?: number
  ask_size?: number
  volume: number
  high?: number
  low?: number
  open?: number
  close?: number
  vwap?: number
  timestamp: string
  cached: boolean
}

interface OptionContract {
  symbol: string
  type: 'call' | 'put'
  strike: number
  expiration: string
  bid: number
  ask: number
  mid: number
  last?: number
  volume: number
  open_interest: number
  delta?: number
  gamma?: number
  theta?: number
  vega?: number
  iv?: number
}

interface OptionChainResponse {
  ticker: string
  underlying_price: number
  expiration: string
  options: OptionContract[]
  cached: boolean
  timestamp: string
}

interface MarketStatus {
  market_status: 'open' | 'closed'
  session: 'pre-market' | 'regular' | 'after-hours' | 'weekend'
  api_status: string
  rate_limit_remaining: number
  rate_limit_reset: string
  cache_stats?: {
    hits: number
    misses: number
    size: number
  }
}

class ApiClient {
  baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`API call failed: ${response.statusText} - ${error}`)
    }

    return response.json()
  }

  async health(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/api/v1/health')
  }

  async getQuote(ticker: string): Promise<QuoteResponse> {
    return this.request<QuoteResponse>(`/api/v1/market/quote/${ticker}`)
  }

  async getOptions(ticker: string, expiration: string, optionType?: 'call' | 'put'): Promise<OptionChainResponse> {
    const params = new URLSearchParams({ expiration })
    if (optionType) params.append('option_type', optionType)
    return this.request<OptionChainResponse>(`/api/v1/market/options/${ticker}?${params}`)
  }

  async getMarketStatus(): Promise<MarketStatus> {
    return this.request<MarketStatus>('/api/v1/market/status')
  }
}

export const apiClient = new ApiClient(API_BASE_URL)