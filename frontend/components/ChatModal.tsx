import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface Question {
  agent: string
  question: string
  context?: string
}

interface ChatModalProps {
  isOpen: boolean
  onClose: () => void
  questions: Question[]
  onSubmit: (answer: string) => void
}

export default function ChatModal({ isOpen, onClose, questions, onSubmit }: ChatModalProps) {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState<string[]>([])
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (isOpen && questions.length > 0) {
      setCurrentQuestionIndex(0)
      setAnswers(new Array(questions.length).fill(''))
      setCurrentAnswer('')
    }
  }, [isOpen, questions])

  const currentQuestion = questions[currentQuestionIndex]

  const handleNext = () => {
    const newAnswers = [...answers]
    newAnswers[currentQuestionIndex] = currentAnswer
    setAnswers(newAnswers)

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
      setCurrentAnswer(newAnswers[currentQuestionIndex + 1] || '')
    }
  }

  const handlePrevious = () => {
    const newAnswers = [...answers]
    newAnswers[currentQuestionIndex] = currentAnswer
    setAnswers(newAnswers)

    setCurrentQuestionIndex(currentQuestionIndex - 1)
    setCurrentAnswer(newAnswers[currentQuestionIndex - 1] || '')
  }

  const handleSubmit = async () => {
    const newAnswers = [...answers]
    newAnswers[currentQuestionIndex] = currentAnswer
    
    setIsSubmitting(true)
    try {
      // Combine all answers into a single response
      const combinedAnswer = newAnswers.map((answer, index) => {
        return `Q${index + 1}: ${questions[index].question}\nA${index + 1}: ${answer}`
      }).join('\n\n')
      
      await onSubmit(combinedAnswer)
      onClose()
    } catch (error) {
      console.error('Failed to submit answers:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen || questions.length === 0) return null

  const isLastQuestion = currentQuestionIndex === questions.length - 1
  const isFirstQuestion = currentQuestionIndex === 0
  const canProceed = currentAnswer.trim().length > 0

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white dark:bg-secondary-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-secondary-200 dark:border-secondary-700">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="domine-subhead text-xl font-semibold text-secondary-900 dark:text-white">
                  Clarification Needed
                </h2>
                <p className="dm-sans-small-400 text-secondary-500 dark:text-secondary-400 mt-1">
                  Question {currentQuestionIndex + 1} of {questions.length} • From {currentQuestion?.agent} agent
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-2 text-secondary-400 hover:text-secondary-600 dark:hover:text-secondary-300 transition-colors"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="px-6 py-2">
            <div className="flex items-center space-x-2">
              {questions.map((_, index) => (
                <div
                  key={index}
                  className={`h-2 flex-1 rounded-full transition-colors ${
                    index < currentQuestionIndex
                      ? 'bg-success-500'
                      : index === currentQuestionIndex
                      ? 'bg-primary-500'
                      : 'bg-secondary-200 dark:bg-secondary-600'
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="px-6 py-6 flex-1 overflow-y-auto">
            {currentQuestion && (
              <div className="space-y-6">
                {/* Context */}
                {currentQuestion.context && (
                  <div className="card bg-primary-50 dark:bg-primary-900/20 border-primary-200 dark:border-primary-800">
                    <h4 className="dm-sans-body-500 font-medium text-primary-900 dark:text-primary-100 mb-2">
                      Context
                    </h4>
                    <p className="dm-sans-small-400 text-primary-700 dark:text-primary-300">
                      {currentQuestion.context}
                    </p>
                  </div>
                )}

                {/* Question */}
                <div>
                  <label className="block dm-sans-body-500 font-medium text-secondary-900 dark:text-white mb-3">
                    {currentQuestion.question}
                  </label>
                  <textarea
                    value={currentAnswer}
                    onChange={(e) => setCurrentAnswer(e.target.value)}
                    rows={4}
                    className="w-full px-3 py-2 border border-secondary-300 dark:border-secondary-600 rounded-md shadow-sm bg-white dark:bg-secondary-700 text-secondary-900 dark:text-white placeholder-secondary-500 dark:placeholder-secondary-400 focus:ring-primary-500 focus:border-primary-500 resize-none"
                    placeholder="Please provide your answer here..."
                  />
                  <div className="mt-2 flex items-center justify-between">
                    <p className="dm-sans-caption-300 text-secondary-500 dark:text-secondary-400">
                      Be as specific and detailed as possible
                    </p>
                    <p className="dm-sans-caption-300 text-secondary-400 dark:text-secondary-500">
                      {currentAnswer.length} characters
                    </p>
                  </div>
                </div>

                {/* AI Assistant Tip */}
                <div className="card bg-secondary-50 dark:bg-secondary-800/50 border-secondary-200 dark:border-secondary-700">
                  <div className="flex items-start space-x-3">
                    <svg className="h-5 w-5 text-secondary-500 dark:text-secondary-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                      <h5 className="dm-sans-body-500 font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                        Why is this question being asked?
                      </h5>
                      <p className="dm-sans-caption-300 text-secondary-600 dark:text-secondary-400">
                        The AI agent needs additional context to provide accurate legal analysis. Your response helps ensure the generated documents are relevant and comprehensive.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-secondary-200 dark:border-secondary-700 bg-secondary-50 dark:bg-secondary-800/50">
            <div className="flex items-center justify-between">
              <button
                onClick={handlePrevious}
                disabled={isFirstQuestion}
                className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Previous
              </button>

              <div className="flex items-center space-x-3">
                {!isLastQuestion ? (
                  <button
                    onClick={handleNext}
                    disabled={!canProceed}
                    className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                    <svg className="h-4 w-4 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                ) : (
                  <button
                    onClick={handleSubmit}
                    disabled={!canProceed || isSubmitting}
                    className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSubmitting ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Submitting...
                      </>
                    ) : (
                      <>
                        Submit Answers
                        <svg className="h-4 w-4 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
