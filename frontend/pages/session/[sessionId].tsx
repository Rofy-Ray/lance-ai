import React, { useState, useEffect } from 'react'
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
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)
  const [countdownText, setCountdownText] = useState<string>('')

  // Fetch session status
  const fetchSessionStatus = async () => {
    if (!sessionId || typeof sessionId !== 'string') return

    try {
      const response = await axios.get(`/api/session/${sessionId}/status`)
      const status: SessionStatus = response.data
      console.log('Received session status:', status)
      setSessionStatus(status)
      setError(null)

      // Stop polling if session is completed, error, or deleted
      if (['completed', 'requires_review', 'error', 'deleted'].includes(status.status)) {
        if (pollingInterval) {
          clearInterval(pollingInterval)
          setPollingInterval(null)
        }
      }

      // Show chat modal if there are pending questions
      if (status.pending_questions && status.pending_questions.length > 0) {
        setShowChatModal(true)
      }

      // Show artifacts panel if artifacts are ready
      if ((status.status === 'completed' || status.status === 'requires_review') && 
          status.artifacts_ready && status.artifacts_available.length > 0) {
        setShowArtifacts(true)
        // Show completion notification
        if (!localStorage.getItem(`notified_${sessionId}`)) {
          toast.success('Analysis complete! Your legal documents are ready for download.')
          localStorage.setItem(`notified_${sessionId}`, 'true')
        }
        
        // Start countdown timer
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
        console.log('Session 404 - stopping all polling and redirecting')
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
  const handleChatResponse = async (answer: string) => {
    if (!sessionId || typeof sessionId !== 'string') return

    try {
      await axios.post(`/api/session/${sessionId}/answer`, { answer })
      setShowChatModal(false)
      toast.success('Response submitted!')
      
      // Resume polling
      if (!pollingInterval) {
        const interval = setInterval(fetchSessionStatus, 2000)
        setPollingInterval(interval)
      }
      
    } catch (err: any) {
      console.error('Failed to submit answer:', err)
      toast.error(err.response?.data?.detail || 'Failed to submit response')
    }
  }

  // Handle session deletion
  const handleDeleteSession = async () => {
    if (!sessionId || typeof sessionId !== 'string') return

    try {
      await axios.post(`/api/session/${sessionId}/delete`, { confirm: true })
      toast.success('Session deleted successfully')
      router.push('/')
    } catch (err: any) {
      console.error('Failed to delete session:', err)
      toast.error(err.response?.data?.detail || 'Failed to delete session')
    }
  }

  // Update countdown timer
  const updateCountdown = (expiresAt: string) => {
    const updateTimer = () => {
      const now = new Date().getTime()
      const expiry = new Date(expiresAt).getTime()
      const timeLeft = expiry - now

      if (timeLeft <= 0) {
        setCountdownText('Files have expired')
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
    const countdownInterval = setInterval(updateTimer, 1000)
    
    // Clean up on component unmount
    return () => clearInterval(countdownInterval)
  }

  useEffect(() => {
    if (sessionId) {
      fetchSessionStatus()
    }

    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [sessionId])

  // Enhanced polling with dynamic intervals
  useEffect(() => {
    if (sessionStatus && ['processing', 'waiting_for_input'].includes(sessionStatus.status)) {
      // Faster polling during active processing (1 second)
      console.log('Starting fast polling for processing status')
      const interval = setInterval(() => {
        console.log('Polling for status updates...')
        fetchSessionStatus()
      }, 1000)
      setPollingInterval(interval)
    } else if (sessionStatus && sessionStatus.status === 'uploading') {
      // Medium polling for uploading (2 seconds)
      console.log('Starting medium polling for uploading status')
      const interval = setInterval(fetchSessionStatus, 2000)
      setPollingInterval(interval)
    } else {
      // Clear polling for completed/error states
      if (pollingInterval) {
        clearInterval(pollingInterval)
        setPollingInterval(null)
      }
    }

    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
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

  // ... (rest of the code remains the same)

  // Fix timezone handling - ensure we're comparing UTC times consistently
  const expiryTime = new Date(sessionStatus.expires_at).getTime()
  const currentTime = Date.now()
  const timeRemaining = Math.max(0, expiryTime - currentTime)
  const totalMinutesRemaining = Math.floor(timeRemaining / (1000 * 60))
  const hoursRemaining = Math.floor(totalMinutesRemaining / 60)
  const minutesRemaining = totalMinutesRemaining % 60
  
  // Debug logging for time calculation
  console.log('Time debugging:', {
    expires_at: sessionStatus.expires_at,
    current_time: new Date().toISOString(),
    expiryTime,
    currentTime,
    timeRemaining,
    totalMinutesRemaining,
    hoursRemaining,
    minutesRemaining
  })
  
  // Debug session status for progress updates
  console.log('Current session status for progress:', {
    status: sessionStatus.status,
    current_step: sessionStatus.current_step,
    step_progress: sessionStatus.step_progress,
    detailed_status_message: sessionStatus.detailed_status_message,
    completed_stages: sessionStatus.completed_stages,
    current_stage: sessionStatus.current_stage
  })

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
          {sessionStatus.status === 'waiting_for_input' && sessionStatus.pending_questions && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card bg-warning-50 dark:bg-warning-900/20 border-warning-200 dark:border-warning-800 mt-8"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <svg className="h-8 w-8 text-warning-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <h3 className="dm-sans-body-500 font-medium text-warning-900 dark:text-warning-100">
                      Clarification Needed
                    </h3>
                    <p className="dm-sans-small-400 text-warning-700 dark:text-warning-300">
                      The AI needs additional information to continue
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowChatModal(true)}
                  className="btn-warning"
                >
                  Answer Questions
                </button>
              </div>
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
