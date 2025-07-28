import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import MarketStatusBar from './MarketStatusBar'
import SentimentPanel from './SentimentPanel'
import RecommendedSpreadsPanel from './RecommendedSpreadsPanel'
import LivePLMonitorPanel from './LivePLMonitorPanel'
import { TradeManagementPanel } from './TradeManagementPanel'
import { apiClient } from '../api/client'

interface MarketData {
  spyPrice: number
  spyChange: number
  vix: number
  sessionStatus: 'pre-market' | 'open' | 'closed'
  timeToClose: string
  apiStatus: 'connected' | 'disconnected' | 'reconnecting'
}

interface SentimentData {
  overallScore: number
  decision: 'PROCEED' | 'SKIP'
  components: {
    vix: number
    futures: number
    technical: number
    news: number
  }
}

interface SpreadRecommendation {
  id: string
  longStrike: number
  shortStrike: number
  debit: number
  maxProfit: number
  maxLoss: number
  breakeven: number
  probability: number
  quantity: number
  expiration: string
}

interface PLData {
  currentValue: number
  entryValue: number
  unrealizedPL: number
  unrealizedPLPercent: number
  timeDecay: number
  alertStatus: 'none' | 'profit-target' | 'stop-loss'
}

interface HistoricalData {
  equityCurve: Array<{
    date: string
    value: number
  }>
  winRate: number
  avgProfitLoss: number
}

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'dashboard' | 'trades'>('dashboard')

  const [marketData, setMarketData] = useState<MarketData>({
    spyPrice: 0,
    spyChange: 0,
    vix: 0,
    sessionStatus: 'closed',
    timeToClose: '',
    apiStatus: 'disconnected',
  })

  const [sentimentData, setSentimentData] = useState<SentimentData>({
    overallScore: 0,
    decision: 'SKIP',
    components: {
      vix: 0,
      futures: 0,
      technical: 0,
      news: 0,
    },
  })

  const [spreadRecommendations, setSpreadRecommendations] = useState<SpreadRecommendation[]>([])

  const [plData] = useState<PLData>({
    currentValue: 0,
    entryValue: 0,
    unrealizedPL: 0,
    unrealizedPLPercent: 0,
    timeDecay: 0,
    alertStatus: 'none',
  })

  const [historicalData] = useState<HistoricalData>({
    equityCurve: [],
    winRate: 0,
    avgProfitLoss: 0,
  })

  // Fetch sentiment data
  const fetchSentiment = async () => {
    try {
      const response = await fetch(`${apiClient.baseURL}/api/v1/sentiment/calculate`)
      if (!response.ok) throw new Error('Failed to fetch sentiment')

      const data = await response.json()

      setSentimentData({
        overallScore: data.score,
        decision: data.decision,
        components: {
          vix: data.breakdown.vix.score,
          futures: data.breakdown.futures.score,
          technical:
            (data.breakdown.rsi.score +
              data.breakdown.ma50.score +
              data.breakdown.bollinger.score) /
            3,
          news: data.breakdown.news.score,
        },
      })

      setMarketData((prev) => ({
        ...prev,
        vix: data.breakdown.vix.value,
        apiStatus: 'connected',
      }))
    } catch (err) {
      console.error('Error fetching sentiment:', err)
      setMarketData((prev) => ({ ...prev, apiStatus: 'disconnected' }))
    }
  }

  // Fetch market quote
  const fetchMarketQuote = async () => {
    try {
      const data = await apiClient.getQuote('SPY')

      setMarketData((prev) => ({
        ...prev,
        spyPrice: data.price,
        spyChange: data.change_percent || 0,
      }))
    } catch (err) {
      console.error('Error fetching quote:', err)
    }
  }

  // Fetch options data for recommendations
  const fetchOptionsData = async () => {
    try {
      // Get today's date in YYYY-MM-DD format
      const today = new Date().toISOString().split('T')[0]
      const data = await apiClient.getOptions('SPY', today)

      // Filter for 0DTE calls
      const todayExpiration = new Date().toISOString().split('T')[0]
      const calls = data.options.filter(
        (opt: { type: string; expiration_date: string }) =>
          opt.type === 'call' && opt.expiration_date.startsWith(todayExpiration)
      )

      if (calls.length >= 2) {
        // Create a sample spread recommendation
        const longStrike = calls[0].strike_price
        const shortStrike = calls[1].strike_price
        const debit = calls[0].ask - calls[1].bid

        setSpreadRecommendations([
          {
            id: '1',
            longStrike,
            shortStrike,
            debit,
            maxProfit: (shortStrike - longStrike - debit) * 100,
            maxLoss: debit * 100,
            breakeven: longStrike + debit,
            probability: 0.42, // Placeholder
            quantity: Math.floor(5000 / (debit * 100)), // $5k risk
            expiration: '0DTE',
          },
        ])
      }
    } catch (err) {
      console.error('Error fetching options:', err)
    }
  }

  // Calculate market session and time to close
  const updateMarketSession = () => {
    const now = new Date()
    const hours = now.getHours()

    let sessionStatus: 'pre-market' | 'open' | 'closed' = 'closed'
    let timeToClose = ''

    if (hours >= 4 && hours < 9.5) {
      sessionStatus = 'pre-market'
    } else if (hours >= 9.5 && hours < 16) {
      sessionStatus = 'open'
      const closeTime = new Date()
      closeTime.setHours(16, 0, 0, 0)
      const diff = closeTime.getTime() - now.getTime()
      const hoursLeft = Math.floor(diff / (1000 * 60 * 60))
      const minutesLeft = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      timeToClose = `${hoursLeft}h ${minutesLeft}m`
    }

    setMarketData((prev) => ({ ...prev, sessionStatus, timeToClose }))
  }

  // Initial data fetch
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        await Promise.all([fetchSentiment(), fetchMarketQuote(), fetchOptionsData()])
        updateMarketSession()
      } catch (error) {
        console.error('Error loading dashboard:', error)
        setError('Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }

    loadData()

    // Refresh data every 30 seconds
    const interval = setInterval(() => {
      fetchSentiment()
      fetchMarketQuote()
      updateMarketSession()
    }, 30000)

    // Update session status every minute
    const sessionInterval = setInterval(updateMarketSession, 60000)

    return () => {
      clearInterval(interval)
      clearInterval(sessionInterval)
    }
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-xl">Loading dashboard...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <div className="text-red-500 text-xl">{error}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white font-mono">
      <div className="container mx-auto p-4 max-w-7xl">
        {/* Market Status Bar - Always visible */}
        <MarketStatusBar marketData={marketData} />

        {/* Tab Navigation */}
        <div className="mt-4 border-b border-slate-700">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'dashboard'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-600'
              }`}
            >
              Live Dashboard
            </button>
            <button
              onClick={() => setActiveTab('trades')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'trades'
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-600'
              }`}
            >
              Trade Management
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="mt-6">
          {activeTab === 'dashboard' ? (
            /* Main Dashboard Grid */
            <motion.div
              className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              {/* Sentiment Panel - Takes full width on mobile, spans 2 columns on xl */}
              <div className="xl:col-span-2">
                <SentimentPanel sentimentData={sentimentData} />
              </div>

              {/* Live P/L Monitor */}
              <div className="lg:col-span-1">
                <LivePLMonitorPanel plData={plData} historicalData={historicalData} />
              </div>

              {/* Recommended Spreads - Full width on smaller screens */}
              <div className="lg:col-span-2 xl:col-span-3">
                <RecommendedSpreadsPanel recommendations={spreadRecommendations} />
              </div>
            </motion.div>
          ) : (
            /* Trade Management Panel */
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <TradeManagementPanel />
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
