import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import TradeHistoryTable from '../../components/TradeHistoryTable'
import { apiClient } from '../../api/client'

// Mock the API client
vi.mock('../../api/client', () => ({
  apiClient: {
    listTrades: vi.fn()
  }
}))

describe('TradeHistoryTable', () => {
  const mockTradeData = {
    items: [
      {
        id: 1,
        trade_date: '2025-01-28',
        trade_type: 'paper',
        status: 'exited',
        entry_time: '2025-01-28T10:30:00',
        contracts: 5,
        net_pnl: '150.00',
        pnl_percentage: '30.00',
        notes: 'Test trade 1',
        spread: {
          long_strike: 570,
          short_strike: 575,
          net_debit: 1.00
        }
      },
      {
        id: 2,
        trade_date: '2025-01-27',
        trade_type: 'real',
        status: 'entered',
        entry_time: '2025-01-27T09:45:00',
        contracts: 3,
        net_pnl: null,
        pnl_percentage: null,
        notes: null,
        spread: {
          long_strike: 565,
          short_strike: 570,
          net_debit: 1.50
        }
      }
    ],
    total: 2,
    page: 1,
    per_page: 20,
    pages: 1
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders trade history table', async () => {
    vi.mocked(apiClient.listTrades).mockResolvedValueOnce(mockTradeData)

    render(<TradeHistoryTable />)

    expect(screen.getByText('Trade History')).toBeInTheDocument()
    expect(screen.getByText('Loading trades...')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.queryByText('Loading trades...')).not.toBeInTheDocument()
    })
  })

  it('displays trades correctly', async () => {
    vi.mocked(apiClient.listTrades).mockResolvedValueOnce(mockTradeData)

    render(<TradeHistoryTable />)

    await waitFor(() => {
      expect(screen.getByText('Test trade 1')).toBeInTheDocument()
      expect(screen.getByText('570/575C')).toBeInTheDocument()
      expect(screen.getByText('565/570C')).toBeInTheDocument()
      // Use getAllByText since $150.00 appears multiple times
      const pnlElements = screen.getAllByText('$150.00')
      expect(pnlElements.length).toBeGreaterThan(0)
      expect(screen.getByText('30.00%')).toBeInTheDocument()
    })
  })

  it('handles empty trade list', async () => {
    vi.mocked(apiClient.listTrades).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      per_page: 20,
      pages: 0
    })

    render(<TradeHistoryTable />)

    await waitFor(() => {
      expect(screen.getByText('No trades found')).toBeInTheDocument()
    })
  })

  it('handles API errors', async () => {
    vi.mocked(apiClient.listTrades).mockRejectedValueOnce(
      new Error('Failed to fetch trades')
    )

    render(<TradeHistoryTable />)

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch trades')).toBeInTheDocument()
    })
  })

  it('filters trades by status', async () => {
    vi.mocked(apiClient.listTrades).mockResolvedValueOnce(mockTradeData)

    render(<TradeHistoryTable />)

    await waitFor(() => {
      expect(screen.queryByText('Loading trades...')).not.toBeInTheDocument()
    })

    // Select status filter - use the first select element (status filter)
    const selects = screen.getAllByRole('combobox')
    const statusFilter = selects[0] // First select is the status filter
    fireEvent.change(statusFilter, { target: { value: 'exited' } })

    // Verify API was called with correct filter
    await waitFor(() => {
      expect(apiClient.listTrades).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'exited'
        })
      )
    })
  })

  it('refreshes on trigger change', async () => {
    vi.mocked(apiClient.listTrades).mockResolvedValue(mockTradeData)

    const { rerender } = render(<TradeHistoryTable refreshTrigger={0} />)

    await waitFor(() => {
      expect(apiClient.listTrades).toHaveBeenCalledTimes(1)
    })

    // Trigger refresh
    rerender(<TradeHistoryTable refreshTrigger={1} />)

    await waitFor(() => {
      expect(apiClient.listTrades).toHaveBeenCalledTimes(2)
    })
  })

  it('displays summary statistics', async () => {
    vi.mocked(apiClient.listTrades).mockResolvedValueOnce(mockTradeData)

    render(<TradeHistoryTable />)

    await waitFor(() => {
      expect(screen.getByText('Total Trades')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument() // Total trades count
      
      expect(screen.getByText('Win Rate')).toBeInTheDocument()
      expect(screen.getByText('100.0%')).toBeInTheDocument() // 1 winning trade out of 1 exited
      
      expect(screen.getByText('Total P/L')).toBeInTheDocument()
      // Use getAllByText since $150.00 appears multiple times in the summary
      const totalPnlElements = screen.getAllByText('$150.00')
      expect(totalPnlElements.length).toBeGreaterThan(0)
    })
  })
})