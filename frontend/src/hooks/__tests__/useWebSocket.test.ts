/**
 * Tests for the useWebSocket hook.
 * 
 * Tests WebSocket connection, reconnection, message handling, and error scenarios.
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useWebSocket, PriceUpdate, ConnectionStatus } from '../useWebSocket'

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = []
  
  public readyState: number = WebSocket.CONNECTING
  public onopen: ((event: Event) => void) | null = null
  public onclose: ((event: CloseEvent) => void) | null = null
  public onerror: ((event: Event) => void) | null = null
  public onmessage: ((event: MessageEvent) => void) | null = null
  
  public sentMessages: string[] = []
  public closed = false
  public closeCode: number | null = null
  
  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }
  
  send(data: string) {
    if (this.readyState === WebSocket.OPEN) {
      this.sentMessages.push(data)
    }
  }
  
  close(code?: number, reason?: string) {
    this.closed = true
    this.closeCode = code || 1000
    this.readyState = WebSocket.CLOSED
    
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code: code || 1000, reason }))
    }
  }
  
  // Test helpers
  simulateOpen() {
    this.readyState = WebSocket.OPEN
    if (this.onopen) {
      this.onopen(new Event('open'))
    }
  }
  
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { 
        data: JSON.stringify(data) 
      }))
    }
  }
  
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'))
    }
  }
  
  static getLastInstance(): MockWebSocket | undefined {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1]
  }
  
  static clear() {
    MockWebSocket.instances = []
  }
}

// Mock useToast hook
const mockToast = {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
  warning: vi.fn()
}

vi.mock('../useToast', () => ({
  useToast: () => ({ toast: mockToast })
}))

// Setup WebSocket mock
Object.defineProperty(global, 'WebSocket', {
  writable: true,
  value: MockWebSocket
})

describe('useWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.clear()
    vi.clearAllMocks()
    vi.useFakeTimers()
  })
  
  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })
  
  it('should connect automatically by default', () => {
    const { result } = renderHook(() => useWebSocket())
    
    expect(MockWebSocket.instances).toHaveLength(1)
    expect(result.current.isConnecting).toBe(true)
    expect(result.current.isConnected).toBe(false)
  })
  
  it('should not connect automatically when autoConnect is false', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))
    
    expect(MockWebSocket.instances).toHaveLength(0)
    expect(result.current.isConnecting).toBe(false)
    expect(result.current.isConnected).toBe(false)
  })
  
  it('should handle successful connection', async () => {
    const { result } = renderHook(() => useWebSocket())
    
    const ws = MockWebSocket.getLastInstance()!
    
    act(() => {
      ws.simulateOpen()
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
      expect(result.current.isConnecting).toBe(false)
      expect(result.current.connectionError).toBeNull()
    })
  })
  
  it('should handle price update messages', async () => {
    const { result } = renderHook(() => useWebSocket())
    
    const ws = MockWebSocket.getLastInstance()!
    
    // Connect first
    act(() => {
      ws.simulateOpen()
    })
    
    const priceUpdate: PriceUpdate = {
      type: 'price_update',
      ticker: 'SPY',
      price: 450.75,
      bid: 450.70,
      ask: 450.80,
      volume: 1000000,
      change: 2.25,
      change_percent: 0.50,
      market_status: 'open',
      timestamp: '2025-01-30T10:30:00Z',
      cached: false
    }
    
    act(() => {
      ws.simulateMessage(priceUpdate)
    })
    
    await waitFor(() => {
      expect(result.current.latestPrice).toEqual(priceUpdate)
    })
  })
  
  it('should handle connection status messages', async () => {
    const { result } = renderHook(() => useWebSocket())
    
    const ws = MockWebSocket.getLastInstance()!
    
    act(() => {
      ws.simulateOpen()
    })
    
    const connectionStatus: ConnectionStatus = {
      type: 'connection_status',
      status: 'connected',
      message: 'Successfully connected',
      timestamp: '2025-01-30T10:30:00Z'
    }
    
    act(() => {
      ws.simulateMessage(connectionStatus)
    })
    
    await waitFor(() => {
      expect(result.current.connectionInfo).toEqual(connectionStatus)
      expect(mockToast.success).toHaveBeenCalledWith('Connected to real-time price feed')
    })
  })
  
  it('should handle connection errors', async () => {
    const { result } = renderHook(() => useWebSocket())
    
    const ws = MockWebSocket.getLastInstance()!
    
    act(() => {
      ws.simulateError()
    })
    
    await waitFor(() => {
      expect(result.current.connectionError).toBe('WebSocket connection error')
      expect(result.current.isConnecting).toBe(false)
      expect(mockToast.error).toHaveBeenCalledWith('Connection error - attempting to reconnect...')
    })
  })
  
  it('should attempt reconnection on unexpected close', async () => {
    const { result } = renderHook(() => useWebSocket({
      reconnectAttempts: 2,
      reconnectInterval: 1000
    }))
    
    let ws = MockWebSocket.getLastInstance()!
    
    // Connect first
    act(() => {
      ws.simulateOpen()
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    // Simulate unexpected disconnection (not code 1000)
    act(() => {
      ws.close(1006, 'Connection lost')
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false)
    })
    
    // Advance timers to trigger reconnection
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    
    // Should create new WebSocket instance
    expect(MockWebSocket.instances).toHaveLength(2)
  })
  
  it('should send heartbeat pings', async () => {
    const { result } = renderHook(() => useWebSocket({
      heartbeatInterval: 1000
    }))
    
    const ws = MockWebSocket.getLastInstance()!
    
    act(() => {
      ws.simulateOpen()
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    // Advance time to trigger heartbeat
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    
    expect(ws.sentMessages).toContain(JSON.stringify({ type: 'ping' }))
  })
  
  it('should send messages when connected', async () => {
    const { result } = renderHook(() => useWebSocket())
    
    const ws = MockWebSocket.getLastInstance()!
    
    act(() => {
      ws.simulateOpen()
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    const testMessage = { type: 'test', data: 'hello' }
    
    act(() => {
      result.current.sendMessage(testMessage)
    })
    
    expect(ws.sentMessages).toContain(JSON.stringify(testMessage))
  })
  
  it('should not send messages when disconnected', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))
    
    const testMessage = { type: 'test' }
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    
    act(() => {
      result.current.sendMessage(testMessage)
    })
    
    expect(consoleSpy).toHaveBeenCalledWith(
      'WebSocket not connected - cannot send message:',
      testMessage
    )
    
    consoleSpy.mockRestore()
  })
  
  it('should manually connect and disconnect', async () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))
    
    expect(result.current.isConnected).toBe(false)
    
    // Manual connect
    act(() => {
      result.current.connect()
    })
    
    expect(MockWebSocket.instances).toHaveLength(1)
    expect(result.current.isConnecting).toBe(true)
    
    const ws = MockWebSocket.getLastInstance()!
    
    act(() => {
      ws.simulateOpen()
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    // Manual disconnect
    act(() => {
      result.current.disconnect()
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false)
      expect(ws.closed).toBe(true)
      expect(ws.closeCode).toBe(1000)
    })
  })
  
  it('should track reconnection attempts', async () => {
    const { result } = renderHook(() => useWebSocket({
      reconnectAttempts: 3,
      reconnectInterval: 500
    }))
    
    const ws = MockWebSocket.getLastInstance()!
    
    // Connect and then disconnect unexpectedly
    act(() => {
      ws.simulateOpen()
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    act(() => {
      ws.close(1006) // Unexpected close
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false)
    })
    
    // Trigger first reconnection attempt
    act(() => {
      vi.advanceTimersByTime(500)
    })
    
    expect(result.current.reconnectAttempts).toBe(1)
    expect(MockWebSocket.instances).toHaveLength(2)
  })
  
  it('should stop reconnecting after max attempts', async () => {
    const { result } = renderHook(() => useWebSocket({
      reconnectAttempts: 2,
      reconnectInterval: 100
    }))
    
    let ws = MockWebSocket.getLastInstance()!
    
    // Connect and close unexpectedly multiple times
    act(() => {
      ws.simulateOpen()
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
    
    // Close and reconnect twice (hitting the limit)
    for (let i = 0; i < 2; i++) {
      act(() => {
        ws.close(1006)
      })
      
      await waitFor(() => {
        expect(result.current.isConnected).toBe(false)
      })
      
      act(() => {
        vi.advanceTimersByTime(100)
      })
      
      ws = MockWebSocket.getLastInstance()!
      
      act(() => {
        ws.simulateOpen()
      })
      
      await waitFor(() => {
        expect(result.current.isConnected).toBe(true)
      })
    }
    
    // Final close should not trigger more reconnection
    act(() => {
      ws.close(1006)
    })
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(false)
    })
    
    const instanceCount = MockWebSocket.instances.length
    
    // Advance time - should not create new instance
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    
    expect(MockWebSocket.instances).toHaveLength(instanceCount)
    expect(mockToast.error).toHaveBeenCalledWith(
      'Lost connection to price feed - please refresh to reconnect'
    )
  })
  
  it('should cleanup on unmount', () => {
    const { result, unmount } = renderHook(() => useWebSocket())
    
    const ws = MockWebSocket.getLastInstance()!
    
    act(() => {
      ws.simulateOpen()
    })
    
    unmount()
    
    expect(ws.closed).toBe(true)
  })
  
  it('should use custom WebSocket URL', () => {
    const customUrl = 'ws://localhost:9000/custom'
    
    renderHook(() => useWebSocket({ url: customUrl }))
    
    const ws = MockWebSocket.getLastInstance()!
    expect(ws.url).toBe(customUrl)
  })
  
  it('should handle malformed JSON messages', async () => {
    const { result } = renderHook(() => useWebSocket())
    
    const ws = MockWebSocket.getLastInstance()!
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    
    act(() => {
      ws.simulateOpen()
    })
    
    // Send malformed JSON
    act(() => {
      if (ws.onmessage) {
        ws.onmessage(new MessageEvent('message', { data: 'invalid json' }))
      }
    })
    
    expect(consoleSpy).toHaveBeenCalledWith(
      'Failed to parse WebSocket message:',
      expect.any(Error)
    )
    
    // Should not crash the hook
    expect(result.current.isConnected).toBe(true)
    
    consoleSpy.mockRestore()
  })
})