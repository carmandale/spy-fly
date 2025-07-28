import React from 'react'

type Status = 'loading' | 'connected' | 'disconnected' | 'error'

interface StatusIndicatorProps {
  status: Status
  error?: string
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({ status, error }) => {
  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'text-green-600'
      case 'disconnected':
        return 'text-yellow-600'
      case 'error':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const getStatusText = () => {
    switch (status) {
      case 'loading':
        return 'Loading...'
      case 'connected':
        return 'Connected'
      case 'disconnected':
        return 'Disconnected'
      case 'error':
        return 'Error'
    }
  }

  return (
    <div className="flex items-center space-x-2">
      <div
        className={`h-3 w-3 rounded-full ${
          status === 'connected'
            ? 'bg-green-600'
            : status === 'disconnected'
              ? 'bg-yellow-600'
              : status === 'error'
                ? 'bg-red-600'
                : 'bg-gray-600'
        } ${status === 'loading' ? 'animate-pulse' : ''}`}
      />
      <span className={`font-medium ${getStatusColor()}`}>API Status: {getStatusText()}</span>
      {error && <span className="text-sm text-red-500">({error})</span>}
    </div>
  )
}
