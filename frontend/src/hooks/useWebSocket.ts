/**
 * Custom React hook for WebSocket connection to real-time price feeds.
 * 
 * Provides real-time SPY price updates with automatic reconnection,
 * connection state management, and error handling.
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useToast } from './useToast'

export interface PriceUpdate {
  type: 'price_update'
  ticker: string
  price: number
  bid?: number
  ask?: number
  volume?: number
  change?: number
  change_percent?: number
  market_status: string
  timestamp: string
  cached: boolean
}

export interface ConnectionStatus {
  type: 'connection_status'
  status: 'connected' | 'disconnected' | 'error'
  message: string
  timestamp: string
}

export type WebSocketMessage = PriceUpdate | ConnectionStatus

export interface UseWebSocketOptions {
  url?: string
  reconnectAttempts?: number
  reconnectInterval?: number
  heartbeatInterval?: number
  autoConnect?: boolean
}

export interface UseWebSocketReturn {
  // Connection state
  isConnected: boolean
  isConnecting: boolean
  connectionError: string | null
  
  // Latest data
  latestPrice: PriceUpdate | null
  connectionInfo: ConnectionStatus | null
  
  // Connection control
  connect: () => void
  disconnect: () => void
  sendMessage: (message: unknown) => void
  
  // Stats
  reconnectAttempts: number
  lastConnected: Date | null
}

const DEFAULT_OPTIONS: Required<UseWebSocketOptions> = {
  url: 'ws://localhost:8003/api/v1/ws/price-feed',
  reconnectAttempts: 5,
  reconnectInterval: 3000,
  heartbeatInterval: 30000,
  autoConnect: true
}

export const useWebSocket = (options: UseWebSocketOptions = {}): UseWebSocketReturn => {
  const config = { ...DEFAULT_OPTIONS, ...options }
  const { toast } = useToast()
  
  // Connection state
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [lastConnected, setLastConnected] = useState<Date | null>(null)
  
  // Latest data
  const [latestPrice, setLatestPrice] = useState<PriceUpdate | null>(null)
  const [connectionInfo, setConnectionInfo] = useState<ConnectionStatus | null>(null)
  
  // Refs for managing WebSocket and timers
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const heartbeatIntervalRef = useRef<NodeJS.Interval | null>(null)
  const mountedRef = useRef(true)
  
  // Clear all timers
  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = null
    }
  }, [])
  
  // Send heartbeat ping
  const sendHeartbeat = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }))
    }
  }, [])
  
  // Start heartbeat timer
  const startHeartbeat = useCallback(() => {
    clearTimers()
    heartbeatIntervalRef.current = setInterval(sendHeartbeat, config.heartbeatInterval)
  }, [sendHeartbeat, config.heartbeatInterval, clearTimers])
  
  // Handle incoming WebSocket messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      
      if (message.type === 'price_update') {
        setLatestPrice(message)
      } else if (message.type === 'connection_status') {
        setConnectionInfo(message)
        
        if (message.status === 'connected') {
          setConnectionError(null)
          setLastConnected(new Date())
          toast.success('Connected to real-time price feed')
        } else if (message.status === 'error') {
          setConnectionError(message.message)
          toast.error(`WebSocket error: ${message.message}`)
        }
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error)
    }
  }, [toast])
  
  // Handle WebSocket connection open
  const handleOpen = useCallback(() => {
    if (!mountedRef.current) return
    
    setIsConnected(true)
    setIsConnecting(false)
    setConnectionError(null)
    setReconnectAttempts(0)
    setLastConnected(new Date())
    startHeartbeat()
    
    console.log('WebSocket connected to real-time price feed')
  }, [startHeartbeat])
  
  // Handle WebSocket connection close
  const handleClose = useCallback((event: CloseEvent) => {
    if (!mountedRef.current) return
    
    setIsConnected(false)
    setIsConnecting(false)
    clearTimers()
    
    console.log('WebSocket disconnected:', event.code, event.reason)
    
    // Attempt reconnection if not manually closed
    if (event.code !== 1000 && reconnectAttempts < config.reconnectAttempts) {
      setReconnectAttempts(prev => prev + 1)
      
      reconnectTimeoutRef.current = setTimeout(() => {
        if (mountedRef.current) {
          console.log(`Attempting WebSocket reconnection (${reconnectAttempts + 1}/${config.reconnectAttempts})`)
          connect()
        }
      }, config.reconnectInterval)
    } else if (reconnectAttempts >= config.reconnectAttempts) {
      setConnectionError('Max reconnection attempts reached')
      toast.error('Lost connection to price feed - please refresh to reconnect')
    }
  }, [reconnectAttempts, config.reconnectAttempts, config.reconnectInterval, clearTimers, toast])
  
  // Handle WebSocket errors
  const handleError = useCallback((event: Event) => {
    console.error('WebSocket error:', event)
    setConnectionError('WebSocket connection error')
    setIsConnecting(false)
    
    if (mountedRef.current) {
      toast.error('Connection error - attempting to reconnect...')
    }
  }, [toast])
  
  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return // Already connected
    }
    
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close()
    }
    
    setIsConnecting(true)
    setConnectionError(null)
    
    try {
      wsRef.current = new WebSocket(config.url)
      
      wsRef.current.onopen = handleOpen
      wsRef.current.onclose = handleClose
      wsRef.current.onerror = handleError
      wsRef.current.onmessage = handleMessage
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setConnectionError('Failed to connect to price feed')
      setIsConnecting(false)
      
      if (mountedRef.current) {
        toast.error('Failed to connect to real-time feed')
      }
    }
  }, [config.url, handleOpen, handleClose, handleError, handleMessage, toast])
  
  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    clearTimers()
    setReconnectAttempts(config.reconnectAttempts) // Prevent auto-reconnect
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect')
      wsRef.current = null
    }
    
    setIsConnected(false)
    setIsConnecting(false)
  }, [clearTimers, config.reconnectAttempts])
  
  // Send message to WebSocket
  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket not connected - cannot send message:', message)
    }
  }, [])
  
  // Auto-connect on mount
  useEffect(() => {
    if (config.autoConnect) {
      connect()
    }
    
    return () => {
      mountedRef.current = false
      disconnect()
    }
  }, [config.autoConnect, connect, disconnect])
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false
      clearTimers()
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [clearTimers])
  
  return {
    // Connection state
    isConnected,
    isConnecting,
    connectionError,
    
    // Latest data
    latestPrice,
    connectionInfo,
    
    // Connection control
    connect,
    disconnect,
    sendMessage,
    
    // Stats
    reconnectAttempts,
    lastConnected
  }
}