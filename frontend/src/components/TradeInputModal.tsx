import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { apiClient, TradeCreate } from '../api/client'

interface TradeInputModalProps {
  isOpen: boolean
  onClose: () => void
  onTradeCreated: () => void
}

const TradeInputModal: React.FC<TradeInputModalProps> = ({ isOpen, onClose, onTradeCreated }) => {
  const [formData, setFormData] = useState<TradeCreate>({
    trade_date: new Date().toISOString().split('T')[0],
    trade_type: 'paper',
    status: 'entered',
    entry_time: new Date().toISOString().slice(0, 16),
    contracts: 1,
    notes: '',
    spread: {
      spread_type: 'bull_call_spread',
      expiration_date: new Date().toISOString().split('T')[0],
      long_strike: 0,
      short_strike: 0,
      long_premium: 0,
      short_premium: 0,
      net_debit: 0,
      max_profit: 0,
      max_loss: 0,
      breakeven: 0,
      risk_reward_ratio: 0,
    }
  })
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const calculateSpreadMetrics = () => {
    if (formData.spread) {
      const spread = formData.spread
      const netDebit = spread.long_premium - spread.short_premium
      const maxLoss = netDebit * (formData.contracts || 1) * 100
      const spreadWidth = spread.short_strike - spread.long_strike
      const maxProfit = (spreadWidth - netDebit) * (formData.contracts || 1) * 100
      const breakeven = spread.long_strike + netDebit
      const riskReward = maxLoss > 0 ? maxProfit / maxLoss : 0

      setFormData(prev => ({
        ...prev,
        max_risk: maxLoss,
        max_reward: maxProfit,
        spread: {
          ...prev.spread!,
          net_debit: netDebit,
          max_profit: maxProfit,
          max_loss: maxLoss,
          breakeven: breakeven,
          risk_reward_ratio: riskReward,
        }
      }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await apiClient.createTrade(formData)
      onTradeCreated()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create trade')
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: string, value: any) => {
    if (field.startsWith('spread.')) {
      const spreadField = field.split('.')[1]
      setFormData(prev => ({
        ...prev,
        spread: {
          ...prev.spread!,
          [spreadField]: value
        }
      }))
    } else {
      setFormData(prev => ({
        ...prev,
        [field]: value
      }))
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
            onClick={onClose}
          />
          
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-gray-800 rounded-xl shadow-2xl z-50 p-6"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-white">Record Trade</h2>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="h-5 w-5 text-gray-400" />
              </button>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Trade Date
                  </label>
                  <input
                    type="date"
                    value={formData.trade_date}
                    onChange={(e) => handleInputChange('trade_date', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Entry Time
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.entry_time}
                    onChange={(e) => handleInputChange('entry_time', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Trade Type
                  </label>
                  <select
                    value={formData.trade_type}
                    onChange={(e) => handleInputChange('trade_type', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="paper">Paper</option>
                    <option value="real">Real</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Status
                  </label>
                  <select
                    value={formData.status}
                    onChange={(e) => handleInputChange('status', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  >
                    <option value="entered">Entered</option>
                    <option value="recommended">Recommended</option>
                    <option value="skipped">Skipped</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Contracts
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={formData.contracts}
                    onChange={(e) => handleInputChange('contracts', parseInt(e.target.value))}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                    required
                  />
                </div>
              </div>

              {/* Spread Details */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-white">Spread Details</h3>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Long Strike
                    </label>
                    <input
                      type="number"
                      step="0.50"
                      value={formData.spread?.long_strike}
                      onChange={(e) => handleInputChange('spread.long_strike', parseFloat(e.target.value))}
                      onBlur={calculateSpreadMetrics}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Short Strike
                    </label>
                    <input
                      type="number"
                      step="0.50"
                      value={formData.spread?.short_strike}
                      onChange={(e) => handleInputChange('spread.short_strike', parseFloat(e.target.value))}
                      onBlur={calculateSpreadMetrics}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Long Premium
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.spread?.long_premium}
                      onChange={(e) => handleInputChange('spread.long_premium', parseFloat(e.target.value))}
                      onBlur={calculateSpreadMetrics}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                      required
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Short Premium
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.spread?.short_premium}
                      onChange={(e) => handleInputChange('spread.short_premium', parseFloat(e.target.value))}
                      onBlur={calculateSpreadMetrics}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                      required
                    />
                  </div>
                </div>

                {/* Calculated Metrics */}
                {formData.spread?.net_debit > 0 && (
                  <div className="grid grid-cols-3 gap-4 p-4 bg-gray-700/50 rounded-lg">
                    <div>
                      <span className="text-sm text-gray-400">Net Debit</span>
                      <p className="text-lg font-semibold text-white">
                        ${formData.spread.net_debit.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-400">Max Profit</span>
                      <p className="text-lg font-semibold text-emerald-400">
                        ${formData.spread.max_profit.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-400">Max Loss</span>
                      <p className="text-lg font-semibold text-red-400">
                        ${formData.spread.max_loss.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-400">Breakeven</span>
                      <p className="text-lg font-semibold text-white">
                        ${formData.spread.breakeven.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <span className="text-sm text-gray-400">Risk/Reward</span>
                      <p className="text-lg font-semibold text-white">
                        {formData.spread.risk_reward_ratio.toFixed(2)}:1
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Notes
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => handleInputChange('notes', e.target.value)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:border-emerald-500 h-24 resize-none"
                  placeholder="Add any notes about this trade..."
                />
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Creating...' : 'Create Trade'}
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export default TradeInputModal