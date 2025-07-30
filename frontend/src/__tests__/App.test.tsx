import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import App from '../App'

// Mock the API client with methods that match the actual implementation
vi.mock('../api/client', () => ({
  apiClient: {
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003',
    health: vi.fn().mockResolvedValue({ status: 'healthy' }),
    getQuote: vi.fn().mockResolvedValue({
      ticker: 'SPY',
      price: 580.5,
      change_percent: 0.5,
      bid: 580.45,
      ask: 580.55,
      volume: 1000000,
      timestamp: new Date().toISOString(),
      cached: false,
    }),
    getOptions: vi.fn().mockResolvedValue({
      ticker: 'SPY',
      underlying_price: 580.5,
      expiration: new Date().toISOString().split('T')[0],
      options: [
        {
          symbol: 'SPY250101C00580000',
          type: 'call',
          strike: 580,
          expiration_date: new Date().toISOString().split('T')[0],
          bid: 2.5,
          ask: 2.55,
          mid: 2.525,
          volume: 100,
          open_interest: 500,
        },
      ],
      cached: false,
      timestamp: new Date().toISOString(),
    }),
    getMarketStatus: vi.fn().mockResolvedValue({
      market_status: 'open',
      session: 'regular',
      api_status: 'connected',
      rate_limit_remaining: 5000,
      rate_limit_reset: new Date().toISOString(),
    }),
  },
}))

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', async () => {
    await act(async () => {
      render(<App />)
    })

    // Should render dashboard container
    const dashboardContainer = document.querySelector('.min-h-screen')
    expect(dashboardContainer).toBeTruthy()
  })

  it('displays dashboard components after loading', async () => {
    await act(async () => {
      render(<App />)
    })

    // Wait for the dashboard to load and API calls to complete
    await waitFor(
      () => {
        // Look for SPY price display in the market status bar
        const spyText = screen.getByText(/SPY:/)
        expect(spyText).toBeInTheDocument()
      },
      { timeout: 3000 }
    )

    // Should show the price value
    await waitFor(() => {
      expect(screen.getByText('$580.50')).toBeInTheDocument()
    })
  })
})
