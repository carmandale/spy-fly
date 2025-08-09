/**
 * API service for position management and P/L data.
 * 
 * Provides functions to interact with the positions REST API endpoints
 * for creating, updating, and monitoring spread positions.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003/api/v1'

export interface Position {
  id: number
  symbol: string
  position_type: string
  status: string
  contracts: number
  entry_date: string
  expiration_date: string
  
  // Spread configuration
  long_strike: number
  short_strike: number
  
  // Entry pricing
  entry_long_premium: number
  entry_short_premium: number
  entry_net_debit: number
  entry_total_cost: number
  
  // Risk metrics
  max_profit: number
  max_loss: number
  breakeven_price: number
  
  // Entry market conditions
  entry_spy_price: number
  entry_vix?: number
  entry_sentiment_score?: number
  
  // Exit details (if closed)
  exit_date?: string
  exit_time?: string
  exit_reason?: string
  exit_long_premium?: number
  exit_short_premium?: number
  exit_net_credit?: number
  exit_total_value?: number
  
  // Final P/L (if closed)
  realized_pnl?: number
  realized_pnl_percent?: number
  
  // Position management
  profit_target_percent: number
  stop_loss_percent: number
  
  // Metadata
  notes?: string
  created_at: string
  updated_at: string
}

export interface CurrentPL {
  position_id: number
  symbol: string
  contracts: number
  current_spy_price: number
  time_to_expiry_hours: number
  
  // Current pricing
  current_long_premium: number
  current_short_premium: number
  current_net_value: number
  current_total_value: number
  
  // P/L calculations
  entry_total_cost: number
  unrealized_pnl: number
  unrealized_pnl_percent: number
  
  // Greeks and risk metrics
  position_delta?: number
  position_gamma?: number
  position_theta?: number
  position_vega?: number
  daily_theta_decay?: number
  
  // Alert information
  alert_triggered: boolean
  alert_type?: string
  alert_message?: string
  
  // Metadata
  market_session: string
  calculation_timestamp: string
  data_quality_score: number
}

export interface PortfolioPL {
  total_positions: number
  total_unrealized_pnl: number
  total_unrealized_pnl_percent: number
  total_daily_theta: number
  current_spy_price: number
  calculation_timestamp: string
  positions: CurrentPL[]
}

export interface PLSnapshot {
  id: number
  position_id: number
  snapshot_time: string
  market_session: string
  
  // Market data
  spy_price: number
  vix_level?: number
  
  // Current pricing
  current_long_premium?: number
  current_short_premium?: number
  current_net_value?: number
  current_total_value?: number
  
  // P/L calculations
  unrealized_pnl: number
  unrealized_pnl_percent: number
  
  // Greeks
  position_delta?: number
  position_gamma?: number
  position_theta?: number
  position_vega?: number
  
  // Time decay
  time_to_expiry_hours?: number
  daily_theta_decay?: number
  
  // Alert info
  alert_triggered: boolean
  alert_type?: string
  
  // Data quality
  data_source: string
  calculation_method: string
  data_quality_score?: number
  
  created_at: string
}

export interface Alert {
  id: number
  position_id: number
  alert_type: string
  alert_level: string
  message: string
  
  // Alert conditions
  trigger_value?: number
  trigger_percent?: number
  threshold_value?: number
  
  // Notification status
  sent_at?: string
  delivery_method?: string
  delivery_status: string
  
  // Alert metadata
  is_acknowledged: boolean
  acknowledged_at?: string
  created_at: string
}

export interface CreatePositionRequest {
  symbol?: string
  position_type: string
  contracts: number
  entry_date: string
  expiration_date: string
  
  // Spread configuration
  long_strike: number
  short_strike: number
  
  // Entry pricing
  entry_long_premium: number
  entry_short_premium: number
  entry_net_debit: number
  entry_total_cost: number
  
  // Risk metrics
  max_profit: number
  max_loss: number
  breakeven_price: number
  
  // Entry market conditions
  entry_spy_price: number
  entry_vix?: number
  entry_sentiment_score?: number
  
  // Position management
  profit_target_percent?: number
  stop_loss_percent?: number
  
  notes?: string
}

export interface UpdatePositionRequest {
  profit_target_percent?: number
  stop_loss_percent?: number
  notes?: string
}

export interface ClosePositionRequest {
  exit_reason: string
  exit_long_premium: number
  exit_short_premium: number
  exit_net_credit: number
  exit_total_value: number
}

class PositionsApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: unknown
  ) {
    super(message)
    this.name = 'PositionsApiError'
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`
    let errorDetails: unknown = null
    
    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorData.message || errorMessage
      errorDetails = errorData
    } catch {
      // If we can't parse the error response, use the default message
    }
    
    throw new PositionsApiError(errorMessage, response.status, errorDetails)
  }
  
  return response.json()
}

export class PositionsApi {
  private baseUrl: string
  
  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
  }
  
  /**
   * Get list of positions with optional filtering
   */
  async getPositions(params?: {
    status?: string
    symbol?: string
    limit?: number
    offset?: number
  }): Promise<Position[]> {
    const searchParams = new URLSearchParams()
    
    if (params?.status) searchParams.append('status', params.status)
    if (params?.symbol) searchParams.append('symbol', params.symbol)
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.offset) searchParams.append('offset', params.offset.toString())
    
    const url = `${this.baseUrl}/positions?${searchParams.toString()}`
    const response = await fetch(url)
    
    return handleResponse<Position[]>(response)
  }
  
  /**
   * Create a new position
   */
  async createPosition(positionData: CreatePositionRequest): Promise<Position> {
    const response = await fetch(`${this.baseUrl}/positions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(positionData),
    })
    
    return handleResponse<Position>(response)
  }
  
  /**
   * Get a specific position by ID
   */
  async getPosition(positionId: number): Promise<Position> {
    const response = await fetch(`${this.baseUrl}/positions/${positionId}`)
    return handleResponse<Position>(response)
  }
  
  /**
   * Update a position's management parameters
   */
  async updatePosition(positionId: number, updateData: UpdatePositionRequest): Promise<Position> {
    const response = await fetch(`${this.baseUrl}/positions/${positionId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updateData),
    })
    
    return handleResponse<Position>(response)
  }
  
  /**
   * Close an open position
   */
  async closePosition(positionId: number, closeData: ClosePositionRequest): Promise<Position> {
    const response = await fetch(`${this.baseUrl}/positions/${positionId}/close`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(closeData),
    })
    
    return handleResponse<Position>(response)
  }
  
  /**
   * Get current P/L calculation for a position
   */
  async getCurrentPL(positionId: number): Promise<CurrentPL> {
    const response = await fetch(`${this.baseUrl}/positions/${positionId}/pl/current`)
    return handleResponse<CurrentPL>(response)
  }
  
  /**
   * Get current portfolio P/L across all open positions
   */
  async getPortfolioPL(): Promise<PortfolioPL> {
    const response = await fetch(`${this.baseUrl}/positions/pl/portfolio`)
    return handleResponse<PortfolioPL>(response)
  }
  
  /**
   * Get historical P/L snapshots for a position
   */
  async getPositionSnapshots(positionId: number, params?: {
    limit?: number
    offset?: number
  }): Promise<PLSnapshot[]> {
    const searchParams = new URLSearchParams()
    
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.offset) searchParams.append('offset', params.offset.toString())
    
    const url = `${this.baseUrl}/positions/${positionId}/snapshots?${searchParams.toString()}`
    const response = await fetch(url)
    
    return handleResponse<PLSnapshot[]>(response)
  }
  
  /**
   * Get alerts for a position
   */
  async getPositionAlerts(positionId: number, params?: {
    acknowledged?: boolean
    limit?: number
    offset?: number
  }): Promise<Alert[]> {
    const searchParams = new URLSearchParams()
    
    if (params?.acknowledged !== undefined) {
      searchParams.append('acknowledged', params.acknowledged.toString())
    }
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.offset) searchParams.append('offset', params.offset.toString())
    
    const url = `${this.baseUrl}/positions/${positionId}/alerts?${searchParams.toString()}`
    const response = await fetch(url)
    
    return handleResponse<Alert[]>(response)
  }
  
  /**
   * Acknowledge an alert
   */
  async acknowledgeAlert(positionId: number, alertId: number): Promise<{ message: string }> {
    const response = await fetch(
      `${this.baseUrl}/positions/${positionId}/alerts/${alertId}/acknowledge`,
      {
        method: 'POST',
      }
    )
    
    return handleResponse<{ message: string }>(response)
  }
}

// Export a default instance
export const positionsApi = new PositionsApi()

// Export the error class for error handling
export { PositionsApiError }
