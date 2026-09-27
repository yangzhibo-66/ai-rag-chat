<template>
  <div class="chat-root">
    <!-- ── Session Sidebar ── -->
    <aside class="session-sidebar">
      <div class="session-header">
        <span class="session-header-title">对话记录</span>
        <button class="new-chat-btn" @click="startNewChat" title="新对话">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          <span>新对话</span>
        </button>
      </div>

      <div class="session-list">
        <div
          v-for="s in sessions" :key="s.session_id"
          class="session-item"
          :class="{ active: currentSessionId === s.session_id }"
          @click="selectSession(s.session_id)"
        >
          <div class="session-item-icon">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div class="session-item-body">
            <div class="session-item-title" :title="s.first_question || '新对话'">{{ getSessionTitle(s) }}</div>
            <div class="session-item-date">{{ formatDateTime(s.last_activity || s.created_at) }}</div>
          </div>
          <button class="session-del-btn" @click.stop="deleteSession(s.session_id)" title="删除">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
              <path d="M10 11v6"/><path d="M14 11v6"/>
            </svg>
          </button>
        </div>

        <div v-if="sessions.length === 0" class="session-empty">
          暂无对话记录
        </div>
      </div>
    </aside>

    <!-- ── Chat Main ── -->
    <div class="chat-main">
      <!-- Top bar -->
      <header class="chat-topbar">
        <div class="topbar-left">
          <div class="ai-badge">
            <span class="ai-badge-dot"></span>
            AI 助手
          </div>
          <span v-if="isGuest" class="guest-badge">游客模式</span>
        </div>
        <div class="topbar-actions">
          <el-select v-model="chatMode" size="small" style="width: 130px">
            <el-option label="自由对话" value="free" />
            <el-option label="文档问答" value="rag_selected" />
          </el-select>
          <el-select
            v-model="selectedCategoryId"
            :disabled="chatMode !== 'rag_selected'"
            placeholder="选择分类"
            size="small"
            style="width: 140px"
          >
            <el-option label="未分类" :value="0" />
            <el-option
              v-for="cat in categories"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
          <el-select
            v-model="ragScope"
            :disabled="chatMode !== 'rag_selected'"
            size="small"
            style="width: 150px"
          >
            <el-option label="按分类检索" value="category" />
            <el-option label="分类内选文档" value="documents" />
          </el-select>
          <el-select
            v-model="selectedDocumentIds"
            multiple
            collapse-tags
            collapse-tags-tooltip
            :disabled="chatMode !== 'rag_selected' || ragScope !== 'documents' || selectedCategoryId === null"
            placeholder="选择文档"
            size="small"
            style="width: 220px"
          >
            <el-option
              v-for="doc in filteredCompletedDocuments"
              :key="doc.id"
              :label="documentLabel(doc)"
              :value="doc.id"
            />
          </el-select>
          <button class="topbar-btn" @click="clearCurrentChat" title="清空当前对话">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.5"/>
            </svg>
            清空
          </button>
          <button class="topbar-btn" @click="exportChat" title="导出对话">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            导出
          </button>
        </div>
      </header>

      <!-- Messages -->
      <div class="messages-area" ref="messagesContainer">
        <!-- Empty state -->
        <div v-if="!hasMessages && !isStreaming" class="empty-chat">
          <div class="empty-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <h3 class="empty-title">开始新的对话</h3>
          <p class="empty-desc">{{ isGuest ? '游客模式：体验基础问答功能。注册后可使用完整知识库。' : '基于您上传的文档，AI 将为您提供精准的答案。' }}</p>

          <div class="empty-guide">
            <div class="guide-card guide-card--warm">
              <span class="guide-badge">使用提示</span>
              <p>先选择“分类知识库”或“指定文档”，再输入问题；按 Ctrl + Enter 可快速发送。</p>
            </div>
            <div v-if="!isGuest" class="guide-card guide-card--fresh">
              <span class="guide-badge">提问建议</span>
              <p>按分类提问适合了解一组资料，指定文档提问适合针对单份或多份文档追问细节。</p>
            </div>
          </div>

          <div v-if="!isGuest" class="empty-tips">
            <div v-for="tip in quickTips" :key="tip" class="tip-chip" @click="useTip(tip)">{{ tip }}</div>
          </div>
        </div>

        <!-- Message list -->
        <div v-else class="messages-list">
          <div
            v-for="msg in currentMessages"
            :key="msg.id"
            class="msg-row"
            :class="msg.role === 'user' ? 'msg-row--user' : 'msg-row--ai'"
          >
            <div v-if="msg.role !== 'user'" class="msg-avatar msg-avatar--ai">AI</div>
            <div class="msg-bubble" :class="msg.role === 'user' ? 'msg-bubble--user' : 'msg-bubble--ai'">
              <div class="msg-text" v-html="formatMessage(msg.content)"></div>
              <div v-if="msg.quality && msg.quality.supported === false" class="msg-quality-warn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                本次回答与参考文档一致性存疑，已自动修正，建议核对下方来源原文
              </div>
              <div v-if="msg.sources?.length" class="msg-sources">
                <div class="sources-label">参考来源</div>
                <div class="sources-chips">
                  <span v-for="s in msg.sources" :key="`${s.document_id}-${s.chunk_index}-${s.filename}`" class="source-chip">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14,2 14,8 20,8"/>
                    </svg>
                    {{ s.filename }}
                    <em v-if="s.page_number !== null && s.page_number !== undefined">第{{ s.page_number }}页</em>
                    <em v-else-if="s.section">{{ s.section }}</em>
                    <em v-if="s.similarity !== null && s.similarity !== undefined">{{ formatSimilarity(s.similarity) }}</em>
                  </span>
                </div>
                <div class="source-snippets">
                  <details v-for="s in msg.sources.filter(item => item.snippet)" :key="`snippet-${s.document_id}-${s.chunk_index}-${s.filename}`" class="source-snippet">
                    <summary>{{ s.filename }}{{ s.page_number !== null && s.page_number !== undefined ? ` · 第${s.page_number}页` : (s.section ? ` · ${s.section}` : '') }}</summary>
                    <p>{{ s.snippet }}</p>
                  </details>
                </div>
              </div>
              <div class="msg-meta-row">
                <div class="msg-time">{{ formatTime(msg.created_at) }}</div>
                <div v-if="msg.role !== 'user'" class="msg-actions">
                  <button class="msg-action-btn" title="复制回复" @click="copyMessage(msg.content)">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                    </svg>
                    复制
                  </button>
                  <button class="msg-action-btn" title="基于这条回复继续提问" @click="askFollowUp(msg.content)">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                      <path d="M8 9h8M8 13h5"/>
                    </svg>
                    追问
                  </button>
                </div>
              </div>
            </div>
            <div v-if="msg.role === 'user'" class="msg-avatar msg-avatar--user">{{ userInitial }}</div>
          </div>

          <!-- Streaming bubble -->
          <div v-if="isStreaming" class="msg-row msg-row--ai">
            <div class="msg-avatar msg-avatar--ai">AI</div>
            <div class="msg-bubble msg-bubble--ai msg-bubble--streaming">
              <div class="msg-text" v-html="formatMessage(currentResponse) || ''"></div>
              <span class="stream-cursor"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-area">
        <div class="input-wrap">
          <el-input
            v-model="currentMessage"
            type="textarea"
            :rows="3"
            placeholder="输入您的问题… （Ctrl + Enter 发送）"
            @keydown.ctrl.enter="sendMessage"
            :disabled="isLoading || isStreaming"
            class="chat-textarea"
            resize="none"
          />
          <div class="input-footer">
            <span class="input-hint">Ctrl + Enter 发送</span>
            <button
              class="send-btn"
              :class="{ 'send-btn--loading': isLoading || isStreaming }"
              :disabled="!currentMessage.trim() || isLoading || isStreaming"
              @click="sendMessage"
            >
              <span v-if="!isLoading && !isStreaming">
                发送
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </span>
              <span v-else class="send-loading">
                <svg width="14" height="14" viewBox="0 0 24 24" class="spin"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="60" stroke-dashoffset="45"/></svg>
                生成中
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useUserStore } from '../store'
import { chatApi } from '../api/chat'
import { documentsApi } from '../api/documents'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const store   = useUserStore()
const isGuest = computed(() => store.user?.username === '游客')

const currentMessage  = ref('')
const currentResponse = ref('')
const isLoading       = ref(false)
const isStreaming     = ref(false)
const currentSessionId = ref('')
const messages        = ref([])
const sessions        = ref([])
const messagesContainer = ref(null)

const username    = computed(() => store.username)
const userInitial = computed(() => (username.value || '?').charAt(0).toUpperCase())
const hasMessages = computed(() => currentMessages.value.length > 0)
const currentMessages = computed(() =>
  !currentSessionId.value
    ? messages.value.filter(m => !m.session_id || m.session_id === currentSessionId.value)
    : messages.value.filter(m => m.session_id === currentSessionId.value)
)

const chatMode = ref('free')
const ragScope = ref('category')
const selectedCategoryId = ref(null)
const selectedDocumentIds = ref([])
const completedDocuments = ref([])
const categories = ref([])

const quickTips = ['这份文档的主要内容是什么？', '请总结文档中的关键点', '文档中提到了哪些重要概念？']

const filteredCompletedDocuments = computed(() => {
  if (selectedCategoryId.value === null || selectedCategoryId.value === undefined) return []
  if (selectedCategoryId.value === 0) {
    return completedDocuments.value.filter(d => d.category_id === null || d.category_id === undefined)
  }
  return completedDocuments.value.filter(d => d.category_id === selectedCategoryId.value)
})

const documentLabel = (doc) => {
  const isImage = doc?.content_type === 'image' || (doc?.file_type || '').includes('image')
  return isImage ? `[图片] ${doc.original_filename}` : doc.original_filename
}

const useTip = (tip) => { currentMessage.value = tip }

const copyMessage = async (content) => {
  try {
    await navigator.clipboard.writeText(content || '')
    ElMessage.success('已复制回复')
  } catch {
    ElMessage.error('复制失败，请手动选择文本复制')
  }
}

const askFollowUp = (content) => {
  const text = (content || '').replace(/\s+/g, ' ').trim()
  currentMessage.value = `请基于这条回复继续说明：${text.slice(0, 80)}${text.length > 80 ? '...' : ''}`
}

const parseApiDate = (d) => {
  if (!d) return null
  const raw = String(d).trim()
  const hasTz = /(?:Z|[+-]\d{2}:\d{2})$/.test(raw)
  const normalized = hasTz ? raw : `${raw}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

const formatDateTime = (d) => {
  const date = parseApiDate(d)
  if (!date) return ''
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatTime = (d) => {
  const date = parseApiDate(d)
  return date ? date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : ''
}

const formatSimilarity = (value) => `${Math.round(Number(value) * 100)}%`

const getSessionTitle = (session) => {
  if (!session?.first_question) return '新对话'
  const title = session.first_question.trim()
  if (!title) return '新对话'
  return title.length > 40 ? `${title.slice(0, 40)}...` : title
}

marked.use({ breaks: true, gfm: true })

const formatMessage = (text) => {
  if (!text) return ''
  return DOMPurify.sanitize(marked.parse(text), { ALLOWED_TAGS: ['p','br','strong','em','code','pre','ul','ol','li','blockquote','h1','h2','h3','h4','h5','h6','a','table','thead','tbody','tr','th','td','hr','span'] })
}

const scrollToBottom = () => nextTick(() => {
  if (messagesContainer.value)
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
})

const startNewChat = () => { currentSessionId.value = ''; currentResponse.value = '' }

const loadSessionMessages = async (sessionId) => {
  if (!sessionId) return
  isLoading.value = true
  try {
    const r = await chatApi.getHistory({ session_id: sessionId, limit: 100 })
    const loaded = (r.messages || []).map(m => ({
      id: m.id || Date.now() + Math.random(),
      role: m.role,
      content: m.content,
      session_id: sessionId,
      created_at: m.created_at,
      sources: m.sources || []
    }))
    messages.value = [
      ...messages.value.filter(m => m.session_id !== sessionId),
      ...loaded
    ]
  } catch { /* silent */ }
  finally { isLoading.value = false }
}

const selectSession = async (id) => {
  currentSessionId.value = id
  await loadSessionMessages(id)
  scrollToBottom()
}

const deleteSession = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？', '确认删除', { type: 'warning' })
    await chatApi.clearHistory(id)
    await loadSessions()
    if (currentSessionId.value === id) currentSessionId.value = ''
    ElMessage.success('对话已删除')
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

const clearCurrentChat = async () => {
  if (!currentSessionId.value) return
  try {
    await ElMessageBox.confirm('确定要清空当前对话吗？', '确认清空', { type: 'warning' })
    await chatApi.clearHistory(currentSessionId.value)
    messages.value = messages.value.filter(m => m.session_id !== currentSessionId.value)
    ElMessage.success('已清空')
  } catch (e) { if (e !== 'cancel') ElMessage.error('清空失败') }
}

const exportChat = () => {
  if (!hasMessages.value) { ElMessage.warning('没有内容可导出'); return }
  const content = currentMessages.value.map(m => `${m.role === 'user' ? '用户' : 'AI'}: ${m.content}`).join('\n\n')
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = `chat_${new Date().toISOString().split('T')[0]}.txt`
  document.body.appendChild(a); a.click(); document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const loadCompletedDocuments = async () => {
  if (isGuest.value) {
    completedDocuments.value = []
    return
  }
  try {
    const r = await documentsApi.getDocuments({ page: 1, page_size: 100 })
    completedDocuments.value = (r.documents || []).filter(d => d.status === 'completed')
  } catch {
    completedDocuments.value = []
  }
}

const loadCategories = async () => {
  if (isGuest.value) {
    categories.value = []
    return
  }
  try {
    const r = await documentsApi.getCategories()
    categories.value = r.categories || []
  } catch {
    categories.value = []
  }
}

const sendMessage = async () => {
  const msg = currentMessage.value.trim()
  if (!msg || isLoading.value || isStreaming.value) return

  currentMessage.value = ''
  isStreaming.value = true
  currentResponse.value = ''

  const userMessageId = Date.now()
  messages.value.push({
    id: userMessageId, role: 'user', content: msg,
    session_id: currentSessionId.value,
    created_at: new Date().toISOString(), sources: []
  })
  await scrollToBottom()

  let responseSources = []
  let responseQuality = null
  try {
    if (chatMode.value === 'rag_selected') {
      if (selectedCategoryId.value === null || selectedCategoryId.value === undefined) {
        ElMessage.warning('文档问答模式下请先选择分类')
        isStreaming.value = false
        currentMessage.value = msg
        return
      }
      if (ragScope.value === 'documents' && !selectedDocumentIds.value.length) {
        ElMessage.warning('请先在该分类内选择文档')
        isStreaming.value = false
        currentMessage.value = msg
        return
      }
    }

    await chatApi.sendMessage(
      msg, currentSessionId.value,
      (token) => { currentResponse.value += token; scrollToBottom() },
      (meta)  => {
        if (meta?.session_id) {
          currentSessionId.value = meta.session_id
          messages.value = messages.value.map(m =>
            m.id === userMessageId ? { ...m, session_id: meta.session_id } : m
          )
        }
        if (meta?.sources) responseSources = meta.sources
      },
      (err)   => { ElMessage.error('发送失败: ' + err); isStreaming.value = false },
      {
        chat_mode: chatMode.value,
        selected_category_id: chatMode.value === 'rag_selected' ? selectedCategoryId.value : null,
        selected_document_ids: chatMode.value === 'rag_selected' && ragScope.value === 'documents' ? selectedDocumentIds.value : null
      },
      (quality) => {
        if (quality && quality.supported === false) responseQuality = quality
      }
    )

    if (currentResponse.value) {
      messages.value.push({
        id: Date.now() + 1, role: 'assistant', content: currentResponse.value,
        session_id: currentSessionId.value,
        created_at: new Date().toISOString(), sources: responseSources,
        quality: responseQuality
      })
    }
  } catch { ElMessage.error('发送失败') }
  finally {
    isStreaming.value = false; currentResponse.value = ''
    scrollToBottom(); await loadSessions()
  }
}

const loadSessions = async () => {
  try {
    const r = await chatApi.getSessions()
    sessions.value = r.sessions || []
  } catch { /* silent */ }
}

onMounted(async () => {
  await loadSessions()
  await Promise.all([loadCompletedDocuments(), loadCategories()])
})
watch(currentSessionId, scrollToBottom)
watch(chatMode, (mode) => {
  if (mode !== 'rag_selected') {
    selectedDocumentIds.value = []
    selectedCategoryId.value = null
    ragScope.value = 'category'
  }
})
watch(selectedCategoryId, () => {
  selectedDocumentIds.value = []
})
watch(ragScope, (scope) => {
  if (scope !== 'documents') selectedDocumentIds.value = []
})
</script>

<style scoped>
.chat-root {
  display: flex;
  height: 100vh;
  background: var(--c-bg);
  overflow: hidden;
}

/* ── Session sidebar ── */
.session-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--c-elevated);
  border-right: 1px solid #e9eef6;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 16px 14px;
  border-bottom: 1px solid var(--c-border);
}
.session-header-title {
  font-size: 11px; font-weight: 600;
  color: var(--c-text-3);
  text-transform: uppercase; letter-spacing: .1em;
}
.new-chat-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 10px;
  background: var(--c-accent-dim);
  border: 1px solid rgba(2,119,189,.25);
  border-radius: var(--r-sm);
  color: var(--c-accent);
  font-size: 11px; font-weight: 600; letter-spacing: .04em;
  cursor: pointer; transition: background .15s;
}
.new-chat-btn:hover { background: rgba(2,119,189,.18); }

.session-list {
  flex: 1; overflow-y: auto; padding: 8px;
}
.session-list::-webkit-scrollbar { width: 4px; }
.session-list::-webkit-scrollbar-track { background: transparent; }
.session-list::-webkit-scrollbar-thumb { background: var(--c-border); border-radius: 2px; }

.session-item {
  display: flex; align-items: center; gap: 8px;
  padding: 11px 10px;
  border: 1px solid transparent;
  border-bottom-color: rgba(179, 193, 211, .42);
  border-radius: var(--r-md);
  cursor: pointer;
  transition: background .15s, border-color .15s, box-shadow .15s, transform .15s;
  position: relative;
  margin-bottom: 6px;
}
.session-item:hover {
  background: #f8fbff;
  border-color: rgba(116, 144, 183, .24);
  box-shadow: 0 8px 20px rgba(51, 63, 83, .06);
  transform: translateY(-1px);
}
.session-item:hover .session-del-btn { opacity: 1; }
.session-item.active {
  background: var(--c-accent-dim);
  border: 1px solid rgba(79,111,220,.2);
  box-shadow: inset 2px 2px 6px rgba(79,111,220,.10), inset -2px -2px 6px rgba(255,255,255,.95);
}
.session-item-icon { color: var(--c-text-3); flex-shrink: 0; }
.session-item.active .session-item-icon { color: var(--c-accent); }
.session-item-body { flex: 1; min-width: 0; }
.session-item-title { font-size: 12px; font-weight: 500; color: var(--c-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.session-item-date { font-size: 11px; color: var(--c-text-3); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.session-del-btn {
  opacity: 0;
  width: 22px; height: 22px;
  background: none;
  border: none; border-radius: var(--r-sm);
  color: var(--c-text-3); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background .15s, color .15s, opacity .15s;
  flex-shrink: 0;
}
.session-del-btn:hover { background: rgba(184,88,88,.15); color: var(--c-err); }

.session-empty {
  text-align: center; color: var(--c-text-3);
  font-size: 12px; padding: 32px 16px;
}

/* ── Chat main ── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* Top bar */
.chat-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  height: 52px;
  background: var(--c-bg);
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}
.topbar-left { display: flex; align-items: center; gap: 10px; }
.ai-badge {
  display: flex; align-items: center; gap: 7px;
  font-size: 13px; font-weight: 600; color: var(--c-text);
}
.ai-badge-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--c-ok);
  box-shadow: 0 0 6px rgba(106,158,110,.6);
  animation: pulse 2s ease infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .5; }
}
.guest-badge {
  font-size: 10px; font-weight: 600;
  padding: 2px 8px;
  background: var(--c-accent-dim);
  border: 1px solid rgba(2,119,189,.25);
  border-radius: var(--r-sm);
  color: var(--c-accent);
  letter-spacing: .04em;
}
.topbar-actions { display: flex; gap: 6px; }
.topbar-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 6px 12px;
  background: var(--c-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  color: var(--c-text-2);
  font-size: 12px; cursor: pointer;
  transition: background .15s, color .15s;
}
.topbar-btn:hover { background: var(--c-border); color: var(--c-text); }

/* Messages area */
.messages-area {
  flex: 1; overflow-y: auto; padding: 28px 24px;
}
.messages-area::-webkit-scrollbar { width: 5px; }
.messages-area::-webkit-scrollbar-track { background: transparent; }
.messages-area::-webkit-scrollbar-thumb { background: var(--c-border); border-radius: 3px; }

/* Empty state */
.empty-chat {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  height: 100%; min-height: 320px;
  text-align: center;
}
.empty-icon {
  width: 64px; height: 64px; border-radius: var(--r-xl);
  background: var(--c-elevated);
  border: 1px solid var(--c-border);
  display: flex; align-items: center; justify-content: center;
  color: var(--c-text-3); margin-bottom: 20px;
}
.empty-title { font-size: 18px; font-weight: 600; color: var(--c-text); margin: 0 0 8px; }
.empty-desc { font-size: 13px; color: var(--c-text-2); margin: 0 0 18px; max-width: 360px; line-height: 1.6; }
.empty-guide {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: min(560px, 100%);
  margin-bottom: 18px;
}
.guide-card {
  padding: 14px 16px;
  border-radius: var(--r-lg);
  text-align: left;
  box-shadow: 0 10px 24px rgba(51, 63, 83, .08);
}
.guide-card--warm {
  background: linear-gradient(135deg, #fffbed, #fffef8);
  border: 1px solid rgba(225, 181, 66, .18);
}
.guide-card--fresh {
  background: linear-gradient(135deg, #f4fbef, #fbfff8);
  border: 1px solid rgba(119, 174, 82, .16);
}
.guide-badge {
  display: inline-block;
  margin-bottom: 7px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255,255,255,.7);
  color: #6f5b12;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .08em;
}
.guide-card--fresh .guide-badge { color: #386a28; }
.guide-card p {
  margin: 0;
  color: var(--c-text-2);
  font-size: 12px;
  line-height: 1.7;
}
.empty-tips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; max-width: 620px; }
.tip-chip {
  padding: 8px 15px;
  background: var(--c-elevated);
  border: 1px solid var(--c-border);
  border-radius: 24px;
  font-size: 12px; color: var(--c-text-2);
  cursor: pointer; transition: all .15s;
}
.tip-chip:hover { background: var(--c-accent-dim); border-color: rgba(2,119,189,.3); color: var(--c-accent); transform: translateY(-1px); }
@media (max-width: 760px) {
  .empty-guide { grid-template-columns: 1fr; }
}

/* Messages */
.messages-list { display: flex; flex-direction: column; gap: 20px; }

.msg-row { display: flex; align-items: flex-end; gap: 10px; }
.msg-row--user { flex-direction: row-reverse; }

.msg-avatar {
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700;
  flex-shrink: 0;
}
.msg-avatar--ai { background: linear-gradient(135deg, var(--c-accent), #7f99e8); color: #ffffff; border: 1px solid rgba(79,111,220,.2); }
.msg-avatar--user { background: linear-gradient(135deg, var(--c-accent), #7f99e8); color: #ffffff; }

.msg-bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: var(--r-lg);
  position: relative;
}
.msg-bubble--ai {
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  box-shadow: var(--shadow-sm);
  border-bottom-left-radius: var(--r-sm);
  padding-bottom: 10px;
}
.msg-bubble--user {
  background: linear-gradient(135deg, rgba(79,111,220,.10), rgba(79,111,220,.06));
  border: 1px solid rgba(79,111,220,.24);
  box-shadow: var(--shadow-sm);
  border-bottom-right-radius: var(--r-sm);
}

.msg-text {
  font-size: 14px; line-height: 1.65; color: var(--c-text);
  word-break: break-word;
}
.msg-text :deep(p) { margin: 0 0 8px; }
.msg-text :deep(p:last-child) { margin-bottom: 0; }
.msg-text :deep(strong) { color: var(--c-text); font-weight: 600; }
.msg-text :deep(em) { color: var(--c-text-2); }
.msg-text :deep(code) {
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--c-elevated);
  padding: 1px 5px; border-radius: var(--r-sm);
  color: var(--c-accent);
}
.msg-text :deep(pre) {
  background: var(--c-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  padding: 12px 14px;
  overflow-x: auto;
  margin: 8px 0;
}
.msg-text :deep(pre code) {
  background: none; padding: 0; border-radius: 0;
  font-size: 12px; color: var(--c-text);
}
.msg-text :deep(ul), .msg-text :deep(ol) {
  margin: 6px 0; padding-left: 20px;
}
.msg-text :deep(li) { margin: 3px 0; }
.msg-text :deep(blockquote) {
  border-left: 3px solid var(--c-accent);
  margin: 8px 0; padding: 6px 12px;
  background: var(--c-elevated);
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
  color: var(--c-text-2);
}
.msg-text :deep(h1), .msg-text :deep(h2), .msg-text :deep(h3) {
  color: var(--c-text); font-weight: 600; margin: 10px 0 6px;
}
.msg-text :deep(h1) { font-size: 16px; }
.msg-text :deep(h2) { font-size: 15px; }
.msg-text :deep(h3) { font-size: 14px; }
.msg-text :deep(table) {
  border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 13px;
}
.msg-text :deep(th), .msg-text :deep(td) {
  border: 1px solid var(--c-border); padding: 6px 10px; text-align: left;
}
.msg-text :deep(th) { background: var(--c-elevated); font-weight: 600; }
.msg-text :deep(a) { color: var(--c-accent); text-decoration: underline; }
.msg-text :deep(hr) { border: none; border-top: 1px solid var(--c-border); margin: 10px 0; }

.msg-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}
.msg-time {
  font-size: 10px; color: var(--c-text-3);
  text-align: right;
}
.msg-bubble--ai .msg-time { text-align: left; }
.msg-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  opacity: .52;
  transition: opacity .15s;
}
.msg-bubble--ai:hover .msg-actions { opacity: 1; }
.msg-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 9px;
  border: 1px solid rgba(151, 164, 185, .34);
  border-radius: 999px;
  background: linear-gradient(180deg, #ffffff, #f7faff);
  color: var(--c-text-3);
  font-size: 11px;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(51, 63, 83, .05);
  transition: color .15s, border-color .15s, background .15s, transform .15s;
}
.msg-action-btn:hover {
  color: var(--c-accent);
  border-color: rgba(2,119,189,.28);
  background: var(--c-accent-dim);
  transform: translateY(-1px);
}

.msg-sources { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--c-border); }
.msg-quality-warn {
  display: flex; align-items: center; gap: 6px;
  margin-top: 8px; padding: 6px 10px;
  font-size: 12px; color: #b45309;
  background: #fef3c7; border: 1px solid #fcd34d; border-radius: 6px;
}
.sources-label { font-size: 10px; font-weight: 600; color: var(--c-text-3); letter-spacing: .06em; text-transform: uppercase; margin-bottom: 6px; }
.sources-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.source-chip {
  display: flex; align-items: center; gap: 4px;
  padding: 3px 8px;
  background: var(--c-elevated);
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  font-size: 11px; color: var(--c-text-2);
}
.source-chip em {
  font-style: normal;
  color: var(--c-accent);
  font-size: 10px;
}
.source-snippets {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.source-snippet {
  border: 1px solid var(--c-border);
  border-radius: var(--r-sm);
  background: #fbfdff;
  padding: 7px 9px;
  font-size: 12px;
}
.source-snippet summary {
  cursor: pointer;
  color: var(--c-text-2);
  font-weight: 600;
}
.source-snippet p {
  margin: 6px 0 0;
  color: var(--c-text-2);
  line-height: 1.6;
}

/* Streaming */
.msg-bubble--streaming { }
.stream-cursor {
  display: inline-block;
  width: 2px; height: 14px;
  background: var(--c-accent);
  border-radius: 1px;
  margin-left: 2px;
  vertical-align: middle;
  animation: blink .8s step-end infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ── Input area ── */
.input-area {
  padding: 16px 24px 20px;
  border-top: 1px solid var(--c-border);
  background: var(--c-bg);
  flex-shrink: 0;
}
.input-wrap {
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: border-color .15s;
}
.input-wrap:focus-within { border-color: var(--c-border-h); }

.chat-textarea :deep(.el-textarea__inner) {
  background: var(--c-surface) !important;
  border: none !important;
  padding: 14px 16px 10px !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
  min-height: 72px !important;
  box-shadow: none !important;
  resize: none !important;
}

.input-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px 10px 16px;
  border-top: 1px solid var(--c-border);
}
.input-hint { font-size: 11px; color: var(--c-text-3); letter-spacing: .02em; }
.send-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 16px;
  background: var(--c-accent);
  border: none; border-radius: var(--r-md);
  color: #ffffff;
  font-size: 13px; font-weight: 600;
  cursor: pointer; transition: opacity .15s, transform .1s, box-shadow .15s;
  box-shadow: var(--glow-accent-soft);
  position: relative;
  overflow: hidden;
}
.send-btn::before {
  content: '';
  position: absolute;
  inset: 1px 1px auto 1px;
  height: 42%;
  border-radius: inherit;
  background: linear-gradient(180deg, rgba(255,255,255,.34) 0%, rgba(255,255,255,0) 100%);
  pointer-events: none;
}
.send-btn:hover:not(:disabled) { opacity: .95; box-shadow: var(--glow-accent); }
.send-btn:active:not(:disabled) { transform: translateY(1px) scale(.987); box-shadow: var(--glow-press); }
.send-btn:disabled { opacity: .4; cursor: not-allowed; }
.send-btn--loading { background: var(--c-elevated); color: var(--c-text-2); box-shadow: none; }
.send-loading { display: flex; align-items: center; gap: 6px; }
.spin { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
