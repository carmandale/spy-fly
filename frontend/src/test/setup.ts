import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Set up environment variables for tests
Object.defineProperty(import.meta, 'env', {
  value: {
      VITE_API_BASE_URL: process.env.VITE_API_BASE_URL || 'http://localhost:8003',
  VITE_WS_BASE_URL: process.env.VITE_WS_BASE_URL || 'ws://localhost:8003',
    ...import.meta.env,
  },
  configurable: true,
})

// Mock fetch for API calls
global.fetch = vi.fn()

// Default fetch mock implementation
;(global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
  // Mock API responses based on URL
  if (url.includes('/api/v1/sentiment/calculate')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          score: 75,
          decision: 'PROCEED',
          breakdown: {
            vix: { score: 70, value: 15.2 },
            futures: { score: 80, value: 0.5 },
            rsi: { score: 75, value: 45 },
            ma50: { score: 70, value: 'above' },
            bollinger: { score: 80, value: 'middle' },
            news: { score: 65, value: 'neutral' },
          },
          timestamp: new Date().toISOString(),
        }),
    })
  }

  if (url.includes('/api/v1/market/quote/SPY')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          ticker: 'SPY',
          price: 580.5,
          change_percent: 0.5,
          bid: 580.45,
          ask: 580.55,
          volume: 1000000,
          timestamp: new Date().toISOString(),
          cached: false,
        }),
    })
  }

  if (url.includes('/api/v1/market/options/SPY')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
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
    })
  }

  // Default fallback
  return Promise.resolve({
    ok: false,
    status: 404,
    statusText: 'Not Found',
    text: () => Promise.resolve('Not Found'),
  })
})

// macOS-specific optimizations for happy-dom
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver for better macOS compatibility
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock ResizeObserver for chart components
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock getBoundingClientRect for charts to have proper dimensions
Element.prototype.getBoundingClientRect = vi.fn(() => ({
  width: 400,
  height: 300,
  top: 0,
  left: 0,
  bottom: 300,
  right: 400,
  x: 0,
  y: 0,
  toJSON: vi.fn(),
}))
