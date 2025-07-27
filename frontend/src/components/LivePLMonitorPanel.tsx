import React from 'react';
import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Clock, AlertCircle } from 'lucide-react';
interface PLData {
  currentValue: number;
  entryValue: number;
  unrealizedPL: number;
  unrealizedPLPercent: number;
  timeDecay: number;
  alertStatus: 'none' | 'profit-target' | 'stop-loss';
}
interface HistoricalData {
  equityCurve: Array<{
    date: string;
    value: number;
  }>;
  winRate: number;
  avgProfitLoss: number;
}
interface LivePLMonitorPanelProps {
  plData: PLData;
  historicalData: HistoricalData;
}
const LivePLMonitorPanel: React.FC<LivePLMonitorPanelProps> = ({
  plData,
  historicalData
}) => {
  const getPLColor = (value: number) => {
    return value >= 0 ? 'text-green-400' : 'text-red-400';
  };
  const getAlertIcon = (status: string) => {
    switch (status) {
      case 'profit-target':
        return <TrendingUp className="w-5 h-5 text-green-400 animate-pulse" aria-label="Profit target alert" />;
      case 'stop-loss':
        return <AlertCircle className="w-5 h-5 text-red-400 animate-pulse" aria-label="Stop loss alert" />;
      default:
        return null;
    }
  };
  const plBarWidth = Math.min(Math.abs(plData.unrealizedPLPercent), 100);
  return <div className="space-y-6">
      {/* Live P/L Monitor */}
      <motion.section className="bg-gray-800 border border-gray-700 rounded-lg p-6" initial={{
      opacity: 0,
      scale: 0.95
    }} animate={{
      opacity: 1,
      scale: 1
    }} transition={{
      duration: 0.4,
      delay: 0.3
    }}>
        <header className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">Live P/L Monitor</h2>
          {getAlertIcon(plData.alertStatus)}
        </header>

        {/* Current P/L Display */}
        <div className="space-y-4">
          <div className="text-center">
            <div className={`text-3xl font-bold ${getPLColor(plData.unrealizedPL)}`}>
              <strong>
                {plData.unrealizedPL >= 0 ? '+' : ''}${plData.unrealizedPL.toFixed(0)}
              </strong>
            </div>
            <div className={`text-lg ${getPLColor(plData.unrealizedPLPercent)}`}>
              <strong>
                ({plData.unrealizedPLPercent >= 0 ? '+' : ''}{plData.unrealizedPLPercent.toFixed(2)}%)
              </strong>
            </div>
          </div>

          {/* P/L Progress Bar */}
          <div className="relative">
            <div className="w-full h-4 bg-gray-700 rounded-full overflow-hidden" role="progressbar" aria-valuenow={Math.abs(plData.unrealizedPLPercent)} aria-valuemin={0} aria-valuemax={100} aria-label={`P/L percentage: ${plData.unrealizedPLPercent.toFixed(2)}%`}>
              <motion.div className={`h-full ${plData.unrealizedPL >= 0 ? 'bg-green-400' : 'bg-red-400'}`} initial={{
              width: 0
            }} animate={{
              width: `${plBarWidth}%`
            }} transition={{
              duration: 0.5
            }} />
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs font-bold text-white">
                {Math.abs(plData.unrealizedPLPercent).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Position Details */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Entry Value:</span>
              <div className="text-white font-bold">
                <strong>${plData.entryValue.toFixed(0)}</strong>
              </div>
            </div>
            <div>
              <span className="text-gray-400">Current Value:</span>
              <div className="text-white font-bold">
                <strong>${plData.currentValue.toFixed(0)}</strong>
              </div>
            </div>
          </div>

          {/* Time Decay */}
          <div className="flex items-center justify-between p-3 bg-gray-900 rounded">
            <div className="flex items-center space-x-2">
              <Clock className="w-4 h-4 text-yellow-400" aria-hidden="true" />
              <span className="text-gray-300 text-sm">Time Decay</span>
            </div>
            <strong className="text-red-400 font-bold">
              ${plData.timeDecay.toFixed(0)}
            </strong>
          </div>
        </div>
      </motion.section>

      {/* Historical Performance */}
      <motion.section className="bg-gray-800 border border-gray-700 rounded-lg p-6" initial={{
      opacity: 0,
      y: 20
    }} animate={{
      opacity: 1,
      y: 0
    }} transition={{
      duration: 0.4,
      delay: 0.4
    }}>
        <h3 className="text-lg font-bold text-white mb-4">Historical Performance</h3>
        
        {/* Equity Curve */}
        <div className="h-32 mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={historicalData.equityCurve}>
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={false} />
              <YAxis hide />
              <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Performance Stats */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="text-center">
            <p className="text-gray-400 mb-1">Win Rate</p>
            <div className="text-green-400 font-bold text-lg">
              <strong>{historicalData.winRate.toFixed(1)}%</strong>
            </div>
          </div>
          <div className="text-center">
            <p className="text-gray-400 mb-1">Avg P/L</p>
            <div className={`font-bold text-lg ${getPLColor(historicalData.avgProfitLoss)}`}>
              <strong>${historicalData.avgProfitLoss.toFixed(0)}</strong>
            </div>
          </div>
        </div>
      </motion.section>
    </div>;
};
export default LivePLMonitorPanel;