import { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/client'
import type { User } from '../types'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isAdmin: boolean
  isLoading: boolean
  loginWithGoogle: (credential: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const mountedRef = useRef(false)

  useEffect(() => {
    // Prevent double-mount issues from React StrictMode
    if (mountedRef.current) {
      return
    }
    mountedRef.current = true

    const token = localStorage.getItem('token')
    if (token) {
      authApi.getMe()
        .then((userData) => {
          setUser(userData)
        })
        .catch(() => {
          localStorage.removeItem('token')
          setUser(null)
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [])

  const loginWithGoogle = async (credential: string) => {
    const response = await authApi.googleLogin(credential)
    localStorage.setItem('token', response.access_token)
    const userData = await authApi.getMe()
    setUser(userData)
    setIsLoading(false)
    navigate('/')
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
    navigate('/login')
  }

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isAdmin: user?.role === 'admin',
      isLoading,
      loginWithGoogle,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
