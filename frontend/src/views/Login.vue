<template>
  <div class="login-root">
    <!-- Background grid -->
    <div class="bg-grid"></div>
    <div class="bg-glow"></div>

    <div class="login-wrap">
      <!-- ── Left Panel ── -->
      <div class="panel-left">
        <div class="left-content">
          <div class="left-glyph">知</div>
          <h1 class="left-title">AI 知识库</h1>
          <p class="left-sub">基于 RAG 技术的智能文档问答系统<br>上传文档，即刻开始对话</p>

          <ul class="feature-list">
            <li v-for="f in features" :key="f.text">
              <span class="feat-dot"></span>
              <span>{{ f.text }}</span>
            </li>
          </ul>
        </div>

        <div class="left-deco">
          <div class="deco-ring deco-ring--1"></div>
          <div class="deco-ring deco-ring--2"></div>
          <div class="deco-ring deco-ring--3"></div>
        </div>
      </div>

      <!-- ── Right Panel ── -->
      <div class="panel-right">
        <!-- Tab switcher -->
        <div class="auth-tabs">
          <button :class="['tab-btn', { active: activeTab === 'login' }]" @click="activeTab = 'login'">登 录</button>
          <button :class="['tab-btn', { active: activeTab === 'register' }]" @click="activeTab = 'register'">注 册</button>
          <div class="tab-indicator" :style="{ transform: activeTab === 'register' ? 'translateX(100%)' : 'translateX(0)' }"></div>
        </div>

        <!-- Login Form -->
        <transition name="tab-slide" mode="out-in">
          <div v-if="activeTab === 'login'" key="login" class="form-block">
            <p class="form-greeting">欢迎回来</p>

            <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" class="auth-form" @keydown.enter="handleLogin" autocomplete="off">
              <el-form-item prop="username">
                <label class="field-label">用户名</label>
                <el-input
                  v-model="loginForm.username"
                  placeholder="请输入用户名"
                  size="large"
                  class="auth-input"
                  autocomplete="new-username"
                  :input-props="{ autocomplete: 'new-username' }"
                />
              </el-form-item>
              <el-form-item prop="password">
                <label class="field-label">密码</label>
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  size="large"
                  show-password
                  class="auth-input"
                  autocomplete="new-password"
                  :input-props="{ autocomplete: 'new-password' }"
                />
              </el-form-item>

              <!-- 角色切换 -->
              <div class="role-toggle-row">
                <button
                  :class="['role-btn', { 'role-btn--admin': isAdminLogin }]"
                  @click="isAdminLogin = !isAdminLogin"
                  type="button"
                >
                  <span class="role-indicator"></span>
                  <span class="role-label">{{ isAdminLogin ? '管理员登录' : '普通用户登录' }}</span>
                </button>
              </div>
            </el-form>

            <button class="submit-btn" :class="{ loading: isLoading }" :disabled="isLoading" @click="handleLogin">
              <span v-if="!isLoading">登 录</span>
              <span v-else class="btn-loading">
                <svg width="16" height="16" viewBox="0 0 24 24" class="spin"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="60" stroke-dashoffset="45"/></svg>
                登录中...
              </span>
            </button>

            <button class="guest-btn" @click="enterAsGuest">以游客身份继续 →</button>
          </div>

          <div v-else key="register" class="form-block">
            <p class="form-greeting">创建账户</p>

            <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" class="auth-form" autocomplete="off">
              <el-form-item prop="username">
                <label class="field-label">用户名</label>
                <el-input
                  v-model="registerForm.username"
                  placeholder="3–50 个字符"
                  size="large"
                  class="auth-input"
                  autocomplete="new-username"
                  :input-props="{ autocomplete: 'new-username' }"
                />
              </el-form-item>
              <el-form-item prop="email">
                <label class="field-label">邮箱</label>
                <el-input
                  v-model="registerForm.email"
                  placeholder="your@email.com"
                  size="large"
                  class="auth-input"
                  autocomplete="new-email"
                  :input-props="{ autocomplete: 'new-email' }"
                />
              </el-form-item>
              <el-form-item prop="full_name">
                <label class="field-label">姓名 <span class="optional">（可选）</span></label>
                <el-input
                  v-model="registerForm.full_name"
                  placeholder="您的真实姓名"
                  size="large"
                  class="auth-input"
                  autocomplete="name"
                  :input-props="{ autocomplete: 'name' }"
                />
              </el-form-item>
              <div class="form-row">
                <el-form-item prop="password">
                  <label class="field-label">密码</label>
                  <el-input
                    v-model="registerForm.password"
                    type="password"
                    placeholder="至少 8 个字符"
                    size="large"
                    show-password
                    class="auth-input"
                    autocomplete="new-password"
                    :input-props="{ autocomplete: 'new-password' }"
                  />
                </el-form-item>
                <el-form-item prop="confirmPassword">
                  <label class="field-label">确认密码</label>
                  <el-input
                    v-model="registerForm.confirmPassword"
                    type="password"
                    placeholder="再次输入密码"
                    size="large"
                    show-password
                    class="auth-input"
                    autocomplete="new-password"
                    :input-props="{ autocomplete: 'new-password' }"
                  />
                </el-form-item>
              </div>
            </el-form>

            <button class="submit-btn" :class="{ loading: isRegistering }" :disabled="isRegistering" @click="handleRegister">
              <span v-if="!isRegistering">注 册</span>
              <span v-else class="btn-loading">
                <svg width="16" height="16" viewBox="0 0 24 24" class="spin"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="60" stroke-dashoffset="45"/></svg>
                注册中...
              </span>
            </button>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../store'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route  = useRoute()
const store  = useUserStore()

const activeTab = ref('login')
const isAdminLogin = ref(false)

// 页面加载时清空所有表单
const clearAllForms = () => {
  // 清空登录表单
  loginForm.username = ''
  loginForm.password = ''
  loginFormRef.value?.resetFields()

  // 清空注册表单
  registerForm.username = ''
  registerForm.email = ''
  registerForm.full_name = ''
  registerForm.password = ''
  registerForm.confirmPassword = ''
  registerFormRef.value?.resetFields()
}

// 组件挂载时清空表单
import { onMounted } from 'vue'

onMounted(() => {
  clearAllForms()
})

// 监听标签切换，自动清空表单以保护隐私
watch(activeTab, (newTab, oldTab) => {
  if (newTab === 'login' && oldTab === 'register') {
    // 切换到登录，清空注册表单
    registerForm.username = ''
    registerForm.email = ''
    registerForm.full_name = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
    registerFormRef.value?.resetFields()
  } else if (newTab === 'register' && oldTab === 'login') {
    // 切换到注册，清空登录表单
    loginForm.username = ''
    loginForm.password = ''
    loginFormRef.value?.resetFields()
  }
})

const features = [
  { text: '支持 PDF、Word、Markdown 等多种格式' },
  { text: '基于向量检索的精准语义匹配' },
  { text: 'Claude AI 驱动，流式实时输出' },
  { text: '多会话隔离，历史记录永久保存' },
]

/* ── Login ── */
const loginFormRef = ref(null)
const loginForm    = reactive({ username: '', password: '' })
const isLoading    = ref(false)
const loginRules   = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, message: '至少 3 个字符', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码',   trigger: 'blur' }, { min: 6, message: '至少 6 个字符', trigger: 'blur' }],
}

const handleLogin = async () => {
  try {
    await loginFormRef.value?.validate()
    isLoading.value = true

    // 提取登录数据后立即清空密码
    const { username, password } = loginForm
    loginForm.password = ''

    const result = await store.login(username, password)
    if (result.success) {
      ElMessage.success('登录成功')
      const redirect = route.query.redirect || (isAdminLogin.value ? '/admin' : '/dashboard')
      router.push(redirect)
    } else {
      ElMessage.error(result.error || '登录失败，请检查用户名和密码')
      loginForm.password = '' // 登录失败也清空密码
    }
  } catch {
    // 表单验证失败时清空密码
    loginForm.password = ''
    ElMessage.error('请检查输入信息')
  } finally {
    isLoading.value = false
  }
}

/* ── Register ── */
const registerFormRef = ref(null)
const isRegistering   = ref(false)
const registerForm    = reactive({ username: '', email: '', full_name: '', password: '', confirmPassword: '' })
const registerRules   = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '3–50 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '至少 8 个字符', trigger: 'blur' },
  ],
  confirmPassword: [{
    validator: (_, v, cb) => v !== registerForm.password ? cb(new Error('两次密码不一致')) : cb(),
    trigger: 'blur',
  }],
}

const handleRegister = async () => {
  try {
    await registerFormRef.value?.validate()
    isRegistering.value = true
    // 验证成功后立即提取数据并清空密码字段
    const formData = {
      username: registerForm.username,
      email: registerForm.email,
      full_name: registerForm.full_name,
      password: registerForm.password,
    }

    // 立即清空密码字段，提高安全性
    registerForm.password = ''
    registerForm.confirmPassword = ''

    const result = await store.register(formData)
    if (result.success) {
      ElMessage.success('注册成功，请登录')
      activeTab.value = 'login'
      // 使用nextTick确保切换后再清空其他字段
      await nextTick()
      registerForm.username = ''
      registerForm.email = ''
      registerForm.full_name = ''
      registerFormRef.value?.resetFields()
    } else {
      ElMessage.error(result.error || '注册失败')
    }
  } catch {
    // 表单验证失败时也清空密码
    registerForm.password = ''
    registerForm.confirmPassword = ''
    ElMessage.error('请检查输入信息')
  }
  finally { isRegistering.value = false }
}

/* ── Guest ── */
const enterAsGuest = () => {
  store.setGuestMode()
  router.push('/chat')
}
</script>

<style scoped>
/* ── Root ── */
.login-root {
  min-height: 100vh;
  background: var(--c-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

/* Background decorations */
.bg-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(2,119,189,.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(2,119,189,.03) 1px, transparent 1px);
  background-size: 48px 48px;
  pointer-events: none;
}
.bg-glow {
  position: absolute;
  top: -20%; left: -10%;
  width: 60%; height: 60%;
  background: radial-gradient(circle, rgba(2,119,189,.06) 0%, transparent 70%);
  pointer-events: none;
}

/* ── Wrap ── */
.login-wrap {
  display: flex;
  width: 900px;
  max-width: calc(100vw - 48px);
  min-height: 560px;
  border-radius: var(--r-xl);
  overflow: hidden;
  border: 1px solid var(--c-border);
  box-shadow: var(--shadow-lg);
  background: var(--c-surface);
  position: relative;
  z-index: 1;
  animation: fadeUp .4s ease both;
}
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Left panel ── */
.panel-left {
  flex: 0 0 360px;
  background: linear-gradient(160deg, #e3f2fd 0%, #bbdefb 100%);
  border-right: 1px solid var(--c-border);
  padding: 48px 40px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}
.left-content { position: relative; z-index: 2; }
.left-glyph {
  width: 52px; height: 52px;
  background: linear-gradient(135deg, var(--c-accent), #0288d1);
  border-radius: var(--r-lg);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-serif);
  font-size: 26px; font-weight: 700;
  color: #ffffff;
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(2,119,189,.4);
}
.left-title {
  font-family: var(--font-serif);
  font-size: 28px; font-weight: 700;
  color: var(--c-text);
  margin: 0 0 12px;
  line-height: 1.2;
}
.left-sub {
  font-size: 14px; line-height: 1.7;
  color: var(--c-text-2);
  margin: 0 0 32px;
}
.feature-list {
  list-style: none;
  margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 12px;
}
.feature-list li {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; color: var(--c-text-2);
}
.feat-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--c-accent);
  flex-shrink: 0;
  box-shadow: 0 0 6px rgba(2,119,189,.5);
}

/* Decorative rings */
.left-deco { position: absolute; bottom: -60px; right: -60px; }
.deco-ring {
  position: absolute; border-radius: 50%;
  border: 1px solid rgba(2,119,189,.08);
}
.deco-ring--1 { width: 200px; height: 200px; bottom: 0; right: 0; }
.deco-ring--2 { width: 320px; height: 320px; bottom: -60px; right: -60px; }
.deco-ring--3 { width: 440px; height: 440px; bottom: -120px; right: -120px; }

/* ── Right panel ── */
.panel-right {
  flex: 1;
  padding: 48px 44px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

/* Tabs */
.auth-tabs {
  display: flex;
  position: relative;
  background: var(--c-elevated);
  border-radius: var(--r-md);
  padding: 3px;
  margin-bottom: 32px;
  width: fit-content;
}
.tab-btn {
  position: relative; z-index: 2;
  padding: 8px 28px;
  background: none; border: none;
  cursor: pointer;
  font-size: 13px; font-weight: 600;
  color: var(--c-text-2);
  letter-spacing: .06em;
  border-radius: calc(var(--r-md) - 2px);
  transition: color .2s;
}
.tab-btn.active { color: var(--c-text); }
.tab-indicator {
  position: absolute;
  top: 3px; left: 3px;
  width: calc(50% - 3px);
  height: calc(100% - 6px);
  background: var(--c-surface);
  border-radius: calc(var(--r-md) - 2px);
  box-shadow: var(--shadow-sm);
  transition: transform .22s cubic-bezier(.4,0,.2,1);
  pointer-events: none;
}

/* Form greeting */
.form-greeting {
  font-family: var(--font-serif);
  font-size: 22px; font-weight: 600;
  color: var(--c-text);
  margin: 0 0 28px;
}

/* Form */
.auth-form { display: flex; flex-direction: column; gap: 4px; margin-bottom: 24px; }
.auth-form :deep(.el-form-item) { margin-bottom: 16px; }
.auth-form :deep(.el-form-item__content) { display: flex; flex-direction: column; line-height: normal; }
.field-label {
  display: block;
  font-size: 11px; font-weight: 600;
  color: var(--c-text-3);
  letter-spacing: .08em; text-transform: uppercase;
  margin-bottom: 6px;
}
.optional { font-weight: 400; text-transform: none; letter-spacing: 0; }
.auth-input :deep(.el-input__wrapper) {
  padding: 0 12px;
  height: 42px;
  border-radius: var(--r-md) !important;
}

.form-row {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
}

/* Submit button */
.submit-btn {
  width: 100%; height: 46px;
  background: linear-gradient(135deg, var(--c-accent), #0288d1);
  border: none; border-radius: var(--r-md);
  color: #ffffff;
  font-size: 14px; font-weight: 700;
  letter-spacing: .08em;
  cursor: pointer;
  transition: opacity .15s, transform .1s;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 16px rgba(2,119,189,.3);
}
.submit-btn:hover:not(:disabled) { opacity: .9; transform: translateY(-1px); }
.submit-btn:active:not(:disabled) { transform: translateY(0); }
.submit-btn:disabled { opacity: .5; cursor: not-allowed; }
.btn-loading { display: flex; align-items: center; gap: 8px; }

/* Guest button */
.guest-btn {
  width: 100%; height: 38px;
  background: none;
  border: 1px dashed var(--c-border-h);
  border-radius: var(--r-md);
  color: var(--c-text-2);
  font-size: 13px; cursor: pointer;
  transition: background .15s, color .15s;
  margin-top: 12px;
}
.guest-btn:hover { background: var(--c-elevated); color: var(--c-text); }

/* Spin animation */
.spin { animation: spin .8s linear infinite; }
@keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

/* Tab transition */
.tab-slide-enter-active,
.tab-slide-leave-active { transition: opacity .18s ease, transform .18s ease; }
.tab-slide-enter-from   { opacity: 0; transform: translateX(12px); }
.tab-slide-leave-to     { opacity: 0; transform: translateX(-12px); }

/* Role toggle */
.role-toggle-row {
  display: flex; justify-content: center;
  margin-bottom: 18px;
}
.role-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 18px;
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: 20px;
  cursor: pointer;
  transition: all .2s;
  font-size: 12px; font-weight: 600;
  color: var(--c-text-2);
}
.role-btn:hover { border-color: var(--c-border-h); color: var(--c-text); }
.role-btn--admin {
  background: linear-gradient(135deg, rgba(79,111,220,.08), rgba(2,136,209,.08));
  border-color: rgba(79,111,220,.3);
  color: var(--c-accent);
  box-shadow: 0 0 12px rgba(79,111,220,.15);
}
.role-indicator {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--c-text-3);
  transition: all .3s;
}
.role-btn--admin .role-indicator {
  background: var(--c-accent);
  box-shadow: 0 0 6px rgba(79,111,220,.6);
}
.role-label { letter-spacing: .04em; }

</style>
