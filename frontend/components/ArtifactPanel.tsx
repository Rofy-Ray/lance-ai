import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import { toast } from 'react-hot-toast'

interface ArtifactPanelProps {
  isOpen: boolean
  onClose: () => void
  sessionId: string
  artifacts: string[]
}

interface ArtifactInfo {
  filename: string
  type: 'hearing_pack' | 'client_letter' | 'declaration' | 'research_memo'
  size: number
  created_at: string
  description: string
}

const ARTIFACT_TYPES = {
  hearing_pack: {
    name: 'Hearing Pack',
    description: 'Court-ready hearing materials with exhibits and proposed orders',
    icon: (
      <svg className="h-8 w-8 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
      </svg>
    ),
    color: 'blue'
  },
  client_letter: {
    name: 'Client Letter',
    description: 'Plain-language summary with safety recommendations',
    icon: (
      <svg className="h-8 w-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
        <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
        <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
      </svg>
    ),
    color: 'green'
  },
  declaration: {
    name: 'Court Declaration',
    description: 'Formal sworn statement for court filing',
    icon: (
      <svg className="h-8 w-8 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" clipRule="evenodd" />
      </svg>
    ),
    color: 'purple'
  },
  research_memo: {
    name: 'Legal Research',
    description: 'Relevant case law and legal authorities',
    icon: (
      <svg className="h-8 w-8 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
        <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
      </svg>
    ),
    color: 'amber'
  },
  analysis_summary: {
    name: 'Analysis Summary',
    description: 'Comprehensive analysis overview and findings',
    icon: (
      <svg className="h-8 w-8 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" clipRule="evenodd" />
      </svg>
    ),
    color: 'indigo'
  }
}

export default function ArtifactPanel({ isOpen, onClose, sessionId, artifacts }: ArtifactPanelProps) {
  const [artifactDetails, setArtifactDetails] = useState<ArtifactInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [downloadingFiles, setDownloadingFiles] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (isOpen && artifacts.length > 0) {
      fetchArtifactDetails()
    }
  }, [isOpen, artifacts])

  const fetchArtifactDetails = async () => {
    setLoading(true)
    try {
      const response = await axios.get(`/api/session/${sessionId}/artifacts`)
      // Use detailed artifact objects from backend
      const artifactList = response.data.artifacts || []
      const details = artifactList.map((artifact: any) => ({
        filename: typeof artifact === 'string' ? artifact : artifact.filename,
        type: getArtifactType(typeof artifact === 'string' ? artifact : artifact.filename),
        size: typeof artifact === 'string' ? 0 : artifact.size,
        created_at: typeof artifact === 'string' ? new Date().toISOString() : artifact.created_at,
        description: ARTIFACT_TYPES[getArtifactType(typeof artifact === 'string' ? artifact : artifact.filename)].description
      }))
      setArtifactDetails(details)
    } catch (error) {
      console.error('Failed to fetch artifact details:', error)
      toast.error('Failed to load artifact details')
    } finally {
      setLoading(false)
    }
  }

  const downloadArtifact = async (filename: string) => {
    setDownloadingFiles(prev => new Set(prev).add(filename))
    
    try {
      const response = await axios.get(`/api/session/${sessionId}/download/${filename}`, {
        responseType: 'blob'
      })
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      toast.success(`Downloaded ${filename}`)
    } catch (error) {
      console.error('Failed to download artifact:', error)
      toast.error(`Failed to download ${filename}`)
    } finally {
      setDownloadingFiles(prev => {
        const updated = new Set(prev)
        updated.delete(filename)
        return updated
      })
    }
  }

  const downloadAll = async () => {
    for (const artifact of artifactDetails) {
      if (!downloadingFiles.has(artifact.filename)) {
        await downloadArtifact(artifact.filename)
        // Small delay between downloads to avoid overwhelming the browser
        await new Promise(resolve => setTimeout(resolve, 500))
      }
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getArtifactType = (filename: string): keyof typeof ARTIFACT_TYPES => {
    if (filename.includes('hearing_pack')) return 'hearing_pack'
    if (filename.includes('client_letter')) return 'client_letter'
    if (filename.includes('declaration')) return 'declaration'
    if (filename.includes('research')) return 'research_memo'
    if (filename.includes('analysis_summary')) return 'analysis_summary'
    return 'hearing_pack' // default
  }

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
          initial={{ scale: 0.95, opacity: 0, x: 50 }}
          animate={{ scale: 1, opacity: 1, x: 0 }}
          exit={{ scale: 0.95, opacity: 0, x: 50 }}
          className="bg-white dark:bg-secondary-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-secondary-200 dark:border-secondary-700 bg-success-50 dark:bg-success-900/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <svg className="h-8 w-8 text-success-600 dark:text-success-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div>
                  <h2 className="domine-subhead text-xl font-semibold text-success-900 dark:text-success-100">
                    Analysis Complete
                  </h2>
                  <p className="dm-sans-small-400 text-success-700 dark:text-success-300">
                    {artifactDetails.length} documents ready for download
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  onClick={downloadAll}
                  disabled={loading || downloadingFiles.size > 0}
                  className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg font-medium flex items-center disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {downloadingFiles.size > 0 ? (
                    <>
                      <svg className="animate-spin h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Downloading...
                    </>
                  ) : (
                    <>
                      <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Download All
                    </>
                  )}
                </button>
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
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
            {loading ? (
              <div className="text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
                <p className="dm-sans-body-400 text-secondary-600 dark:text-secondary-400">Loading artifacts...</p>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {artifactDetails.map((artifact, index) => {
                  const artifactType = getArtifactType(artifact.filename)
                  const typeInfo = ARTIFACT_TYPES[artifactType]
                  const isDownloading = downloadingFiles.has(artifact.filename)
                  
                  return (
                    <motion.div
                      key={artifact.filename}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="card hover:shadow-lg transition-shadow"
                    >
                      <div className="p-6">
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex items-center space-x-3">
                            {typeInfo.icon}
                            <div>
                              <h3 className="domine-subhead font-semibold text-secondary-900 dark:text-white">
                                {typeInfo.name}
                              </h3>
                              <p className="dm-sans-caption-300 text-secondary-500 dark:text-secondary-400">
                                {artifact.filename}
                              </p>
                            </div>
                          </div>
                          
                          <button
                            onClick={() => downloadArtifact(artifact.filename)}
                            disabled={isDownloading}
                            className={`p-2 rounded-lg transition-colors ${
                              typeInfo.color === 'blue' ? 'text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20' :
                              typeInfo.color === 'green' ? 'text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20' :
                              typeInfo.color === 'purple' ? 'text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/20' :
                              'text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20'
                            } disabled:opacity-50`}
                          >
                            {isDownloading ? (
                              <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                            ) : (
                              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                            )}
                          </button>
                        </div>
                        
                        <p className="dm-sans-small-400 text-secondary-600 dark:text-secondary-400 mb-4">
                          {typeInfo.description}
                        </p>
                        
                        <div className="flex items-center justify-between text-sm">
                          <div className="flex items-center space-x-4">
                            <span className="dm-sans-caption-300 text-secondary-500 dark:text-secondary-400">
                              {formatFileSize(artifact.size)}
                            </span>
                            <span className="dm-sans-caption-300 text-secondary-500 dark:text-secondary-400">
                              {new Date(artifact.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                          
                          <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                            typeInfo.color === 'blue' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200' :
                            typeInfo.color === 'green' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' :
                            typeInfo.color === 'purple' ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200' :
                            'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200'
                          }`}>
                            Ready
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            )}

            {/* Legal Notice */}
            <div className="mt-8 p-4 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg">
              <div className="flex items-start space-x-3">
                <svg className="h-5 w-5 text-warning-600 dark:text-warning-400 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <div>
                  <h4 className="dm-sans-body-500 font-medium text-warning-900 dark:text-warning-100 mb-1">
                    Important Legal Notice
                  </h4>
                  <p className="dm-sans-caption-300 text-warning-700 dark:text-warning-300">
                    These AI-generated documents are drafts for your review and should be reviewed by a qualified attorney before filing. 
                    Always consult with legal counsel for advice specific to your situation. Lance AI does not provide legal advice.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
