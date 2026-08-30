<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()

// 注册方式选择
const registerType = ref<'email' | 'phone'>('email')

// 表单数据
const formData = ref({
  username: '',
  email: '',
  phone: '',
  password: ''
})

const confirmPassword = ref('')
const verificationCode = ref('')
const emailToken = ref('')

const error = ref('')
const loading = ref(false)
const isSubmitting = ref(false)
const sendingCode = ref(false)
const codeSent = ref(false)
const countdown = ref(0)

// 密码强度指示
const passwordStrength = ref(0)
const passwordStrengthText = ref('')

// 计算密码强度
const calculatePasswordStrength = (password: string) => {
  if (!password) {
    passwordStrength.value = 0
    passwordStrengthText.value = ''
    return
  }

  let strength = 0
  if (password.length >= 8) strength += 1
  if (password.length >= 12) strength += 1
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength += 1
  if (/\d/.test(password)) strength += 1
  if (/[^a-zA-Z0-9]/.test(password)) strength += 1

  passwordStrength.value = strength

  if (strength <= 2) {
    passwordStrengthText.value = '弱'
  } else if (strength <= 3) {
    passwordStrengthText.value = '中'
  } else {
    passwordStrengthText.value = '强'
  }
}

// 监听密码变化
watch(() => formData.value.password, (newPassword) => {
  calculatePasswordStrength(newPassword)
})

// 验证邮箱格式
const validateEmail = (email: string) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

// 验证手机号格式
const validatePhone = (phone: string) => {
  const phoneRegex = /^1[3-9]\d{9}$/
  return phoneRegex.test(phone)
}

// 发送验证码（仅邮箱注册使用）
const sendVerificationCode = async () => {
  await sendEmailVerification()
}

// 发送邮箱验证码
const sendEmailVerification = async () => {
  if (!formData.value.email) {
    error.value = '请输入邮箱地址'
    return
  }

  if (!validateEmail(formData.value.email)) {
    error.value = '请输入有效的邮箱地址'
    return
  }

  sendingCode.value = true
  error.value = ''

  try {
    const data = await authApi.sendEmailVerification(formData.value.email)

    if (data.token) {
      emailToken.value = data.token
      codeSent.value = true
      error.value = ''

      // 开始倒计时
      countdown.value = 60
      const timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) {
          clearInterval(timer)
        }
      }, 1000)

      // 显示成功消息
      showMessage('验证码已发送到您的邮箱，请查收邮件', 'success')
      console.log('验证码已发送，token:', data.token)
    } else {
      error.value = data.detail || '发送验证码失败'
      console.error('发送验证码失败:', data.detail)
    }
  } catch (err: any) {
    error.value = '网络错误，请检查网络连接后重试'
    console.error('发送验证码网络错误:', err)
  } finally {
    sendingCode.value = false
  }
}

const validateForm = (): boolean => {
  if (formData.value.username.length < 3) {
    error.value = '用户名至少需要3个字符'
    return false
  }

  const usernameRegex = /^[A-Za-z0-9_]+$/
  if (!usernameRegex.test(formData.value.username)) {
    error.value = '用户名只能包含字母、数字和下划线'
    return false
  }

  if (registerType.value === 'email') {
    if (!formData.value.email) {
      error.value = '请输入邮箱地址'
      return false
    }

    if (!validateEmail(formData.value.email)) {
      error.value = '请输入有效的邮箱地址'
      return false
    }

    if (!codeSent.value) {
      error.value = '请先获取邮箱验证码'
      return false
    }

    if (!verificationCode.value || verificationCode.value.length !== 6) {
      error.value = '请输入6位邮箱验证码'
      return false
    }
  } else {
    if (!formData.value.phone) {
      error.value = '请输入手机号码'
      return false
    }

    if (!validatePhone(formData.value.phone)) {
      error.value = '请输入有效的手机号码'
      return false
    }

  }

  if (formData.value.password.length < 8) {
    error.value = '密码至少需要8个字符'
    return false
  }

  if (formData.value.password.length > 72) {
    error.value = '密码最多72个字符'
    return false
  }

  if (formData.value.password !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return false
  }

  return true
}

const handleRegister = async () => {
  if (isSubmitting.value) return

  error.value = ''

  if (!validateForm()) {
    return
  }

  isSubmitting.value = true
  loading.value = true

  try {
    // 根据注册方式构建不同的注册数据
    const registerData: any = {
      username: formData.value.username,
      password: formData.value.password
    }

    if (registerType.value === 'email') {
      // 邮箱注册
      registerData.email = formData.value.email
      registerData.email_token = emailToken.value
      registerData.email_code = verificationCode.value
    } else {
      // 手机注册（无需验证码）
      registerData.phone = formData.value.phone
    }

    const success = await authStore.register(registerData)
    if (success) {
      router.push('/')
    } else {
      error.value = '注册失败，请稍后重试'
    }
  } catch (err: any) {
    const errorMsg = err.response?.data?.detail || '注册失败，用户名或联系方式可能已存在'
    error.value = errorMsg
  } finally {
    isSubmitting.value = false
    loading.value = false
  }
}

// 显示消息
const showMessage = (msg: string, type: 'success' | 'error') => {
  error.value = type === 'error' ? msg : ''
  if (type === 'success') {
    console.log('Success:', msg)
  }
}

// 切换注册方式时重置状态
const switchRegisterType = (type: 'email' | 'phone') => {
  registerType.value = type
  codeSent.value = false
  countdown.value = 0
  verificationCode.value = ''
  emailToken.value = ''
  error.value = ''
}
</script>

<template>
  <div class="register-page">
    <div class="register-card">
      <h1 class="register-title">✨ Jason227</h1>
      <div class="register-subtitle">注册新账户</div>

      <!-- 注册方式选择 -->
      <div class="register-type-selector">
        <button
          @click="switchRegisterType('email')"
          :class="['type-btn', { 'active': registerType === 'email' }]"
        >
          📧 邮箱注册
        </button>
        <button
          @click="switchRegisterType('phone')"
          :class="['type-btn', { 'active': registerType === 'phone' }]"
        >
          📱 手机注册
        </button>
      </div>

      <!-- 注册表单 -->
      <form @submit.prevent="handleRegister" class="register-form">
        <!-- 用户名 -->
        <div class="form-group">
          <input
            v-model="formData.username"
            type="text"
            class="form-input"
            placeholder="用户名（3-50位字母、数字或下划线）"
            required
            minlength="3"
            maxlength="50"
            pattern="[A-Za-z0-9_]+"
          />
        </div>

        <!-- 邮箱注册方式 -->
        <div v-if="registerType === 'email'">
          <!-- 邮箱 -->
          <div class="form-group">
            <div class="input-row">
              <input
                v-model="formData.email"
                type="email"
                class="form-input flex-input"
                placeholder="电子邮箱"
                required
              />
              <button
                v-if="!codeSent"
                type="button"
                @click="sendVerificationCode"
                :disabled="sendingCode"
                class="send-code-btn"
              >
                {{ sendingCode ? '发送中...' : '获取验证码' }}
              </button>
              <button
                v-else
                type="button"
                @click="sendVerificationCode"
                :disabled="countdown > 0"
                class="send-code-btn"
              >
                {{ countdown > 0 ? `${countdown}秒后重发` : '重新发送' }}
              </button>
            </div>
          </div>

          <!-- 邮箱验证码 -->
          <div class="form-group" v-if="codeSent">
            <input
              v-model="verificationCode"
              type="text"
              class="form-input"
              placeholder="请输入6位邮箱验证码"
              maxlength="6"
              required
            />
          </div>

        </div>

        <!-- 手机注册方式 -->
        <div v-else>
          <!-- 手机号 -->
          <div class="form-group">
            <input
              v-model="formData.phone"
              type="tel"
              class="form-input"
              placeholder="手机号码"
              required
            />
          </div>
        </div>

        <!-- 密码 -->
        <div class="form-group">
          <input
            v-model="formData.password"
            type="password"
            class="form-input"
            placeholder="密码（8-72位）"
            required
            minlength="8"
            maxlength="72"
          />
          <!-- 密码强度指示器 -->
          <div v-if="formData.password" class="password-strength">
            <div class="strength-bar">
              <div
                :class="['strength-fill', `strength-${passwordStrength}`]"
                :style="{ width: `${(passwordStrength / 5) * 100}%` }"
              ></div>
            </div>
            <div class="strength-text">
              密码强度：{{ passwordStrengthText }}
            </div>
          </div>
        </div>

        <!-- 确认密码 -->
        <div class="form-group">
          <input
            v-model="confirmPassword"
            type="password"
            class="form-input"
            placeholder="确认密码"
            required
          />
        </div>

        <!-- 错误信息 -->
        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <!-- 注册按钮 -->
        <button
          type="submit"
          :disabled="loading"
          class="register-btn"
        >
          {{ loading ? '注册中...' : '注册账户' }}
        </button>
      </form>

      <!-- 底部链接 -->
      <div class="footer-links">
        <router-link to="/login" class="footer-link">
          已有账号？登录
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 页面容器 */
.register-page {
  min-height: 100vh;
  background: #f5f7fa;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
}

/* 注册卡片 */
.register-card {
  background: white;
  width: 460px;
  max-width: 90%;
  border-radius: 16px;
  padding: 32px 28px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* 标题 */
.register-title {
  font-size: 28px;
  text-align: center;
  color: #e74c3c;
  margin-bottom: 8px;
  font-weight: 700;
}

.register-subtitle {
  text-align: center;
  color: #5b6e8c;
  margin-bottom: 28px;
  font-size: 14px;
}

/* 注册方式选择器 */
.register-type-selector {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.type-btn {
  flex: 1;
  padding: 12px 20px;
  background: #f9fafb;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  color: #6b7280;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.type-btn:hover {
  border-color: #e74c3c;
  color: #e74c3c;
}

.type-btn.active {
  background: #e74c3c;
  border-color: #e74c3c;
  color: white;
  cursor: default;
}

/* 表单样式 */
.register-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  margin-bottom: 4px;
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
  border-color: #e74c3c;
  box-shadow: 0 0 0 2px rgba(231, 76, 60, 0.1);
  background: white;
}

.form-input::placeholder {
  color: #9ca3af;
}

.form-input:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
}

/* 输入行 */
.input-row {
  display: flex;
  gap: 12px;
}

.flex-input {
  flex: 1;
}

/* 发送验证码按钮 */
.send-code-btn {
  padding: 12px 16px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s;
}

.send-code-btn:hover:not(:disabled) {
  background: #c0392b;
}

.send-code-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 密码强度指示器 */
.password-strength {
  margin-top: 8px;
}

.strength-bar {
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 4px;
}

.strength-fill {
  height: 100%;
  transition: all 0.3s ease;
}

.strength-1 {
  background: #ef4444;
}

.strength-2 {
  background: #f59e0b;
}

.strength-3 {
  background: #10b981;
}

.strength-4 {
  background: #3b82f6;
}

.strength-5 {
  background: #8b5cf6;
}

.strength-text {
  font-size: 12px;
  color: #6b7280;
}

/* 错误信息 */
.error-message {
  padding: 8px;
  border-radius: 12px;
  font-size: 13px;
  text-align: center;
  background: #fee2e2;
  color: #b91c1c;
}

/* 注册按钮 */
.register-btn {
  width: 100%;
  padding: 12px;
  background: #e74c3c;
  border: none;
  border-radius: 40px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 02s;
}

.register-btn:hover:not(:disabled) {
  background: #c0392b;
}

.register-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 底部链接 */
.footer-links {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 24px;
  font-size: 14px;
}

.footer-link {
  color: #e74c3c;
  text-decoration: none;
  transition: color 0.2s;
}

.footer-link:hover {
  color: #c0392b;
  text-decoration: underline;
}

/* 响应式适配 */
@media (max-width: 480px) {
  .register-card {
    padding: 24px 20px;
  }

  .register-title {
    font-size: 24px;
  }

  .register-type-selector {
    flex-direction: column;
  }

  .type-btn {
    width: 100%;
  }

  .input-row {
    flex-direction: column;
  }

  .send-code-btn {
    width: 100%;
  }

  .form-input {
    padding: 10px 14px;
    font-size: 14px;
  }

  .register-btn {
    padding: 10px;
    font-size: 15px;
  }
}
</style>
