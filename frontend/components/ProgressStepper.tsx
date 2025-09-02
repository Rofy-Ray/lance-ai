import React from 'react'
import { motion } from 'framer-motion'

interface Step {
  id: string
  name: string
  description: string
}

interface ProgressStepperProps {
  steps: Step[]
  currentStep: string | null
  completedSteps: string[]
  failedSteps: string[]
  status: 'uploading' | 'processing' | 'waiting_for_input' | 'completed' | 'requires_review' | 'error' | 'deleted'
  stepProgress?: number // 0-100 for current step
  detailedStatusMessage?: string
  artifactsReady?: boolean
  onViewDocuments?: () => void
}

export default function ProgressStepper({
  steps,
  currentStep,
  completedSteps = [],
  failedSteps = [],
  status,
  stepProgress = 0,
  detailedStatusMessage = "",
  artifactsReady = false,
  onViewDocuments
}: ProgressStepperProps) {
  // Debug logging for progress stepper
  console.log('ProgressStepper props:', {
    currentStep,
    completedSteps,
    failedSteps,
    status,
    stepProgress,
    detailedStatusMessage
  })
  const getStepStatus = (stepId: string) => {
    if (failedSteps.includes(stepId)) return 'failed'
    if (completedSteps.includes(stepId)) return 'completed'
    if (currentStep === stepId && ['processing', 'waiting_for_input'].includes(status)) return 'current'
    if (currentStep && steps.findIndex(s => s.id === currentStep) > steps.findIndex(s => s.id === stepId)) return 'completed'
    return 'pending'
  }

  const getStepIcon = (stepId: string, stepStatus: string) => {
    switch (stepStatus) {
      case 'completed':
        return (
          <svg className="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        )
      case 'failed':
        return (
          <svg className="h-5 w-5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        )
      case 'current':
        return (
          <div className="relative h-5 w-5">
            {/* Circular progress ring */}
            <svg className="h-5 w-5 transform -rotate-90" viewBox="0 0 20 20">
              <circle
                cx="10"
                cy="10"
                r="8"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="text-white/30"
              />
              <motion.circle
                cx="10"
                cy="10"
                r="8"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="text-white"
                strokeLinecap="round"
                strokeDasharray={50.27} // 2 * π * 8
                initial={{ strokeDashoffset: 50.27 }}
                animate={{ strokeDashoffset: 50.27 - (50.27 * stepProgress / 100) }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </svg>
            {/* Center dot */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="h-1.5 w-1.5 bg-white rounded-full animate-pulse"></div>
            </div>
          </div>
        )
      default:
        return (
          <div className="h-3 w-3 border-2 border-secondary-300 dark:border-secondary-600 rounded-full bg-white dark:bg-secondary-800"></div>
        )
    }
  }

  const getStepColor = (stepStatus: string) => {
    switch (stepStatus) {
      case 'completed':
        return 'bg-success-500'
      case 'failed':
        return 'bg-danger-500'
      case 'current':
        return 'bg-primary-500'
      default:
        return 'bg-secondary-300 dark:bg-secondary-600'
    }
  }

  const getConnectorColor = (currentIndex: number) => {
    const currentStepStatus = getStepStatus(steps[currentIndex].id)
    const nextStepStatus = currentIndex < steps.length - 1 ? getStepStatus(steps[currentIndex + 1].id) : 'pending'
    
    if (currentStepStatus === 'completed' || currentStepStatus === 'failed') {
      return 'bg-secondary-300 dark:bg-secondary-600'
    }
    return 'bg-secondary-200 dark:bg-secondary-700'
  }

  return (
    <div className="card">
      <div className="p-6">
        <h2 className="domine-subhead text-xl font-semibold text-secondary-900 dark:text-white mb-6">
          Analysis Progress
        </h2>

        <div className="relative">
          {steps.map((step, index) => {
            const stepStatus = getStepStatus(step.id)
            const isLast = index === steps.length - 1

            return (
              <div key={step.id} className="relative">
                {/* Step */}
                <div className="flex items-start">
                  {/* Icon */}
                  <div className="flex-shrink-0 relative">
                    <motion.div
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: index * 0.1 }}
                      className={`h-10 w-10 rounded-full flex items-center justify-center ${getStepColor(stepStatus)} transition-colors duration-200`}
                    >
                      {getStepIcon(step.id, stepStatus)}
                    </motion.div>
                    
                    {/* Connector line */}
                    {!isLast && (
                      <div 
                        className={`absolute top-10 left-5 w-0.5 h-16 -ml-px ${getConnectorColor(index)} transition-colors duration-200`}
                      />
                    )}
                  </div>

                  {/* Content */}
                  <div className="ml-4 flex-grow pb-8">
                    <motion.div
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 + 0.2 }}
                    >
                      <h3 className={`dm-sans-body-500 font-medium ${
                        stepStatus === 'current' 
                          ? 'text-primary-900 dark:text-primary-100' 
                          : stepStatus === 'completed'
                          ? 'text-success-900 dark:text-success-100'
                          : stepStatus === 'failed'
                          ? 'text-danger-900 dark:text-danger-100'
                          : 'text-secondary-500 dark:text-secondary-400'
                      }`}>
                        {step.name}
                        {stepStatus === 'current' && (
                          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-800 dark:text-primary-200">
                            {stepProgress}% Complete
                          </span>
                        )}
                        {stepStatus === 'failed' && (
                          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-danger-100 dark:bg-danger-900/30 text-danger-800 dark:text-danger-200">
                            Failed
                          </span>
                        )}
                        {status === 'waiting_for_input' && stepStatus === 'current' && (
                          <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-warning-100 dark:bg-warning-900/30 text-warning-800 dark:text-warning-200">
                            Waiting for Input
                          </span>
                        )}
                      </h3>
                      <p className={`dm-sans-small-400 mt-1 ${
                        stepStatus === 'current' 
                          ? 'text-primary-700 dark:text-primary-300' 
                          : stepStatus === 'completed'
                          ? 'text-success-700 dark:text-success-300'
                          : stepStatus === 'failed'
                          ? 'text-danger-700 dark:text-danger-300'
                          : 'text-secondary-400 dark:text-secondary-500'
                      }`}>
                        {step.description}
                      </p>
                      
                      {/* Processing animation for current step */}
                      {stepStatus === 'current' && status === 'processing' && (
                        <div className="mt-3 flex items-center space-x-2">
                          <div className="flex space-x-1">
                            <div className="h-2 w-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                            <div className="h-2 w-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                            <div className="h-2 w-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                          </div>
                          <span className="dm-sans-caption-300 text-primary-600 dark:text-primary-400">
                            {detailedStatusMessage || "Processing..."}
                          </span>
                        </div>
                      )}
                    </motion.div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Summary */}
        <div className="mt-6 pt-6 border-t border-secondary-200 dark:border-secondary-700">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-4">
              <span className="dm-sans-small-400 text-secondary-500 dark:text-secondary-400">
                {completedSteps.length} of {steps.length} completed
              </span>
              {failedSteps.length > 0 && (
                <span className="dm-sans-small-400 text-danger-600 dark:text-danger-400">
                  {failedSteps.length} failed
                </span>
              )}
            </div>
            
            <div className="flex items-center space-x-3">
              {status === 'processing' && (
                <div className="flex items-center space-x-2">
                  <div className="h-2 w-2 bg-primary-500 rounded-full animate-pulse"></div>
                  <span className="dm-sans-small-400 text-primary-600 dark:text-primary-400">
                    Processing
                  </span>
                </div>
              )}
              
              {status === 'completed' && (
                <div className="flex items-center space-x-2">
                  <svg className="h-4 w-4 text-success-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="dm-sans-small-400 text-success-600 dark:text-success-400">
                    Complete
                  </span>
                </div>
              )}
              
              {status === 'requires_review' && (
                <div className="flex items-center space-x-2">
                  <svg className="h-4 w-4 text-success-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="dm-sans-small-400 text-success-600 dark:text-success-400">
                    Complete
                  </span>
                </div>
              )}
              
              {status === 'error' && (
                <div className="flex items-center space-x-2">
                  <svg className="h-4 w-4 text-danger-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                  <span className="dm-sans-small-400 text-danger-600 dark:text-danger-400">
                    Error
                  </span>
                </div>
              )}

              {/* View Documents Button */}
              {artifactsReady && onViewDocuments && (status === 'completed' || status === 'requires_review') && (
                <button
                  onClick={onViewDocuments}
                  className="bg-success-600 hover:bg-success-700 text-white px-4 py-2 rounded-lg font-medium text-sm transition-colors"
                >
                  View Documents
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
