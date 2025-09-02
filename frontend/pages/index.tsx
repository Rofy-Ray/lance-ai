import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/router'
import Layout from '../components/Layout'
import FileUpload from '../components/FileUpload'
import axios from 'axios'
import { toast } from 'react-hot-toast'

export default function Home() {
  const router = useRouter()
  const [isUploading, setIsUploading] = useState(false)

  const handleUpload = async (files: File[]) => {
    setIsUploading(true)
    
    try {
      const formData = new FormData()
      files.forEach((file, index) => {
        formData.append(`files`, file)
      })

      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      const { session_id } = response.data
      toast.success('Files uploaded successfully!')
      
      // Navigate to session page
      router.push(`/session/${session_id}`)
      
    } catch (error: any) {
      console.error('Upload failed:', error)
      toast.error(error.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <Layout 
      title="Lance AI - Detecting Post-Separation Abuse & Coercive Control"
      description="AI-powered analysis of family law documents to detect post-separation abuse and coercive control patterns. Privacy-first, trauma-informed legal technology."
    >
      <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50 dark:from-secondary-900 dark:via-secondary-800 dark:to-primary-900">
        {/* Hero Section */}
        <div className="relative overflow-hidden">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
            <div className="text-center">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
              >
                <h1 className="domine-title-xl text-4xl sm:text-5xl lg:text-6xl font-bold text-secondary-900 dark:text-white leading-tight">
                  Detecting Post-Separation
                  <br />
                  <span className="text-primary-600 dark:text-primary-400">Abuse & Coercive Control</span>
                </h1>
                <p className="dm-sans-body-400 mt-6 text-xl text-secondary-600 dark:text-secondary-300 max-w-3xl mx-auto">
                  AI-powered analysis of family law documents using trauma-informed, privacy-first technology. 
                  Generate court-ready materials with comprehensive legal analysis.
                </p>
              </motion.div>

              {/* Key Features */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto"
              >
                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 mb-4">
                    <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <h3 className="domine-subhead text-lg font-semibold text-secondary-900 dark:text-white">Privacy-First</h3>
                  <p className="dm-sans-small-400 mt-2 text-secondary-500 dark:text-secondary-400">
                    1-hour TTL, no persistent storage. All data deleted automatically.
                  </p>
                </div>
                
                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-success-100 dark:bg-success-900/30 text-success-600 dark:text-success-400 mb-4">
                    <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                  </div>
                  <h3 className="domine-subhead text-lg font-semibold text-secondary-900 dark:text-white">Trauma-Informed</h3>
                  <p className="dm-sans-small-400 mt-2 text-secondary-500 dark:text-secondary-400">
                    Built with understanding of domestic violence survivors' needs.
                  </p>
                </div>
                
                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-warning-100 dark:bg-warning-900/30 text-warning-600 dark:text-warning-400 mb-4">
                    <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h3 className="domine-subhead text-lg font-semibold text-secondary-900 dark:text-white">Court-Ready</h3>
                  <p className="dm-sans-small-400 mt-2 text-secondary-500 dark:text-secondary-400">
                    Generate declarations, hearing packs, and legal research.
                  </p>
                </div>
              </motion.div>
            </div>
          </div>
        </div>

        {/* Upload Section */}
        <div className="py-20 bg-white dark:bg-secondary-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="text-center mb-12"
            >
              <h2 className="domine-title-lg text-3xl font-bold text-secondary-900 dark:text-white">
                Begin Your Analysis
              </h2>
              <p className="dm-sans-body-400 mt-4 text-lg text-secondary-600 dark:text-secondary-300">
                Upload your family law documents for AI-powered analysis
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.6 }}
            >
              <FileUpload 
                onUpload={handleUpload} 
                isUploading={isUploading}
                maxFiles={10}
                maxSizeBytes={50 * 1024 * 1024}
              />
            </motion.div>
          </div>
        </div>

        {/* Legal Disclaimer */}
        <div className="py-16 bg-secondary-50 dark:bg-secondary-900">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.8 }}
              className="bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg p-6"
            >
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-warning-600 dark:text-warning-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="dm-sans-body-500 text-base font-semibold text-warning-800 dark:text-warning-200">
                    Important Legal Disclaimer
                  </h3>
                  <p className="dm-sans-small-400 mt-2 text-warning-700 dark:text-warning-300">
                    Lance AI is a legal technology tool designed to assist with document analysis and is not a substitute for professional legal advice. 
                    All generated documents should be reviewed by a qualified attorney before filing with any court. 
                    The analysis provided is based on patterns in the submitted documents and should not be considered definitive legal conclusions.
                  </p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </Layout>
  )
}
