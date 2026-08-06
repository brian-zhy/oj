<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authApi } from '@/api/auth'

const router = useRouter()
const route = useRoute()

// 表单数据
const token = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

// 状态
const loading = ref(false)
const isSubmitting = ref(false)
const error = ref('')
const success = ref(false)
const isValidToken = ref(true)
const isCheckingToken = ref(true)

// 检查令牌是否有效
onMounted(() => {
  token.value = route.query.token as string || ''

  if (!token.value) {
    isValidToken.value = false
    error.value = '重置令牌缺失，请重新申请密码重置'
  }

  isCheckingToken.value = false
})

// 处理提交
const handleSubmit = async () => {
  if (isSubmitting.value) return

  error.value = ''

  if (!newPassword.value) {
    error.value = '请输入新密码'
    return
  }

  if (newPassword.value.length < 6) {
    error.value = '密码长度至少为6位'
    return
  }

  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }

  isSubmitting.value = true
  loading.value = true

  try {
    await authApi.confirmPasswordReset(token.value, newPassword.value)
    success.value = true
    error.value = ''
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || err.message || '密码重置失败，请稍后重试'
    error.value = errorMsg
  } finally {
    isSubmitting.value = false
    loading.value = false
  }
}

// 返回登录页
const goToLogin = () => {
  router.push('/login')
}
</script>

<template>
  <div class="reset-password-page">
    <div class="reset-password-card">
      <!-- 检查令牌状态 -->
      <div v-if="isCheckingToken" class="loading-state">
        <div class="spinner"></div>
        <div class="loading-text">验证重置令牌...</div>
      </div>

      <!-- 令牌无效 -->
      <div v-else-if="!isValidToken" class="error-state">
        <div class="error-icon">✕</div>
        <div class="error-title">重置链接无效</div>
        <div class="error-message">{{ error }}</div>
        <button @click="goToLogin" class="action-btn">
          返回登录
        </button>
      </div>

      <!-- 成功状态 -->
      <div v-else-if="success" class="success-state">
        <div class="success-icon">✓</div>
        <div class="success-title">密码重置成功</div>
        <div class="success-message">
          您的密码已成功重置，现在可以使用新密码登录了。
        </div>
        <button @click="goToLogin" class="action-btn">
          前往登录
        </button>
      </div>

      <!-- 表单状态 -->
      <form v-else @submit.prevent="handleSubmit" class="reset-password-form">
        <h1 class="title">重置密码</h1>
        <div class="subtitle">请输入您的新密码</div>

        <div class="form-group">
          <input
            v-model="newPassword"
            type="password"
            class="form-input"
            placeholder="新密码（至少6位）"
            autocomplete="new-password"
          />
        </div>

        <div class="form-group">
          <input
            v-model="confirmPassword"
            type="password"
            class="form-input"
            placeholder="确认新密码"
            autocomplete="new-password"
          />
        </div>

        <!-- 错误信息 -->
        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <!-- 提交按钮 -->
        <button
          type="submit"
          :disabled="loading"
          class="submit-btn"
        >
          {{ loading ? '重置中...' : '重置密码' }}
        </button>

        <!-- 返回登录链接 -->
        <div class="back-link">
          <a @click="goToLogin" href="#">返回登录</a>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
/* 页面容器 */
.reset-password-page {
  min-height: 100vh;
  background: #f5f7fa;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
}

/* 卡片容器 */
.reset-password-card {
  background: white;
  width: 420px;
  max-width: 90%;
  border-radius: 16px;
  padding: 32px 28px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* 标题 */
.title {
  font-size: 28px;
  text-align: center;
  color: #1a202c;
  margin-bottom: 8px;
  font-weight: 700;
}

.subtitle {
  text-align: center;
  color: #5b6e8c;
  margin-bottom: 28px;
  font-size: 14px;
}

/* 表单样式 */
.reset-password-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  font-size: 15px;
  background: #f9fafb;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
  background: white;
}

.form-input::placeholder {
  color: #9ca3af;
}

/* 错误信息 */
.error-message {
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13px;
  background: #fee2e2;
  color: #b91c1c;
}

/* 提交按钮 */
.submit-btn {
  width: 100%;
  padding: 12px;
  background: #3b82f6;
  border: none;
  border-radius: 40px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 8px;
}

.submit-btn:hover:not(:disabled) {
  background: #2563eb;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 返回链接 */
.back-link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
}

.back-link a {
  color: #3b82f6;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.2s;
}

.back-link a:hover {
  color: #2563eb;
  text-decoration: underline;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 40px 20px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  color: #5b6e8c;
  font-size: 15px;
}

/* 错误状态 */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 20px;
  padding: 40px 20px;
}

.error-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #ef4444;
  color: white;
  font-size: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.error-title {
  font-size: 20px;
  font-weight: 600;
  color: #1a202c;
}

.error-message {
  font-size: 14px;
  color: #5b6e8c;
  line-height: 1.6;
  max-width: 320px;
}

/* 成功状态 */
.success-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 20px;
  padding: 40px 20px;
}

.success-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #10b981;
  color: white;
  font-size: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.success-title {
  font-size: 20px;
  font-weight: 600;
  color: #1a202c;
}

.success-message {
  font-size: 15px;
  color: #5b6e8c;
  line-height: 1.6;
  max-width: 320px;
}

.action-btn {
  padding: 12px 32px;
  background: #3b82f6;
  border: none;
  border-radius: 40px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.action-btn:hover {
  background: #2563eb;
}

/* 响应式适配 */
@media (max-width: 480px) {
  .reset-password-card {
    padding: 24px 20px;
  }

  .title {
    font-size: 24px;
  }

  .form-input {
    padding: 10px 14px;
    font-size: 14px;
  }

  .submit-btn {
    padding: 10px;
    font-size: 15px;
  }
}
</style>
