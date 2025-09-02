import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface DeleteModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  sessionId: string
}

export default function DeleteModal({ isOpen, onClose, onConfirm, sessionId }: DeleteModalProps) {
  const [confirmText, setConfirmText] = useState('')
  const [isDeleting, setIsDeleting] = useState(false)
  const [confirmCheck, setConfirmCheck] = useState(false)

  const handleConfirm = async () => {
    setIsDeleting(true)
    try {
      await onConfirm()
    } finally {
      setIsDeleting(false)
      setConfirmText('')
      setConfirmCheck(false)
    }
  }

  const canDelete = confirmCheck && confirmText.toLowerCase().trim() === 'delete'

  if (!isOpen) return null

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
          className="bg-white dark:bg-secondary-800 rounded-lg shadow-xl max-w-md w-full"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-secondary-200 dark:border-secondary-700">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <div className="h-10 w-10 bg-danger-100 dark:bg-danger-900/30 rounded-full flex items-center justify-center">
                  <svg className="h-6 w-6 text-danger-600 dark:text-danger-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
              </div>
              <div>
                <h2 className="domine-subhead text-lg font-semibold text-danger-900 dark:text-danger-100">
                  Delete Session
                </h2>
                <p className="dm-sans-small-400 text-danger-700 dark:text-danger-300">
                  This action cannot be undone
                </p>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="px-6 py-6 space-y-6">
            {/* Warning */}
            <div className="bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-md p-4">
              <div className="flex">
                <svg className="h-5 w-5 text-danger-400 dark:text-danger-300" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div className="ml-3">
                  <h3 className="dm-sans-body-500 text-sm font-medium text-danger-800 dark:text-danger-200">
                    All data will be permanently deleted
                  </h3>
                  <div className="mt-2 dm-sans-small-400 text-danger-700 dark:text-danger-300">
                    <ul className="list-disc list-inside space-y-1">
                      <li>All uploaded documents</li>
                      <li>Generated analysis and artifacts</li>
                      <li>Session metadata and chat history</li>
                      <li>Vector embeddings and indices</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            {/* Session Info */}
            <div className="bg-secondary-50 dark:bg-secondary-800/50 border border-secondary-200 dark:border-secondary-700 rounded-md p-4">
              <h4 className="dm-sans-body-500 font-medium text-secondary-900 dark:text-white mb-2">
                Session Details
              </h4>
              <div className="space-y-1 dm-sans-small-400 text-secondary-600 dark:text-secondary-400">
                <p>Session ID: <span className="font-mono">{sessionId}</span></p>
                <p>Created: {new Date().toLocaleString()}</p>
              </div>
            </div>

            {/* Confirmation Checkbox */}
            <div className="flex items-start space-x-3">
              <input
                id="confirm-delete"
                type="checkbox"
                checked={confirmCheck}
                onChange={(e) => setConfirmCheck(e.target.checked)}
                className="mt-1 h-4 w-4 text-danger-600 focus:ring-danger-500 border-secondary-300 dark:border-secondary-600 rounded bg-white dark:bg-secondary-700"
              />
              <label htmlFor="confirm-delete" className="dm-sans-small-400 text-secondary-700 dark:text-secondary-300">
                I understand that this action will permanently delete all session data and cannot be undone. 
                This includes any documents I uploaded and all generated legal artifacts.
              </label>
            </div>

            {/* Type DELETE confirmation */}
            <div>
              <label className="block dm-sans-body-500 font-medium text-secondary-900 dark:text-white mb-2">
                Type <span className="font-mono bg-secondary-100 dark:bg-secondary-700 px-2 py-1 rounded text-sm">DELETE</span> to confirm:
              </label>
              <input
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="Type DELETE here"
                className="w-full px-3 py-2 border border-secondary-300 dark:border-secondary-600 rounded-md shadow-sm bg-white dark:bg-secondary-700 text-secondary-900 dark:text-white placeholder-secondary-500 dark:placeholder-secondary-400 focus:ring-danger-500 focus:border-danger-500"
              />
            </div>

            {/* Privacy Note */}
            <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-md p-4">
              <div className="flex items-start space-x-3">
                <svg className="h-5 w-5 text-primary-600 dark:text-primary-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <div>
                  <h4 className="dm-sans-body-500 font-medium text-primary-900 dark:text-primary-100 mb-1">
                    Privacy Protection
                  </h4>
                  <p className="dm-sans-caption-300 text-primary-700 dark:text-primary-300">
                    All data is stored temporarily and encrypted. Sessions automatically expire and are deleted after 1 hour if not manually deleted first.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-secondary-200 dark:border-secondary-700 bg-secondary-50 dark:bg-secondary-800/50">
            <div className="flex justify-between space-x-3">
              <button
                onClick={onClose}
                disabled={isDeleting}
                className="btn-secondary flex-1 disabled:opacity-50"
              >
                Cancel
              </button>
              
              <button
                onClick={handleConfirm}
                disabled={!canDelete || isDeleting}
                className="btn-danger flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDeleting ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Deleting...
                  </>
                ) : (
                  <>
                    <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    Delete Session
                  </>
                )}
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
