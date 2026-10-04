import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api } from '../api/axios'
import type { User } from '../types'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>
}

interface RegisterData {
  username: string
  email: string
  first_name: string
  last_name: string
  password: string
  password_confirm: string
  role?: string
  department?: string
  employee_id?: string
  phone?: string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    try {
      const response = await api.get('/auth/me/')
      setUser(response.data)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    // Check for existing tokens on load
    const accessToken = localStorage.getItem('access_token')
    const refreshToken = localStorage.getItem('refresh_token')

    if (accessToken && refreshToken) {
      api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
      refreshUser()
    } else {
      setLoading(false)
    }
  }, [refreshUser])

  const login = async (username: string, password: string) => {
    const response = await api.post('/auth/login/', { username, password })
    const { access, refresh, user: userData } = response.data

    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    api.defaults.headers.common['Authorization'] = `Bearer ${access}`
    setUser(userData)
  }

  const register = async (data: RegisterData) => {
    const response = await api.post('/auth/register/', data)
    const { access, refresh, user: userData } = response.data

    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    api.defaults.headers.common['Authorization'] = `Bearer ${access}`
    setUser(userData)
  }

  const logout = async () => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      try {
        await api.post('/auth/logout/', { refresh: refreshToken })
      } catch {
        // Ignore logout errors
      }
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    delete api.defaults.headers.common['Authorization']
    setUser(null)
  }

  const changePassword = async (oldPassword: string, newPassword: string) => {
    await api.post('/auth/change-password/', { old_password: oldPassword, new_password: newPassword })
  }

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      loading,
      login,
      register,
      logout,
      refreshUser,
      changePassword,
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