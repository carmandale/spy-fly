import React, { useState } from 'react'
import { apiClient, Trade, TradeSpread } from '../api/client'

interface TradeInputPanelProps {
  onTradeCreated?: (trade: Trade) => void
  onClose?: () => void
}

export const TradeInputPanel: React.FC<TradeInputPanelProps> = ({ 
  onTradeCreated, 
  onClose 
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Trade form state
  const [tradeData, setTradeData] = useState<Partial<Trade>>({
    trade_date: new Date().toISOString().split('T')[0],
    trade_type: 'paper',
    status: 'recommended',
    entry_signal_reason: '',
    contracts: 1,
    notes: ''
  })

  // Spread form state
  const [showSpread, setShowSpread] = useState(false)
  const [spreadData, setSpreadData] = useState<Partial<TradeSpread>>({
    spread_type: 'bull_call_spread',
    expiration_date: new Date().toISOString().split('T')[0],
    long_strike: 0,
    long_premium: 0,
    short_strike: 0,
    short_premium: 0,
    net_debit: 0,
    max_profit: 0,
    max_loss: 0,
    breakeven: 0,
    risk_reward_ratio: 1.0
  })

  const handleTradeChange = (field: keyof Trade, value: any) => {
    setTradeData(prev => ({ ...prev, [field]: value }))
  }

  const handleSpreadChange = (field: keyof TradeSpread, value: any) => {
    setSpreadData(prev => ({ ...prev, [field]: value }))
    
    // Auto-calculate spread metrics when key values change
    if (['long_strike', 'short_strike', 'long_premium', 'short_premium'].includes(field)) {
      const updated = { ...spreadData, [field]: value }
      if (updated.long_strike && updated.short_strike && updated.long_premium && updated.short_premium) {
        const netDebit = updated.long_premium - updated.short_premium
        const maxProfit = (updated.short_strike - updated.long_strike) - netDebit
        const maxLoss = netDebit
        const breakeven = updated.long_strike + netDebit
        const riskRewardRatio = maxProfit / maxLoss

        setSpreadData(prev => ({
          ...prev,
          net_debit: netDebit,
          max_profit: maxProfit,
          max_loss: maxLoss,
          breakeven: breakeven,
          risk_reward_ratio: riskRewardRatio
        }))
      }
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setError(null)

    try {
      const tradePayload: any = { ...tradeData }
      
      if (showSpread && spreadData.long_strike && spreadData.short_strike) {
        tradePayload.spread = spreadData
      }

      const newTrade = await apiClient.createTrade(tradePayload)
      
      if (onTradeCreated) {
        onTradeCreated(newTrade)
      }
      
      // Reset form
      setTradeData({
        trade_date: new Date().toISOString().split('T')[0],
        trade_type: 'paper',
        status: 'recommended',
        entry_signal_reason: '',
        contracts: 1,
        notes: ''
      })
      
      setSpreadData({
        spread_type: 'bull_call_spread',
        expiration_date: new Date().toISOString().split('T')[0],
        long_strike: 0,
        long_premium: 0,
        short_strike: 0,
        short_premium: 0,
        net_debit: 0,
        max_profit: 0,
        max_loss: 0,
        breakeven: 0,
        risk_reward_ratio: 1.0
      })
      
      if (onClose) {
        onClose()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create trade')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-900">Add New Trade</h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600"
          >
            ✕
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Basic Trade Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Trade Date
            </label>
            <input
              type="date"
              value={tradeData.trade_date || ''}
              onChange={(e) => handleTradeChange('trade_date', e.target.value)}
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Trade Type
            </label>
            <select
              value={tradeData.trade_type || 'paper'}
              onChange={(e) => handleTradeChange('trade_type', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="paper">Paper</option>
              <option value="real">Real</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Status
            </label>
            <select
              value={tradeData.status || 'recommended'}
              onChange={(e) => handleTradeChange('status', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="recommended">Recommended</option>
              <option value="entered">Entered</option>
              <option value="exited">Exited</option>
              <option value="stopped">Stopped</option>
              <option value="skipped">Skipped</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Contracts
            </label>
            <input
              type="number"
              min="1"
              value={tradeData.contracts || 1}
              onChange={(e) => handleTradeChange('contracts', parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Entry Details */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Entry Signal Reason
          </label>
          <textarea
            value={tradeData.entry_signal_reason || ''}
            onChange={(e) => handleTradeChange('entry_signal_reason', e.target.value)}
            placeholder="Why was this trade recommended?"
            rows={2}
            className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Spread Details Toggle */}
        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={showSpread}
              onChange={(e) => setShowSpread(e.target.checked)}
              className="mr-2"
            />
            <span className="text-sm font-medium text-slate-700">Add Spread Details</span>
          </label>
        </div>

        {/* Spread Details */}
        {showSpread && (
          <div className="border-t pt-4 space-y-4">
            <h4 className="text-md font-medium text-slate-800">Spread Details</h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Expiration Date
                </label>
                <input
                  type="date"
                  value={spreadData.expiration_date || ''}
                  onChange={(e) => handleSpreadChange('expiration_date', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Spread Type
                </label>
                <select
                  value={spreadData.spread_type || 'bull_call_spread'}
                  onChange={(e) => handleSpreadChange('spread_type', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="bull_call_spread">Bull Call Spread</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Long Strike
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={spreadData.long_strike || ''}
                  onChange={(e) => handleSpreadChange('long_strike', parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Long Premium
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={spreadData.long_premium || ''}
                  onChange={(e) => handleSpreadChange('long_premium', parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Short Strike
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={spreadData.short_strike || ''}
                  onChange={(e) => handleSpreadChange('short_strike', parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Short Premium
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={spreadData.short_premium || ''}
                  onChange={(e) => handleSpreadChange('short_premium', parseFloat(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Calculated Metrics */}
            <div className="bg-slate-50 p-3 rounded-md">
              <h5 className="text-sm font-medium text-slate-700 mb-2">Calculated Metrics</h5>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                  <span className="text-slate-600">Net Debit:</span>
                  <span className="ml-1 font-medium">${spreadData.net_debit?.toFixed(2) || '0.00'}</span>
                </div>
                <div>
                  <span className="text-slate-600">Max Profit:</span>
                  <span className="ml-1 font-medium">${spreadData.max_profit?.toFixed(2) || '0.00'}</span>
                </div>
                <div>
                  <span className="text-slate-600">Max Loss:</span>
                  <span className="ml-1 font-medium">${spreadData.max_loss?.toFixed(2) || '0.00'}</span>
                </div>
                <div>
                  <span className="text-slate-600">R/R Ratio:</span>
                  <span className="ml-1 font-medium">{spreadData.risk_reward_ratio?.toFixed(2) || '0.00'}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Notes
          </label>
          <textarea
            value={tradeData.notes || ''}
            onChange={(e) => handleTradeChange('notes', e.target.value)}
            placeholder="Additional notes about this trade..."
            rows={3}
            className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Submit Button */}
        <div className="flex justify-end space-x-3">
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-md transition-colors"
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            disabled={isSubmitting}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors disabled:opacity-50"
          >
            {isSubmitting ? 'Creating...' : 'Create Trade'}
          </button>
        </div>
      </form>
    </div>
  )
}