<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/auth'

const router = useRouter()

// 表单数据
const email = ref('')
const loading = ref(false)
const isSubmitting = ref(false)
const error = ref('')
const success = ref(false)

// 处理提交
const handleSubmit = async () => {
  if (isSubmitting.value) return

  error.value = ''

  if (!email.value.trim()) {
    error.value = '请输入电子邮箱地址'
    return
  }

  // 简单的邮箱格式验证
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email.value.trim())) {
    error.value = '请输入有效的电子邮箱地址'
    return
  }

  isSubmitting.value = true
  loading.value = true

  try {
    await authApi.requestPasswordReset(email.value.trim())
    success.value = true
    error.value = ''
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || err.message || '发送失败，请稍后重试'
    error.value = errorMsg
  } finally {
    isSubmitting.value = false
    loading.value = false
  }
}

// 返回登录页
const backToLogin = () => {
  router.push('/login')
}
</script>

<template>
  <div class="forgot-password-page">
    <div class="forgot-password-card">
      <h1 class="title">重置密码</h1>
      <div class="subtitle">输入您的电子邮箱，我们将发送密码重置链接</div>

      <!-- 成功状态 -->
      <div v-if="success" class="success-state">
        <div class="success-icon">✓</div>
        <div class="success-message">
          密码重置邮件已发送到 <strong>{{ email }}</strong>
        </div>
        <div class="success-tips">
          请检查您的邮箱并按照邮件中的说明重置密码。如果几分钟内没有收到邮件，请检查垃圾邮件文件夹。
        </div>
        <button @click="backToLogin" class="back-btn">
          返回登录
        </button>
      </div>

      <!-- 表单状态 -->
      <form v-else @submit.prevent="handleSubmit" class="forgot-password-form">
        <div class="form-group">
          <input
            v-model="email"
            type="email"
            class="form-input"
            placeholder="电子邮箱地址"
            autocomplete="email"
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
          {{ loading ? '发送中...' : '发送密码重置邮件' }}
        </button>

        <!-- 返回登录链接 -->
        <div class="back-link">
          <a @click="backToLogin" href="#">返回登录</a>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
/* 页面容器 */
.forgot-password-page {
  min-height: 100vh;
  background: #f5f7fa;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
}

/* 卡片容器 */
.forgot-password-card {
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
  line-height: 1.5;
}

/* 表单样式 */
.forgot-password-form {
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

/* 成功状态 */
.success-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 20px;
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

.success-message {
  font-size: 15px;
  color: #1a202c;
  line-height: 1.6;
}

.success-tips {
  font-size: 13px;
  color: #5b6e8c;
  line-height: 1.6;
  max-width: 320px;
}

.back-btn {
  padding: 10px 24px;
  background: #3b82f6;
  border: none;
  border-radius: 40px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.back-btn:hover {
  background: #2563eb;
}

/* 响应式适配 */
@media (max-width: 480px) {
  .forgot-password-card {
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
