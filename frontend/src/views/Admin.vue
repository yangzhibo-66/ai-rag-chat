<template>
  <div class="admin-root">
    <div class="page-header">
      <div>
        <h1 class="page-title">管理后台</h1>
        <p class="page-sub">管理员可查看全局列表；涉及用户内容时仅用于运维排查，请勿随意外传或滥用。</p>
      </div>
      <button class="refresh-btn" @click="refreshCurrent">刷新数据</button>
    </div>

    <div class="stats-grid">
      <button
        v-for="s in statCards"
        :key="s.key"
        class="stat-card"
        type="button"
        @click="handleStatClick(s)"
      >
        <div class="stat-icon" :style="{ background: s.bg, color: s.color }">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" v-html="s.icon"></svg>
        </div>
        <div class="stat-body">
          <div class="stat-num">{{ s.format ? s.format(stats[s.key]) : formatNum(stats[s.key]) }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
        <span class="stat-more">{{ s.hint }}</span>
      </button>
    </div>

    <el-tabs v-model="activeTab" class="admin-tabs" @tab-change="handleTabChange">
      <el-tab-pane label="用户列表" name="users" />
      <el-tab-pane label="文档列表" name="documents" />
      <el-tab-pane label="对话列表" name="sessions" />
      <el-tab-pane label="操作审计" name="audit" />
    </el-tabs>

    <section v-if="activeTab === 'users'" class="panel">
      <div class="toolbar">
        <input v-model="userSearch" class="search-input" placeholder="搜索用户名或邮箱..." @input="searchUsers" />
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>用户</th>
            <th>邮箱</th>
            <th>文档数</th>
            <th>注册时间</th>
            <th>角色</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>#{{ u.id }}</td>
            <td>
              <b>{{ u.username }}</b>
              <small v-if="u.full_name">{{ u.full_name }}</small>
            </td>
            <td>{{ u.email }}</td>
            <td>{{ u.document_count }}</td>
            <td>{{ formatDate(u.created_at) }}</td>
            <td><span class="tag" :class="u.is_superuser ? 'tag-admin' : 'tag-user'">{{ u.is_superuser ? '管理员' : '普通用户' }}</span></td>
            <td><span class="tag" :class="u.is_active ? 'tag-ok' : 'tag-bad'">{{ u.is_active ? '正常' : '已禁用' }}</span></td>
            <td>
              <div class="actions">
                <button class="mini-btn" @click="toggleActive(u)">{{ u.is_active ? '禁用' : '启用' }}</button>
                <button class="mini-btn accent" @click="toggleAdmin(u)">{{ u.is_superuser ? '撤权' : '提权' }}</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <EmptyState v-if="users.length === 0 && !loadingUsers" text="暂无用户数据" />
      <Pager v-if="userTotal > pageSize" :total="userTotal" :page="userPage" :page-size="pageSize" @change="changeUserPage" />
    </section>

    <section v-if="activeTab === 'documents'" class="panel">
      <div class="notice-line">权限边界：管理员可查看文档元数据和处理状态，用于排查上传/解析问题；用户正文内容默认不在此页展开。</div>
      <div class="toolbar">
        <input v-model="documentSearch" class="search-input" placeholder="搜索文件名、用户名或邮箱..." @input="searchDocuments" />
        <select v-model="documentStatus" class="select-input" @change="loadDocuments">
          <option value="">全部状态</option>
          <option value="completed">已完成</option>
          <option value="processing">处理中</option>
          <option value="uploading">上传中</option>
          <option value="failed">失败</option>
        </select>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>文件名</th>
            <th>上传用户</th>
            <th>状态</th>
            <th>大小</th>
            <th>字数</th>
            <th>分块</th>
            <th>上传时间</th>
            <th>处理结果</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in documents" :key="d.id">
            <td>#{{ d.id }}</td>
            <td>
              <b>{{ d.filename }}</b>
              <small>{{ d.file_type || d.content_type || '未知类型' }}</small>
            </td>
            <td>{{ d.owner?.username || '-' }}</td>
            <td><span class="tag" :class="statusClass(d.status)">{{ statusText(d.status) }}</span></td>
            <td>{{ formatSize(d.file_size) }}</td>
            <td>{{ formatNum(d.word_count) }}</td>
            <td>{{ d.chunk_count }}</td>
            <td>{{ formatDateTime(d.created_at) }}</td>
            <td class="error-cell">{{ d.processing_error || '正常' }}</td>
          </tr>
        </tbody>
      </table>
      <EmptyState v-if="documents.length === 0 && !loadingDocuments" text="暂无文档数据" />
      <Pager v-if="documentTotal > pageSize" :total="documentTotal" :page="documentPage" :page-size="pageSize" @change="changeDocumentPage" />
    </section>

    <section v-if="activeTab === 'sessions'" class="panel">
      <div class="notice-line">权限边界：对话列表仅展示最近消息摘要，主要用于统计和故障定位，不建议作为内容审阅入口。</div>
      <div class="toolbar">
        <input v-model="sessionSearch" class="search-input" placeholder="搜索会话ID、用户名或邮箱..." @input="searchSessions" />
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>会话ID</th>
            <th>用户</th>
            <th>消息数</th>
            <th>创建时间</th>
            <th>最后活跃</th>
            <th>最近消息</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in sessions" :key="s.id">
            <td class="mono">{{ shortId(s.id) }}</td>
            <td>{{ s.owner?.username || '-' }}</td>
            <td>{{ s.message_count }}</td>
            <td>{{ formatDateTime(s.created_at) }}</td>
            <td>{{ formatDateTime(s.last_activity) }}</td>
            <td class="message-cell">
              <span v-if="s.latest_message" class="tag tag-user">{{ roleText(s.latest_message.role) }}</span>
              {{ s.latest_message?.content || '暂无消息' }}
            </td>
          </tr>
        </tbody>
      </table>
      <EmptyState v-if="sessions.length === 0 && !loadingSessions" text="暂无对话数据" />
      <Pager v-if="sessionTotal > pageSize" :total="sessionTotal" :page="sessionPage" :page-size="pageSize" @change="changeSessionPage" />
    </section>

    <section v-if="activeTab === 'audit'" class="panel">
      <div class="notice-line">管理员操作会记录在这里，便于后续追踪是谁在什么时候改了用户状态或权限。</div>
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>管理员</th>
            <th>动作</th>
            <th>目标</th>
            <th>详情</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in auditLogs" :key="log.id">
            <td>#{{ log.id }}</td>
            <td>{{ log.admin?.username || '-' }}</td>
            <td><span class="tag tag-admin">{{ actionText(log.action) }}</span></td>
            <td>{{ log.target_type }} #{{ log.target_id || '-' }}</td>
            <td class="message-cell">{{ log.detail || '-' }}</td>
            <td>{{ formatDateTime(log.created_at) }}</td>
          </tr>
        </tbody>
      </table>
      <EmptyState v-if="auditLogs.length === 0 && !loadingAudit" text="暂无审计日志" />
      <Pager v-if="auditTotal > pageSize" :total="auditTotal" :page="auditPage" :page-size="pageSize" @change="changeAuditPage" />
    </section>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminApi } from '../api/admin'
import { useUserStore } from '../store'

const store = useUserStore()
const router = useRouter()

const activeTab = ref('users')
const pageSize = 20
const stats = reactive({
  total_users: 0,
  total_documents: 0,
  completed_documents: 0,
  failed_documents: 0,
  total_sessions: 0,
  total_messages: 0,
  total_storage: 0,
})

const users = ref([])
const documents = ref([])
const sessions = ref([])
const auditLogs = ref([])
const userTotal = ref(0)
const documentTotal = ref(0)
const sessionTotal = ref(0)
const auditTotal = ref(0)
const userPage = ref(1)
const documentPage = ref(1)
const sessionPage = ref(1)
const auditPage = ref(1)
const userSearch = ref('')
const documentSearch = ref('')
const documentStatus = ref('')
const sessionSearch = ref('')
const loadingUsers = ref(false)
const loadingDocuments = ref(false)
const loadingSessions = ref(false)
const loadingAudit = ref(false)
let userTimer = null
let documentTimer = null
let sessionTimer = null

const EmptyState = defineComponent({
  props: { text: { type: String, required: true } },
  setup(props) {
    return () => h('div', { class: 'empty-state' }, props.text)
  },
})

const Pager = defineComponent({
  props: {
    total: { type: Number, required: true },
    page: { type: Number, required: true },
    pageSize: { type: Number, required: true },
  },
  emits: ['change'],
  setup(props, { emit }) {
    const pages = computed(() => Math.ceil(props.total / props.pageSize))
    return () => h('div', { class: 'pager' }, [
      h('button', { disabled: props.page <= 1, onClick: () => emit('change', props.page - 1) }, '上一页'),
      h('span', `${props.page} / ${pages.value}`),
      h('button', { disabled: props.page >= pages.value, onClick: () => emit('change', props.page + 1) }, '下一页'),
    ])
  },
})

const statCards = [
  { key: 'total_users', label: '注册用户', hint: '查看用户列表', tab: 'users', bg: 'rgba(79,111,220,.12)', color: '#4f6fdc', icon: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/>' },
  { key: 'total_documents', label: '文档总数', hint: '查看文档列表', tab: 'documents', bg: 'rgba(106,158,110,.15)', color: '#4d8f58', icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/>' },
  { key: 'completed_documents', label: '处理完成', hint: '筛选完成文档', tab: 'documents', status: 'completed', bg: 'rgba(82,166,118,.13)', color: '#42a66a', icon: '<polyline points="20 6 9 17 4 12"/>' },
  { key: 'failed_documents', label: '处理失败', hint: '筛选失败文档', tab: 'documents', status: 'failed', bg: 'rgba(220,79,79,.12)', color: '#cc5959', icon: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>' },
  { key: 'total_sessions', label: '对话会话', hint: '查看对话列表', tab: 'sessions', bg: 'rgba(192,136,80,.15)', color: '#c08850', icon: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>' },
  { key: 'total_storage', label: '存储占用', hint: '查看文件明细', tab: 'documents', bg: 'rgba(145,111,219,.15)', color: '#916fdb', format: (v) => formatSize(v), icon: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>' },
]

const loadStats = async () => {
  try {
    Object.assign(stats, await adminApi.getStats())
  } catch {
    ElMessage.error('加载系统统计失败')
  }
}

const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const data = await adminApi.getUsers({ page: userPage.value, page_size: pageSize, search: userSearch.value })
    users.value = data.users || []
    userTotal.value = data.total || 0
  } catch {
    ElMessage.error('加载用户列表失败')
  } finally {
    loadingUsers.value = false
  }
}

const loadDocuments = async () => {
  loadingDocuments.value = true
  try {
    const data = await adminApi.getDocuments({
      page: documentPage.value,
      page_size: pageSize,
      search: documentSearch.value,
      status: documentStatus.value,
    })
    documents.value = data.documents || []
    documentTotal.value = data.total || 0
  } catch {
    ElMessage.error('加载文档列表失败')
  } finally {
    loadingDocuments.value = false
  }
}

const loadSessions = async () => {
  loadingSessions.value = true
  try {
    const data = await adminApi.getSessions({ page: sessionPage.value, page_size: pageSize, search: sessionSearch.value })
    sessions.value = data.sessions || []
    sessionTotal.value = data.total || 0
  } catch {
    ElMessage.error('加载对话列表失败')
  } finally {
    loadingSessions.value = false
  }
}

const loadAuditLogs = async () => {
  loadingAudit.value = true
  try {
    const data = await adminApi.getAuditLogs({ page: auditPage.value, page_size: pageSize })
    auditLogs.value = data.logs || []
    auditTotal.value = data.total || 0
  } catch {
    ElMessage.error('加载审计日志失败')
  } finally {
    loadingAudit.value = false
  }
}

const refreshCurrent = async () => {
  await loadStats()
  if (activeTab.value === 'users') await loadUsers()
  if (activeTab.value === 'documents') await loadDocuments()
  if (activeTab.value === 'sessions') await loadSessions()
  if (activeTab.value === 'audit') await loadAuditLogs()
}

const handleStatClick = async (card) => {
  activeTab.value = card.tab
  if (card.tab === 'documents') {
    documentStatus.value = card.status || ''
    documentPage.value = 1
  }
  await refreshCurrent()
}

const handleTabChange = () => refreshCurrent()
const changeUserPage = (page) => { userPage.value = page; loadUsers() }
const changeDocumentPage = (page) => { documentPage.value = page; loadDocuments() }
const changeSessionPage = (page) => { sessionPage.value = page; loadSessions() }
const changeAuditPage = (page) => { auditPage.value = page; loadAuditLogs() }
const searchUsers = () => { clearTimeout(userTimer); userTimer = setTimeout(() => { userPage.value = 1; loadUsers() }, 300) }
const searchDocuments = () => { clearTimeout(documentTimer); documentTimer = setTimeout(() => { documentPage.value = 1; loadDocuments() }, 300) }
const searchSessions = () => { clearTimeout(sessionTimer); sessionTimer = setTimeout(() => { sessionPage.value = 1; loadSessions() }, 300) }

const toggleActive = async (user) => {
  try {
    await ElMessageBox.confirm(`确定${user.is_active ? '禁用' : '启用'}用户「${user.username}」？`, '确认操作', { type: 'warning' })
    await adminApi.toggleUserActive(user.id)
    ElMessage.success(`用户已${user.is_active ? '禁用' : '启用'}`)
    await loadUsers()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error?.message || '操作失败')
  }
}

const toggleAdmin = async (user) => {
  try {
    await ElMessageBox.confirm(`确定${user.is_superuser ? '撤销' : '授予'}「${user.username}」管理员权限？`, '确认操作', { type: 'warning' })
    await adminApi.toggleUserAdmin(user.id)
    ElMessage.success(`管理员权限已${user.is_superuser ? '撤销' : '授予'}`)
    await loadUsers()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error?.message || '操作失败')
  }
}

const formatNum = (value) => Number(value || 0).toLocaleString('zh-CN')
const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}
const formatDate = (date) => date ? new Date(date).toLocaleDateString('zh-CN') : '-'
const formatDateTime = (date) => date ? new Date(date).toLocaleString('zh-CN', { hour12: false }) : '-'
const shortId = (id) => id ? `${id.slice(0, 8)}...${id.slice(-6)}` : '-'
const roleText = (role) => role === 'assistant' ? 'AI' : '用户'
const actionText = (action) => ({
  toggle_user_active: '启停用户',
  toggle_user_admin: '权限变更',
}[action] || action)
const statusText = (status) => ({ completed: '已完成', processing: '处理中', uploading: '上传中', failed: '失败' }[status] || status || '未知')
const statusClass = (status) => ({
  completed: 'tag-ok',
  processing: 'tag-warn',
  uploading: 'tag-user',
  failed: 'tag-bad',
}[status] || 'tag-user')

onMounted(async () => {
  if (!store.isAdmin) {
    router.push('/dashboard')
    return
  }
  await refreshCurrent()
})
</script>

<style scoped>
.admin-root { max-width: 1180px; margin: 0 auto; padding: 24px 0 40px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.page-title { margin: 0; font-size: 24px; font-weight: 800; color: var(--c-text); }
.page-sub { margin: 6px 0 0; color: var(--c-text-3); font-size: 13px; }
.refresh-btn, .mini-btn, .pager button {
  border: 1px solid #e5ebf5; background: #fff; color: var(--c-text);
  border-radius: 10px; padding: 8px 14px; cursor: pointer; transition: all .15s;
}
.refresh-btn:hover, .mini-btn:hover, .pager button:hover:not(:disabled) { border-color: var(--c-accent); color: var(--c-accent); }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 18px; }
.stat-card {
  position: relative; display: flex; align-items: center; gap: 14px; text-align: left;
  background: var(--c-elevated); border: 1px solid #e9eef6; border-radius: 18px;
  box-shadow: var(--shadow-sm); padding: 18px; cursor: pointer; transition: all .16s;
}
.stat-card:hover { transform: translateY(-2px); border-color: rgba(79,111,220,.35); box-shadow: var(--shadow-md); }
.stat-icon { width: 44px; height: 44px; border-radius: 14px; display: flex; align-items: center; justify-content: center; }
.stat-num { font-size: 25px; font-weight: 800; color: var(--c-text); line-height: 1; }
.stat-label { margin-top: 6px; font-size: 12px; color: var(--c-text-2); }
.stat-more { margin-left: auto; font-size: 12px; color: var(--c-accent); }
.admin-tabs { margin-top: 6px; }
.panel { background: var(--c-elevated); border: 1px solid #e9eef6; border-radius: 18px; box-shadow: var(--shadow-sm); overflow: hidden; }
.toolbar { display: flex; gap: 10px; padding: 14px; border-bottom: 1px solid var(--c-border); background: #fbfdff; }
.notice-line { padding: 12px 14px; color: var(--c-text-2); font-size: 13px; background: #fbfdff; border-bottom: 1px solid var(--c-border); }
.search-input, .select-input {
  min-width: 260px; border: 1px solid #e5ebf5; border-radius: 10px;
  padding: 9px 12px; outline: none; background: #fff; color: var(--c-text);
}
.search-input:focus, .select-input:focus { border-color: var(--c-accent); }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th {
  text-align: left; padding: 12px 14px; color: var(--c-text-2);
  background: #f7f9fc; border-bottom: 1px solid var(--c-border); font-weight: 700;
}
.data-table td { padding: 13px 14px; border-bottom: 1px solid var(--c-border); color: var(--c-text); vertical-align: top; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #f9fbff; }
.data-table b { display: block; margin-bottom: 3px; }
.data-table small { display: block; color: var(--c-text-3); font-size: 11px; }
.tag { display: inline-block; border-radius: 999px; padding: 3px 9px; font-size: 11px; font-weight: 700; white-space: nowrap; }
.tag-admin { background: rgba(79,111,220,.12); color: var(--c-accent); }
.tag-user { background: rgba(128,137,155,.12); color: var(--c-text-2); }
.tag-ok { background: rgba(70,170,100,.13); color: #2f9b57; }
.tag-warn { background: rgba(210,146,65,.14); color: #b7772f; }
.tag-bad { background: rgba(210,72,72,.13); color: #c84c4c; }
.actions { display: flex; gap: 6px; }
.mini-btn { padding: 5px 9px; border-radius: 8px; font-size: 12px; }
.mini-btn.accent { color: var(--c-accent); }
.mono { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; color: var(--c-text-2); }
.error-cell { max-width: 220px; color: var(--c-text-2); }
.message-cell { max-width: 360px; color: var(--c-text-2); }
.empty-state { padding: 42px; text-align: center; color: var(--c-text-3); }
.pager { display: flex; justify-content: flex-end; align-items: center; gap: 12px; padding: 14px; border-top: 1px solid var(--c-border); }
.pager button:disabled { opacity: .45; cursor: not-allowed; }
@media (max-width: 900px) {
  .stats-grid { grid-template-columns: 1fr; }
  .panel { overflow-x: auto; }
  .data-table { min-width: 900px; }
}
</style>
