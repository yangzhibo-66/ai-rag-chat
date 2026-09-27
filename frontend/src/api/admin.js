import api from './auth'

export const adminApi = {
  async getStats() {
    const r = await api.get('/admin/stats')
    if (r?.code === 200) return r.data
    throw new Error(r?.message || '获取系统概览失败')
  },

  async getUsers(params = {}) {
    const { page = 1, page_size = 20, search = '' } = params
    const skip = (page - 1) * page_size
    const r = await api.get('/admin/users', { params: { skip, limit: page_size, search } })
    if (r?.code === 200) return r.data
    throw new Error(r?.message || '获取用户列表失败')
  },

  async getDocuments(params = {}) {
    const { page = 1, page_size = 20, search = '', status = '' } = params
    const skip = (page - 1) * page_size
    const r = await api.get('/admin/documents', { params: { skip, limit: page_size, search, status } })
    if (r?.code === 200) return r.data
    throw new Error(r?.message || '获取文档列表失败')
  },

  async getSessions(params = {}) {
    const { page = 1, page_size = 20, search = '' } = params
    const skip = (page - 1) * page_size
    const r = await api.get('/admin/sessions', { params: { skip, limit: page_size, search } })
    if (r?.code === 200) return r.data
    throw new Error(r?.message || '获取对话列表失败')
  },

  async getAuditLogs(params = {}) {
    const { page = 1, page_size = 20 } = params
    const skip = (page - 1) * page_size
    const r = await api.get('/admin/audit-logs', { params: { skip, limit: page_size } })
    if (r?.code === 200) return r.data
    throw new Error(r?.message || '获取审计日志失败')
  },

  async toggleUserActive(userId) {
    const r = await api.put(`/admin/users/${userId}/toggle-active`)
    if (r?.code === 200) return r.data
    throw new Error(r?.message || '操作失败')
  },

  async toggleUserAdmin(userId) {
    const r = await api.put(`/admin/users/${userId}/toggle-admin`)
    if (r?.code === 200) return r.data
    throw new Error(r?.message || '操作失败')
  },
}
