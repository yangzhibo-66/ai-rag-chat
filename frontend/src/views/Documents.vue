<template>
  <div class="docs-root">
    <!-- ── Page header ── -->
    <div class="page-header">
      <div>
        <h1 class="page-title">文档库</h1>
        <p class="page-sub">{{ total }} 个文档已索引</p>
      </div>
      <div class="header-actions">
        <div class="search-box">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="search-icon">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input v-model="searchQuery" placeholder="搜索文档…" class="search-input" @input="handleSearch" />
        </div>
        <el-select v-model="statusFilter" placeholder="全部状态" clearable @change="loadDocuments" class="status-select" size="default">
          <el-option label="全部" value="" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败"   value="failed" />
        </el-select>
        <el-select v-model="categoryFilter" placeholder="全部分类" @change="handleCategoryFilterChange" class="category-select" size="default">
          <el-option label="全部分类" value="all" />
          <el-option label="未分类" value="uncategorized" />
          <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="String(cat.id)" />
        </el-select>
        <button class="manage-cat-btn" :disabled="isGuest" @click="categoryDialogVisible = true">管理分类</button>
        <el-select v-model="uploadCategoryId" placeholder="上传到分类" class="upload-category-select" size="default" :disabled="isGuest">
          <el-option label="未分类" :value="null" />
          <el-option v-for="cat in categories" :key="cat.id" :label="cat.name" :value="cat.id" />
        </el-select>
        <el-upload
          :action="uploadUrl"
          :headers="uploadHeaders"
          accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,.bmp"
          :show-file-list="false"
          :before-upload="beforeUpload"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :on-progress="onUploadProgress"
          :data="uploadData"
        >
          <button class="upload-btn" :disabled="isGuest">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/>
              <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
            </svg>
            上传文档
          </button>
        </el-upload>
      </div>
    </div>

    <!-- ── Guest notice ── -->
    <div v-if="isGuest" class="guest-notice">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      游客模式下无法上传或管理文档，注册账户后即可解锁全部功能。
    </div>

    <!-- ── Upload progress ── -->
    <div v-if="uploading" class="upload-progress-bar">
      <div class="progress-info">
        <span class="progress-name">{{ uploadFileName }}</span>
        <span class="progress-pct">{{ uploadProgress }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
      </div>
    </div>

    <!-- ── Document grid ── -->
    <div v-if="loading" class="doc-skeleton">
      <div v-for="i in 6" :key="i" class="doc-card doc-card--skeleton">
        <div class="sk-icon"></div>
        <div class="sk-line sk-line--title"></div>
        <div class="sk-line sk-line--meta"></div>
      </div>
    </div>

    <div v-else-if="filteredDocuments.length" class="doc-grid">
      <div v-for="doc in filteredDocuments" :key="doc.id" class="doc-card">
        <div class="doc-card-header">
          <div class="doc-type-icon" :class="typeClass(doc.file_type, doc.content_type)">
            {{ typeLabel(doc.file_type, doc.content_type) }}
          </div>
          <div class="doc-status">
            <span class="status-badge" :class="statusBadgeClass(doc.status)">{{ statusText(doc.status) }}</span>
          </div>
        </div>

        <div class="doc-card-body">
          <div class="doc-name" :title="doc.original_filename">{{ doc.original_filename }}</div>
          <div class="doc-stats">
            <span v-if="doc.word_count">{{ formatNum(doc.word_count) }} 字</span>
            <span>{{ formatSize(doc.file_size) }}</span>
            <span v-if="doc.chunk_count">{{ doc.chunk_count }} 段</span>
            <span class="doc-category-chip">{{ doc.category_name || '未分类' }}</span>
          </div>
          <div class="doc-progress-text" :class="{ 'doc-progress-text--err': doc.status === 'failed' }">
            {{ doc.status === 'failed' && doc.processing_error ? `失败原因：${doc.processing_error}` : doc.progress_text }}
          </div>
        </div>

        <div class="doc-card-footer">
          <span class="doc-date">{{ formatDate(doc.created_at) }}</span>
          <div class="doc-actions">
            <button class="doc-btn doc-btn--view" :disabled="doc.status !== 'completed'" @click="viewDocument(doc)" title="查看详情">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
            <button class="doc-btn doc-btn--refresh" :disabled="doc.status === 'processing'" @click="reprocessDocument(doc)" :title="doc.status === 'failed' ? '重试处理' : '重新处理'">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.5"/>
              </svg>
            </button>
            <button class="doc-btn doc-btn--del" @click="deleteDocument(doc)" title="删除">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                <path d="M10 11v6"/><path d="M14 11v6"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="doc-empty">
      <div class="doc-empty-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14,2 14,8 20,8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
      </div>
      <p class="doc-empty-title">尚无文档</p>
      <p class="doc-empty-sub">{{ isGuest ? '注册账户后即可上传文档' : '上传文档后即可进行 AI 问答' }}</p>
    </div>

    <!-- ── Pagination ── -->
    <div v-if="total > pageSize" class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <!-- ── Detail dialog ── -->
    <el-dialog v-model="detailVisible" title="文档详情" width="520px">
      <div v-if="selectedDoc" class="detail-grid">
        <div class="detail-row"><span class="detail-key">文件名</span><span class="detail-val">{{ selectedDoc.original_filename }}</span></div>
        <div class="detail-row"><span class="detail-key">大小</span><span class="detail-val">{{ formatSize(selectedDoc.file_size) }}</span></div>
        <div class="detail-row"><span class="detail-key">状态</span><span class="detail-val"><span class="status-badge" :class="statusBadgeClass(selectedDoc.status)">{{ statusText(selectedDoc.status) }}</span></span></div>
        <div class="detail-row"><span class="detail-key">分类</span><span class="detail-val">{{ selectedDoc.category_name || '未分类' }}</span></div>
        <div class="detail-row"><span class="detail-key">字数</span><span class="detail-val">{{ selectedDoc.word_count ? formatNum(selectedDoc.word_count) : '—' }}</span></div>
        <div class="detail-row"><span class="detail-key">向量段</span><span class="detail-val">{{ selectedDoc.chunk_count || 0 }}</span></div>
        <div class="detail-row"><span class="detail-key">上传时间</span><span class="detail-val">{{ formatDateTime(selectedDoc.created_at) }}</span></div>
        <div class="detail-row"><span class="detail-key">处理时间</span><span class="detail-val">{{ selectedDoc.processed_at ? formatDateTime(selectedDoc.processed_at) : '—' }}</span></div>
        <div v-if="selectedDoc.processing_error" class="detail-error">{{ selectedDoc.processing_error }}</div>
      </div>
    </el-dialog>

    <el-dialog v-model="categoryDialogVisible" title="分类管理" width="520px">
      <div class="category-create-row">
        <el-input v-model="newCategoryName" placeholder="输入分类名称" maxlength="50" />
        <el-button type="primary" @click="createCategory" :disabled="!newCategoryName.trim()">新建</el-button>
      </div>
      <div v-if="categories.length" class="category-list">
        <div v-for="cat in categories" :key="cat.id" class="category-row">
          <div class="category-name">{{ cat.name }}</div>
          <div class="category-meta">{{ cat.document_count || 0 }} 个文档</div>
          <div class="category-actions">
            <button class="cat-action-btn" @click="renameCategory(cat)" title="重命名">改名</button>
            <button class="cat-action-btn cat-action-btn--del" @click="removeCategory(cat)" title="删除">删除</button>
          </div>
        </div>
      </div>
      <div v-else class="doc-empty-sub">暂无分类，先创建一个吧。</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useUserStore } from '../store'
import { documentsApi } from '../api/documents'
import { ElMessage, ElMessageBox } from 'element-plus'

const store   = useUserStore()
const isGuest = computed(() => store.user?.username === '游客')

const documents   = ref([])
const categories  = ref([])
const loading     = ref(false)
const uploading   = ref(false)
const uploadProgress = ref(0)
const uploadFileName = ref('')
const searchQuery  = ref('')
const statusFilter = ref('')
const categoryFilter = ref('all')
const uploadCategoryId = ref(null)
const currentPage  = ref(1)
const pageSize     = ref(12)
const total        = ref(0)

const detailVisible = ref(false)
const selectedDoc   = ref(null)
const categoryDialogVisible = ref(false)
const newCategoryName = ref('')
const pollingTimers = new Map()

const uploadUrl     = computed(() =>
  import.meta.env.DEV
    ? '/api/documents/upload'
    : `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/documents/upload`
)
const uploadHeaders = computed(() => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}` }))
const uploadData = computed(() => (
  uploadCategoryId.value === null || uploadCategoryId.value === undefined || uploadCategoryId.value === ''
    ? {}
    : { category_id: uploadCategoryId.value }
))

const filteredDocuments = computed(() =>
  documents.value.filter(d => {
    const matchName   = !searchQuery.value || d.original_filename.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchStatus = !statusFilter.value || d.status === statusFilter.value
    return matchName && matchStatus
  })
)

const formatNum  = (n) => n >= 1000 ? (n / 1000).toFixed(1) + 'K' : String(n || 0)
const formatSize = (b) => { if (!b) return '0 B'; const u = ['B','KB','MB','GB']; const i = Math.floor(Math.log(b) / Math.log(1024)); return parseFloat((b / Math.pow(1024,i)).toFixed(1)) + ' ' + u[i] }
const formatDate     = (d) => d ? new Date(d).toLocaleDateString('zh-CN') : ''
const formatDateTime = (d) => d ? new Date(d).toLocaleString('zh-CN')     : ''

const statusText = (s) => ({ uploading: '上传中', processing: '处理中', completed: '完成', failed: '失败' }[s] || s)
const statusBadgeClass = (s) => ({ uploading: 'badge--info', processing: 'badge--warn', completed: 'badge--ok', failed: 'badge--err' }[s] || '')

const typeLabel = (mime, contentType) => {
  if (contentType === 'image' || (mime && mime.includes('image'))) return 'IMG'
  if (!mime) return 'FILE'
  if (mime.includes('pdf')) return 'PDF'
  if (mime.includes('word') || mime.includes('docx')) return 'DOC'
  if (mime.includes('text') || mime.includes('md')) return 'TXT'
  return 'FILE'
}
const typeClass = (mime, contentType) => {
  if (contentType === 'image' || (mime && mime.includes('image'))) return 'type--img'
  if (!mime) return ''
  if (mime.includes('pdf')) return 'type--pdf'
  if (mime.includes('word')) return 'type--doc'
  return 'type--txt'
}

const clearPolling = (docId = null) => {
  if (docId !== null) {
    const timer = pollingTimers.get(docId)
    if (timer) {
      clearInterval(timer)
      pollingTimers.delete(docId)
    }
    return
  }
  pollingTimers.forEach((timer) => clearInterval(timer))
  pollingTimers.clear()
}

const startPolling = (docId) => {
  if (!docId || pollingTimers.has(docId)) return
  const timer = setInterval(async () => {
    try {
      const status = await documentsApi.getDocumentStatus(docId)
      if (status?.status === 'completed' || status?.status === 'failed') {
        clearPolling(docId)
        await loadDocuments()
      }
    } catch {
      clearPolling(docId)
    }
  }, 3000)
  pollingTimers.set(docId, timer)
}

const loadCategories = async () => {
  try {
    const r = await documentsApi.getCategories()
    categories.value = r.categories || []
  } catch {
    categories.value = []
  }
}

const loadDocuments = async () => {
  loading.value = true
  try {
    const params = { page: currentPage.value, page_size: pageSize.value }
    if (categoryFilter.value === 'uncategorized') {
      params.uncategorized = true
    } else if (categoryFilter.value !== 'all') {
      params.category_id = Number(categoryFilter.value)
    }
    const r = await documentsApi.getDocuments(params)
    documents.value = r.documents || []
    total.value = r.total || 0
    const processingIds = new Set(documents.value.filter(d => d.status === 'processing').map(d => d.id))
    pollingTimers.forEach((_, docId) => {
      if (!processingIds.has(docId)) clearPolling(docId)
    })
    processingIds.forEach((docId) => startPolling(docId))
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

const handleSearch = () => { currentPage.value = 1 }
const handleCategoryFilterChange = () => { currentPage.value = 1; loadDocuments() }
const handleSizeChange = (s) => { pageSize.value = s; currentPage.value = 1; loadDocuments() }
const handleCurrentChange = (p) => { currentPage.value = p; loadDocuments() }

const beforeUpload = (file) => {
  const ext = '.' + file.name.split('.').pop().toLowerCase()
  if (!['.pdf','.docx','.txt','.md','.png','.jpg','.jpeg','.webp','.bmp'].includes(ext)) { ElMessage.error('不支持该文件格式'); return false }
  if (file.size > 50 * 1024 * 1024) { ElMessage.error('文件超过 50MB 限制'); return false }
  uploading.value = true; uploadProgress.value = 0; uploadFileName.value = file.name
  return true
}
const onUploadProgress = (e) => { uploadProgress.value = Math.round((e.loaded * 100) / e.total) }
const onUploadSuccess  = (response)  => {
  uploading.value = false
  uploadProgress.value = 0
  if (response?.code !== 200) {
    ElMessage.error(response?.message || '上传失败')
    return
  }
  ElMessage.success('上传成功，正在解析、分块并写入知识库…')
  const docId = response?.data?.id
  if (docId) startPolling(docId)
  loadDocuments()
}
const onUploadError = (err) => {
  uploading.value = false
  uploadProgress.value = 0
  ElMessage.error(err?.response?.data?.message || '上传失败')
}

const viewDocument = (doc) => { selectedDoc.value = doc; detailVisible.value = true }

const createCategory = async () => {
  const name = newCategoryName.value.trim()
  if (!name) return
  try {
    await documentsApi.createCategory(name)
    ElMessage.success('分类创建成功')
    newCategoryName.value = ''
    await loadCategories()
  } catch (e) {
    ElMessage.error(e?.message || '创建分类失败')
  }
}

const renameCategory = async (cat) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的分类名称', '重命名分类', {
      inputValue: cat.name,
      inputPattern: /\S+/,
      inputErrorMessage: '名称不能为空'
    })
    await documentsApi.renameCategory(cat.id, value.trim())
    ElMessage.success('分类重命名成功')
    await loadCategories()
    await loadDocuments()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.message || '重命名失败')
  }
}

const removeCategory = async (cat) => {
  try {
    await ElMessageBox.confirm(`确定删除分类“${cat.name}”？该分类下文档将变为未分类。`, '确认删除', { type: 'warning' })
    await documentsApi.deleteCategory(cat.id)
    ElMessage.success('分类已删除')
    if (categoryFilter.value === String(cat.id)) categoryFilter.value = 'all'
    if (uploadCategoryId.value === cat.id) uploadCategoryId.value = null
    await loadCategories()
    await loadDocuments()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.message || '删除失败')
  }
}

const reprocessDocument = async (doc) => {
  try {
    await ElMessageBox.confirm('确定重新处理？', '确认', { type: 'warning' })
    await documentsApi.reprocessDocument(doc.id)
    ElMessage.success('已开始重新处理，请稍等片刻')
    loadDocuments()
  } catch (e) { if (e !== 'cancel') ElMessage.error('失败') }
}

const deleteDocument = async (doc) => {
  try {
    await ElMessageBox.confirm(`确定删除"${doc.original_filename}"？`, '确认删除', { type: 'warning' })
    await documentsApi.deleteDocument(doc.id)
    ElMessage.success('已删除'); loadDocuments()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

onMounted(async () => {
  await loadCategories()
  await loadDocuments()
})
onBeforeUnmount(() => clearPolling())
</script>

<style scoped>
.docs-root {
  padding: 32px 36px;
  max-width: 1200px;
  margin: 0 auto;
  display: flex; flex-direction: column; gap: 20px;
}

/* ── Header ── */
.page-header {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap;
}
.page-title {
  font-family: var(--font-serif);
  font-size: 26px; font-weight: 700; color: var(--c-text); margin: 0 0 4px;
}
.page-sub { font-size: 13px; color: var(--c-text-2); margin: 0; }
.header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

.search-box {
  display: flex; align-items: center; gap: 8px;
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-md);
  box-shadow: inset 2px 2px 6px rgba(15,23,42,.04), inset -2px -2px 6px rgba(255,255,255,.92);
  padding: 0 12px;
  height: 36px;
  transition: border-color .15s;
}
.search-box:focus-within { border-color: var(--c-border-h); }
.search-icon { color: var(--c-text-3); flex-shrink: 0; }
.search-input {
  background: none; border: none; outline: none;
  color: var(--c-text); font-size: 13px; width: 180px;
}
.search-input::placeholder { color: var(--c-text-3); }

.status-select { width: 120px; }
.category-select { width: 140px; }
.upload-category-select { width: 150px; }
.status-select :deep(.el-input__wrapper),
.category-select :deep(.el-input__wrapper),
.upload-category-select :deep(.el-input__wrapper) { height: 36px !important; }
.manage-cat-btn {
  height: 36px;
  padding: 0 12px;
  border-radius: var(--r-md);
  border: 1px solid #e9eef6;
  background: var(--c-elevated);
  color: var(--c-text-2);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}
.manage-cat-btn:disabled { opacity: .4; cursor: not-allowed; }
.manage-cat-btn:hover:not(:disabled) { background: #f8fbff; color: var(--c-text); }

.upload-btn {
  display: flex; align-items: center; gap: 7px;
  padding: 0 16px; height: 36px;
  background: var(--c-accent);
  border: none; border-radius: var(--r-md);
  color: #ffffff; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: opacity .15s, box-shadow .15s, transform .1s;
  box-shadow: var(--glow-accent-soft);
  position: relative;
  overflow: hidden;
}
.upload-btn::before {
  content: '';
  position: absolute;
  inset: 1px 1px auto 1px;
  height: 42%;
  border-radius: inherit;
  background: linear-gradient(180deg, rgba(255,255,255,.34) 0%, rgba(255,255,255,0) 100%);
  pointer-events: none;
}
.upload-btn:hover:not(:disabled) { opacity: .95; box-shadow: var(--glow-accent); }
.upload-btn:active:not(:disabled) { transform: translateY(1px) scale(.987); box-shadow: var(--glow-press); }
.upload-btn:disabled { opacity: .4; cursor: not-allowed; }

/* ── Notices ── */
.guest-notice {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px;
  background: rgba(239,108,0,.1);
  border: 1px solid rgba(239,108,0,.25);
  border-radius: var(--r-md);
  font-size: 13px; color: #ef6c00;
}

/* ── Upload progress ── */
.upload-progress-bar {
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-md);
  box-shadow: var(--shadow-sm);
  padding: 14px 18px;
}
.progress-info { display: flex; justify-content: space-between; margin-bottom: 8px; }
.progress-name { font-size: 13px; color: var(--c-text-2); }
.progress-pct  { font-size: 12px; color: var(--c-accent); font-weight: 600; }
.progress-track { height: 4px; background: var(--c-border); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: linear-gradient(90deg, var(--c-accent), #7f99e8); border-radius: 2px; transition: width .3s ease; }

/* ── Doc grid ── */
.doc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }

.doc-card {
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-sm);
  padding: 18px;
  display: flex; flex-direction: column; gap: 12px;
  transition: border-color .15s, transform .15s, box-shadow .15s;
}
.doc-card:hover { border-color: var(--c-border-h); transform: translateY(-1px); box-shadow: var(--shadow-md); }

.doc-card-header { display: flex; align-items: center; justify-content: space-between; }
.doc-type-icon {
  padding: 3px 8px;
  border-radius: var(--r-sm);
  font-size: 9px; font-weight: 700; letter-spacing: .1em;
  background: var(--c-elevated); color: var(--c-text-2);
}
.type--pdf { background: rgba(184,88,88,.15); color: #e08888; }
.type--doc { background: rgba(100,150,240,.15); color: #8ab0f0; }
.type--txt { background: rgba(106,158,110,.15); color: #88c88c; }
.type--img { background: rgba(145,111,219,.18); color: #b197fc; }

.status-badge {
  font-size: 10px; font-weight: 600; letter-spacing: .04em;
  padding: 2px 7px; border-radius: var(--r-sm);
}
.badge--ok   { background: rgba(106,158,110,.15); color: #88c88c; }
.badge--err  { background: rgba(184,88,88,.15);   color: #e08888; }
.badge--warn { background: rgba(192,136,80,.15);  color: #dfaa66; }
.badge--info { background: rgba(160,152,137,.12); color: var(--c-text-2); }

.doc-card-body { flex: 1; }
.doc-name {
  font-size: 14px; font-weight: 600; color: var(--c-text);
  margin-bottom: 6px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.doc-stats {
  display: flex; flex-wrap: wrap; gap: 8px;
  font-size: 11px; color: var(--c-text-3);
}
.doc-stats span { display: flex; align-items: center; gap: 2px; }
.doc-progress-text {
  margin-top: 8px;
  color: var(--c-text-3);
  font-size: 11px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.doc-progress-text--err { color: var(--c-err); }
.doc-category-chip {
  padding: 1px 6px;
  border-radius: var(--r-sm);
  background: var(--c-accent-dim);
  border: 1px solid rgba(79,111,220,.2);
  color: var(--c-accent);
}

.doc-card-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding-top: 10px; border-top: 1px solid var(--c-border);
}
.doc-date { font-size: 11px; color: var(--c-text-3); }
.doc-actions { display: flex; gap: 4px; }
.doc-btn {
  width: 26px; height: 26px;
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-sm);
  box-shadow: var(--shadow-sm);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: var(--c-text-2);
  transition: background .12s, color .12s;
}
.doc-btn:hover:not(:disabled) { background: #f8fbff; color: var(--c-text); }
.doc-btn:disabled { opacity: .35; cursor: not-allowed; }
.doc-btn--del:hover:not(:disabled) { background: rgba(184,88,88,.15); color: var(--c-err); border-color: rgba(184,88,88,.3); }

/* Skeleton */
.doc-skeleton { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }
.doc-card--skeleton { min-height: 160px; justify-content: space-between; pointer-events: none; }
.sk-icon { width: 36px; height: 20px; border-radius: var(--r-sm); background: var(--c-elevated); animation: shimmer 1.5s infinite; }
.sk-line { height: 12px; border-radius: 6px; background: var(--c-elevated); animation: shimmer 1.5s infinite; }
.sk-line--title { width: 80%; margin-bottom: 8px; }
.sk-line--meta  { width: 55%; }
@keyframes shimmer { 0%,100%{opacity:.4} 50%{opacity:.8} }

/* Empty */
.doc-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 72px 24px; gap: 10px;
}
.doc-empty-icon { color: var(--c-text-3); }
.doc-empty-title { font-size: 16px; font-weight: 600; color: var(--c-text-2); margin: 0; }
.doc-empty-sub   { font-size: 13px; color: var(--c-text-3); margin: 0; }

/* Pagination */
.pagination-wrap { display: flex; justify-content: flex-end; }

/* Dialog detail */
.detail-grid { display: flex; flex-direction: column; gap: 0; }
.detail-row {
  display: flex; align-items: center; gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid var(--c-border);
}
.detail-row:last-child { border-bottom: none; }
.detail-key { font-size: 12px; color: var(--c-text-3); width: 72px; flex-shrink: 0; font-weight: 500; }
.detail-val { font-size: 13px; color: var(--c-text); word-break: break-all; }
.detail-error {
  margin-top: 12px; padding: 12px;
  background: rgba(184,88,88,.1);
  border: 1px solid rgba(184,88,88,.25);
  border-radius: var(--r-md);
  font-size: 12px; color: #e08888;
  word-break: break-word;
}

.category-create-row {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.category-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.category-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  background: var(--c-elevated);
}
.category-name { color: var(--c-text); font-weight: 600; }
.category-meta { color: var(--c-text-3); font-size: 12px; }
.category-actions { display: flex; gap: 6px; }
.cat-action-btn {
  height: 26px;
  padding: 0 8px;
  border-radius: var(--r-sm);
  border: 1px solid #e9eef6;
  background: var(--c-elevated);
  color: var(--c-text-2);
  font-size: 12px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}
.cat-action-btn:hover { background: #f8fbff; color: var(--c-text); }
.cat-action-btn--del:hover {
  background: rgba(184,88,88,.15);
  color: var(--c-err);
  border-color: rgba(184,88,88,.3);
}
</style>
