import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from 'recharts'
import { TrendingUp, Clock, AlertCircle, RefreshCw, Activity } from 'lucide-react'
import { positionsApi, PositionsApiError } from '../services/positionsApi'
import type { PortfolioPL, Position } from '../services/positionsApi'
import type { PortfolioPLUpdate } from '../hooks/useWebSocket'
interface PLData {
  currentValue: number
  entryValue: number
  unrealizedPL: number
  unrealizedPLPercent: number
  timeDecay: number
  alertStatus: 'none' | 'profit-target' | 'stop-loss'
}
interface HistoricalData {
  equityCurve: Array<{
    date: string
    value: number
  }>
  winRate: number
  avgProfitLoss: number
}
interface LivePLMonitorPanelProps {
  portfolioPLUpdate?: PortfolioPLUpdate | null
}

const LivePLMonitorPanel: React.FC<LivePLMonitorPanelProps> = ({ portfolioPLUpdate }) => {
  const [portfolioData, setPortfolioData] = useState<PortfolioPL | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  
  // Load initial portfolio data
  const loadPortfolioData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const [portfolioPL, openPositions] = await Promise.all([
        positionsApi.getPortfolioPL(),
        positionsApi.getPositions({ status: 'open' })
      ])
      
      setPortfolioData(portfolioPL)
      setPositions(openPositions)
      setLastUpdated(new Date())
      
    } catch (err) {
      console.error('Error loading portfolio data:', err)
      if (err instanceof PositionsApiError) {
        setError(`Failed to load portfolio data: ${err.message}`)
      } else {
        setError('Failed to load portfolio data')
      }
    } finally {
      setLoading(false)
    }
  }
  
  // Load data on component mount
  useEffect(() => {
    loadPortfolioData()
  }, [])
  
  // Update data when WebSocket portfolio update arrives
  useEffect(() => {
    if (portfolioPLUpdate) {
      setPortfolioData({
        total_positions: portfolioPLUpdate.total_positions,
        total_unrealized_pnl: portfolioPLUpdate.total_unrealized_pnl,
        total_unrealized_pnl_percent: portfolioPLUpdate.total_unrealized_pnl_percent,
        total_daily_theta: portfolioPLUpdate.total_daily_theta,
        current_spy_price: portfolioPLUpdate.current_spy_price,
        calculation_timestamp: portfolioPLUpdate.timestamp,
        positions: portfolioPLUpdate.positions.map(pos => ({
          position_id: pos.position_id,
          symbol: pos.symbol,
          contracts: pos.contracts,
          current_spy_price: portfolioPLUpdate.current_spy_price,
          time_to_expiry_hours: 0, // This would need to be calculated
          current_long_premium: 0, // These would come from the detailed calculation
          current_short_premium: 0,
          current_net_value: pos.current_total_value - pos.entry_total_cost,
          current_total_value: pos.current_total_value,
          entry_total_cost: pos.entry_total_cost,
          unrealized_pnl: pos.unrealized_pnl,
          unrealized_pnl_percent: pos.unrealized_pnl_percent,
          position_delta: pos.position_delta,
          position_gamma: undefined,
          position_theta: pos.position_theta,
          position_vega: undefined,
          daily_theta_decay: pos.daily_theta_decay,
          alert_triggered: pos.alert_triggered,
          alert_type: pos.alert_type,
          alert_message: pos.alert_message,
          market_session: pos.market_session,
          calculation_timestamp: portfolioPLUpdate.timestamp,
          data_quality_score: 1.0
        }))
      })
      setLastUpdated(new Date())
    }
  }, [portfolioPLUpdate])
  
  // Generate historical data from positions (simplified)
  const generateHistoricalData = () => {
    if (!positions.length) {
      return { equityCurve: [], winRate: 0, avgProfitLoss: 0 }
    }
    
    const closedPositions = positions.filter(p => p.status === 'closed' && p.realized_pnl !== undefined)
    
    if (closedPositions.length === 0) {
      return { equityCurve: [], winRate: 0, avgProfitLoss: 0 }
    }
    
    const winningTrades = closedPositions.filter(p => (p.realized_pnl || 0) > 0)
    const winRate = (winningTrades.length / closedPositions.length) * 100
    const avgProfitLoss = closedPositions.reduce((sum, p) => sum + (p.realized_pnl || 0), 0) / closedPositions.length
    
    // Generate simple equity curve (last 30 days)
    const equityCurve = Array.from({ length: 30 }, (_, i) => ({
      date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      value: Math.random() * 1000 + 5000 // Placeholder data
    }))
    
    return { equityCurve, winRate, avgProfitLoss }
  }
  
  const historicalData = generateHistoricalData()
  const getPLColor = (value: number) => {
    return value >= 0 ? 'text-green-400' : 'text-red-400'
  }
  const getAlertIcon = (hasAlerts: boolean) => {
    if (!hasAlerts) return null
    
    return (
      <AlertCircle
        className="w-5 h-5 text-yellow-400 animate-pulse"
        aria-label="Position alerts active"
      />
    )
  }
  
  const getConnectionIcon = () => {
    if (loading) {
      return <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
    }
    
    if (portfolioPLUpdate) {
      return <Activity className="w-4 h-4 text-green-400" />
    }
    
    return <Clock className="w-4 h-4 text-gray-400" />
  }
  
  // Handle loading state
  if (loading && !portfolioData) {
    return (
      <div className="space-y-6">
        <motion.section
          className="bg-gray-800 border border-gray-700 rounded-lg p-6"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.3 }}
        >
          <div className="flex items-center justify-center h-32">
            <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
            <span className="ml-2 text-gray-400">Loading portfolio data...</span>
          </div>
        </motion.section>
      </div>
    )
  }
  
  // Handle error state
  if (error && !portfolioData) {
    return (
      <div className="space-y-6">
        <motion.section
          className="bg-gray-800 border border-gray-700 rounded-lg p-6"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.3 }}
        >
          <div className="flex items-center justify-center h-32 text-center">
            <div>
              <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
              <p className="text-red-400 mb-2">{error}</p>
              <button
                onClick={loadPortfolioData}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </motion.section>
      </div>
    )
  }
  
  // Use portfolio data or fallback to zero values
  const currentPL = portfolioData?.total_unrealized_pnl || 0
  const currentPLPercent = portfolioData?.total_unrealized_pnl_percent || 0
  const totalPositions = portfolioData?.total_positions || 0
  const totalTheta = portfolioData?.total_daily_theta || 0
  const hasAlerts = portfolioData?.positions.some(p => p.alert_triggered) || false
  
  const plBarWidth = Math.min(Math.abs(currentPLPercent), 100)
  return (
    <div className="space-y-6">
      {/* Live P/L Monitor */}
      <motion.section
        className="bg-gray-800 border border-gray-700 rounded-lg p-6"
        initial={{
          opacity: 0,
          scale: 0.95,
        }}
        animate={{
          opacity: 1,
          scale: 1,
        }}
        transition={{
          duration: 0.4,
          delay: 0.3,
        }}
      >
        <header className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-bold text-white">Live P/L Monitor</h2>
            {getConnectionIcon()}
          </div>
          <div className="flex items-center space-x-2">
            {getAlertIcon(hasAlerts)}
            {lastUpdated && (
              <span className="text-xs text-gray-400">
                {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </div>
        </header>

        {/* Current P/L Display */}
        <div className="space-y-4">
          <div className="text-center">
            <div className={`text-3xl font-bold ${getPLColor(currentPL)}`}>
              <strong>
                {currentPL >= 0 ? '+' : ''}${currentPL.toFixed(0)}
              </strong>
            </div>
            <div className={`text-lg ${getPLColor(currentPLPercent)}`}>
              <strong>
                ({currentPLPercent >= 0 ? '+' : ''}
                {currentPLPercent.toFixed(2)}%)
              </strong>
            </div>
            {totalPositions > 0 && (
              <div className="text-sm text-gray-400 mt-1">
                {totalPositions} open position{totalPositions !== 1 ? 's' : ''}
              </div>
            )}
          </div>

          {/* P/L Progress Bar */}
          <div className="relative">
            <div
              className="w-full h-4 bg-gray-700 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={Math.abs(currentPLPercent)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`P/L percentage: ${currentPLPercent.toFixed(2)}%`}
            >
              <motion.div
                className={`h-full ${currentPL >= 0 ? 'bg-green-400' : 'bg-red-400'}`}
                initial={{
                  width: 0,
                }}
                animate={{
                  width: `${plBarWidth}%`,
                }}
                transition={{
                  duration: 0.5,
                }}
              />
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs font-bold text-white">
                {Math.abs(currentPLPercent).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Portfolio Details */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Total Entry Cost:</span>
              <div className="text-white font-bold">
                <strong>
                  ${portfolioData?.positions.reduce((sum, p) => sum + p.entry_total_cost, 0).toFixed(0) || '0'}
                </strong>
              </div>
            </div>
            <div>
              <span className="text-gray-400">Current Value:</span>
              <div className="text-white font-bold">
                <strong>
                  ${portfolioData?.positions.reduce((sum, p) => sum + p.current_total_value, 0).toFixed(0) || '0'}
                </strong>
              </div>
            </div>
          </div>

          {/* Time Decay */}
          <div className="flex items-center justify-between p-3 bg-gray-900 rounded">
            <div className="flex items-center space-x-2">
              <Clock className="w-4 h-4 text-yellow-400" aria-hidden="true" />
              <span className="text-gray-300 text-sm">Daily Theta Decay</span>
            </div>
            <strong className="text-red-400 font-bold">${Math.abs(totalTheta).toFixed(0)}</strong>
          </div>
          
          {/* Active Alerts */}
          {hasAlerts && (
            <div className="p-3 bg-yellow-900/20 border border-yellow-600/30 rounded">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-yellow-400" />
                <span className="text-yellow-400 text-sm font-medium">Active Alerts</span>
              </div>
              <div className="mt-2 space-y-1">
                {portfolioData?.positions
                  .filter(p => p.alert_triggered)
                  .map(p => (
                    <div key={p.position_id} className="text-xs text-yellow-300">
                      Position {p.position_id}: {p.alert_message}
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      </motion.section>

      {/* Historical Performance */}
      <motion.section
        className="bg-gray-800 border border-gray-700 rounded-lg p-6"
        initial={{
          opacity: 0,
          y: 20,
        }}
        animate={{
          opacity: 1,
          y: 0,
        }}
        transition={{
          duration: 0.4,
          delay: 0.4,
        }}
      >
        <h3 className="text-lg font-bold text-white mb-4">Historical Performance</h3>

        {/* Equity Curve */}
        <div className="h-32 mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={historicalData.equityCurve}>
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={false} />
              <YAxis hide />
              <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Performance Stats */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="text-center">
            <p className="text-gray-400 mb-1">Win Rate</p>
            <div className="text-green-400 font-bold text-lg">
              <strong>{historicalData.winRate.toFixed(1)}%</strong>
            </div>
          </div>
          <div className="text-center">
            <p className="text-gray-400 mb-1">Avg P/L</p>
            <div className={`font-bold text-lg ${getPLColor(historicalData.avgProfitLoss)}`}>
              <strong>${historicalData.avgProfitLoss.toFixed(0)}</strong>
            </div>
          </div>
        </div>
      </motion.section>
    </div>
  )
}
export default LivePLMonitorPanel
