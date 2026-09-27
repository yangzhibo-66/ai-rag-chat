<template>
  <div class="settings-page">
    <div class="page-header">
      <h1 class="page-title">设置</h1>
      <p class="page-desc">自定义 AI 大模型配置，保存后立即生效</p>
    </div>

    <div class="settings-card">
      <div class="card-header">
        <div class="card-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
          </svg>
        </div>
        <span>AI 模型配置</span>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="settings-form"
        @submit.prevent
      >
        <el-form-item label="模型名称" prop="model">
          <el-input
            v-model="form.model"
            placeholder="例如：claude-opus-4-7 / gpt-4o / deepseek-chat"
            clearable
          />
          <div class="field-hint">填写所用 API 提供商的模型 ID</div>
        </el-form-item>

        <el-form-item label="API Base URL" prop="base_url">
          <el-input
            v-model="form.base_url"
            placeholder="留空则使用默认 Anthropic 地址"
            clearable
          />
          <div class="field-hint">兼容 OpenAI 格式的第三方接口地址，例如 https://api.example.com</div>
        </el-form-item>

        <el-form-item label="API Key" prop="api_key">
          <el-input
            v-model="form.api_key"
            type="password"
            :placeholder="hasStoredKey ? '已保存（留空保持不变）' : '请输入 API Key'"
            show-password
            clearable
          />
          <div class="field-hint">
            <span v-if="hasStoredKey" class="key-saved">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              已保存密钥，留空则不更改
            </span>
            <span v-else>Key 将加密存储于服务器，仅用于 AI 请求</span>
          </div>
        </el-form-item>

        <div class="form-actions">
          <el-button
            type="primary"
            :loading="saving"
            @click="handleSave"
          >
            保存配置
          </el-button>
          <el-button @click="handleReset" :disabled="saving">重置为默认</el-button>
        </div>
      </el-form>
    </div>

    <div class="settings-card">
      <div class="card-header">
        <div class="card-icon card-icon--lock">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
        </div>
        <span>修改登录密码</span>
      </div>

      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-position="top"
        class="settings-form"
        @submit.prevent
      >
        <el-form-item label="当前密码" prop="old_password">
          <el-input
            v-model="passwordForm.old_password"
            type="password"
            placeholder="请输入当前登录密码"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            placeholder="请输入至少 6 位的新密码"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input
            v-model="passwordForm.confirm_password"
            type="password"
            placeholder="请再次输入新密码"
            show-password
            clearable
          />
        </el-form-item>

        <div class="form-actions">
          <el-button
            type="primary"
            :loading="changingPassword"
            @click="handleChangePassword"
          >
            修改密码
          </el-button>
          <el-button @click="resetPasswordForm" :disabled="changingPassword">清空</el-button>
        </div>
      </el-form>
    </div>

    <div class="settings-card info-card">
      <div class="card-header">
        <div class="card-icon card-icon--info">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <span>使用说明</span>
      </div>
      <ul class="info-list">
        <li>模型名称和 API Key 为必填项，Base URL 可留空（默认使用 Anthropic 官方地址）</li>
        <li>若使用第三方 OpenAI 兼容接口，请填写对应的 Base URL 和模型名称</li>
        <li>配置仅对当前账号生效，不影响其他用户</li>
        <li>API Key 保存在服务器端，不会在客户端明文暴露</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '../api/auth'

const formRef = ref(null)
const passwordFormRef = ref(null)
const saving = ref(false)
const changingPassword = ref(false)
const hasStoredKey = ref(false)
const loading = ref(true)

// 使用 reactive 而不是 ref，并设置默认值
const form = reactive({
  model: 'claude-opus-4-7',  // 设置默认值
  base_url: '',
  api_key: '',
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const rules = {
  model: [{ required: true, message: '请填写模型名称', trigger: 'blur' }],
}

const validateConfirmPassword = (rule, value, callback) => {
  if (!value) {
    callback(new Error('请再次输入新密码'))
    return
  }
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的新密码不一致'))
    return
  }
  callback()
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [{ validator: validateConfirmPassword, trigger: 'blur' }],
}

async function loadConfig() {
  loading.value = true
  try {
    const data = await authApi.getAIConfig()
    console.log('Loaded config:', data)  // 调试日志
    
    // 更新表单数据，如果后端返回空值则保持默认
    form.model = data.model || 'claude-opus-4-7'
    form.base_url = data.base_url || ''
    hasStoredKey.value = !!data.has_api_key
    
    // 清除 API Key 字段（安全原因，不显示已保存的 key）
    form.api_key = ''
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error('加载配置失败，使用默认配置')
    // 出错时也保持默认值
    form.model = 'claude-opus-4-7'
    form.base_url = ''
    form.api_key = ''
    hasStoredKey.value = false
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  // 确保 formRef 存在
  if (!formRef.value) {
    console.error('Form reference not found')
    return
  }
  
  try {
    // 验证表单
    await formRef.value.validate()
  } catch (error) {
    console.error('表单验证失败:', error)
    return
  }
  
  saving.value = true
  try {
    const payload = {
      model: form.model.trim(),
      base_url: form.base_url.trim() || null,
      api_key: form.api_key.trim() || null,
    }
    
    console.log('Saving config:', { ...payload, api_key: payload.api_key ? '***' : null })
    
    const data = await authApi.updateAIConfig(payload)
    hasStoredKey.value = !!data.has_api_key
    form.api_key = ''  // 清空 API Key 输入框
    ElMessage.success('配置已保存')
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function handleReset() {
  form.model = 'claude-opus-4-7'
  form.base_url = ''
  form.api_key = ''
  ElMessage.info('已重置为默认配置，请点击保存生效')
}

async function handleChangePassword() {
  if (!passwordFormRef.value) return

  try {
    await passwordFormRef.value.validate()
  } catch {
    return
  }

  if (passwordForm.old_password === passwordForm.new_password) {
    ElMessage.warning('新密码不能与当前密码相同')
    return
  }

  changingPassword.value = true
  try {
    const result = await authApi.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    if (!result.success) {
      ElMessage.error(result.error || '密码修改失败')
      return
    }
    resetPasswordForm()
    ElMessage.success('密码已修改并同步到数据库')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '密码修改失败')
  } finally {
    changingPassword.value = false
  }
}

function resetPasswordForm() {
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  passwordFormRef.value?.clearValidate()
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.settings-page {
  max-width: 680px;
  margin: 0 auto;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header { margin-bottom: 8px; }
.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--c-text);
  margin: 0 0 6px;
}
.page-desc {
  font-size: 13px;
  color: var(--c-text-3);
  margin: 0;
}

.settings-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-lg);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border);
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
}

.card-icon {
  width: 30px; height: 30px;
  background: var(--c-accent-dim);
  border: 1px solid rgba(2,119,189,.2);
  border-radius: var(--r-sm);
  display: flex; align-items: center; justify-content: center;
  color: var(--c-accent);
  flex-shrink: 0;
}
.card-icon--info {
  background: rgba(63,81,181,.08);
  border-color: rgba(63,81,181,.18);
  color: var(--c-text-2);
}
.card-icon--lock {
  background: rgba(79,111,220,.08);
  border-color: rgba(79,111,220,.18);
  color: var(--c-accent);
}

.settings-form {
  padding: 20px;
}

.field-hint {
  margin-top: 5px;
  font-size: 11px;
  color: var(--c-text-3);
  line-height: 1.5;
}

.key-saved {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--c-ok);
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}

.info-card .card-header { border-bottom: none; }

.info-list {
  margin: 0;
  padding: 0 20px 20px 36px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: var(--c-text-2);
  line-height: 1.6;
}
</style>
