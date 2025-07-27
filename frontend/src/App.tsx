import { useEffect, useState } from 'react'
import { StatusIndicator } from './components/StatusIndicator'
import { apiClient } from './api/client'

type ConnectionStatus = 'loading' | 'connected' | 'disconnected' | 'error'

function App() {
  const [status, setStatus] = useState<ConnectionStatus>('loading')
  const [error, setError] = useState<string>('')
  const [apiInfo, setApiInfo] = useState<{
    version: string
    environment: string
  } | null>(null)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await apiClient.health()
        setStatus('connected')
        setApiInfo({
          version: response.version,
          environment: response.environment
        })
        setError('')
      } catch (err) {
        setStatus('error')
        setError(err instanceof Error ? err.message : 'Unknown error')
      }
    }

    checkHealth()
    
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000)
    
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 dark:text-white mb-4">
            SPY-FLY Trading Automation
          </h1>
          <StatusIndicator status={status} error={error} />
        </header>

        <main className="space-y-6">
          <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">
              System Information
            </h2>
            
            {apiInfo && (
              <div className="space-y-2 text-slate-600 dark:text-slate-300">
                <p>
                  <span className="font-medium">Version:</span> {apiInfo.version}
                </p>
                <p>
                  <span className="font-medium">Environment:</span> {apiInfo.environment}
                </p>
              </div>
            )}
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">
              Quick Start
            </h2>
            <p className="text-slate-600 dark:text-slate-300">
              The SPY-FLY trading automation system is now set up and running. 
              Both the FastAPI backend and React frontend are connected and ready for development.
            </p>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App