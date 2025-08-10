import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Activity, TrendingUp, Shield, AlertCircle, CheckCircle } from 'lucide-react'
import ExecutionWizard from '../components/execution/ExecutionWizard'
import ExecutionChecklist from '../components/execution/ExecutionChecklist'

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
  sentiment_score?: number
  created_at?: string
}

type ViewMode = 'wizard' | 'checklist'

const ExecutionPage: React.FC = () => {
  const { recommendationId } = useParams<{ recommendationId: string }>()
  const navigate = useNavigate()
  const [viewMode, setViewMode] = useState<ViewMode>('wizard')
  const [recommendation, setRecommendation] = useState<SpreadRecommendation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [executionComplete, setExecutionComplete] = useState(false)

  useEffect(() => {
    const fetchRecommendation = async () => {
      if (!recommendationId) {
        setError('No recommendation ID provided')
        setLoading(false)
        return
      }

      try {
        // In production, this would fetch from the API
        // For now, using mock data that matches the recommendation structure
        const mockRecommendation: SpreadRecommendation = {
          id: recommendationId,
          longStrike: 585,
          shortStrike: 590,
          debit: 125,
          maxProfit: 375,
          maxLoss: 125,
          breakeven: 586.25,
          probability: 42,
          quantity: 2,
          expiration: '2025-01-10',
          sentiment_score: 75,
          created_at: new Date().toISOString()
        }
        
        setRecommendation(mockRecommendation)
      } catch (err) {
        setError('Failed to load recommendation details')
        console.error('Error fetching recommendation:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchRecommendation()
  }, [recommendationId])

  const handleWizardComplete = () => {
    setExecutionComplete(true)
    // Could also update the recommendation status in the backend
  }

  const handleChecklistComplete = () => {
    setExecutionComplete(true)
    // Could also update the recommendation status in the backend
  }

  const handleBackToDashboard = () => {
    navigate('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 text-blue-400 animate-pulse mx-auto mb-4" />
          <p className="text-gray-400">Loading recommendation details...</p>
        </div>
      </div>
    )
  }

  if (error || !recommendation) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-400 mb-4">{error || 'Recommendation not found'}</p>
          <button
            onClick={handleBackToDashboard}
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  if (executionComplete) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="text-center max-w-md"
        >
          <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Execution Complete!</h1>
          <p className="text-gray-400 mb-6">
            Your bull call spread order has been prepared and is ready for submission to your broker.
          </p>
          <div className="bg-gray-800 rounded-lg p-4 mb-6">
            <div className="space-y-2 text-left">
              <div className="flex justify-between">
                <span className="text-gray-400">Strategy:</span>
                <span className="text-white font-medium">
                  ${recommendation.longStrike}/${recommendation.shortStrike} Bull Call
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Quantity:</span>
                <span className="text-white font-medium">{recommendation.quantity} contracts</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Net Debit:</span>
                <span className="text-red-400 font-medium">${recommendation.debit.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Max Profit:</span>
                <span className="text-green-400 font-medium">${recommendation.maxProfit.toFixed(2)}</span>
              </div>
            </div>
          </div>
          <button
            onClick={handleBackToDashboard}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Back to Dashboard
          </button>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={handleBackToDashboard}
                className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-white" />
              </button>
              <div>
                <h1 className="text-xl font-bold text-white">Trade Execution</h1>
                <p className="text-sm text-gray-400">
                  SPY ${recommendation.longStrike}/${recommendation.shortStrike} Bull Call Spread
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-green-400" />
              <span className="text-green-400 font-medium">
                Sentiment: {recommendation.sentiment_score}%
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* View Mode Toggle */}
        <div className="flex justify-center mb-8">
          <div className="bg-gray-800 rounded-lg p-1 flex">
            <button
              onClick={() => setViewMode('wizard')}
              className={`px-6 py-2 rounded-md transition-colors ${
                viewMode === 'wizard'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Guided Wizard
            </button>
            <button
              onClick={() => setViewMode('checklist')}
              className={`px-6 py-2 rounded-md transition-colors ${
                viewMode === 'checklist'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Interactive Checklist
            </button>
          </div>
        </div>

        {/* Risk Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-8"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Risk Summary</h2>
            <Shield className="w-5 h-5 text-blue-400" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-400">Max Loss</p>
              <p className="text-xl font-bold text-red-400">${recommendation.maxLoss.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400">Max Profit</p>
              <p className="text-xl font-bold text-green-400">${recommendation.maxProfit.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400">Breakeven</p>
              <p className="text-xl font-bold text-yellow-400">${recommendation.breakeven.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400">Probability</p>
              <p className="text-xl font-bold text-blue-400">{recommendation.probability}%</p>
            </div>
          </div>
        </motion.div>

        {/* Execution Interface */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          {viewMode === 'wizard' ? (
            <ExecutionWizard
              recommendationId={recommendation.id}
              spreadData={recommendation}
              onComplete={handleWizardComplete}
              onCancel={handleBackToDashboard}
            />
          ) : (
            <ExecutionChecklist
              spreadData={recommendation}
              onComplete={handleChecklistComplete}
            />
          )}
        </motion.div>

        {/* Important Notes */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="mt-8 bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-4"
        >
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-yellow-400 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-yellow-400 font-medium mb-1">Important Notes</h3>
              <ul className="text-yellow-300 text-sm space-y-1">
                <li>• This is a 0-DTE (same-day expiration) trade with high risk</li>
                <li>• Ensure you have sufficient buying power before placing the order</li>
                <li>• Set stop-loss alerts at 20% of max loss (${(recommendation.maxLoss * 0.2).toFixed(2)})</li>
                <li>• Monitor the position closely throughout the trading day</li>
                <li>• This tool is for educational purposes - verify all details with your broker</li>
              </ul>
            </div>
          </div>
        </motion.div>
      </main>
    </div>
  )
}

export default ExecutionPage