import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '../api/client'

interface PLPosition {
  id: number
  symbol: string
  unrealized_pl: number
  unrealized_pl_percent: number
  current_value: number
  stop_loss_alert: boolean
}

interface PLResponse {
  positions: PLPosition[]
  total_unrealized_pl: number
  spy_price: number
  timestamp: string
}

interface PLHistoryEntry {
  id: number
  position_id: number
  snapshot_time: string
  spy_price: number
  current_value: number
  unrealized_pl: number
  unrealized_pl_percent: number
}

interface DerivedMetrics {
  hasPositions: boolean
  totalPositions: number
  profitablePositions: number
  alertPositions: number
  maxUnrealizedPL: number
  minUnrealizedPL: number
  avgUnrealizedPL: number
}

interface UsePLDataReturn {
  currentPL: PLResponse | null
  loading: boolean
  error: string | null
  fetchPLHistory: (positionId: number) => Promise<PLHistoryEntry[]>
  refresh: () => Promise<void>
  getDerivedMetrics: () => DerivedMetrics
}

export const usePLData = (): UsePLDataReturn => {
  const [currentPL, setCurrentPL] = useState<PLResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchCurrentPL = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await apiClient.get('/api/v1/positions/pl/current')
      setCurrentPL(response.data)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      setCurrentPL(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchPLHistory = useCallback(async (positionId: number): Promise<PLHistoryEntry[]> => {
    try {
      const response = await apiClient.get(`/api/v1/positions/${positionId}/pl/history`)
      return response?.data || response
    } catch (err) {
      throw err
    }
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    await fetchCurrentPL()
  }, [fetchCurrentPL])

  const getDerivedMetrics = useCallback((): DerivedMetrics => {
    if (!currentPL || currentPL.positions.length === 0) {
      return {
        hasPositions: false,
        totalPositions: 0,
        profitablePositions: 0,
        alertPositions: 0,
        maxUnrealizedPL: 0,
        minUnrealizedPL: 0,
        avgUnrealizedPL: 0,
      }
    }

    const positions = currentPL.positions
    const unrealizedPLValues = positions.map(p => p.unrealized_pl)
    
    return {
      hasPositions: true,
      totalPositions: positions.length,
      profitablePositions: positions.filter(p => p.unrealized_pl > 0).length,
      alertPositions: positions.filter(p => p.stop_loss_alert).length,
      maxUnrealizedPL: Math.max(...unrealizedPLValues),
      minUnrealizedPL: Math.min(...unrealizedPLValues),
      avgUnrealizedPL: unrealizedPLValues.reduce((sum, val) => sum + val, 0) / positions.length,
    }
  }, [currentPL])

  // Fetch initial data on mount
  useEffect(() => {
    fetchCurrentPL()
  }, [fetchCurrentPL])

  return {
    currentPL,
    loading,
    error,
    fetchPLHistory,
    refresh,
    getDerivedMetrics,
  }
}