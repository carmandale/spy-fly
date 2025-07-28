import React, { useState } from 'react'
import { TradeInputPanel } from './TradeInputPanel'
import { TradeHistoryPanel } from './TradeHistoryPanel'
import { Trade } from '../api/client'

export const TradeManagementPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'history' | 'input'>('history')
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleTradeCreated = (trade: Trade) => {
    // Refresh the history panel
    setRefreshTrigger(prev => prev + 1)
    // Switch back to history tab to show the new trade
    setActiveTab('history')
  }

  return (
    <div className="w-full">
      {/* Tab Navigation */}
      <div className="border-b border-slate-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('history')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'history'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            Trade History
          </button>
          <button
            onClick={() => setActiveTab('input')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'input'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            Add Trade
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'history' ? (
          <TradeHistoryPanel refreshTrigger={refreshTrigger} />
        ) : (
          <TradeInputPanel 
            onTradeCreated={handleTradeCreated}
            onClose={() => setActiveTab('history')}
          />
        )}
      </div>
    </div>
  )
}