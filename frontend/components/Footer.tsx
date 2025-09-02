import React from 'react'

export default function Footer() {
  return (
    <footer className="bg-white dark:bg-secondary-900 border-t border-secondary-200 dark:border-secondary-700">
      <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
          <div className="flex items-center space-x-4">
            <span className="domine-subhead text-primary-600 dark:text-primary-400 font-semibold">
              Lance AI
            </span>
            <span className="dm-sans-small-400 text-secondary-500 dark:text-secondary-400">
              © 2025 All rights reserved
            </span>
          </div>

          <div className="flex items-center space-x-6">
            <span className="dm-sans-small-400 text-secondary-500 dark:text-secondary-400">
              Privacy-first AI for family law
            </span>
            
            <div className="flex items-center space-x-2 text-success-600 dark:text-success-400">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span className="dm-sans-small-400">Trauma-Informed</span>
            </div>

            <div className="flex items-center space-x-2 text-primary-600 dark:text-primary-400">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <span className="dm-sans-small-400">1-Hour TTL</span>
            </div>
          </div>
        </div>

        <div className="mt-6 pt-6 border-t border-secondary-200 dark:border-secondary-700">
          <div className="text-center">
            <p className="dm-sans-caption-300 text-secondary-400 dark:text-secondary-500 max-w-3xl mx-auto">
              Lance AI processes documents temporarily in memory only. All data is automatically deleted after 1 hour or on explicit user request. 
              This tool is designed to assist with family law analysis but does not replace professional legal counsel. 
              Always consult with a qualified attorney for legal advice specific to your situation.
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
