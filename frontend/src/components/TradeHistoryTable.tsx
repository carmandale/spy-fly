import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ChevronUp, ChevronDown, Filter, TrendingUp, TrendingDown } from 'lucide-react'
import { apiClient, Trade, TradeListResponse } from '../api/client'

interface TradeHistoryTableProps {
  refreshTrigger?: number
}

type SortField = 'trade_date' | 'status' | 'net_pnl' | 'pnl_percentage'
type SortDirection = 'asc' | 'desc'

const TradeHistoryTable: React.FC<TradeHistoryTableProps> = ({ refreshTrigger }) => {
  const [trades, setTrades] = useState<Trade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [sortField, setSortField] = useState<SortField>('trade_date')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [dateFilter, setDateFilter] = useState({
    start: '',
    end: ''
  })

  const fetchTrades = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const params: any = {
        page,
        per_page: 20
      }
      
      if (statusFilter) params.status = statusFilter
      if (dateFilter.start) params.start_date = dateFilter.start
      if (dateFilter.end) params.end_date = dateFilter.end
      
      const response: TradeListResponse = await apiClient.listTrades(params)
      setTrades(response.items)
      setTotalPages(response.pages)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch trades')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTrades()
  }, [page, statusFilter, dateFilter, refreshTrigger])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const formatCurrency = (value: number | string | undefined) => {
    if (value === undefined || value === null) return '-'
    const num = typeof value === 'string' ? parseFloat(value) : value
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(num)
  }

  const formatPercentage = (value: number | string | undefined) => {
    if (value === undefined || value === null) return '-'
    const num = typeof value === 'string' ? parseFloat(value) : value
    return `${num.toFixed(2)}%`
  }

  const getStatusBadge = (status: string) => {
    const statusColors = {
      entered: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
      exited: 'bg-gray-500/20 text-gray-400 border-gray-500/50',
      stopped: 'bg-red-500/20 text-red-400 border-red-500/50',
      recommended: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
      skipped: 'bg-gray-600/20 text-gray-500 border-gray-600/50'
    }
    
    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full border ${statusColors[status as keyof typeof statusColors] || statusColors.entered}`}>
        {status.toUpperCase()}
      </span>
    )
  }

  const getPnLColor = (pnl: number | string | undefined) => {
    if (pnl === undefined || pnl === null) return 'text-gray-400'
    const num = typeof pnl === 'string' ? parseFloat(pnl) : pnl
    if (num > 0) return 'text-emerald-400'
    if (num < 0) return 'text-red-400'
    return 'text-gray-400'
  }

  return (
    <div className="bg-gray-800 rounded-xl shadow-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Trade History</h2>
        
        {/* Filters */}
        <div className="flex items-center gap-4">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-emerald-500"
          >
            <option value="">All Status</option>
            <option value="entered">Entered</option>
            <option value="exited">Exited</option>
            <option value="stopped">Stopped</option>
            <option value="recommended">Recommended</option>
            <option value="skipped">Skipped</option>
          </select>
          
          <input
            type="date"
            value={dateFilter.start}
            onChange={(e) => setDateFilter(prev => ({ ...prev, start: e.target.value }))}
            className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-emerald-500"
            placeholder="Start date"
          />
          
          <input
            type="date"
            value={dateFilter.end}
            onChange={(e) => setDateFilter(prev => ({ ...prev, end: e.target.value }))}
            className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:border-emerald-500"
            placeholder="End date"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left border-b border-gray-700">
              <th className="pb-3 text-sm font-medium text-gray-400">
                <button
                  onClick={() => handleSort('trade_date')}
                  className="flex items-center gap-1 hover:text-white transition-colors"
                >
                  Date
                  {sortField === 'trade_date' && (
                    sortDirection === 'desc' ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />
                  )}
                </button>
              </th>
              <th className="pb-3 text-sm font-medium text-gray-400">Time</th>
              <th className="pb-3 text-sm font-medium text-gray-400">Type</th>
              <th className="pb-3 text-sm font-medium text-gray-400">
                <button
                  onClick={() => handleSort('status')}
                  className="flex items-center gap-1 hover:text-white transition-colors"
                >
                  Status
                  {sortField === 'status' && (
                    sortDirection === 'desc' ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />
                  )}
                </button>
              </th>
              <th className="pb-3 text-sm font-medium text-gray-400">Spread</th>
              <th className="pb-3 text-sm font-medium text-gray-400">Contracts</th>
              <th className="pb-3 text-sm font-medium text-gray-400">Entry</th>
              <th className="pb-3 text-sm font-medium text-gray-400">
                <button
                  onClick={() => handleSort('net_pnl')}
                  className="flex items-center gap-1 hover:text-white transition-colors"
                >
                  Net P/L
                  {sortField === 'net_pnl' && (
                    sortDirection === 'desc' ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />
                  )}
                </button>
              </th>
              <th className="pb-3 text-sm font-medium text-gray-400">
                <button
                  onClick={() => handleSort('pnl_percentage')}
                  className="flex items-center gap-1 hover:text-white transition-colors"
                >
                  P/L %
                  {sortField === 'pnl_percentage' && (
                    sortDirection === 'desc' ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />
                  )}
                </button>
              </th>
              <th className="pb-3 text-sm font-medium text-gray-400">Notes</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={10} className="py-8 text-center text-gray-400">
                  Loading trades...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td colSpan={10} className="py-8 text-center text-red-400">
                  {error}
                </td>
              </tr>
            ) : trades.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-8 text-center text-gray-400">
                  No trades found
                </td>
              </tr>
            ) : (
              trades.map((trade) => (
                <motion.tr
                  key={trade.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="border-b border-gray-700/50 hover:bg-gray-700/20 transition-colors"
                >
                  <td className="py-3 text-white">
                    {new Date(trade.trade_date).toLocaleDateString()}
                  </td>
                  <td className="py-3 text-gray-300">
                    {trade.entry_time ? new Date(trade.entry_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'}
                  </td>
                  <td className="py-3">
                    <span className={`text-sm ${trade.trade_type === 'real' ? 'text-emerald-400' : 'text-blue-400'}`}>
                      {trade.trade_type.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3">
                    {getStatusBadge(trade.status)}
                  </td>
                  <td className="py-3 text-gray-300">
                    {trade.spread ? (
                      <span className="text-sm">
                        {trade.spread.long_strike}/{trade.spread.short_strike}C
                      </span>
                    ) : '-'}
                  </td>
                  <td className="py-3 text-gray-300">
                    {trade.contracts || '-'}
                  </td>
                  <td className="py-3 text-gray-300">
                    {trade.spread ? formatCurrency(trade.spread.net_debit) : '-'}
                  </td>
                  <td className={`py-3 font-semibold ${getPnLColor(trade.net_pnl)}`}>
                    <div className="flex items-center gap-1">
                      {trade.net_pnl && (
                        parseFloat(trade.net_pnl.toString()) > 0 
                          ? <TrendingUp className="h-4 w-4" />
                          : <TrendingDown className="h-4 w-4" />
                      )}
                      {formatCurrency(trade.net_pnl)}
                    </div>
                  </td>
                  <td className={`py-3 font-semibold ${getPnLColor(trade.pnl_percentage)}`}>
                    {formatPercentage(trade.pnl_percentage)}
                  </td>
                  <td className="py-3 text-gray-400 text-sm max-w-xs truncate">
                    {trade.notes || '-'}
                  </td>
                </motion.tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <button
            onClick={() => setPage(prev => Math.max(1, prev - 1))}
            disabled={page === 1}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          
          <span className="text-gray-400">
            Page {page} of {totalPages}
          </span>
          
          <button
            onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
            disabled={page === totalPages}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}

      {/* Summary Stats */}
      {trades.length > 0 && (
        <div className="mt-6 pt-6 border-t border-gray-700 grid grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-sm text-gray-400">Total Trades</p>
            <p className="text-xl font-bold text-white">{trades.length}</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-400">Win Rate</p>
            <p className="text-xl font-bold text-emerald-400">
              {((trades.filter(t => t.net_pnl && parseFloat(t.net_pnl.toString()) > 0).length / trades.filter(t => t.status === 'exited').length) * 100 || 0).toFixed(1)}%
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-400">Total P/L</p>
            <p className={`text-xl font-bold ${getPnLColor(trades.reduce((sum, t) => sum + (t.net_pnl ? parseFloat(t.net_pnl.toString()) : 0), 0))}`}>
              {formatCurrency(trades.reduce((sum, t) => sum + (t.net_pnl ? parseFloat(t.net_pnl.toString()) : 0), 0))}
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-400">Avg P/L</p>
            <p className={`text-xl font-bold ${getPnLColor(trades.filter(t => t.status === 'exited').length > 0 ? trades.reduce((sum, t) => sum + (t.net_pnl ? parseFloat(t.net_pnl.toString()) : 0), 0) / trades.filter(t => t.status === 'exited').length : 0)}`}>
              {formatCurrency(trades.filter(t => t.status === 'exited').length > 0 ? trades.reduce((sum, t) => sum + (t.net_pnl ? parseFloat(t.net_pnl.toString()) : 0), 0) / trades.filter(t => t.status === 'exited').length : 0)}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default TradeHistoryTable