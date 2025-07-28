// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003'

// WebSocket URL for real-time updates (future enhancement)
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8003'

// Update intervals (in milliseconds)
export const UPDATE_INTERVALS = {
  sentiment: 30000, // 30 seconds
  marketData: 30000, // 30 seconds
  positions: 5000, // 5 seconds
  sessionStatus: 60000, // 1 minute
}

// Trading configuration
export const TRADING_CONFIG = {
  defaultRiskAmount: 5000, // $5,000 default risk per trade
  maxRiskAmount: 10000, // $10,000 max risk per trade
  profitTargetPercent: 50, // 50% profit target
  stopLossPercent: 30, // 30% stop loss
  sentimentThreshold: 60, // Minimum sentiment score to trade
}
