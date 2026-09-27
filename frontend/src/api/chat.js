import api from './auth'

// 统一获取 API 基础地址
const getBaseUrl = () => {
  // 开发环境：使用 Vite 代理（/api 会被代理到后端）
  if (import.meta.env.DEV) {
    return '/api'
  }
  // 生产环境：从环境变量读取 Sealos 后端地址
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  return `${API_BASE_URL}/api`
}

const buildHeaders = () => {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  }
}

const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return false
  try {
    const refreshResp = await api.post('/user/refresh', { refresh_token: refreshToken })
    if (refreshResp?.code !== 200 || !refreshResp?.data?.token) return false
    localStorage.setItem('access_token', refreshResp.data.token)
    if (refreshResp.data.refresh_token) {
      localStorage.setItem('refresh_token', refreshResp.data.refresh_token)
    }
    return true
  } catch {
    return false
  }
}

export const chatApi = {
  // Send chat message (streaming)
  async sendMessage(message, sessionId = null, onToken = null, onComplete = null, onError = null, options = {}, onQuality = null) {
    const baseUrl = getBaseUrl()
    let response = await fetch(`${baseUrl}/chat/ask`, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({
        message,
        session_id: sessionId,
        stream: true,
        ...options
      })
    })

    if (response.status === 401) {
      const refreshed = await refreshAccessToken()
      if (!refreshed) throw new Error('认证过期，请重新登录')
      response = await fetch(`${baseUrl}/chat/ask`, {
        method: 'POST',
        headers: buildHeaders(),
        body: JSON.stringify({
          message,
          session_id: sessionId,
          stream: true,
          ...options
        })
      })
    }

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const result = await response.json()
      if (result?.code !== 200) {
        throw new Error(result?.message || '请求失败')
      }
      return result?.data
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const handleLine = (line) => {
      if (!line.startsWith('data: ')) return
      try {
        const data = JSON.parse(line.slice(6))

        if (data.type === 'token' && onToken) {
          onToken(data.content)
        } else if (data.type === 'context' && onComplete) {
          onComplete(data.metadata)
        } else if (data.type === 'quality' && onQuality) {
          onQuality(data.content)
        } else if (data.type === 'complete' && onComplete) {
          onComplete(data.metadata)
        } else if (data.type === 'error' && onError) {
          onError(data.content)
        }
      } catch (e) {
        console.error('Error parsing SSE data:', e)
      }
    }

    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // Keep incomplete line in buffer

        for (const line of lines) {
          handleLine(line)
        }
      }
      if (buffer.trim()) handleLine(buffer.trim())
    } catch (error) {
      if (onError) onError(error.message)
    }
  },

  // Send chat message (non-streaming)
  async sendMessageSync(message, sessionId = null, options = {}) {
    return api.post('/chat/ask/sync', {
      message,
      session_id: sessionId,
      stream: false,
      ...options
    })
  },

  // Get chat history
  async getHistory(params = {}) {
    const { session_id = null, limit = 50, offset = 0 } = params
    const response = await api.get('/chat/history', {
      params: { session_id, limit, offset }
    })
    if (response?.code === 200) return response.data
    return response?.data || response || { messages: [], total: 0 }
  },

  // Get chat sessions
  async getSessions() {
    const response = await api.get('/chat/sessions')
    if (response?.code === 200) return response.data
    return response?.data || response || { sessions: [] }
  },

  // Clear chat history
  async clearHistory(sessionId = null) {
    const response = await api.delete('/chat/clear', {
      data: { session_id: sessionId }
    })
    if (response?.code === 200) return response.data
    return response?.data || response
  }
}
