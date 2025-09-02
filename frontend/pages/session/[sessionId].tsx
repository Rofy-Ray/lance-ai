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
  status: 'uploading' | 'processing' | 'waiting_for_input' | 'completed' | 'error' | 'deleted'
  current_agent: string | null
  agents_completed: string[]
  agents_failed: string[]
  created_at: string
  expires_at: string
  artifacts_available: string[]
  pending_questions?: Array<{
    agent: string
    question: string
    context?: string
  }>
  error_message?: string
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
  const [showChat, setShowChat] = useState(false)
  const [showArtifacts, setShowArtifacts] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)

  // Fetch session status
  const fetchSessionStatus = async () => {
    if (!sessionId || typeof sessionId !== 'string') return

    try {
      const response = await axios.get(`/api/sessions/${sessionId}/status`)
      const status: SessionStatus = response.data
      setSessionStatus(status)
      setError(null)

      // Stop polling if session is completed, error, or deleted
      if (['completed', 'error', 'deleted'].includes(status.status)) {
        if (pollingInterval) {
          clearInterval(pollingInterval)
          setPollingInterval(null)
        }
      }

      // Show chat modal if there are pending questions
      if (status.pending_questions && status.pending_questions.length > 0) {
        setShowChat(true)
      }

      // Show artifacts panel if completed
      if (status.status === 'completed' && status.artifacts_available.length > 0) {
        setShowArtifacts(true)
      }

    } catch (err: any) {
      console.error('Failed to fetch session status:', err)
      
      if (err.response?.status === 404) {
        setError('Session not found or has been deleted')
      } else if (err.response?.status === 410) {
        setError('Session has expired and been automatically deleted')
      } else {
        setError('Failed to load session status')
      }
    } finally {
      setLoading(false)
    }
  }

  // Start processing
  const startProcessing = async () => {
    if (!sessionId || typeof sessionId !== 'string') return

    try {
      await axios.post(`/api/sessions/${sessionId}/start`)
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
      await axios.post(`/api/sessions/${sessionId}/answer`, { answer })
      setShowChat(false)
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
  const handleDelete = async () => {
    if (!sessionId || typeof sessionId !== 'string') return

    try {
      await axios.delete(`/api/sessions/${sessionId}`)
      toast.success('Session deleted successfully')
      router.push('/')
    } catch (err: any) {
      console.error('Failed to delete session:', err)
      toast.error(err.response?.data?.detail || 'Failed to delete session')
    }
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

  const timeRemaining = new Date(sessionStatus.expires_at).getTime() - Date.now()
  const hoursRemaining = Math.max(0, Math.floor(timeRemaining / (1000 * 60 * 60)))
  const minutesRemaining = Math.max(0, Math.floor((timeRemaining % (1000 * 60 * 60)) / (1000 * 60)))

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
              {/* Timer */}
              <div className="flex items-center space-x-2 text-secondary-500 dark:text-secondary-400">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="dm-sans-small-400">
                  {hoursRemaining}h {minutesRemaining}m remaining
                </span>
              </div>

              {/* Delete Button */}
              <button
                onClick={() => setShowDeleteModal(true)}
                className="btn-danger-outline"
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

          {sessionStatus.status === 'completed' && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-800 mb-8"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <svg className="h-8 w-8 text-success-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <h3 className="dm-sans-body-500 font-medium text-success-900 dark:text-success-100">
                      Analysis Complete
                    </h3>
                    <p className="dm-sans-small-400 text-success-700 dark:text-success-300">
                      {sessionStatus.artifacts_available.length} artifacts ready for download
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowArtifacts(true)}
                  className="btn-success"
                >
                  View Artifacts
                </button>
              </div>
            </motion.div>
          )}

          {/* Progress Stepper */}
          <ProgressStepper
            steps={AGENT_STEPS}
            currentStep={sessionStatus.current_agent}
            completedSteps={sessionStatus.agents_completed}
            failedSteps={sessionStatus.agents_failed}
            status={sessionStatus.status}
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
                  onClick={() => setShowChat(true)}
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
          isOpen={showChat}
          onClose={() => setShowChat(false)}
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
          onConfirm={handleDelete}
          sessionId={sessionStatus.session_id}
        />
      </div>
    </Layout>
  )
}
