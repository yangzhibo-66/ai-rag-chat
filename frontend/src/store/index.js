import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const _storedUser = localStorage.getItem('user_info')
  const user = ref(_storedUser ? (() => { try { return JSON.parse(_storedUser) } catch { return null } })() : null)
  const token = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const guestMode = ref(localStorage.getItem('guest_mode') === 'true')
  const isLoading = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isGuest = computed(() => guestMode.value)
  const isAdmin = computed(() => user.value?.is_superuser === true)
  const username = computed(() => user.value?.username || '')
  const userEmail = computed(() => user.value?.email || '')

  async function login(username, password) {
    isLoading.value = true
    try {
      const response = await authApi.login({ username, password })

      if (response.success) {
        guestMode.value = false
        localStorage.removeItem('guest_mode')

        token.value = response.data.token
        refreshToken.value = response.data.refresh_token || ''
        localStorage.setItem('access_token', response.data.token)
        if (response.data.refresh_token) {
          localStorage.setItem('refresh_token', response.data.refresh_token)
        }

        if (response.data.userInfo) {
          localStorage.setItem('user_info', JSON.stringify(response.data.userInfo))
          user.value = response.data.userInfo
        }

        return { success: true }
      }

      return {
        success: false,
        error: response.error || '登录失败'
      }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || '登录失败'
      }
    } finally {
      isLoading.value = false
    }
  }

  async function register(userData) {
    isLoading.value = true
    try {
      const response = await authApi.register(userData)
      if (response.success) {
        return { success: true, user: response.data }
      }

      return {
        success: false,
        error: response.error || '注册失败'
      }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || '注册失败'
      }
    } finally {
      isLoading.value = false
    }
  }

  async function fetchUserInfo() {
    try {
      const response = await authApi.getMe()
      user.value = response
      localStorage.setItem('user_info', JSON.stringify(response))
    } catch (error) {
      await logout()
      throw error
    }
  }

  async function refreshAuthToken() {
    if (!refreshToken.value) {
      await logout()
      return null
    }

    try {
      const newToken = await authApi.refreshToken({ refresh_token: refreshToken.value })
      token.value = newToken
      refreshToken.value = localStorage.getItem('refresh_token') || ''
      return newToken
    } catch (error) {
      await logout()
      throw error
    }
  }

  async function logout() {
    user.value = null
    token.value = ''
    refreshToken.value = ''
    guestMode.value = false

    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_info')
    localStorage.removeItem('guest_mode')
  }

  function setGuestMode() {
    token.value = ''
    refreshToken.value = ''
    guestMode.value = true
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_info')
    localStorage.setItem('guest_mode', 'true')
    user.value = {
      id: 0,
      username: '游客',
      full_name: '游客用户',
      email: 'guest@example.com',
      avatar_url: null,
      is_active: true,
      is_superuser: false
    }
  }

  function checkAuthStatus() {
    const storedToken = localStorage.getItem('access_token')
    const storedUserInfo = localStorage.getItem('user_info')
    guestMode.value = localStorage.getItem('guest_mode') === 'true'

    if (guestMode.value && !storedToken) {
      user.value = {
        id: 0,
        username: '游客',
        full_name: '游客用户',
        email: 'guest@example.com',
        avatar_url: null,
        is_active: true,
        is_superuser: false
      }
      return
    }

    if (storedToken) {
      token.value = storedToken
      refreshToken.value = localStorage.getItem('refresh_token') || ''

      if (storedUserInfo) {
        try {
          user.value = JSON.parse(storedUserInfo)
        } catch (error) {
          console.error('解析用户信息失败:', error)
        }
      }

      fetchUserInfo().catch(() => logout())
    }
  }

  function clearError() {}

  return {
    user,
    token,
    refreshToken,
    guestMode,
    isLoading,
    isAuthenticated,
    isGuest,
    isAdmin,
    username,
    userEmail,
    login,
    register,
    fetchUserInfo,
    refreshAuthToken,
    logout,
    checkAuthStatus,
    setGuestMode,
    clearError
  }
})
