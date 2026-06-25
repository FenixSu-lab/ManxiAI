/*
 * Pinia store for authentication state and account bootstrap.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/utils/api'
import Cookies from 'js-cookie'

interface User {
  id: string
  email: string
  username: string
  first_name: string
  last_name: string
  avatar?: string
  created_at: string
}

interface LoginForm {
  email: string
  password: string
}

interface RegisterForm {
  email: string
  username: string
  password: string
  confirm_password: string
  first_name?: string
  last_name?: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(Cookies.get('token') || null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  // Logs in and stores both token and current user profile.
  const login = async (form: LoginForm) => {
    loading.value = true
    try {
      const response = await api.post('/auth/users/login/', form)
      token.value = response.data.token
      user.value = response.data.user

      if (!token.value) {
        throw new Error('Login token is missing from the response')
      }
      Cookies.set('token', token.value, { expires: 7 })

      return response.data
    } finally {
      loading.value = false
    }
  }

  // Registers a new account; the caller decides where to navigate next.
  const register = async (form: RegisterForm) => {
    loading.value = true
    try {
      const response = await api.post('/auth/users/', form)
      return response.data
    } finally {
      loading.value = false
    }
  }

  // Refreshes the authenticated user from the backend.
  const getUserInfo = async () => {
    if (!token.value) return

    try {
      const response = await api.get('/auth/users/me/')
      user.value = response.data
    } catch (error) {
      logout()
      throw error
    }
  }

  // Clears local authentication state.
  const logout = () => {
    user.value = null
    token.value = null
    Cookies.remove('token')
  }

  // Restores the user object when a persisted token already exists.
  const initialize = async () => {
    if (token.value) {
      try {
        await getUserInfo()
      } catch (error) {
        console.error('Failed to initialize auth state:', error)
      }
    }
  }

  return {
    user,
    token,
    loading,
    isAuthenticated,
    login,
    register,
    getUserInfo,
    logout,
    initialize
  }
})
