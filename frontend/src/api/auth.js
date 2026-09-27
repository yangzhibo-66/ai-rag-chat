import axios from 'axios'

const getApiBaseUrl = () => {
  if (import.meta.env.DEV) {
    return '/api'
  }

  const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  return `${apiBaseUrl}/api`
}

const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    const isGuest = localStorage.getItem('guest_mode')

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    } else if (isGuest) {
      config.headers['X-Guest-Mode'] = 'true'
    }

    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await axios.post(
            `${api.defaults.baseURL}/user/refresh`,
            { refresh_token: refreshToken }
          )

          const newToken = response.data?.data?.token
          const newRefreshToken = response.data?.data?.refresh_token
          if (!newToken) {
            throw new Error('Invalid refresh response')
          }

          localStorage.setItem('access_token', newToken)
          if (newRefreshToken) {
            localStorage.setItem('refresh_token', newRefreshToken)
          }

          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export const authApi = {
  async login(credentials) {
    const response = await api.post('/user/login', credentials)
    if (response.code === 200) {
      const { token, refresh_token, userInfo } = response.data
      localStorage.setItem('access_token', token)
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token)
      }
      localStorage.setItem('user_info', JSON.stringify(userInfo))
      return { success: true, data: { token, refresh_token, userInfo } }
    }
    return { success: false, error: response.message }
  },

  async register(userData) {
    const response = await api.post('/user/register', userData)
    if (response.code === 200) {
      return { success: true, data: response.data }
    }
    return { success: false, error: response.message }
  },

  async getMe() {
    const response = await api.get('/user/info')
    if (response.code === 200) {
      return response.data
    }
    throw new Error(response.message)
  },

  async updateUser(userData) {
    const response = await api.put('/user/update', userData)
    if (response.code === 200) {
      localStorage.setItem('user_info', JSON.stringify(response.data))
      return response.data
    }
    throw new Error(response.message)
  },

  async changePassword(passwordData) {
    const response = await api.put('/user/password', passwordData)
    if (response.code === 200) {
      return { success: true, message: response.message }
    }
    return { success: false, error: response.message }
  },

  async refreshToken(refreshData) {
    const response = await api.post('/user/refresh', refreshData)
    if (response.code === 200) {
      const { token, refresh_token } = response.data
      localStorage.setItem('access_token', token)
      if (refresh_token) {
        localStorage.setItem('refresh_token', refresh_token)
      }
      return token
    }
    throw new Error(response.message)
  },

  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_info')
    localStorage.removeItem('guest_mode')
  },

  async getAIConfig() {
    const response = await api.get('/user/ai-config')
    if (response.code === 200) {
      return response.data
    }
    throw new Error(response.message)
  },

  async updateAIConfig(config) {
    const response = await api.put('/user/ai-config', config)
    if (response.code === 200) {
      return response.data
    }
    throw new Error(response.message)
  }
}

export default api
