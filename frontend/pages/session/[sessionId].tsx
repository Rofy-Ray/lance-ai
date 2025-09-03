import React, { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/router'
import Layout from '../../components/Layout'
import ProgressStepper from '../../components/ProgressStepper'
import ChatModal from '../../components/ChatModal'
import ArtifactPanel from '../../components/ArtifactPanel'
import DeleteModal from '../../components/DeleteModal'
import { motion } from 'framer-motion'
import axios from 'axios'
import { toast } from 'react-hot-toast'

interface SessionStatus {
  session_id: string
  status: 'uploading' | 'processing' | 'waiting_for_input' | 'completed' | 'requires_review' | 'error' | 'deleted'
  progress: number
  current_stage: string
  current_step: string
  current_agent?: string | null
  step_progress: number
  detailed_status_message: string
  estimated_completion_time?: string
  agents_completed?: string[]
  agents_failed?: string[]
  completed_stages?: string[]
  failed_stages?: string[]
  created_at: string
  expires_at: string
  artifacts_available: string[]
  artifacts_ready: boolean
  message: string
  has_clarifying_questions: boolean
  clarifying_questions: Array<{
    agent: string
    question: string
    context?: string
  }>
  pending_questions?: Array<{
    agent: string
    question: string
    context?: string
  }>
  error_message?: string
  step_start_time?: string
}

const AGENT_STEPS = [
  { id: 'intake', name: 'Intake Analysis', description: 'Analyzing documents and extracting key information' },
  { id: 'analysis', name: 'Legal Analysis', description: 'Mapping incidents to legal elements' },
  { id: 'psla', name: 'PSLA Classification', description: 'Classifying post-separation legal abuse patterns' },
  { id: 'hearing_pack', name: 'Hearing Pack', description: 'Generating court-ready hearing materials' },
  { id: 'client_letter', name: 'Client Letter', description: 'Creating plain-language summary for client' },
  { id: 'declaration', name: 'Declaration', description: 'Drafting formal court declaration' },
  { id: 'research', name: 'Legal Research', description: 'Finding relevant legal authorities' },
  { id: 'quality_gate', name: 'Quality Review', description: 'Final quality assessment and validation' }
]

export default function SessionPage() {
  const router = useRouter()
  const { sessionId } = router.query
  const [sessionStatus, setSessionStatus] = useState<SessionStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showChatModal, setShowChatModal] = useState(false)
  const [showArtifacts, setShowArtifacts] = useState(false)
  const [artifactsAutoOpened, setArtifactsAutoOpened] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)
  const [countdownText, setCountdownText] = useState<string>('')
  const [countdownInterval, setCountdownInterval] = useState<NodeJS.Timeout | null>(null)
  const [deletionInProgress, setDeletionInProgress] = useState(false)
  const [autoDeleteAttempted, setAutoDeleteAttempted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Refs to prevent race conditions and ensure cleanup
  const deletionInProgressRef = useRef(false)
  const autoDeleteAttemptedRef = useRef(false)
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const componentMountedRef = useRef(true)

  // Fetch session status
  const fetchSessionStatus = async () => {
    if (!sessionId || typeof sessionId !== 'string') return

    try {
      const response = await axios.get(`/api/session/${sessionId}/status`)
      const status: SessionStatus = response.data
      setSessionStatus(status)
      setLoading(false)
      setError(null)

      // Stop polling if session is completed, error, or deleted
      if (['completed', 'requires_review', 'error', 'deleted'].includes(status.status)) {
        if (pollingInterval) {
          clearInterval(pollingInterval)
          setPollingInterval(null)
        }
      }

      // Show chat modal if there are pending questions (automatically open modal)
      if (status.status === 'waiting_for_input' && status.pending_questions && status.pending_questions.length > 0 && !showChatModal) {
        setShowChatModal(true)
      }

      // Show artifacts panel if artifacts are ready (only once)
      if ((status.status === 'completed' || status.status === 'requires_review') && 
          status.artifacts_ready && status.artifacts_available && status.artifacts_available.length > 0 && 
          !artifactsAutoOpened) {
        console.log('Opening artifacts modal - artifacts ready:', status.artifacts_available)
        setShowArtifacts(true)
        setArtifactsAutoOpened(true)
        // Show completion notification
        if (!localStorage.getItem(`notified_${sessionId}`)) {
          toast.success('Analysis complete! Your legal documents are ready for download.')
          localStorage.setItem(`notified_${sessionId}`, 'true')
        }
        
        // Start countdown timer
        const cleanup = updateCountdown(status.expires_at)
        return cleanup
      } else if ((status.status === 'completed' || status.status === 'requires_review') && 
                 status.artifacts_ready && artifactsAutoOpened) {
        // Just update countdown for already completed sessions without reopening modal
        const cleanup = updateCountdown(status.expires_at)
        return cleanup
      }

    } catch (err: any) {
      console.error('Failed to fetch session status:', err)
      console.error('Error details:', {
        status: err.response?.status,
        data: err.response?.data,
        message: err.message
      })
      
      // Handle specific error cases
      if (err.response?.status === 404) {
        setError('Session not found or has expired')
        // Immediately stop polling and redirect to home
        if (pollingInterval) {
          clearInterval(pollingInterval)
          setPollingInterval(null)
        }
        // Redirect to home page after a brief delay
        setTimeout(() => {
          router.push('/')
        }, 2000)
      } else if (err.response?.status === 500) {
        setError('Server error occurred')
      } else {
        setError('Failed to connect to server')
      }
      
      // Stop polling on any error
      if (pollingInterval) {
        clearInterval(pollingInterval)
        setPollingInterval(null)
      }
    } finally {
      setLoading(false)
    }
  }

  // Start processing
  const startProcessing = async () => {
    if (!sessionId || typeof sessionId !== 'string') return

    try {
      await axios.post(`/api/session/${sessionId}/start`)
      toast.success('Processing started!')
      
      // Start polling for status updates
      const interval = setInterval(fetchSessionStatus, 2000)
      setPollingInterval(interval)
      
    } catch (err: any) {
      console.error('Failed to start processing:', err)
      toast.error(err.response?.data?.detail || 'Failed to start processing')
    }
  }

  // Handle chat response
  const handleChatResponse = async (response: string) => {
    try {
      setIsSubmitting(true)
      
      // Parse the response to extract structured answers
      let answers: { [key: string]: string } = {}
      try {
        // Try to parse as JSON first
        const parsed = JSON.parse(response)
        if (typeof parsed === 'object' && parsed !== null) {
          answers = parsed
        } else {
          // Fallback: create a single answer
          answers = { 'general_response': response }
        }
      } catch {
        // If parsing fails, create a single answer entry
        answers = { 'general_response': response }
      }
      
      const apiResponse = await fetch(`/api/session/${sessionId}/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ answers })
      })
      
      if (!apiResponse.ok) {
        const errorData = await apiResponse.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to submit answers')
      }
      
      const result = await apiResponse.json()
      
      // Close both modals and resume polling
      setShowChatModal(false)
      
      // Resume polling to track progress
      if (!pollingInterval) {
        const intervalId = setInterval(fetchSessionStatus, 2000)
        setPollingInterval(intervalId)
      }
      
      // Force an immediate status fetch to see progress continue
      await fetchSessionStatus()
      
      toast.success('Answers submitted successfully! Continuing analysis...')
      
    } catch (error: any) {
      toast.error(error.message || 'Failed to submit answers')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle session deletion
  const handleDeleteSession = async () => {
    if (!sessionId || typeof sessionId !== 'string' || deletionInProgressRef.current) return

    // Immediately set refs to prevent race conditions
    deletionInProgressRef.current = true
    setDeletionInProgress(true)
    
    // Clear all intervals immediately using refs
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
      setPollingInterval(null)
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current)
      countdownIntervalRef.current = null
      setCountdownInterval(null)
    }

    try {
      await axios.delete(`/api/session/${sessionId}`)
      toast.success('Session deleted successfully!')
      router.push('/')
    } catch (error: any) {
      
      // Handle different error scenarios
      if (error.response?.status === 404) {
        // Session already deleted (likely by TTL cleanup) - don't reset deletion flags
        if (componentMountedRef.current) {
          toast.success('Session has already been cleaned up')
          router.push('/')
        }
      } else if (error.response?.status === 500) {
        // For 500 errors, don't show toast and don't reset flags to prevent retries
        if (componentMountedRef.current) {
          router.push('/')
        }
      } else if (error.code === 'NETWORK_ERROR' || !error.response) {
        // Only reset on actual network errors
        deletionInProgressRef.current = false
        setDeletionInProgress(false)
        if (componentMountedRef.current) {
          toast.error('Network error. Please check your connection and try again.')
        }
      } else {
        // Reset for other errors that might be temporary
        deletionInProgressRef.current = false
        setDeletionInProgress(false)
        if (componentMountedRef.current) {
          const errorMessage = error.response?.data?.detail || error.message || 'Failed to delete session'
          toast.error(errorMessage)
        }
      }
    }
  }

  // Update countdown timer
  const updateCountdown = (expiresAt: string) => {
    // Clear any existing countdown interval first using refs
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current)
      countdownIntervalRef.current = null
      setCountdownInterval(null)
    }

    const updateTimer = () => {
      const now = new Date().getTime()
      const expiry = new Date(expiresAt).getTime()
      const timeLeft = expiry - now

      if (timeLeft <= 0) {
        setCountdownText('Files have expired')
        // Auto-delete session only if not already attempted and not in progress (use refs for immediate check)
        if (!deletionInProgressRef.current && !autoDeleteAttemptedRef.current && componentMountedRef.current) {
          
          // Immediately set refs to prevent any other timers from triggering
          deletionInProgressRef.current = true
          autoDeleteAttemptedRef.current = true
          setDeletionInProgress(true)
          setAutoDeleteAttempted(true)
          
          // Clear ALL intervals immediately to prevent any repeated firing
          if (countdownIntervalRef.current) {
            clearInterval(countdownIntervalRef.current)
            countdownIntervalRef.current = null
            setCountdownInterval(null)
          }
          
          // Single toast notification with unique ID
          toast('Session expired. Cleaning up files and redirecting...', {
            icon: '⏰',
            id: `session-expired-${sessionId}` // Unique ID per session
          })
          
          // Use immediate async call
          handleDeleteSession().catch(error => {
            console.error('Auto-deletion failed:', error)
            // Don't reset deletion flags on error to prevent retries
          })
        }
        return
      }

      const hours = Math.floor(timeLeft / (1000 * 60 * 60))
      const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60))
      const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000)

      if (hours > 0) {
        setCountdownText(`Files expire in ${hours}h ${minutes}m ${seconds}s`)
      } else if (minutes > 0) {
        setCountdownText(`Files expire in ${minutes}m ${seconds}s`)
      } else {
        setCountdownText(`Files expire in ${seconds}s`)
      }
    }

    updateTimer()
    const newCountdownInterval = setInterval(updateTimer, 1000)
    countdownIntervalRef.current = newCountdownInterval
    setCountdownInterval(newCountdownInterval)
    
    // Clean up on component unmount
    return () => {
      clearInterval(newCountdownInterval)
      countdownIntervalRef.current = null
      setCountdownInterval(null)
    }
  }

  useEffect(() => {
    if (sessionId) {
      fetchSessionStatus()
    }

    return () => {
      // Mark component as unmounted
      componentMountedRef.current = false
      
      // Clear intervals using refs for immediate effect
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current)
        countdownIntervalRef.current = null
      }
      
      // Clear state intervals as well
      if (pollingInterval) {
        clearInterval(pollingInterval)
        setPollingInterval(null)
      }
      if (countdownInterval) {
        clearInterval(countdownInterval)
        setCountdownInterval(null)
      }
      
      // Reset auto-opened flag when component unmounts
      setArtifactsAutoOpened(false)
    }
  }, [sessionId])

  // Enhanced polling with dynamic intervals
  useEffect(() => {
    if (sessionStatus && ['processing', 'waiting_for_input'].includes(sessionStatus.status)) {
      // Faster polling during active processing (1 second)
      const interval = setInterval(() => {
        fetchSessionStatus()
      }, 1000)
      pollingIntervalRef.current = interval
      setPollingInterval(interval)
    } else if (sessionStatus && sessionStatus.status === 'uploading') {
      // Medium polling for uploading (2 seconds)
      const interval = setInterval(fetchSessionStatus, 2000)
      pollingIntervalRef.current = interval
      setPollingInterval(interval)
    } else if (sessionStatus && ['completed', 'requires_review', 'error', 'deleted'].includes(sessionStatus.status)) {
      // STOP all polling for final states
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
      if (pollingInterval) {
        clearInterval(pollingInterval)
        setPollingInterval(null)
      }
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
      if (pollingInterval) {
        clearInterval(pollingInterval)
        setPollingInterval(null)
      }
    }
  }, [sessionStatus?.status])

  if (loading) {
    return (
      <Layout title="Loading Session - Lance AI">
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600 mx-auto mb-4"></div>
            <p className="dm-sans-body-400 text-secondary-600 dark:text-secondary-400">Loading session...</p>
          </div>
        </div>
      </Layout>
    )
  }

  if (error || !sessionStatus) {
    return (
      <Layout title="Session Error - Lance AI">
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center max-w-md">
            <svg className="h-16 w-16 text-danger-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <h1 className="domine-subhead text-xl font-semibold text-secondary-900 dark:text-white mb-2">
              Session Error
            </h1>
            <p className="dm-sans-body-400 text-secondary-600 dark:text-secondary-400 mb-6">
              {error}
            </p>
            <button
              onClick={() => router.push('/')}
              className="btn-primary"
            >
              Return Home
            </button>
          </div>
        </div>
      </Layout>
    )
  }

  // Fix timezone handling - ensure we're comparing UTC times consistently
  const expiryTime = new Date(sessionStatus.expires_at).getTime()
  const currentTime = Date.now()
  const timeRemaining = Math.max(0, expiryTime - currentTime)
  const totalMinutesRemaining = Math.floor(timeRemaining / (1000 * 60))
  const hoursRemaining = Math.floor(totalMinutesRemaining / 60)
  const minutesRemaining = totalMinutesRemaining % 60

  return (
    <Layout title={`Session ${sessionId.slice(-8)} - Lance AI`}>
      <div className="min-h-screen bg-secondary-50 dark:bg-secondary-900">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8">
            <div>
              <h1 className="domine-title-lg text-3xl font-bold text-secondary-900 dark:text-white">
                Analysis Session
              </h1>
              <p className="dm-sans-body-400 text-secondary-600 dark:text-secondary-400 mt-2">
                Session ID: {sessionId}
              </p>
            </div>
            
            <div className="flex items-center space-x-4 mt-4 sm:mt-0">
              {/* Timer - show countdown for completed sessions with artifacts */}
              {(sessionStatus.status === 'completed' || sessionStatus.status === 'requires_review') && sessionStatus.artifacts_ready && countdownText && (
                <div className="flex items-center space-x-2 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <svg className="h-5 w-5 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="dm-sans-small-400 font-medium text-red-700 dark:text-red-300">
                    {countdownText}
                  </span>
                </div>
              )}

              {/* Delete Button */}
              <button
                onClick={() => setShowDeleteModal(true)}
                className="btn-danger"
              >
                Delete Session
              </button>
            </div>
          </div>

          {/* Status Banner */}
          {sessionStatus.status === 'uploading' && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card bg-primary-50 dark:bg-primary-900/20 border-primary-200 dark:border-primary-800 mb-8"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                  <div>
                    <h3 className="dm-sans-body-500 font-medium text-primary-900 dark:text-primary-100">
                      Documents Uploaded
                    </h3>
                    <p className="dm-sans-small-400 text-primary-700 dark:text-primary-300">
                      Ready to begin analysis
                    </p>
                  </div>
                </div>
                <button
                  onClick={startProcessing}
                  className="btn-primary"
                >
                  Start Analysis
                </button>
              </div>
            </motion.div>
          )}

          {/* Processing Error */}
          {sessionStatus.status === 'error' && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card bg-danger-50 dark:bg-danger-900/20 border-danger-200 dark:border-danger-800 mb-8"
            >
              <div className="flex items-center space-x-3">
                <svg className="h-8 w-8 text-danger-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <div>
                  <h3 className="dm-sans-body-500 font-medium text-danger-900 dark:text-danger-100">
                    Processing Error
                  </h3>
                  <p className="dm-sans-small-400 text-danger-700 dark:text-danger-300">
                    {sessionStatus.error_message || 'An error occurred during processing'}
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Progress Stepper */}
          <ProgressStepper
            steps={AGENT_STEPS}
            currentStep={sessionStatus.current_step || sessionStatus.current_agent || sessionStatus.current_stage}
            completedSteps={sessionStatus.completed_stages || sessionStatus.agents_completed || []}
            failedSteps={sessionStatus.failed_stages || sessionStatus.agents_failed || []}
            status={sessionStatus.status}
            stepProgress={sessionStatus.step_progress || 0}
            detailedStatusMessage={sessionStatus.detailed_status_message || sessionStatus.message || ""}
            artifactsReady={sessionStatus.artifacts_ready}
            onViewDocuments={() => setShowArtifacts(true)}
          />

          {/* Waiting for Input Banner */}
          {sessionStatus.status === 'waiting_for_input' && sessionStatus.pending_questions && sessionStatus.pending_questions.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
            >
              <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="bg-gradient-to-r from-orange-50 to-amber-50 dark:from-orange-900/20 dark:to-amber-900/20 rounded-xl shadow-2xl max-w-lg w-full border border-orange-200 dark:border-orange-800 overflow-hidden"
              >
                {/* Header */}
                <div className="px-6 py-4 bg-gradient-to-r from-orange-500 to-amber-500 text-white">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-white bg-opacity-20 rounded-full">
                      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="domine-subhead text-xl font-semibold">
                        Clarification Needed
                      </h2>
                      <p className="dm-sans-small-400 text-orange-100">
                        The AI needs additional information to continue analysis
                      </p>
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="px-6 py-6">
                  <div className="text-center space-y-4">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-100 dark:bg-orange-900/30 rounded-full">
                      <svg className="h-8 w-8 text-orange-600 dark:text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="dm-sans-body-500 font-semibold text-secondary-900 dark:text-white mb-2">
                        {sessionStatus.pending_questions.length} Question{sessionStatus.pending_questions.length > 1 ? 's' : ''} Remaining
                      </h3>
                      <p className="dm-sans-small-400 text-secondary-600 dark:text-secondary-400">
                        To provide the most accurate legal analysis, we need a few additional details from you.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 bg-secondary-50 dark:bg-secondary-800/50 border-t border-orange-200 dark:border-orange-800">
                  <div className="flex justify-center space-x-3">
                    <button
                      onClick={() => setShowChatModal(true)}
                      className="px-6 py-3 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white font-medium rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2"
                    >
                      <svg className="h-5 w-5 mr-2 inline-block" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                      </svg>
                      Answer Questions
                    </button>
                  </div>
                  <p className="dm-sans-caption-300 text-center text-secondary-500 dark:text-secondary-400 mt-3">
                    This should only take a minute
                  </p>
                </div>
              </motion.div>
            </motion.div>
          )}
        </div>

        {/* Modals */}
        <ChatModal
          isOpen={showChatModal}
          onClose={() => setShowChatModal(false)}
          questions={sessionStatus.pending_questions || []}
          onSubmit={handleChatResponse}
        />

        <ArtifactPanel
          isOpen={showArtifacts}
          onClose={() => setShowArtifacts(false)}
          sessionId={sessionStatus.session_id}
          artifacts={sessionStatus.artifacts_available}
        />

        <DeleteModal
          isOpen={showDeleteModal}
          onClose={() => setShowDeleteModal(false)}
          onConfirm={handleDeleteSession}
          sessionId={sessionStatus.session_id}
        />
      </div>
    </Layout>
  )
}
