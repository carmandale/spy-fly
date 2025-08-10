import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, X, AlertCircle, Clock, Shield, TrendingUp, DollarSign, Activity, ChevronDown } from 'lucide-react'
import { CopyButton } from './CopyButton'

interface ChecklistItem {
  id: string
  category: 'pre-trade' | 'validation' | 'execution' | 'post-trade'
  title: string
  description: string
  icon: React.ElementType
  status: 'pending' | 'completed' | 'skipped' | 'error'
  required: boolean
  action?: () => void
}

interface ExecutionChecklistProps {
  spreadData: {
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
  onComplete?: () => void
}

const ExecutionChecklist: React.FC<ExecutionChecklistProps> = ({ spreadData, onComplete }) => {
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set())
  const [expandedCategory, setExpandedCategory] = useState<string>('pre-trade')

  const generateOrderText = () => {
    return `SPY Bull Call Spread (${spreadData.expiration})
Buy ${spreadData.quantity} x $${spreadData.longStrike} Call
Sell ${spreadData.quantity} x $${spreadData.shortStrike} Call
Net Debit: $${spreadData.debit.toFixed(2)}
Max Profit: $${spreadData.maxProfit.toFixed(2)}
Max Loss: $${spreadData.maxLoss.toFixed(2)}
Breakeven: $${spreadData.breakeven.toFixed(2)}
Probability: ${spreadData.probability}%`
  }

  const checklistItems: ChecklistItem[] = [
    // Pre-Trade Checks
    {
      id: 'market-hours',
      category: 'pre-trade',
      title: 'Market Hours Check',
      description: 'Verify market is open and has sufficient liquidity',
      icon: Clock,
      status: checkedItems.has('market-hours') ? 'completed' : 'pending',
      required: true
    },
    {
      id: 'sentiment-review',
      category: 'pre-trade',
      title: 'Sentiment Review',
      description: 'Confirm overall market sentiment is bullish',
      icon: TrendingUp,
      status: checkedItems.has('sentiment-review') ? 'completed' : 'pending',
      required: true
    },
    {
      id: 'account-balance',
      category: 'pre-trade',
      title: 'Account Balance',
      description: 'Ensure sufficient buying power for the trade',
      icon: DollarSign,
      status: checkedItems.has('account-balance') ? 'completed' : 'pending',
      required: true
    },
    
    // Validation Checks
    {
      id: 'position-size',
      category: 'validation',
      title: 'Position Size Validation',
      description: `Confirm risk is within 5% limit: $${spreadData.maxLoss.toFixed(2)}`,
      icon: Shield,
      status: checkedItems.has('position-size') ? 'completed' : 'pending',
      required: true
    },
    {
      id: 'risk-reward',
      category: 'validation',
      title: 'Risk/Reward Check',
      description: `Verify 1:1 minimum ratio (Current: ${(spreadData.maxProfit / spreadData.maxLoss).toFixed(2)}:1)`,
      icon: Activity,
      status: checkedItems.has('risk-reward') ? 'completed' : 'pending',
      required: true
    },
    {
      id: 'spread-validity',
      category: 'validation',
      title: 'Spread Parameters',
      description: 'Confirm strikes and expiration are correct',
      icon: Check,
      status: checkedItems.has('spread-validity') ? 'completed' : 'pending',
      required: true
    },
    
    // Execution Steps
    {
      id: 'copy-order',
      category: 'execution',
      title: 'Copy Order Details',
      description: 'Copy formatted order to clipboard',
      icon: Activity,
      status: checkedItems.has('copy-order') ? 'completed' : 'pending',
      required: true,
      action: () => {
        navigator.clipboard.writeText(generateOrderText())
        setCheckedItems(prev => new Set([...prev, 'copy-order']))
      }
    },
    {
      id: 'broker-open',
      category: 'execution',
      title: 'Open Broker Platform',
      description: 'Launch your trading platform',
      icon: Activity,
      status: checkedItems.has('broker-open') ? 'completed' : 'pending',
      required: true
    },
    {
      id: 'order-entry',
      category: 'execution',
      title: 'Enter Order Details',
      description: 'Input spread parameters in broker',
      icon: Activity,
      status: checkedItems.has('order-entry') ? 'completed' : 'pending',
      required: true
    },
    {
      id: 'order-review',
      category: 'execution',
      title: 'Review Order',
      description: 'Double-check all parameters before submission',
      icon: Shield,
      status: checkedItems.has('order-review') ? 'completed' : 'pending',
      required: true
    },
    
    // Post-Trade Steps
    {
      id: 'order-submit',
      category: 'post-trade',
      title: 'Submit Order',
      description: 'Place the order with your broker',
      icon: Check,
      status: checkedItems.has('order-submit') ? 'completed' : 'pending',
      required: true
    },
    {
      id: 'order-confirm',
      category: 'post-trade',
      title: 'Confirmation Number',
      description: 'Record order confirmation or fill details',
      icon: Activity,
      status: checkedItems.has('order-confirm') ? 'completed' : 'pending',
      required: false
    },
    {
      id: 'stop-loss',
      category: 'post-trade',
      title: 'Set Stop Loss Alert',
      description: `Create alert at 20% loss: $${(spreadData.maxLoss * 0.2).toFixed(2)}`,
      icon: AlertCircle,
      status: checkedItems.has('stop-loss') ? 'completed' : 'pending',
      required: false
    },
    {
      id: 'profit-target',
      category: 'post-trade',
      title: 'Set Profit Target',
      description: `Create alert at 50% profit: $${(spreadData.maxProfit * 0.5).toFixed(2)}`,
      icon: TrendingUp,
      status: checkedItems.has('profit-target') ? 'completed' : 'pending',
      required: false
    }
  ]

  const categories = [
    { id: 'pre-trade', title: 'Pre-Trade Checks', icon: Shield },
    { id: 'validation', title: 'Risk Validation', icon: AlertCircle },
    { id: 'execution', title: 'Order Execution', icon: Activity },
    { id: 'post-trade', title: 'Post-Trade Setup', icon: Check }
  ]

  const handleItemToggle = (itemId: string) => {
    setCheckedItems(prev => {
      const newSet = new Set(prev)
      if (newSet.has(itemId)) {
        newSet.delete(itemId)
      } else {
        newSet.add(itemId)
      }
      return newSet
    })
  }

  const getCategoryProgress = (category: string) => {
    const categoryItems = checklistItems.filter(item => item.category === category)
    const completedItems = categoryItems.filter(item => checkedItems.has(item.id))
    return {
      completed: completedItems.length,
      total: categoryItems.length,
      percentage: (completedItems.length / categoryItems.length) * 100
    }
  }

  const allRequiredComplete = checklistItems
    .filter(item => item.required)
    .every(item => checkedItems.has(item.id))

  return (
    <div className="space-y-4">
      {/* Overall Progress */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-white">Execution Checklist</h3>
          <span className="text-sm text-gray-400">
            {checkedItems.size} of {checklistItems.length} complete
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2">
          <motion.div
            className="bg-blue-600 h-2 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${(checkedItems.size / checklistItems.length) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      {/* Category Sections */}
      {categories.map(category => {
        const progress = getCategoryProgress(category.id)
        const isExpanded = expandedCategory === category.id
        const items = checklistItems.filter(item => item.category === category.id)

        return (
          <motion.div
            key={category.id}
            className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <button
              onClick={() => setExpandedCategory(isExpanded ? '' : category.id)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-700/50 transition-colors"
            >
              <div className="flex items-center space-x-3">
                <category.icon className={`w-5 h-5 ${
                  progress.percentage === 100 ? 'text-green-400' : 'text-gray-400'
                }`} />
                <h4 className="text-white font-medium">{category.title}</h4>
                <span className="text-sm text-gray-400">
                  {progress.completed}/{progress.total}
                </span>
              </div>
              <motion.div
                animate={{ rotate: isExpanded ? 180 : 0 }}
                transition={{ duration: 0.2 }}
              >
                <ChevronDown className="w-5 h-5 text-gray-400" />
              </motion.div>
            </button>

            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: 'auto' }}
                  exit={{ height: 0 }}
                  transition={{ duration: 0.3 }}
                  className="border-t border-gray-700"
                >
                  <div className="p-4 space-y-2">
                    {items.map(item => (
                      <div
                        key={item.id}
                        className={`flex items-start space-x-3 p-3 rounded-lg transition-colors ${
                          checkedItems.has(item.id) ? 'bg-gray-700/30' : 'hover:bg-gray-700/20'
                        }`}
                      >
                        <button
                          onClick={() => item.action ? item.action() : handleItemToggle(item.id)}
                          className={`mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                            checkedItems.has(item.id)
                              ? 'bg-green-600 border-green-600'
                              : 'border-gray-500 hover:border-gray-400'
                          }`}
                        >
                          {checkedItems.has(item.id) && (
                            <Check className="w-3 h-3 text-white" />
                          )}
                        </button>
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <p className={`font-medium ${
                              checkedItems.has(item.id) ? 'text-gray-400 line-through' : 'text-white'
                            }`}>
                              {item.title}
                            </p>
                            {item.required && (
                              <span className="text-xs text-red-400 font-medium">Required</span>
                            )}
                          </div>
                          <p className="text-sm text-gray-400 mt-0.5">{item.description}</p>
                          {item.id === 'copy-order' && (
                            <div className="mt-2">
                              <CopyButton
                                text={generateOrderText()}
                                buttonText="Copy Order Details"
                                onCopy={() => handleItemToggle('copy-order')}
                                size="sm"
                                variant="outline"
                              />
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )
      })}

      {/* Complete Button */}
      {allRequiredComplete && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <button
            onClick={onComplete}
            className="w-full py-3 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center space-x-2"
          >
            <Check className="w-5 h-5" />
            <span>Complete Execution Workflow</span>
          </button>
        </motion.div>
      )}

      {/* Warning if not all required items are complete */}
      {!allRequiredComplete && checkedItems.size > 0 && (
        <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-4">
          <div className="flex items-start space-x-2">
            <AlertCircle className="w-5 h-5 text-yellow-400 mt-0.5" />
            <div>
              <p className="text-yellow-400 font-medium">Required Items Incomplete</p>
              <p className="text-yellow-300 text-sm mt-1">
                Please complete all required checklist items before proceeding.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ExecutionChecklist