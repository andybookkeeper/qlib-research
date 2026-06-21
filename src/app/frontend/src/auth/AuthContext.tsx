import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'

type AuthUser = {
  id: number
  username: string
  email: string
  full_name?: string | null
  is_active: boolean
}

type AuthContextValue = {
  token: string | null
  user: AuthUser | null
  isAuthenticated: boolean
  loading: boolean
  login: (token: string) => Promise<void>
  logout: () => void
}

const TOKEN_KEY = 'qlib_auth_token'
const AuthContext = createContext<AuthContextValue | undefined>(undefined)

async function fetchMe(token: string): Promise<AuthUser> {
  const response = await fetch('http://localhost:8000/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) {
    throw new Error('Failed to fetch user profile')
  }
  return response.json()
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const bootstrap = async () => {
      const existingToken = localStorage.getItem(TOKEN_KEY)
      if (!existingToken) {
        setLoading(false)
        return
      }
      try {
        const profile = await fetchMe(existingToken)
        setToken(existingToken)
        setUser(profile)
      } catch {
        localStorage.removeItem(TOKEN_KEY)
      } finally {
        setLoading(false)
      }
    }
    bootstrap()
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      isAuthenticated: !!token && !!user,
      loading,
      login: async (newToken: string) => {
        const profile = await fetchMe(newToken)
        localStorage.setItem(TOKEN_KEY, newToken)
        setToken(newToken)
        setUser(profile)
      },
      logout: () => {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setUser(null)
      },
    }),
    [token, user, loading]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

