import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronRight, ChevronLeft, Check, AlertCircle, FileText, Shield, Send } from 'lucide-react'

interface WizardStep {
  id: number
  title: string
  description: string
  icon: React.ElementType
  status: 'pending' | 'current' | 'completed' | 'error'
}

interface ExecutionWizardProps {
  recommendationId: string
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
  onComplete: () => void
  onCancel: () => void
}

const ExecutionWizard: React.FC<ExecutionWizardProps> = ({
  recommendationId,
  spreadData,
  onComplete,
  onCancel
}) => {
  const [currentStep, setCurrentStep] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set())
  const [errors, setErrors] = useState<Record<number, string>>({})

  const steps: WizardStep[] = [
    {
      id: 0,
      title: 'Review Order',
      description: 'Review spread details and risk parameters',
      icon: FileText,
      status: currentStep === 0 ? 'current' : completedSteps.has(0) ? 'completed' : 'pending'
    },
    {
      id: 1,
      title: 'Validate Risk',
      description: 'Confirm position sizing and risk management',
      icon: Shield,
      status: currentStep === 1 ? 'current' : completedSteps.has(1) ? 'completed' : 'pending'
    },
    {
      id: 2,
      title: 'Generate Order',
      description: 'Create order ticket for your broker',
      icon: FileText,
      status: currentStep === 2 ? 'current' : completedSteps.has(2) ? 'completed' : 'pending'
    },
    {
      id: 3,
      title: 'Execute Trade',
      description: 'Submit order to your broker',
      icon: Send,
      status: currentStep === 3 ? 'current' : completedSteps.has(3) ? 'completed' : 'pending'
    }
  ]

  const handleNext = () => {
    // Mark current step as completed
    setCompletedSteps(prev => new Set([...prev, currentStep]))
    
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      onComplete()
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleStepClick = (stepId: number) => {
    // Only allow navigation to completed steps or the next step
    if (completedSteps.has(stepId) || stepId === currentStep + 1) {
      setCurrentStep(stepId)
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Order Summary</h3>
            <div className="bg-gray-900 rounded-lg p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-400">Strategy:</span>
                <span className="text-white font-medium">Bull Call Spread</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Expiration:</span>
                <span className="text-white font-medium">{spreadData.expiration}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Long Strike:</span>
                <span className="text-white font-medium">${spreadData.longStrike}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Short Strike:</span>
                <span className="text-white font-medium">${spreadData.shortStrike}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Quantity:</span>
                <span className="text-white font-medium">{spreadData.quantity} contracts</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Net Debit:</span>
                <span className="text-white font-medium">${spreadData.debit.toFixed(2)}</span>
              </div>
            </div>
            <div className="bg-gray-900 rounded-lg p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-400">Max Profit:</span>
                <span className="text-green-400 font-medium">${spreadData.maxProfit.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Max Loss:</span>
                <span className="text-red-400 font-medium">${spreadData.maxLoss.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Breakeven:</span>
                <span className="text-white font-medium">${spreadData.breakeven.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Probability:</span>
                <span className="text-white font-medium">{spreadData.probability}%</span>
              </div>
            </div>
          </div>
        )

      case 1:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Risk Validation</h3>
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="space-y-3">
                <div className="flex items-start space-x-2">
                  <Check className="w-5 h-5 text-green-400 mt-0.5" />
                  <div>
                    <p className="text-white font-medium">Position Size Check</p>
                    <p className="text-gray-400 text-sm">Risk is within 5% of buying power</p>
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <Check className="w-5 h-5 text-green-400 mt-0.5" />
                  <div>
                    <p className="text-white font-medium">Risk/Reward Ratio</p>
                    <p className="text-gray-400 text-sm">Meets minimum 1:1 requirement</p>
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <Check className="w-5 h-5 text-green-400 mt-0.5" />
                  <div>
                    <p className="text-white font-medium">Market Hours</p>
                    <p className="text-gray-400 text-sm">Market is open and liquid</p>
                  </div>
                </div>
                <div className="flex items-start space-x-2">
                  <Check className="w-5 h-5 text-green-400 mt-0.5" />
                  <div>
                    <p className="text-white font-medium">Spread Validity</p>
                    <p className="text-gray-400 text-sm">Strikes and expiration are valid</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <AlertCircle className="w-5 h-5 text-yellow-400 mt-0.5" />
                <div>
                  <p className="text-yellow-400 font-medium">Risk Warning</p>
                  <p className="text-yellow-300 text-sm">
                    You could lose up to ${spreadData.maxLoss.toFixed(2)} on this trade.
                    Only proceed if you accept this risk.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )

      case 2:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Order Generation</h3>
            <div className="bg-gray-900 rounded-lg p-4">
              <p className="text-gray-400 mb-3">Select your broker format:</p>
              <div className="space-y-2">
                <button className="w-full text-left px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
                  <p className="text-white font-medium">Interactive Brokers</p>
                  <p className="text-gray-400 text-sm">TWS or IBKR Mobile format</p>
                </button>
                <button className="w-full text-left px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
                  <p className="text-white font-medium">TD Ameritrade</p>
                  <p className="text-gray-400 text-sm">thinkorswim format</p>
                </button>
                <button className="w-full text-left px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
                  <p className="text-white font-medium">E*TRADE</p>
                  <p className="text-gray-400 text-sm">Power E*TRADE format</p>
                </button>
              </div>
            </div>
            <div className="bg-blue-900/20 border border-blue-600/30 rounded-lg p-4">
              <p className="text-blue-400 text-sm">
                Click on your broker to generate the order ticket in the correct format.
                The order details will be copied to your clipboard.
              </p>
            </div>
          </div>
        )

      case 3:
        return (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Execute Trade</h3>
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-medium">
                    1
                  </div>
                  <p className="text-white">Open your broker platform</p>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-medium">
                    2
                  </div>
                  <p className="text-white">Navigate to options trading</p>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-medium">
                    3
                  </div>
                  <p className="text-white">Enter the spread order details</p>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-medium">
                    4
                  </div>
                  <p className="text-white">Review and submit the order</p>
                </div>
              </div>
            </div>
            <div className="bg-green-900/20 border border-green-600/30 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <Check className="w-5 h-5 text-green-400 mt-0.5" />
                <div>
                  <p className="text-green-400 font-medium">Ready to Execute</p>
                  <p className="text-green-300 text-sm">
                    Once you've submitted the order to your broker, click "Complete" to finish the workflow.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center flex-1">
              <button
                onClick={() => handleStepClick(step.id)}
                disabled={!completedSteps.has(step.id) && step.id !== currentStep + 1}
                className={`relative flex items-center justify-center w-10 h-10 rounded-full transition-colors ${
                  step.status === 'completed'
                    ? 'bg-green-600 cursor-pointer'
                    : step.status === 'current'
                    ? 'bg-blue-600'
                    : step.status === 'error'
                    ? 'bg-red-600'
                    : 'bg-gray-700 cursor-not-allowed'
                }`}
              >
                {step.status === 'completed' ? (
                  <Check className="w-5 h-5 text-white" />
                ) : (
                  <span className="text-white font-medium">{step.id + 1}</span>
                )}
              </button>
              {index < steps.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 transition-colors ${
                    completedSteps.has(step.id) ? 'bg-green-600' : 'bg-gray-700'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between mt-2">
          {steps.map(step => (
            <div key={step.id} className="flex-1 text-center">
              <p className={`text-xs ${
                step.status === 'current' ? 'text-blue-400' : 'text-gray-400'
              }`}>
                {step.title}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
          className="min-h-[300px]"
        >
          {renderStepContent()}
        </motion.div>
      </AnimatePresence>

      {/* Navigation Buttons */}
      <div className="flex justify-between mt-8 pt-6 border-t border-gray-700">
        <button
          onClick={currentStep === 0 ? onCancel : handlePrevious}
          className="px-6 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors flex items-center space-x-2"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>{currentStep === 0 ? 'Cancel' : 'Previous'}</span>
        </button>
        <button
          onClick={handleNext}
          className={`px-6 py-2 rounded-lg transition-colors flex items-center space-x-2 ${
            currentStep === steps.length - 1
              ? 'bg-green-600 hover:bg-green-700 text-white'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          <span>{currentStep === steps.length - 1 ? 'Complete' : 'Next'}</span>
          {currentStep !== steps.length - 1 && <ChevronRight className="w-4 h-4" />}
        </button>
      </div>
    </div>
  )
}

export default ExecutionWizard