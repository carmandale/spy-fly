import React from 'react';
import { motion } from 'framer-motion';
import { Copy, TrendingUp, Target, AlertTriangle } from 'lucide-react';
interface SpreadRecommendation {
  id: string;
  longStrike: number;
  shortStrike: number;
  debit: number;
  maxProfit: number;
  maxLoss: number;
  breakeven: number;
  probability: number;
  quantity: number;
  expiration: string;
}
interface RecommendedSpreadsPanelProps {
  recommendations: SpreadRecommendation[];
}
const RecommendedSpreadsPanel: React.FC<RecommendedSpreadsPanelProps> = ({
  recommendations
}) => {
  const copyToClipboard = (spread: SpreadRecommendation) => {
    const orderDetails = `
SPY Bull Call Spread (${spread.expiration})
Long: ${spread.quantity} x $${spread.longStrike} Call
Short: ${spread.quantity} x $${spread.shortStrike} Call
Net Debit: $${spread.debit.toFixed(2)}
Max Profit: $${spread.maxProfit.toFixed(2)}
Max Loss: $${spread.maxLoss.toFixed(2)}
Breakeven: $${spread.breakeven.toFixed(2)}
Probability: ${spread.probability}%
    `.trim();
    navigator.clipboard.writeText(orderDetails);
  };
  return <motion.section className="bg-gray-800 border border-gray-700 rounded-lg p-6" initial={{
    opacity: 0,
    y: 20
  }} animate={{
    opacity: 1,
    y: 0
  }} transition={{
    duration: 0.4,
    delay: 0.2
  }}>
      <header className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-white">Recommended Spreads</h2>
        <div className="flex items-center space-x-2 text-green-400">
          <TrendingUp className="w-5 h-5" aria-hidden="true" />
          <span className="text-sm font-medium">Bull Call Spreads</span>
        </div>
      </header>

      <div className="space-y-4">
        {recommendations.map((spread, index) => <motion.article key={spread.id} className="bg-gray-900 border border-gray-600 rounded-lg p-4" initial={{
        opacity: 0,
        x: -20
      }} animate={{
        opacity: 1,
        x: 0
      }} transition={{
        duration: 0.3,
        delay: index * 0.1
      }}>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Strike Prices */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400">Strikes</h3>
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-green-400 text-xs font-bold">LONG</span>
                    <strong className="text-white font-bold">${spread.longStrike}</strong>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-red-400 text-xs font-bold">SHORT</span>
                    <strong className="text-white font-bold">${spread.shortStrike}</strong>
                  </div>
                </div>
              </div>

              {/* Cost & Profit */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400">Cost & Profit</h3>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-gray-300 text-sm">Debit:</span>
                    <strong className="text-red-400 font-bold">${spread.debit.toFixed(2)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300 text-sm">Max Profit:</span>
                    <strong className="text-green-400 font-bold">${spread.maxProfit.toFixed(2)}</strong>
                  </div>
                </div>
              </div>

              {/* Risk & Probability */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400">Risk Analysis</h3>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-gray-300 text-sm">Breakeven:</span>
                    <strong className="text-yellow-400 font-bold">${spread.breakeven.toFixed(2)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-300 text-sm">Probability:</span>
                    <strong className="text-blue-400 font-bold">{spread.probability}%</strong>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400">Actions</h3>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Target className="w-4 h-4 text-gray-400" aria-hidden="true" />
                    <span className="text-sm text-gray-300">Qty: <strong>{spread.quantity}</strong></span>
                  </div>
                  <motion.button onClick={() => copyToClipboard(spread)} className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 
                             text-white px-3 py-1 rounded text-sm font-medium transition-colors
                             focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900" whileHover={{
                scale: 1.05
              }} whileTap={{
                scale: 0.95
              }} aria-label={`Copy order details for ${spread.longStrike}/${spread.shortStrike} spread`}>
                    <Copy className="w-4 h-4" aria-hidden="true" />
                    <span>Copy Order</span>
                  </motion.button>
                </div>
              </div>
            </div>

            {/* Risk Warning */}
            <footer className="mt-4 pt-4 border-t border-gray-700">
              <div className="flex items-center space-x-2 text-yellow-400">
                <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                <p className="text-xs">
                  <strong>Risk Warning:</strong> 0DTE options carry high risk. Max loss: <strong>${spread.maxLoss.toFixed(2)}</strong> per spread
                </p>
              </div>
            </footer>
          </motion.article>)}
      </div>
    </motion.section>;
};
export default RecommendedSpreadsPanel;