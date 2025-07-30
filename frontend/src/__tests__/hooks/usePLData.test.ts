import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { usePLData } from '../../hooks/usePLData'
import { apiClient } from '../../api/client'

// Mock the API client
vi.mock('../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
  },
}))

describe('usePLData', () => {
  const mockPLResponse = {
    positions: [
      {
        id: 1,
        symbol: 'SPY',
        unrealized_pl: 50.0,
        unrealized_pl_percent: 10.0,
        current_value: -200.0,
        stop_loss_alert: false,
      },
    ],
    total_unrealized_pl: 50.0,
    spy_price: 451.25,
    timestamp: '2025-07-30T10:30:00Z',
  }

  const mockPLHistoryResponse = [
    {
      id: 1,
      position_id: 1,
      snapshot_time: '2025-07-30T10:00:00Z',
      spy_price: 450.0,
      current_value: -220.0,
      unrealized_pl: 30.0,
      unrealized_pl_percent: 6.0,
    },
    {
      id: 2,
      position_id: 1,
      snapshot_time: '2025-07-30T10:15:00Z',
      spy_price: 451.0,
      current_value: -210.0,
      unrealized_pl: 40.0,
      unrealized_pl_percent: 8.0,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches current P/L data successfully', async () => {
    const mockApiClient = apiClient as any
    mockApiClient.get.mockResolvedValueOnce({ data: mockPLResponse })

    const { result } = renderHook(() => usePLData())

    expect(result.current.loading).toBe(true)
    expect(result.current.currentPL).toBeNull()

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.currentPL).toEqual(mockPLResponse)
    expect(result.current.error).toBeNull()
    expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/positions/pl/current')
  })

  it('handles API error when fetching current P/L', async () => {
    const mockApiClient = apiClient as any
    const errorMessage = 'Failed to fetch P/L data'
    mockApiClient.get.mockRejectedValueOnce(new Error(errorMessage))

    const { result } = renderHook(() => usePLData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.currentPL).toBeNull()
    expect(result.current.error).toBe(errorMessage)
  })

  it('fetches P/L history for a specific position', async () => {
    const mockApiClient = apiClient as any
    // Mock initial P/L call 
    mockApiClient.get.mockResolvedValueOnce({ data: mockPLResponse })
    // Mock history call
    mockApiClient.get.mockResolvedValueOnce({ data: mockPLHistoryResponse })

    const { result } = renderHook(() => usePLData())

    // Wait for initial load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Fetch history for position 1
    const history = await result.current.fetchPLHistory(1)
    expect(history).toEqual(mockPLHistoryResponse)

    expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/positions/1/pl/history')
  })

  it('handles error when fetching P/L history', async () => {
    const mockApiClient = apiClient as any
    // Mock initial P/L call to succeed
    mockApiClient.get.mockResolvedValueOnce({ data: mockPLResponse })
    // Mock history call to fail
    mockApiClient.get.mockRejectedValueOnce(new Error('History fetch failed'))

    const { result } = renderHook(() => usePLData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const historyPromise = result.current.fetchPLHistory(1)

    await expect(historyPromise).rejects.toThrow('History fetch failed')
  })

  it('refreshes current P/L data', async () => {
    const mockApiClient = apiClient as any
    // Mock initial P/L call
    mockApiClient.get.mockResolvedValueOnce({ data: mockPLResponse })

    const { result } = renderHook(() => usePLData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Mock refresh call with updated data
    mockApiClient.get.mockResolvedValueOnce({ data: { ...mockPLResponse, total_unrealized_pl: 75.0 } })

    await result.current.refresh()

    // Wait for the data to update
    await waitFor(() => {
      expect(result.current.currentPL?.total_unrealized_pl).toBe(75.0)
    })

    expect(mockApiClient.get).toHaveBeenCalledWith('/api/v1/positions/pl/current')
  })

  it('provides loading state during refresh', async () => {
    const mockApiClient = apiClient as any
    // Mock initial P/L call
    mockApiClient.get.mockResolvedValueOnce({ data: mockPLResponse })

    const { result } = renderHook(() => usePLData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Mock slow response for refresh
    mockApiClient.get.mockImplementationOnce(
      () => new Promise(resolve => setTimeout(() => resolve({ data: mockPLResponse }), 100))
    )

    const refreshPromise = result.current.refresh()
    
    // Should be loading during refresh (check immediately)
    await waitFor(() => {
      expect(result.current.loading).toBe(true)
    })

    await refreshPromise

    expect(result.current.loading).toBe(false)
  })

  it('calculates derived P/L metrics correctly', async () => {
    const mockApiClient = apiClient as any
    mockApiClient.get.mockResolvedValueOnce({ data: mockPLResponse })

    const { result } = renderHook(() => usePLData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const derived = result.current.getDerivedMetrics()

    expect(derived).toEqual({
      hasPositions: true,
      totalPositions: 1,
      profitablePositions: 1,
      alertPositions: 0,
      maxUnrealizedPL: 50.0,
      minUnrealizedPL: 50.0,
      avgUnrealizedPL: 50.0,
    })
  })

  it('handles empty positions correctly', async () => {
    const emptyResponse = {
      positions: [],
      total_unrealized_pl: 0.0,
      spy_price: 451.25,
      timestamp: '2025-07-30T10:30:00Z',
    }

    const mockApiClient = apiClient as any
    mockApiClient.get.mockResolvedValueOnce({ data: emptyResponse })

    const { result } = renderHook(() => usePLData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const derived = result.current.getDerivedMetrics()

    expect(derived).toEqual({
      hasPositions: false,
      totalPositions: 0,
      profitablePositions: 0,
      alertPositions: 0,
      maxUnrealizedPL: 0,
      minUnrealizedPL: 0,
      avgUnrealizedPL: 0,
    })
  })

  it('identifies stop-loss alerts correctly', async () => {
    const alertResponse = {
      positions: [
        {
          id: 1,
          symbol: 'SPY',
          unrealized_pl: -100.0,
          unrealized_pl_percent: -20.0,
          current_value: -350.0,
          stop_loss_alert: true,
        },
        {
          id: 2,
          symbol: 'SPY',
          unrealized_pl: 25.0,
          unrealized_pl_percent: 5.0,
          current_value: -125.0,
          stop_loss_alert: false,
        },
      ],
      total_unrealized_pl: -75.0,
      spy_price: 448.75,
      timestamp: '2025-07-30T10:30:00Z',
    }

    const mockApiClient = apiClient as any
    mockApiClient.get.mockResolvedValueOnce({ data: alertResponse })

    const { result } = renderHook(() => usePLData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const derived = result.current.getDerivedMetrics()

    expect(derived.alertPositions).toBe(1)
    expect(derived.profitablePositions).toBe(1)
    expect(derived.totalPositions).toBe(2)
  })
})