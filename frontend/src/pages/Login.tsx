import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { authApi } from '../api/client'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential: string }) => void
          }) => void
          renderButton: (
            element: HTMLElement,
            options: {
              theme?: string
              size?: string
              width?: number
              text?: string
            }
          ) => void
        }
      }
    }
  }
}

export default function Login() {
  const { loginWithGoogle } = useAuth()
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [clientId, setClientId] = useState('')

  useEffect(() => {
    // Fetch Google client ID from backend
    authApi.getConfig()
      .then((config) => {
        setClientId(config.google_client_id)
        setIsLoading(false)
      })
      .catch(() => {
        setError('Failed to load authentication config')
        setIsLoading(false)
      })
  }, [])

  useEffect(() => {
    if (!clientId) return

    // Load Google Identity Services script
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = initializeGoogle
    document.body.appendChild(script)

    return () => {
      document.body.removeChild(script)
    }
  }, [clientId])

  const initializeGoogle = () => {
    if (!window.google || !clientId) return

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: handleGoogleCallback,
    })

    const buttonDiv = document.getElementById('google-signin-button')
    if (buttonDiv) {
      window.google.accounts.id.renderButton(buttonDiv, {
        theme: 'outline',
        size: 'large',
        width: 320,
        text: 'signin_with',
      })
    }
  }

  const handleGoogleCallback = async (response: { credential: string }) => {
    setError('')
    try {
      await loginWithGoogle(response.credential)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Authentication failed')
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-cream-100">
        <div className="text-xl text-warm-600">Loading...</div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-cream-100">
      <div className="w-full max-w-md p-8 bg-white border border-warm-200 rounded-2xl shadow-sm">
        <h1 className="text-2xl font-bold text-warm-800 text-center mb-2">EduStream AI</h1>
        <p className="text-warm-400 text-center mb-8">
          Automated educational content generation
        </p>

        {error && (
          <div className="p-3 mb-6 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg">
            {error}
          </div>
        )}

        {!clientId ? (
          <div className="text-center text-warm-400">
            <p>Google OAuth not configured.</p>
            <p className="text-sm mt-2">
              Add GOOGLE_CLIENT_ID to your .env file.
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div id="google-signin-button" className="mb-4"></div>
            <p className="text-xs text-warm-400 text-center mt-4">
              Sign in with your authorized Google account
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
