import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import App from '../App'

// Mock the API client
vi.mock('../api/client', () => ({
  apiClient: {
    getHealth: vi.fn().mockResolvedValue({ status: 'healthy' }),
    getQuote: vi.fn().mockResolvedValue({
      symbol: 'SPY',
      price: 580.50,
      change: 2.35,
      changePercent: 0.41
    }),
    getSentiment: vi.fn().mockResolvedValue({
      score: 75,
      decision: 'PROCEED',
      components: {
        vix: { score: 70, value: 18.5 },
        futures: { score: 80, value: 0.25 }
      }
    }),
    getOptions: vi.fn().mockResolvedValue([])
  }
}))

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', () => {
    render(<App />)
    expect(screen.getByText('Loading dashboard...')).toBeInTheDocument()
  })

  it('displays dashboard components after loading', async () => {
    render(<App />)
    
    // Wait for the dashboard to load
    await waitFor(() => {
      expect(screen.queryByText('Loading dashboard...')).not.toBeInTheDocument()
    }, { timeout: 2000 })

    // Should show the market status bar
    await waitFor(() => {
      expect(screen.getByText('SPY')).toBeInTheDocument()
    })
  })
})