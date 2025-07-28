const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

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

  // Trade API methods
  async createTrade(trade: TradeCreate): Promise<Trade> {
    return this.request<Trade>('/api/v1/trades', {
      method: 'POST',
      body: JSON.stringify(trade),
    })
  }

  async getTrade(tradeId: number): Promise<Trade> {
    return this.request<Trade>(`/api/v1/trades/${tradeId}`)
  }

  async listTrades(params?: {
    start_date?: string
    end_date?: string
    status?: string
    trade_type?: string
    page?: number
    per_page?: number
  }): Promise<TradeListResponse> {
    const queryParams = params ? new URLSearchParams(
      Object.entries(params)
        .filter(([_, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ) : ''
    return this.request<TradeListResponse>(`/api/v1/trades${queryParams ? `?${queryParams}` : ''}`)
  }

  async updateTrade(tradeId: number, update: TradeUpdate): Promise<Trade> {
    return this.request<Trade>(`/api/v1/trades/${tradeId}`, {
      method: 'PATCH',
      body: JSON.stringify(update),
    })
  }

  async calculatePnL(tradeId: number, pnlRequest: TradePnLRequest): Promise<TradePnLResponse> {
    return this.request<TradePnLResponse>(`/api/v1/trades/${tradeId}/calculate-pnl`, {
      method: 'POST',
      body: JSON.stringify(pnlRequest),
    })
  }

  async deleteTrade(tradeId: number): Promise<void> {
    await this.request<void>(`/api/v1/trades/${tradeId}`, {
      method: 'DELETE',
    })
  }
}

// Trade types
export interface TradeSpread {
  id?: number
  spread_type: string
  expiration_date: string
  long_strike: number
  short_strike: number
  long_premium: number
  short_premium: number
  net_debit: number
  max_profit: number
  max_loss: number
  breakeven: number
  risk_reward_ratio: number
  long_iv?: number
  long_delta?: number
  long_gamma?: number
  long_theta?: number
  short_iv?: number
  short_delta?: number
  short_gamma?: number
  short_theta?: number
}

export interface Trade {
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
  spread?: TradeSpread
  created_at?: string
  updated_at?: string
}

export interface TradeCreate {
  trade_date: string
  trade_type: 'paper' | 'real'
  status: 'recommended' | 'skipped' | 'entered' | 'exited' | 'stopped'
  entry_time?: string
  contracts?: number
  max_risk?: number
  max_reward?: number
  notes?: string
  spread?: Omit<TradeSpread, 'id'>
}

export interface TradeUpdate {
  status?: 'recommended' | 'skipped' | 'entered' | 'exited' | 'stopped'
  exit_time?: string
  exit_reason?: string
  exit_price?: number
  gross_pnl?: number
  commissions?: number
  net_pnl?: number
  pnl_percentage?: number
  notes?: string
}

export interface TradeListResponse {
  items: Trade[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface TradePnLRequest {
  exit_price: number
  commission_per_contract?: number
}

export interface TradePnLResponse {
  gross_pnl: number
  commissions: number
  net_pnl: number
  pnl_percentage: number
  exit_value: number
}

export const apiClient = new ApiClient(API_BASE_URL)