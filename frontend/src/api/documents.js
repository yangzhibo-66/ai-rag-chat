import api from './auth'

export const documentsApi = {
  // Upload document
  async uploadDocument(file, categoryId = null, onProgress = null) {
    // Check if user is logged in
    const token = localStorage.getItem('access_token')
    if (!token) {
      throw new Error('用户未登录，请先登录')
    }

    const formData = new FormData()
    formData.append('file', file)
    if (categoryId !== null && categoryId !== undefined && categoryId !== '') {
      formData.append('category_id', String(categoryId))
    }

    try {
      const response = await api.post('/documents/upload', formData, {
        // Remove Content-Type header to let browser handle it automatically
        onUploadProgress: (progressEvent) => {
          if (onProgress) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            onProgress(progress)
          }
        }
      })

      // Handle backend response format
      if (response?.code === 200) {
        return response.data
      } else {
        throw new Error(response?.message || '上传失败')
      }
    } catch (error) {
      // Handle different types of errors
      if (error.response) {
        if (error.response.status === 401) {
          throw new Error('认证过期，请重新登录')
        } else if (error.response.status === 413) {
          throw new Error('文件太大，请选择小于50MB的文件')
        } else if (error.response.status === 400) {
          throw new Error(error.response.data?.message || '文件格式不支持或处理失败')
        } else if (error.response.status === 500) {
          throw new Error('服务器内部错误，请稍后重试')
        } else {
          throw new Error(`上传失败 (${error.response.status}): ${error.response.statusText}`)
        }
      } else if (error.message) {
        throw error
      } else {
        throw new Error('上传失败，请检查网络连接')
      }
    }
  },

  // Get documents list
  async getDocuments(params = {}) {
    try {
      const { page = 1, page_size = 10, ...otherParams } = params
      const skip = (page - 1) * page_size
      const response = await api.get('/documents', {
        params: { skip, limit: page_size, ...otherParams }
      })
      if (response?.code === 200) return response.data
      return response?.data || response || { documents: [], total: 0 }
    } catch (error) {
      console.error('获取文档列表失败:', error)
      return { documents: [], total: 0 }
    }
  },

  // Get document details
  async getDocument(documentId) {
    try {
      const response = await api.get(`/documents/${documentId}`)
      if (response?.code === 200) return response.data
      throw new Error(response?.message || '获取文档详情失败')
    } catch (error) {
      console.error('获取文档详情失败:', error)
      throw error
    }
  },

  // Get document processing status
  async getDocumentStatus(documentId) {
    try {
      const response = await api.get(`/documents/${documentId}/status`)
      if (response?.code === 200) return response.data
      throw new Error(response?.message || '获取文档状态失败')
    } catch (error) {
      console.error('获取文档状态失败:', error)
      throw error
    }
  },

  // Delete document
  async deleteDocument(documentId) {
    try {
      const response = await api.delete(`/documents/${documentId}`)
      if (response?.code === 200) return response.data
      throw new Error(response?.message || '删除文档失败')
    } catch (error) {
      console.error('删除文档失败:', error)
      throw error
    }
  },

  // Reprocess document
  async reprocessDocument(documentId) {
    try {
      const response = await api.post(`/documents/${documentId}/process`)
      if (response?.code === 200) return response.data
      throw new Error(response?.message || '重新处理文档失败')
    } catch (error) {
      console.error('重新处理文档失败:', error)
      throw error
    }
  },

  // Categories
  async getCategories() {
    const response = await api.get('/documents/categories')
    if (response?.code === 200) return response.data
    return response?.data || response || { categories: [] }
  },

  async createCategory(name) {
    const response = await api.post('/documents/categories', { name })
    if (response?.code === 200) return response.data
    throw new Error(response?.message || '创建分类失败')
  },

  async renameCategory(categoryId, name) {
    const response = await api.patch(`/documents/categories/${categoryId}`, { name })
    if (response?.code === 200) return response.data
    throw new Error(response?.message || '重命名分类失败')
  },

  async deleteCategory(categoryId) {
    const response = await api.delete(`/documents/categories/${categoryId}`)
    if (response?.code === 200) return response.data
    throw new Error(response?.message || '删除分类失败')
  }
}
