import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity, BarChart3 } from 'lucide-react';
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
interface SentimentPanelProps {
  sentimentData: SentimentData;
}
const SentimentPanel: React.FC<SentimentPanelProps> = ({
  sentimentData
}) => {
  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };
  const getDecisionColor = (decision: string) => {
    return decision === 'PROCEED' ? 'text-green-400' : 'text-red-400';
  };
  const componentIcons = {
    vix: <Activity className="w-5 h-5" aria-hidden="true" />,
    futures: <TrendingUp className="w-5 h-5" aria-hidden="true" />,
    technical: <BarChart3 className="w-5 h-5" aria-hidden="true" />,
    news: <TrendingDown className="w-5 h-5" aria-hidden="true" />
  };
  return <motion.section className="bg-gray-800 border border-gray-700 rounded-lg p-6" initial={{
    opacity: 0,
    scale: 0.95
  }} animate={{
    opacity: 1,
    scale: 1
  }} transition={{
    duration: 0.4
  }}>
      <h2 className="text-xl font-bold text-white mb-6">Market Sentiment</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Overall Sentiment Score */}
        <div className="flex flex-col items-center">
          <div className="relative w-32 h-32 mb-4">
            {/* Circular Progress */}
            <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 120 120" role="img" aria-label={`Sentiment score: ${sentimentData.overallScore} out of 100`}>
              <circle cx="60" cy="60" r="50" stroke="currentColor" strokeWidth="8" fill="none" className="text-gray-700" />
              <motion.circle cx="60" cy="60" r="50" stroke="currentColor" strokeWidth="8" fill="none" strokeLinecap="round" className={getScoreColor(sentimentData.overallScore)} strokeDasharray={`${2 * Math.PI * 50}`} initial={{
              strokeDashoffset: 2 * Math.PI * 50
            }} animate={{
              strokeDashoffset: 2 * Math.PI * 50 * (1 - sentimentData.overallScore / 100)
            }} transition={{
              duration: 1,
              ease: "easeOut"
            }} />
            </svg>
            
            {/* Score Text */}
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`text-3xl font-bold ${getScoreColor(sentimentData.overallScore)}`}>
                {sentimentData.overallScore}
              </span>
            </div>
          </div>
          
          {/* Decision */}
          <motion.div className={`text-2xl font-bold ${getDecisionColor(sentimentData.decision)}`} initial={{
          scale: 0.8
        }} animate={{
          scale: 1
        }} transition={{
          duration: 0.3,
          delay: 0.5
        }}>
            <strong>{sentimentData.decision}</strong>
          </motion.div>
        </div>

        {/* Component Breakdown */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-300 mb-4">Components</h3>
          
          <ul className="space-y-4">
            {Object.entries(sentimentData.components).map(([key, value], index) => <motion.li key={key} className="flex items-center justify-between" initial={{
            opacity: 0,
            x: 20
          }} animate={{
            opacity: 1,
            x: 0
          }} transition={{
            duration: 0.3,
            delay: index * 0.1
          }}>
                <div className="flex items-center space-x-3">
                  <div className={getScoreColor(value)}>
                    {componentIcons[key as keyof typeof componentIcons]}
                  </div>
                  <span className="text-gray-300 capitalize font-medium">
                    {key}
                  </span>
                </div>
                
                <div className="flex items-center space-x-3">
                  {/* Mini Progress Bar */}
                  <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
                    <motion.div className={`h-full ${value >= 70 ? 'bg-green-400' : value >= 50 ? 'bg-yellow-400' : 'bg-red-400'}`} initial={{
                  width: 0
                }} animate={{
                  width: `${value}%`
                }} transition={{
                  duration: 0.8,
                  delay: index * 0.1
                }} />
                  </div>
                  
                  <strong className={`font-bold text-sm ${getScoreColor(value)}`}>
                    {value}
                  </strong>
                </div>
              </motion.li>)}
          </ul>
        </div>
      </div>
    </motion.section>;
};
export default SentimentPanel;