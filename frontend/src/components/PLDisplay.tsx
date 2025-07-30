import React from 'react'
import LivePLMonitorPanel from './LivePLMonitorPanel'
import { usePLData } from '../hooks/usePLData'

interface PLDisplayProps {
  className?: string
}

// Transform API data format to LivePLMonitorPanel component format
const transformPLData = (apiData: any) => {
  if (!apiData || !apiData.positions || apiData.positions.length === 0) {
    return {
      currentValue: 0,
      entryValue: 0,
      unrealizedPL: 0,
      unrealizedPLPercent: 0,
      timeDecay: 0,
      alertStatus: 'none' as const,
    }
  }

  // For now, aggregate all positions for display
  const totalUnrealizedPL = apiData.total_unrealized_pl || 0
  const totalCurrentValue = apiData.positions.reduce((sum: number, pos: any) => sum + (pos.current_value || 0), 0)
  
  // Calculate entry value based on current value and P/L
  const totalEntryValue = totalCurrentValue - totalUnrealizedPL
  
  // Calculate percentage based on total risk (simplified for now)
  const totalUnrealizedPercent = totalEntryValue !== 0 ? (totalUnrealizedPL / Math.abs(totalEntryValue)) * 100 : 0
  
  // Check if any position has stop-loss alert
  const hasStopLossAlert = apiData.positions.some((pos: any) => pos.stop_loss_alert)
  
  // TODO: Time decay calculation (placeholder for now)
  const timeDecay = 0

  return {
    currentValue: totalCurrentValue,
    entryValue: totalEntryValue,
    unrealizedPL: totalUnrealizedPL,
    unrealizedPLPercent: totalUnrealizedPercent,
    timeDecay,
    alertStatus: hasStopLossAlert ? 'stop-loss' as const : 'none' as const,
  }
}

// Transform historical data (placeholder for now - will be enhanced in future tasks)
const transformHistoricalData = () => {
  // TODO: Implement historical data transformation when history API is available
  return {
    equityCurve: [],
    winRate: 0,
    avgProfitLoss: 0,
  }
}

const PLDisplay: React.FC<PLDisplayProps> = ({ className }) => {
  const { currentPL, loading, error } = usePLData()

  // Handle loading state
  if (loading) {
    return (
      <div className={`bg-gray-800 border border-gray-700 rounded-lg p-6 ${className || ''}`}>
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-400">Loading P/L data...</div>
        </div>
      </div>
    )
  }

  // Handle error state
  if (error) {
    return (
      <div className={`bg-gray-800 border border-gray-700 rounded-lg p-6 ${className || ''}`}>
        <div className="flex items-center justify-center h-64">
          <div className="text-red-400">Error loading P/L data: {error}</div>
        </div>
      </div>
    )
  }

  // Transform data for LivePLMonitorPanel
  const plData = transformPLData(currentPL)
  const historicalData = transformHistoricalData(currentPL)

  return (
    <LivePLMonitorPanel 
      plData={plData} 
      historicalData={historicalData}
    />
  )
}

export default PLDisplay