import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'

interface FileUploadProps {
  onUpload: (files: File[]) => void
  isUploading: boolean
  maxFiles?: number
  maxSizeBytes?: number
}

interface FileWithPreview extends File {
  id: string
  preview?: string
}

export default function FileUpload({ 
  onUpload, 
  isUploading, 
  maxFiles = 10, 
  maxSizeBytes = 50 * 1024 * 1024 
}: FileUploadProps) {
  const [files, setFiles] = useState<FileWithPreview[]>([])
  const [errors, setErrors] = useState<string[]>([])

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    setErrors([])
    
    // Handle rejected files
    const newErrors: string[] = []
    rejectedFiles.forEach(({ file, errors: fileErrors }) => {
      fileErrors.forEach((error: any) => {
        if (error.code === 'file-too-large') {
          newErrors.push(`${file.name} is too large. Maximum size is ${Math.round(maxSizeBytes / 1024 / 1024)}MB`)
        } else if (error.code === 'file-invalid-type') {
          newErrors.push(`${file.name} has an unsupported file type`)
        } else if (error.code === 'too-many-files') {
          newErrors.push(`Too many files. Maximum is ${maxFiles} files`)
        }
      })
    })

    // Process accepted files
    const filesWithPreview = acceptedFiles.map((file) => {
      const fileWithPreview = file as FileWithPreview
      fileWithPreview.id = Math.random().toString(36).substring(7)
      
      // Create preview for images
      if (file.type.startsWith('image/')) {
        fileWithPreview.preview = URL.createObjectURL(file)
      }
      
      return fileWithPreview
    })

    setFiles(prev => [...prev, ...filesWithPreview].slice(0, maxFiles))
    setErrors(newErrors)
  }, [maxFiles, maxSizeBytes])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    },
    maxFiles,
    maxSize: maxSizeBytes,
    multiple: true,
    disabled: isUploading
  })

  const removeFile = (fileId: string) => {
    setFiles(prev => {
      const updated = prev.filter(file => file.id !== fileId)
      // Revoke preview URLs for removed files
      const removedFile = prev.find(file => file.id === fileId)
      if (removedFile?.preview) {
        URL.revokeObjectURL(removedFile.preview)
      }
      return updated
    })
  }

  const handleUpload = () => {
    if (files.length > 0) {
      onUpload(files)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getFileIcon = (file: File) => {
    const type = file.type.toLowerCase()
    
    if (type.includes('pdf')) {
      return (
        <svg className="h-8 w-8 text-red-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
        </svg>
      )
    } else if (type.includes('word') || type.includes('document')) {
      return (
        <svg className="h-8 w-8 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
        </svg>
      )
    } else if (type.includes('image')) {
      return (
        <svg className="h-8 w-8 text-green-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
        </svg>
      )
    } else {
      return (
        <svg className="h-8 w-8 text-secondary-500" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
        </svg>
      )
    }
  }

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={`upload-dropzone cursor-pointer ${isDragActive ? 'upload-dropzone-active' : ''} ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-secondary-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <div className="mt-4">
            <p className="dm-sans-body-500 text-lg text-secondary-900 dark:text-white">
              {isDragActive ? 'Drop files here...' : 'Drag & drop files here'}
            </p>
            <p className="dm-sans-small-400 text-secondary-500 dark:text-secondary-400 mt-2">
              or click to select files
            </p>
            <p className="dm-sans-caption-300 text-secondary-400 dark:text-secondary-500 mt-2">
              PDF, Word, Text, or Image files up to {Math.round(maxSizeBytes / 1024 / 1024)}MB each
            </p>
          </div>
        </div>
      </div>

      {/* Error Messages */}
      <AnimatePresence>
        {errors.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-800 rounded-md p-4"
          >
            <div className="flex">
              <svg className="h-5 w-5 text-danger-400 dark:text-danger-300" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="ml-3">
                <h3 className="dm-sans-body-500 text-sm font-medium text-danger-800 dark:text-danger-200">
                  Upload errors:
                </h3>
                <div className="mt-2">
                  <ul className="dm-sans-small-400 list-disc list-inside space-y-1 text-danger-700 dark:text-danger-300">
                    {errors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* File List */}
      <AnimatePresence>
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-6"
          >
            <h3 className="dm-sans-body-500 text-lg font-medium text-secondary-900 dark:text-white mb-4">
              Selected Files ({files.length})
            </h3>
            <div className="space-y-3">
              {files.map((file) => (
                <motion.div
                  key={file.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="card p-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {getFileIcon(file)}
                      <div>
                        <p className="dm-sans-body-400 text-sm font-medium text-secondary-900 dark:text-white truncate max-w-xs">
                          {file.name}
                        </p>
                        <p className="dm-sans-caption-300 text-xs text-secondary-500 dark:text-secondary-400">
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => removeFile(file.id)}
                      disabled={isUploading}
                      className="p-1 text-secondary-400 hover:text-danger-500 disabled:opacity-50 transition-colors"
                    >
                      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Upload Button */}
            <div className="mt-6 text-center">
              <button
                onClick={handleUpload}
                disabled={isUploading || files.length === 0}
                className="btn-primary px-8 py-3 text-base font-medium"
              >
                {isUploading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Uploading...
                  </>
                ) : (
                  `Upload ${files.length} ${files.length === 1 ? 'File' : 'Files'}`
                )}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
