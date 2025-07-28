import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient } from '../../api/client'

describe('API Client', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })

  it('should have correct base configuration', () => {
    expect(apiClient.baseURL).toBe(import.meta.env.VITE_API_BASE_URL || '')
  })

  it('should call health endpoint', async () => {
    const mockResponse = {
      status: 'healthy',
      timestamp: '2025-07-26T12:00:00Z',
      version: '0.1.0',
      environment: 'development',
    }

    ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const result = await apiClient.health()

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/health'),
      expect.any(Object)
    )
    expect(result).toEqual(mockResponse)
  })

  it('should handle errors gracefully', async () => {
    ;(global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network error'))

    await expect(apiClient.health()).rejects.toThrow('Network error')
  })
})
