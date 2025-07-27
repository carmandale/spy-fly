import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import MarketStatusBar from './MarketStatusBar';
import SentimentPanel from './SentimentPanel';
import RecommendedSpreadsPanel from './RecommendedSpreadsPanel';
import LivePLMonitorPanel from './LivePLMonitorPanel';
interface MarketData {
  spyPrice: number;
  spyChange: number;
  vix: number;
  sessionStatus: 'pre-market' | 'open' | 'closed';
  timeToClose: string;
  apiStatus: 'connected' | 'disconnected' | 'reconnecting';
}
interface SentimentData {
  overallScore: number;
  decision: 'PROCEED' | 'SKIP';
  components: {
    vix: number;
    futures: number;
    technical: number;
    news: number;
  };
}
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
const SPYBullCallSpreadDashboard: React.FC = () => {
  const [marketData, setMarketData] = useState<MarketData>({
    spyPrice: 485.67,
    spyChange: 2.34,
    vix: 18.45,
    sessionStatus: 'open',
    timeToClose: '3h 42m',
    apiStatus: 'connected'
  });
  const [sentimentData, setSentimentData] = useState<SentimentData>({
    overallScore: 72,
    decision: 'PROCEED',
    components: {
      vix: 68,
      futures: 75,
      technical: 71,
      news: 74
    }
  });
  const [spreadRecommendations, setSpreadRecommendations] = useState<SpreadRecommendation[]>([{
    id: '1',
    longStrike: 485,
    shortStrike: 490,
    debit: 2.15,
    maxProfit: 2.85,
    maxLoss: 2.15,
    breakeven: 487.15,
    probability: 68,
    quantity: 10,
    expiration: '0DTE'
  }]);
  const [plData, setPLData] = useState<PLData>({
    currentValue: 1850,
    entryValue: 2150,
    unrealizedPL: -300,
    unrealizedPLPercent: -13.95,
    timeDecay: -45,
    alertStatus: 'none'
  });
  const [historicalData, setHistoricalData] = useState<HistoricalData>({
    equityCurve: [{
      date: '2024-01-01',
      value: 10000
    }, {
      date: '2024-01-02',
      value: 10150
    }, {
      date: '2024-01-03',
      value: 9980
    }, {
      date: '2024-01-04',
      value: 10320
    }, {
      date: '2024-01-05',
      value: 10450
    }],
    winRate: 64.2,
    avgProfitLoss: 127.50
  });

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      // Update market data
      setMarketData(prev => ({
        ...prev,
        spyPrice: prev.spyPrice + (Math.random() - 0.5) * 0.5,
        spyChange: prev.spyChange + (Math.random() - 0.5) * 0.1
      }));

      // Update P/L data
      setPLData(prev => ({
        ...prev,
        currentValue: prev.currentValue + (Math.random() - 0.5) * 50,
        unrealizedPL: prev.unrealizedPL + (Math.random() - 0.5) * 25,
        timeDecay: prev.timeDecay - Math.random() * 2
      }));
    }, 2000);
    return () => clearInterval(interval);
  }, []);
  return <div className="min-h-screen bg-gray-900 text-white font-mono">
      <div className="container mx-auto p-4 max-w-7xl">
        {/* Market Status Bar */}
        <MarketStatusBar marketData={marketData} />
        
        {/* Main Dashboard Grid */}
        <motion.div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6 mt-6" initial={{
        opacity: 0,
        y: 20
      }} animate={{
        opacity: 1,
        y: 0
      }} transition={{
        duration: 0.5
      }}>
          {/* Sentiment Panel - Takes full width on mobile, spans 2 columns on xl */}
          <div className="xl:col-span-2">
            <SentimentPanel sentimentData={sentimentData} />
          </div>
          
          {/* Live P/L Monitor */}
          <div className="lg:col-span-1">
            <LivePLMonitorPanel plData={plData} historicalData={historicalData} />
          </div>
          
          {/* Recommended Spreads - Full width on smaller screens */}
          <div className="lg:col-span-2 xl:col-span-3">
            <RecommendedSpreadsPanel recommendations={spreadRecommendations} />
          </div>
        </motion.div>
      </div>
    </div>;
};
export default SPYBullCallSpreadDashboard;