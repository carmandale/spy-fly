import { API_BASE_URL } from '../config'

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

interface TradeSpread {
  id?: number
  trade_id?: number
  spread_type: string
  expiration_date: string
  long_strike: number
  long_premium: number
  long_iv?: number
  long_delta?: number
  long_gamma?: number
  long_theta?: number
  short_strike: number
  short_premium: number
  short_iv?: number
  short_delta?: number
  short_gamma?: number
  short_theta?: number
  net_debit: number
  max_profit: number
  max_loss: number
  breakeven: number
  risk_reward_ratio: number
  created_at?: string
}

interface Trade {
  id?: number
  trade_date: string
  trade_type: 'paper' | 'real'
  status: 'recommended' | 'skipped' | 'entered' | 'exited' | 'stopped'
  entry_time?: string
  entry_sentiment_score_id?: number
  entry_signal_reason?: string
  contracts?: number
  max_risk?: number
  max_reward?: number
  probability_of_profit?: number
  exit_time?: string
  exit_reason?: string
  exit_price?: number
  gross_pnl?: number
  commissions?: number
  net_pnl?: number
  pnl_percentage?: number
  notes?: string
  created_at?: string
  updated_at?: string
  spread?: TradeSpread
}

interface TradeListResponse {
  trades: Trade[]
  total: number
  skip: number
  limit: number
}

interface TradeSummary {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl: number
  average_win: number
  average_loss: number
  largest_win: number
  largest_loss: number
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

  async getOptions(
    ticker: string,
    expiration: string,
    optionType?: 'call' | 'put'
  ): Promise<OptionChainResponse> {
    const params = new URLSearchParams({ expiration })
    if (optionType) params.append('option_type', optionType)
    return this.request<OptionChainResponse>(`/api/v1/market/options/${ticker}?${params}`)
  }

  async getMarketStatus(): Promise<MarketStatus> {
    return this.request<MarketStatus>('/api/v1/market/status')
  }

  // Trade methods
  async getTrades(params?: {
    skip?: number
    limit?: number
    trade_date?: string
    status?: string
    trade_type?: string
  }): Promise<TradeListResponse> {
    const searchParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString())
        }
      })
    }
    const query = searchParams.toString()
    return this.request<TradeListResponse>(`/api/v1/trades${query ? `?${query}` : ''}`)
  }

  async getTrade(id: number): Promise<Trade> {
    return this.request<Trade>(`/api/v1/trades/${id}`)
  }

  async createTrade(trade: Omit<Trade, 'id' | 'created_at' | 'updated_at'>): Promise<Trade> {
    return this.request<Trade>('/api/v1/trades', {
      method: 'POST',
      body: JSON.stringify(trade),
    })
  }

  async updateTrade(id: number, updates: Partial<Trade>): Promise<Trade> {
    return this.request<Trade>(`/api/v1/trades/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    })
  }

  async deleteTrade(id: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/trades/${id}`, {
      method: 'DELETE',
    })
  }

  async getTradeSummary(params?: {
    start_date?: string
    end_date?: string
  }): Promise<TradeSummary> {
    const searchParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value)
        }
      })
    }
    const query = searchParams.toString()
    return this.request<TradeSummary>(`/api/v1/trades/summary${query ? `?${query}` : ''}`)
  }

  async getRecentActivity(limit = 10): Promise<Trade[]> {
    return this.request<Trade[]>(`/api/v1/trades/recent/activity?limit=${limit}`)
  }

  // Generic GET method for flexible API calls
  async get<T = any>(endpoint: string): Promise<{ data: T }> {
    const data = await this.request<T>(endpoint)
    return { data }
  }
}

export const apiClient = new ApiClient(API_BASE_URL)

// Export types for use in components
export type { Trade, TradeSpread, TradeListResponse, TradeSummary }
