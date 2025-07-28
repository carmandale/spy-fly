import React from 'react'
import { motion } from 'framer-motion'
import { Activity, Wifi, WifiOff, Clock } from 'lucide-react'
interface MarketData {
  spyPrice: number
  spyChange: number
  vix: number
  sessionStatus: 'pre-market' | 'open' | 'closed'
  timeToClose: string
  apiStatus: 'connected' | 'disconnected' | 'reconnecting'
}
interface MarketStatusBarProps {
  marketData: MarketData
}
const MarketStatusBar: React.FC<MarketStatusBarProps> = ({ marketData }) => {
  const getSessionStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'text-green-400'
      case 'pre-market':
        return 'text-yellow-400'
      case 'closed':
        return 'text-red-400'
      default:
        return 'text-gray-400'
    }
  }
  const getApiStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <Wifi className="w-4 h-4 text-green-400" />
      case 'disconnected':
        return <WifiOff className="w-4 h-4 text-red-400" />
      case 'reconnecting':
        return <Activity className="w-4 h-4 text-yellow-400 animate-pulse" />
      default:
        return <WifiOff className="w-4 h-4 text-gray-400" />
    }
  }
  return (
    <motion.header
      className="bg-gray-800 border border-gray-700 rounded-lg p-4"
      initial={{
        opacity: 0,
        y: -20,
      }}
      animate={{
        opacity: 1,
        y: 0,
      }}
      transition={{
        duration: 0.3,
      }}
    >
      <nav className="flex flex-wrap items-center justify-between gap-4 text-sm">
        {/* SPY Price */}
        <section className="flex items-center space-x-2">
          <span className="text-gray-400">SPY:</span>
          <strong className="text-white font-bold text-lg">
            ${marketData.spyPrice.toFixed(2)}
          </strong>
          <span className={`${marketData.spyChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {marketData.spyChange >= 0 ? '+' : ''}
            {marketData.spyChange.toFixed(2)}
          </span>
        </section>

        {/* VIX */}
        <section className="flex items-center space-x-2">
          <span className="text-gray-400">VIX:</span>
          <strong className="text-white font-bold">{marketData.vix.toFixed(2)}</strong>
        </section>

        {/* Session Status */}
        <section className="flex items-center space-x-2">
          <span className="text-gray-400">Session:</span>
          <strong
            className={`font-bold uppercase ${getSessionStatusColor(marketData.sessionStatus)}`}
          >
            {marketData.sessionStatus.replace('-', ' ')}
          </strong>
        </section>

        {/* Time to Close */}
        <section className="flex items-center space-x-2">
          <Clock className="w-4 h-4 text-gray-400" aria-hidden="true" />
          <span className="text-gray-400">Close in:</span>
          <strong className="text-white font-bold">{marketData.timeToClose}</strong>
        </section>

        {/* API Status */}
        <section className="flex items-center space-x-2">
          {getApiStatusIcon(marketData.apiStatus)}
          <span className="text-gray-400 capitalize">{marketData.apiStatus}</span>
        </section>
      </nav>
    </motion.header>
  )
}
export default MarketStatusBar
