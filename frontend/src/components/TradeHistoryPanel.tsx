import React, { useState, useEffect } from 'react'
import { apiClient, Trade, TradeListResponse, TradeSummary } from '../api/client'

interface TradeHistoryPanelProps {
  refreshTrigger?: number
}

export const TradeHistoryPanel: React.FC<TradeHistoryPanelProps> = ({ refreshTrigger }) => {
  const [trades, setTrades] = useState<Trade[]>([])
  const [summary, setSummary] = useState<TradeSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null)
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(0)
  const [totalTrades, setTotalTrades] = useState(0)
  const pageSize = 20

  // Filter state
  const [filters, setFilters] = useState({
    status: '',
    trade_type: '',
    start_date: '',
    end_date: ''
  })

  const loadTrades = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const params: any = {
        skip: currentPage * pageSize,
        limit: pageSize
      }
      
      // Add filters
      if (filters.status) params.status = filters.status
      if (filters.trade_type) params.trade_type = filters.trade_type
      
      const response = await apiClient.getTrades(params)
      setTrades(response.trades)
      setTotalTrades(response.total)
      
      // Load summary
      const summaryParams: any = {}
      if (filters.start_date) summaryParams.start_date = filters.start_date
      if (filters.end_date) summaryParams.end_date = filters.end_date
      
      const summaryResponse = await apiClient.getTradeSummary(summaryParams)
      setSummary(summaryResponse)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trades')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTrades()
  }, [currentPage, filters, refreshTrigger])

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }))
    setCurrentPage(0) // Reset to first page when filtering
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'entered': return 'bg-blue-100 text-blue-800'
      case 'exited': return 'bg-green-100 text-green-800'
      case 'stopped': return 'bg-red-100 text-red-800'
      case 'recommended': return 'bg-yellow-100 text-yellow-800'
      case 'skipped': return 'bg-slate-100 text-slate-800'
      default: return 'bg-slate-100 text-slate-800'
    }
  }

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const totalPages = Math.ceil(totalTrades / pageSize)

  return (
    <div className="bg-white rounded-lg shadow-sm border">
      {/* Summary Stats */}
      {summary && (
        <div className="p-4 border-b bg-slate-50">
          <h3 className="text-lg font-semibold text-slate-900 mb-3">Performance Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-slate-900">{summary.total_trades}</div>
              <div className="text-sm text-slate-600">Total Trades</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{summary.winning_trades}</div>
              <div className="text-sm text-slate-600">Winners</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{summary.losing_trades}</div>
              <div className="text-sm text-slate-600">Losers</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{summary.win_rate.toFixed(1)}%</div>
              <div className="text-sm text-slate-600">Win Rate</div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${summary.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(summary.total_pnl)}
              </div>
              <div className="text-sm text-slate-600">Total P&L</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-slate-900">{formatCurrency(summary.average_win)}</div>
              <div className="text-sm text-slate-600">Avg Win</div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="p-4 border-b">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
            >
              <option value="">All Statuses</option>
              <option value="recommended">Recommended</option>
              <option value="entered">Entered</option>
              <option value="exited">Exited</option>
              <option value="stopped">Stopped</option>
              <option value="skipped">Skipped</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Type</label>
            <select
              value={filters.trade_type}
              onChange={(e) => handleFilterChange('trade_type', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
            >
              <option value="">All Types</option>
              <option value="paper">Paper</option>
              <option value="real">Real</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Start Date</label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => handleFilterChange('start_date', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">End Date</label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => handleFilterChange('end_date', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
            />
          </div>
        </div>
      </div>

      {/* Trade List */}
      <div className="p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-slate-900">
            Trade History ({totalTrades} total)
          </h3>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
              disabled={currentPage === 0}
              className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-sm text-slate-600">
              Page {currentPage + 1} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages - 1, currentPage + 1))}
              disabled={currentPage === totalPages - 1}
              className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="text-slate-600">Loading trades...</div>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        ) : trades.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-slate-600">No trades found</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 font-medium text-slate-700">Date</th>
                  <th className="text-left py-2 font-medium text-slate-700">Type</th>
                  <th className="text-left py-2 font-medium text-slate-700">Status</th>
                  <th className="text-left py-2 font-medium text-slate-700">Contracts</th>
                  <th className="text-left py-2 font-medium text-slate-700">Max Profit</th>
                  <th className="text-left py-2 font-medium text-slate-700">Net P&L</th>
                  <th className="text-left py-2 font-medium text-slate-700">Notes</th>
                  <th className="text-left py-2 font-medium text-slate-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => (
                  <tr key={trade.id} className="border-b hover:bg-slate-50">
                    <td className="py-2">{formatDate(trade.trade_date)}</td>
                    <td className="py-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        trade.trade_type === 'real' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                      }`}>
                        {trade.trade_type}
                      </span>
                    </td>
                    <td className="py-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(trade.status)}`}>
                        {trade.status}
                      </span>
                    </td>
                    <td className="py-2">{trade.contracts || '-'}</td>
                    <td className="py-2">{formatCurrency(trade.max_reward)}</td>
                    <td className="py-2">
                      <span className={trade.net_pnl && trade.net_pnl < 0 ? 'text-red-600' : 'text-green-600'}>
                        {formatCurrency(trade.net_pnl)}
                      </span>
                    </td>
                    <td className="py-2 max-w-xs truncate" title={trade.notes || ''}>
                      {trade.notes || '-'}
                    </td>
                    <td className="py-2">
                      <button
                        onClick={() => setSelectedTrade(trade)}
                        className="text-blue-600 hover:text-blue-800 text-xs"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Trade Details Modal */}
      {selectedTrade && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Trade Details</h3>
                <button
                  onClick={() => setSelectedTrade(null)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>
              
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Date</label>
                    <div className="text-slate-900">{formatDate(selectedTrade.trade_date)}</div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Status</label>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(selectedTrade.status)}`}>
                      {selectedTrade.status}
                    </span>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Type</label>
                    <div className="text-slate-900">{selectedTrade.trade_type}</div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Contracts</label>
                    <div className="text-slate-900">{selectedTrade.contracts || '-'}</div>
                  </div>
                </div>

                {selectedTrade.entry_signal_reason && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Entry Signal</label>
                    <div className="text-slate-900">{selectedTrade.entry_signal_reason}</div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Max Risk</label>
                    <div className="text-slate-900">{formatCurrency(selectedTrade.max_risk)}</div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Max Reward</label>
                    <div className="text-slate-900">{formatCurrency(selectedTrade.max_reward)}</div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Net P&L</label>
                    <div className={`font-medium ${selectedTrade.net_pnl && selectedTrade.net_pnl < 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {formatCurrency(selectedTrade.net_pnl)}
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700">P&L %</label>
                    <div className={`font-medium ${selectedTrade.pnl_percentage && selectedTrade.pnl_percentage < 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {selectedTrade.pnl_percentage ? `${selectedTrade.pnl_percentage.toFixed(2)}%` : '-'}
                    </div>
                  </div>
                </div>

                {selectedTrade.notes && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700">Notes</label>
                    <div className="text-slate-900 bg-slate-50 p-3 rounded">{selectedTrade.notes}</div>
                  </div>
                )}

                {/* Spread details would go here if we loaded them */}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}