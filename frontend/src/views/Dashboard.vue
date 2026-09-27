<template>
  <div class="dash-root">
    <!-- ── Page header ── -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">仪表板</h1>
        <p class="page-sub">{{ greeting }}，<strong>{{ displayName }}</strong></p>
      </div>
      <div class="header-actions">
        <button class="action-btn action-btn--primary" :disabled="isGuestUser" @click="goToUpload">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/>
            <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
          </svg>
          上传文档
        </button>
        <button class="action-btn" @click="goToChat">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          开始对话
        </button>
        <button v-if="isGuestUser" class="action-btn action-btn--accent" @click="goToLogin">
          注册解锁全功能 →
        </button>
      </div>
    </div>

    <!-- ── Stats row ── -->
    <div class="stats-grid">
      <div v-for="s in statCards" :key="s.key" class="stat-card">
        <div class="stat-card-icon" :style="{ background: s.iconBg }">
          <component :is="s.icon" />
        </div>
        <div class="stat-card-body">
          <div class="stat-num" :class="{ 'stat-num--loading': !statsLoaded }">
            {{ statsLoaded ? formatNum(stats[s.key]) : '—' }}
          </div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
        <div class="stat-card-trend">{{ s.trend }}</div>
      </div>
    </div>

    <!-- ── Activity row ── -->
    <div class="activity-grid">
      <!-- Recent documents -->
      <div class="activity-card">
        <div class="activity-card-header">
          <span class="activity-card-title">最近文档</span>
          <button class="link-btn" @click="goToDocuments">查看全部 →</button>
        </div>

        <div v-if="recentDocuments.length" class="doc-list">
          <div v-for="doc in recentDocuments" :key="doc.id" class="doc-row" @click="goToDocuments">
            <div class="doc-icon">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
              </svg>
            </div>
            <div class="doc-info">
              <div class="doc-name">{{ doc.original_filename }}</div>
              <div class="doc-meta">{{ formatDate(doc.created_at) }}</div>
            </div>
            <span class="status-dot" :class="statusClass(doc.status)"></span>
            <span class="status-text">{{ statusText(doc.status) }}</span>
          </div>
        </div>

        <div v-else class="activity-empty">
          <div class="ae-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
            </svg>
          </div>
          <p>尚未上传任何文档</p>
          <button v-if="!isGuestUser" class="action-btn action-btn--sm" @click="goToUpload">立即上传</button>
        </div>
      </div>

      <!-- Recent chats -->
      <div class="activity-card">
        <div class="activity-card-header">
          <span class="activity-card-title">最近对话</span>
          <button class="link-btn" @click="goToChat">查看全部 →</button>
        </div>

        <div v-if="recentChats.length" class="chat-list">
          <div v-for="chat in recentChats" :key="chat.id" class="chat-row" @click="goToChat">
            <div class="chat-bubble-icon">Q</div>
            <div class="chat-info">
              <div class="chat-q">{{ truncate(chat.content, 52) }}</div>
              <div class="chat-meta">{{ formatDate(chat.created_at) }}</div>
            </div>
          </div>
        </div>

        <div v-else class="activity-empty">
          <div class="ae-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <p>还没有对话记录</p>
          <button class="action-btn action-btn--sm" @click="goToChat">开始对话</button>
        </div>
      </div>
    </div>

    <!-- ── Quick actions ── -->
    <div class="quick-actions">
      <div class="qa-header">快速操作</div>
      <div class="qa-grid">
        <button v-for="qa in quickActions" :key="qa.label" class="qa-card" @click="qa.action()">
          <div class="qa-icon" :style="{ color: qa.color }">
            <component :is="qa.icon" />
          </div>
          <div class="qa-label">{{ qa.label }}</div>
          <div class="qa-arrow">→</div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store'
import { documentsApi } from '../api/documents'
import { chatApi } from '../api/chat'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const store  = useUserStore()
const user   = computed(() => store.user)
const isGuestUser = computed(() => !store.isAuthenticated && !!store.user)
const displayName = computed(() => user.value?.full_name || user.value?.username || '访客')
const greeting    = computed(() => {
  const h = new Date().getHours()
  if (h < 6)  return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const stats       = ref({ documents: 0, messages: 0, total_words: 0, sessions: 0 })
const statsLoaded = ref(false)
const recentDocuments = ref([])
const recentChats     = ref([])

const formatNum = (n) => {
  if (!n) return '0'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return String(n)
}
const formatDate = (d) => d ? new Date(d).toLocaleDateString('zh-CN') : ''
const truncate   = (s, n) => s?.length > n ? s.substring(0, n) + '…' : s

const statusText = (s) => ({ uploading: '上传中', processing: '处理中', completed: '完成', failed: '失败' }[s] || s)
const statusClass = (s) => ({ uploading: 'dot--info', processing: 'dot--warn', completed: 'dot--ok', failed: 'dot--err' }[s] || '')

// SVG icon helpers
const IconDoc = { render: () => h('svg', { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('path', { d: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' }),
  h('polyline', { points: '14,2 14,8 20,8' }),
]) }
const IconChat = { render: () => h('svg', { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('path', { d: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' }),
]) }
const IconWord = { render: () => h('svg', { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('path', { d: 'M12 20h9' }), h('path', { d: 'M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z' }),
]) }
const IconSession = { render: () => h('svg', { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('circle', { cx: 12, cy: 12, r: 10 }), h('polyline', { points: '12 6 12 12 16 14' }),
]) }
const IconUpload = { render: () => h('svg', { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('polyline', { points: '16 16 12 12 8 16' }), h('line', { x1: 12, y1: 12, x2: 12, y2: 21 }),
  h('path', { d: 'M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3' }),
]) }
const IconTrash = { render: () => h('svg', { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('polyline', { points: '3 6 5 6 21 6' }), h('path', { d: 'M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6' }),
  h('path', { d: 'M10 11v6' }), h('path', { d: 'M14 11v6' }),
]) }
const IconManage = { render: () => h('svg', { width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('line', { x1: 8, y1: 6, x2: 21, y2: 6 }), h('line', { x1: 8, y1: 12, x2: 21, y2: 12 }),
  h('line', { x1: 8, y1: 18, x2: 21, y2: 18 }), h('line', { x1: 3, y1: 6, x2: '3.01', y2: 6 }),
  h('line', { x1: 3, y1: 12, x2: '3.01', y2: 12 }), h('line', { x1: 3, y1: 18, x2: '3.01', y2: 18 }),
]) }

const statCards = [
  { key: 'documents',   label: '文档总数',   iconBg: 'rgba(2,119,189,.12)',    icon: IconDoc,     trend: '文档库' },
  { key: 'messages',    label: '对话消息',   iconBg: 'rgba(46,125,50,.12)',    icon: IconChat,    trend: '累计' },
  { key: 'total_words', label: '总字数',     iconBg: 'rgba(100,150,240,.12)',  icon: IconWord,    trend: '已索引' },
  { key: 'sessions',    label: '对话会话',   iconBg: 'rgba(160,100,200,.12)',  icon: IconSession, trend: '全部' },
]

const goToLogin     = () => router.push('/login')
const goToUpload    = () => router.push('/documents')
const goToChat      = () => router.push('/chat')
const goToDocuments = () => router.push('/documents')

const quickActions = [
  { label: '上传新文档', icon: IconUpload, color: 'var(--c-accent)', action: goToUpload },
  { label: '开始新对话', icon: IconChat,   color: 'var(--c-ok)',     action: goToChat },
  { label: '管理文档库', icon: IconManage, color: '#8ab0f0',         action: goToDocuments },
  {
    label: '清空对话记录', icon: IconTrash, color: 'var(--c-err)',
    action: async () => {
      try {
        await ElMessageBox.confirm('将删除所有对话记录，此操作不可恢复。', '确认清空', { type: 'warning' })
        await chatApi.clearHistory()
        ElMessage.success('对话记录已清空')
        loadData()
      } catch (e) { if (e !== 'cancel') ElMessage.error('操作失败') }
    }
  },
]

const loadData = async () => {
  try {
    const [docsRes, chatRes, sessRes] = await Promise.all([
      documentsApi.getDocuments({ page: 1, page_size: 5 }),
      chatApi.getHistory({ limit: 5 }),
      chatApi.getSessions(),
    ])

    recentDocuments.value = docsRes.documents || []
    stats.value.documents  = docsRes.total || 0
    stats.value.total_words = recentDocuments.value.reduce((s, d) => s + (d.word_count || 0), 0)

    const allMessages = chatRes.messages || []
    recentChats.value = allMessages.filter(m => m.role === 'user')
    stats.value.messages = chatRes.total || 0
    stats.value.sessions = sessRes.sessions?.length || 0
    statsLoaded.value = true
  } catch {
    statsLoaded.value = true
  }
}

onMounted(loadData)
</script>

<style scoped>
.dash-root {
  padding: 32px 36px;
  max-width: 1100px;
  margin: 0 auto;
  display: flex; flex-direction: column; gap: 28px;
}

/* ── Header ── */
.page-header {
  display: flex; align-items: flex-end; justify-content: space-between;
}
.page-title {
  font-family: var(--font-serif);
  font-size: 26px; font-weight: 700;
  color: var(--c-text);
  margin: 0 0 4px;
}
.page-sub { font-size: 14px; color: var(--c-text-2); margin: 0; }
.page-sub strong { color: var(--c-accent); font-weight: 600; }
.header-actions { display: flex; gap: 8px; align-items: center; }

.action-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px;
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-md);
  color: var(--c-text-2); font-size: 13px; font-weight: 500;
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
  cursor: pointer; transition: all .15s;
}
.action-btn::before {
  content: '';
  position: absolute;
  inset: 1px 1px auto 1px;
  height: 42%;
  border-radius: inherit;
  background: linear-gradient(180deg, rgba(255,255,255,.68) 0%, rgba(255,255,255,0) 100%);
  pointer-events: none;
}
.action-btn:hover:not(:disabled) { background: #f8fbff; color: var(--c-text); }
.action-btn:active:not(:disabled) { transform: translateY(1px) scale(.987); box-shadow: var(--glow-press); }
.action-btn:disabled { opacity: .4; cursor: not-allowed; }
.action-btn--primary { background: var(--c-accent); border-color: var(--c-accent); color: #ffffff; font-weight: 600; box-shadow: var(--glow-accent-soft); }
.action-btn--primary:hover:not(:disabled) { background: var(--c-accent-h); box-shadow: var(--glow-accent); }
.action-btn--accent  { background: var(--c-accent-dim); border-color: rgba(79,111,220,.28); color: var(--c-accent); box-shadow: 0 0 0 1px rgba(79,111,220,.10), 0 6px 14px rgba(79,111,220,.16); }
.action-btn--sm      { padding: 5px 12px; font-size: 12px; }

/* ── Stats ── */
.stats-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
}
.stat-card {
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-sm);
  padding: 20px;
  display: flex; align-items: center; gap: 14px;
  transition: border-color .15s, transform .15s, box-shadow .15s;
}
.stat-card:hover { border-color: var(--c-border-h); transform: translateY(-1px); box-shadow: var(--shadow-md); }
.stat-card-icon {
  width: 44px; height: 44px; border-radius: var(--r-md);
  display: flex; align-items: center; justify-content: center;
  color: var(--c-accent); flex-shrink: 0;
}
.stat-card-body { flex: 1; min-width: 0; }
.stat-num {
  font-size: 26px; font-weight: 700;
  color: var(--c-text); line-height: 1;
  margin-bottom: 4px;
  font-variant-numeric: tabular-nums;
}
.stat-num--loading { color: var(--c-text-3); }
.stat-label { font-size: 12px; color: var(--c-text-2); }
.stat-card-trend {
  font-size: 10px; color: var(--c-text-3);
  letter-spacing: .04em; text-transform: uppercase;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

/* ── Activity ── */
.activity-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.activity-card {
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}
.activity-card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border);
}
.activity-card-title {
  font-size: 12px; font-weight: 600;
  color: var(--c-text-2);
  text-transform: uppercase; letter-spacing: .08em;
}
.link-btn {
  background: none; border: none;
  color: var(--c-accent); font-size: 12px; cursor: pointer;
  transition: opacity .15s;
}
.link-btn:hover { opacity: .75; }

.doc-list, .chat-list { display: flex; flex-direction: column; }
.doc-row, .chat-row {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 20px;
  cursor: pointer; transition: background .12s;
  border-bottom: 1px solid var(--c-border);
}
.doc-row:last-child, .chat-row:last-child { border-bottom: none; }
.doc-row:hover, .chat-row:hover { background: #f8fbff; }
.doc-icon {
  width: 28px; height: 28px; border-radius: var(--r-sm);
  background: var(--c-elevated); border: 1px solid #e9eef6;
  box-shadow: var(--shadow-sm);
  display: flex; align-items: center; justify-content: center;
  color: var(--c-text-3); flex-shrink: 0;
}
.doc-info, .chat-info { flex: 1; min-width: 0; }
.doc-name { font-size: 13px; font-weight: 500; color: var(--c-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-meta, .chat-meta { font-size: 11px; color: var(--c-text-3); margin-top: 2px; }

.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.dot--ok   { background: var(--c-ok);   box-shadow: 0 0 4px rgba(106,158,110,.5); }
.dot--err  { background: var(--c-err);  box-shadow: 0 0 4px rgba(184,88,88,.5); }
.dot--warn { background: var(--c-warn); box-shadow: 0 0 4px rgba(192,136,80,.5); animation: pulse 1.5s ease infinite; }
.dot--info { background: #8ab0f0;       }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
.status-text { font-size: 11px; color: var(--c-text-3); width: 36px; text-align: right; flex-shrink: 0; }

.chat-bubble-icon {
  width: 28px; height: 28px; border-radius: var(--r-sm);
  background: var(--c-accent-dim); border: 1px solid rgba(79,111,220,.2);
  box-shadow: var(--shadow-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: var(--c-accent);
  flex-shrink: 0;
}
.chat-q { font-size: 13px; font-weight: 500; color: var(--c-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.activity-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 36px 20px; gap: 10px;
}
.ae-icon { color: var(--c-text-3); }
.activity-empty p { font-size: 13px; color: var(--c-text-3); margin: 0; }

/* ── Quick actions ── */
.quick-actions { }
.qa-header {
  font-size: 11px; font-weight: 600; color: var(--c-text-3);
  text-transform: uppercase; letter-spacing: .1em;
  margin-bottom: 12px;
}
.qa-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.qa-card {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 16px;
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-md);
  box-shadow: var(--shadow-sm);
  cursor: pointer; transition: border-color .15s, background .15s, transform .15s;
  text-align: left;
}
.qa-card:hover { background: #f8fbff; border-color: var(--c-border-h); transform: translateY(-1px); }
.qa-icon { flex-shrink: 0; }
.qa-label { flex: 1; font-size: 13px; font-weight: 500; color: var(--c-text-2); }
.qa-arrow { font-size: 13px; color: var(--c-text-3); }
.qa-card:hover .qa-arrow { color: var(--c-text); }
</style>
