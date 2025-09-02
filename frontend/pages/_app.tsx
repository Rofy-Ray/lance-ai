import { AppProps } from 'next/app'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider } from '../contexts/ThemeContext'
import '../styles/globals.css'

export default function App({ Component, pageProps }: AppProps) {
  return (
    <ThemeProvider>
      <Component {...pageProps} />
      <Toaster 
        position="top-right"
        toastOptions={{
          className: 'dm-sans-small-400',
          duration: 5000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            iconTheme: {
              primary: '#22c55e',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
    </ThemeProvider>
  )
}
