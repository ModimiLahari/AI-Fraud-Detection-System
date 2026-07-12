import React, { createContext, useContext, useState, useEffect } from 'react'
import * as authApi from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('sentinel_user')
    return stored ? JSON.parse(stored) : null
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('sentinel_token')
    if (!token) {
      setLoading(false)
      return
    }
    authApi
      .getMe()
      .then((data) => {
        setUser(data)
        localStorage.setItem('sentinel_user', JSON.stringify(data))
      })
      .catch(() => {
        localStorage.removeItem('sentinel_token')
        localStorage.removeItem('sentinel_user')
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  async function signIn(email, password) {
    const data = await authApi.login(email, password)
    localStorage.setItem('sentinel_token', data.access_token)
    localStorage.setItem('sentinel_user', JSON.stringify(data.user))
    setUser(data.user)
    return data.user
  }

  function signOut() {
    localStorage.removeItem('sentinel_token')
    localStorage.removeItem('sentinel_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
