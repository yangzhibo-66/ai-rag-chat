<template>
  <el-config-provider :locale="locale">
    <div id="app" :class="isFullLayout ? 'layout-full' : 'layout-app'">

      <template v-if="!isFullLayout">
        <!-- ── Sidebar ── -->
        <aside class="sidebar">
          <div class="sidebar-brand">
            <div class="brand-glyph">知</div>
            <div class="brand-copy">
              <span class="brand-name">AI 知识库</span>
              <span class="brand-tag">RAG · SYSTEM</span>
            </div>
          </div>

          <nav class="sidebar-nav">
            <router-link to="/dashboard" class="nav-link" active-class="nav-link--active">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>
                <rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/>
              </svg>
              <span>仪表板</span>
            </router-link>

            <router-link to="/documents" class="nav-link" active-class="nav-link--active">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
              <span>文档库</span>
            </router-link>

            <router-link to="/chat" class="nav-link" active-class="nav-link--active">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <span>AI 问答</span>
            </router-link>

            <router-link to="/admin" class="nav-link" active-class="nav-link--active" v-if="store.isAdmin">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><polygon points="12,2 22,8.5 22,15.5 12,22 2,15.5 2,8.5"/><line x1="12" y1="22" x2="12" y2="15.5"/><polyline points="22,8.5 12,15.5 2,8.5"/><polyline points="2,15.5 12,8.5 22,15.5"/></svg>
              <span>管理后台</span>
            </router-link>

            <router-link to="/settings" class="nav-link" active-class="nav-link--active">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
              <span>设置</span>
            </router-link>

            <router-link to="/" class="nav-link" exact-active-class="nav-link--active">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 11l9-8 9 8"/>
                <path d="M5 10v10h14V10"/>
              </svg>
              <span>返回导航页</span>
            </router-link>
          </nav>

          <div class="sidebar-divider"></div>

          <div class="sidebar-user">
            <div class="user-avatar">{{ userInitial }}</div>
            <div class="user-meta">
              <div class="user-name">{{ displayName }}</div>
              <div class="user-role">{{ isGuestMode ? '游客模式' : '已认证' }}</div>
            </div>
            <button v-if="isAuthenticated" class="user-action-btn" title="退出登录" @click="handleLogout">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </button>
            <button v-else class="user-action-btn user-action-btn--login" title="前往登录" @click="goToLogin">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
                <polyline points="10 17 15 12 10 7"/>
                <line x1="15" y1="12" x2="3" y2="12"/>
              </svg>
            </button>
          </div>
        </aside>

        <!-- ── Main ── -->
        <main class="app-main">
          <router-view v-slot="{ Component }">
            <transition name="page" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </main>
      </template>

      <template v-else>
        <router-view />
      </template>
    </div>
  </el-config-provider>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from './store'
import { ElMessage } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const router = useRouter()
const route  = useRoute()
const store  = useUserStore()
const locale = zhCn

const isFullLayout   = computed(() => route.meta.layout === 'full')
const isAuthenticated = computed(() => store.isAuthenticated)
const isGuestMode    = computed(() => !store.isAuthenticated && !!store.user)
const user           = computed(() => store.user)
const displayName    = computed(() => user.value?.full_name || user.value?.username || '访客')
const userInitial    = computed(() => (displayName.value || '?').charAt(0).toUpperCase())

const goToLogin = () => router.push('/login')

const handleLogout = async () => {
  await store.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}

onMounted(() => store.checkAuthStatus())
</script>

<!-- ══════════════════════════════════════════
     GLOBAL STYLES — Element Plus dark overrides
     ══════════════════════════════════════════ -->
<style>
/* ── Font ── */
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }

:root {
  /* Palette - White-first Neumorphism Theme */
  --c-bg:         #f5f7fb;
  --c-surface:    #f8faff;
  --c-elevated:   #ffffff;
  --c-border:     #e8edf5;
  --c-border-h:   #dbe5f3;
  --c-accent:     #4f6fdc;
  --c-accent-h:   #3f5ec7;
  --c-accent-dim: rgba(79,111,220,.10);
  --c-text:       #1f2937;
  --c-text-2:     #4b5563;
  --c-text-3:     #94a3b8;
  --c-ok:         #2e7d32;
  --c-err:        #c62828;
  --c-warn:       #ef6c00;

  /* Radius */
  --r-sm:  4px;
  --r-md:  8px;
  --r-lg:  14px;
  --r-xl:  20px;

  /* Shadows */
  --shadow-sm:  6px 6px 14px rgba(15,23,42,.06), -6px -6px 14px rgba(255,255,255,.95);
  --shadow-md: 10px 10px 24px rgba(15,23,42,.08), -10px -10px 24px rgba(255,255,255,.96);
  --shadow-lg: 16px 16px 36px rgba(15,23,42,.10), -16px -16px 36px rgba(255,255,255,.98);
  --glow-accent: 0 0 0 1px rgba(79,111,220,.22), 0 14px 30px rgba(79,111,220,.34), 0 0 34px rgba(127,153,232,.34), inset 0 1px 0 rgba(255,255,255,.36);
  --glow-accent-soft: 0 0 0 1px rgba(79,111,220,.16), 0 8px 20px rgba(79,111,220,.24), 0 0 18px rgba(127,153,232,.24), inset 0 1px 0 rgba(255,255,255,.28);
  --glow-press: inset 0 2px 4px rgba(24,36,74,.28), 0 2px 6px rgba(79,111,220,.18);

  /* Typography */
  --font-sans:   "PingFang SC","Hiragino Sans GB","Microsoft YaHei UI","Microsoft YaHei",sans-serif;
  --font-serif:  "Noto Serif SC","STSong","SimSun",serif;
  --font-mono:   "JetBrains Mono","Fira Code","Cascadia Code",monospace;

  /* El-plus overrides */
  --el-color-primary:          var(--c-accent);
  --el-color-primary-light-3:  rgba(79,111,220,.75);
  --el-color-primary-light-5:  rgba(79,111,220,.55);
  --el-color-primary-light-7:  rgba(79,111,220,.30);
  --el-color-primary-light-8:  rgba(79,111,220,.18);
  --el-color-primary-light-9:  rgba(79,111,220,.08);
  --el-color-primary-dark-2:   #3f5ec7;
  --el-color-success:          var(--c-ok);
  --el-color-danger:           var(--c-err);
  --el-color-warning:          var(--c-warn);
  --el-color-info:             var(--c-text-2);
  --el-bg-color:               var(--c-surface);
  --el-bg-color-page:          var(--c-bg);
  --el-bg-color-overlay:       var(--c-elevated);
  --el-text-color-primary:     var(--c-text);
  --el-text-color-regular:     #303f9f;
  --el-text-color-secondary:   var(--c-text-2);
  --el-text-color-placeholder: var(--c-text-3);
  --el-text-color-disabled:    #9fa8da;
  --el-border-color:           var(--c-border);
  --el-border-color-light:     #c1e2fc;
  --el-border-color-lighter:   #e3f2fd;
  --el-border-color-extra-light:#f0f8ff;
  --el-fill-color:             var(--c-elevated);
  --el-fill-color-light:       #f3f9ff;
  --el-fill-color-lighter:     var(--c-surface);
  --el-fill-color-blank:       var(--c-surface);
  --el-fill-color-dark:        var(--c-border);
  --el-fill-color-darker:      var(--c-border-h);
  --el-mask-color:             rgba(2,119,189,.35);
  --el-border-radius-base:     var(--r-md);
  --el-border-radius-small:    var(--r-sm);
  --el-font-size-base:         14px;
  --el-font-family:            var(--font-sans);
  --el-box-shadow-base:        var(--shadow-md);
}

html, body {
  margin: 0; padding: 0;
  background: var(--c-bg);
  color: var(--c-text);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ── El-Plus global fixes ── */
.el-card {
  background: var(--c-elevated) !important;
  border: 1px solid #eef2f8 !important;
  border-radius: var(--r-lg) !important;
  box-shadow: var(--shadow-sm) !important;
  color: var(--c-text) !important;
}
.el-card__header {
  border-bottom: 1px solid var(--c-border) !important;
  padding: 16px 20px !important;
}
.el-card__body { padding: 20px !important; }

.el-input__wrapper {
  background: var(--c-elevated) !important;
  border-color: #e9eef6 !important;
  box-shadow: inset 2px 2px 5px rgba(15,23,42,.04), inset -2px -2px 5px rgba(255,255,255,.92) !important;
}
.el-input__wrapper:hover { border-color: var(--c-border-h) !important; }
.el-input__wrapper.is-focus { border-color: var(--c-accent) !important; box-shadow: 0 0 0 2px rgba(79,111,220,.16) !important; }
.el-input__inner { color: var(--c-text) !important; background: transparent !important; }
.el-textarea__inner {
  background: var(--c-elevated) !important;
  border-color: #e9eef6 !important;
  color: var(--c-text) !important;
  box-shadow: inset 2px 2px 5px rgba(15,23,42,.04), inset -2px -2px 5px rgba(255,255,255,.92) !important;
}
.el-textarea__inner:focus { border-color: var(--c-accent) !important; box-shadow: 0 0 0 2px rgba(79,111,220,.16) !important; }
.el-textarea__inner::placeholder { color: var(--c-text-3) !important; }

.el-button { border-radius: var(--r-md) !important; font-weight: 500 !important; transition: box-shadow .16s ease, transform .1s ease !important; }
.el-button:active { transform: translateY(1px) scale(.985) !important; }
.el-button--primary {
  background: var(--c-accent) !important;
  border-color: var(--c-accent) !important;
  color: #ffffff !important;
  box-shadow: var(--glow-accent-soft) !important;
}
.el-button--primary:hover, .el-button--primary:focus {
  background: var(--c-accent-h) !important;
  border-color: var(--c-accent-h) !important;
  box-shadow: var(--glow-accent) !important;
}
.el-button--primary:active { box-shadow: var(--glow-press) !important; }
.el-button--default {
  background: var(--c-elevated) !important;
  border-color: #e9eef6 !important;
  color: var(--c-text-2) !important;
  box-shadow: var(--shadow-sm) !important;
}
.el-button--default:hover {
  background: #f7faff !important;
  border-color: var(--c-border-h) !important;
  color: var(--c-text) !important;
  box-shadow: 0 0 0 1px rgba(79,111,220,.08), 0 8px 16px rgba(79,111,220,.14) !important;
}
.el-button--danger { background: var(--c-err) !important; border-color: var(--c-err) !important; color: #fff !important; box-shadow: 0 0 0 1px rgba(198,40,40,.18), 0 8px 18px rgba(198,40,40,.24) !important; }
.el-button.is-disabled { opacity: .4 !important; }

.el-table {
  background: transparent !important;
  color: var(--c-text) !important;
  --el-table-border-color: var(--c-border);
  --el-table-bg-color: var(--c-surface);
  --el-table-tr-bg-color: var(--c-surface);
  --el-table-header-bg-color: var(--c-elevated);
  --el-table-row-hover-bg-color: var(--c-elevated);
  --el-table-current-row-bg-color: var(--c-accent-dim);
  --el-table-header-text-color: var(--c-text-2);
  --el-table-text-color: var(--c-text);
}
.el-table th { font-weight: 500 !important; letter-spacing: .02em; }

.el-tag {
  border-radius: var(--r-sm) !important;
  font-size: 11px !important;
  font-weight: 500 !important;
  letter-spacing: .03em !important;
}
.el-tag--success { background: rgba(106,158,110,.15) !important; border-color: rgba(106,158,110,.3) !important; color: #88c88c !important; }
.el-tag--danger  { background: rgba(184,88,88,.15)  !important; border-color: rgba(184,88,88,.3)  !important; color: #e08888 !important; }
.el-tag--warning { background: rgba(192,136,80,.15) !important; border-color: rgba(192,136,80,.3) !important; color: #dfaa66 !important; }
.el-tag--info    { background: rgba(160,152,137,.12) !important; border-color: rgba(160,152,137,.25) !important; color: var(--c-text-2) !important; }
.el-tag--primary { background: var(--c-accent-dim) !important; border-color: rgba(2,119,189,.3) !important; color: var(--c-accent) !important; }

.el-dialog {
  background: var(--c-surface) !important;
  border: 1px solid var(--c-border) !important;
  border-radius: var(--r-xl) !important;
  box-shadow: var(--shadow-lg) !important;
}
.el-dialog__title { color: var(--c-text) !important; font-weight: 600 !important; }
.el-dialog__headerbtn .el-dialog__close { color: var(--c-text-2) !important; }

.el-select .el-input__wrapper { background: var(--c-elevated) !important; }
.el-select-dropdown { background: var(--c-elevated) !important; border-color: #e9eef6 !important; box-shadow: var(--shadow-md) !important; }
.el-select-dropdown__item { color: var(--c-text-2) !important; }
.el-select-dropdown__item:hover, .el-select-dropdown__item.is-hovering { background: var(--c-elevated) !important; color: var(--c-text) !important; }
.el-select-dropdown__item.is-selected { color: var(--c-accent) !important; background: var(--c-accent-dim) !important; }

.el-dropdown-menu {
  background: var(--c-surface) !important;
  border: 1px solid var(--c-border) !important;
  border-radius: var(--r-md) !important;
  box-shadow: var(--shadow-md) !important;
}
.el-dropdown-menu__item { color: var(--c-text-2) !important; }
.el-dropdown-menu__item:hover { background: var(--c-elevated) !important; color: var(--c-text) !important; }

.el-pagination {
  --el-pagination-bg-color: var(--c-elevated);
  --el-pagination-text-color: var(--c-text-2);
  --el-pagination-border-radius: var(--r-sm);
  --el-pagination-button-color: var(--c-text-2);
  --el-pagination-button-bg-color: var(--c-elevated);
  --el-pagination-button-disabled-color: var(--c-text-3);
  --el-pagination-button-disabled-bg-color: var(--c-surface);
  --el-pagination-hover-color: var(--c-accent);
}

.el-progress-bar__outer { background: var(--c-border) !important; }
.el-progress-bar__inner { background: linear-gradient(90deg, var(--c-accent), #7f99e8) !important; }

.el-empty__description { color: var(--c-text-3) !important; }

.el-form-item__label { color: var(--c-text-2) !important; font-size: 13px !important; }
.el-form-item__error { color: var(--c-err) !important; font-size: 11px !important; }

.el-alert {
  border-radius: var(--r-md) !important;
}
.el-alert--warning {
  background: rgba(192,136,80,.12) !important;
  border: 1px solid rgba(192,136,80,.25) !important;
  color: #dfaa66 !important;
}
.el-alert--error {
  background: rgba(184,88,88,.12) !important;
  border: 1px solid rgba(184,88,88,.25) !important;
  color: #e08888 !important;
}

.el-message {
  background: var(--c-surface) !important;
  border-color: var(--c-border) !important;
  border-radius: var(--r-md) !important;
  box-shadow: var(--shadow-md) !important;
}
.el-message--success .el-message__content { color: #88c88c !important; }
.el-message--error   .el-message__content { color: #e08888 !important; }
.el-message--warning .el-message__content { color: #dfaa66 !important; }
.el-message--info    .el-message__content { color: var(--c-text-2) !important; }
</style>

<!-- ── Component Scoped ── -->
<style scoped>
#app { min-height: 100vh; }

/* ── App layout ── */
.layout-app {
  display: grid;
  grid-template-columns: 216px 1fr;
  height: 100vh;
  overflow: hidden;
}
.layout-full { height: 100vh; }

/* ── Sidebar ── */
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--c-elevated);
  border-right: 1px solid #eef2f8;
  box-shadow: var(--shadow-sm);
  padding: 0;
  overflow: hidden;
  position: relative;
}
.sidebar::after {
  content: '';
  position: absolute;
  top: 0; right: 0;
  width: 1px; height: 100%;
  background: linear-gradient(to bottom, transparent, rgba(79,111,220,.12) 40%, rgba(79,111,220,.12) 60%, transparent);
  pointer-events: none;
}

/* Brand */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px 20px;
  border-bottom: 1px solid var(--c-border);
}
.brand-glyph {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, var(--c-accent), #0288d1);
  border-radius: var(--r-md);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 700;
  color: #ffffff;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(2,119,189,.3);
}
.brand-copy { display: flex; flex-direction: column; gap: 1px; overflow: hidden; }
.brand-name {
  font-size: 14px; font-weight: 600; color: var(--c-text);
  white-space: nowrap; letter-spacing: .02em;
}
.brand-tag {
  font-size: 9px; font-weight: 500; color: var(--c-text-3);
  letter-spacing: .12em; text-transform: uppercase;
}

/* Nav */
.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 16px 12px;
  overflow-y: auto;
}
.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--r-md);
  text-decoration: none;
  color: var(--c-text-2);
  font-size: 13px;
  font-weight: 500;
  transition: background .15s, color .15s;
  position: relative;
}
.nav-link:hover {
  background: #f8fbff;
  color: var(--c-text);
  box-shadow: var(--shadow-sm);
}
.nav-link--active {
  background: var(--c-accent-dim);
  color: var(--c-accent);
  box-shadow: inset 2px 2px 6px rgba(79,111,220,.10), inset -2px -2px 6px rgba(255,255,255,.95);
}
.nav-link--active::before {
  content: '';
  position: absolute;
  left: 0; top: 50%;
  transform: translateY(-50%);
  width: 3px; height: 18px;
  background: var(--c-accent);
  border-radius: 0 3px 3px 0;
}

/* Divider */
.sidebar-divider {
  height: 1px;
  background: var(--c-border);
  margin: 0 12px;
  flex-shrink: 0;
}

/* User */
.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 16px 20px;
  flex-shrink: 0;
}
.user-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, var(--c-accent), #0288d1);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: #ffffff;
  flex-shrink: 0;
}
.user-meta { flex: 1; min-width: 0; }
.user-name {
  font-size: 12px; font-weight: 600; color: var(--c-text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.user-role { font-size: 10px; color: var(--c-text-3); letter-spacing: .03em; margin-top: 1px; }
.user-action-btn {
  width: 28px; height: 28px;
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-sm);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: var(--c-text-2);
  box-shadow: var(--shadow-sm);
  flex-shrink: 0; transition: background .15s, color .15s;
}
.user-action-btn:hover { background: #f8fbff; color: var(--c-text); }
.user-action-btn--login { color: var(--c-accent); border-color: rgba(79,111,220,.28); }
.user-action-btn--login:hover { background: var(--c-accent-dim); }

/* ── Main ── */
.app-main {
  overflow-y: auto;
  height: 100vh;
  background: linear-gradient(180deg, #f7f9fd 0%, #f5f7fb 100%);
}

/* ── Transitions ── */
.page-enter-active,
.page-leave-active { transition: opacity .18s ease, transform .18s ease; }
.page-enter-from   { opacity: 0; transform: translateY(6px); }
.page-leave-to     { opacity: 0; transform: translateY(-4px); }
</style>
