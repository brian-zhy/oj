<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 表单数据
const identifier = ref('')
const password = ref('')
const captcha = ref('')
const captchaId = ref('')

// 验证码相关
const captchaCanvas = ref<HTMLCanvasElement | null>(null)
const currentCaptcha = ref('')

// 错误和加载状态
const error = ref('')
const loading = ref(false)
const isSubmitting = ref(false)
const loginSuccess = ref(false)

// 获取验证码
const fetchCaptcha = async () => {
  try {
    console.log('正在获取验证码...')
    const data = await apiClient.get('/auth/captcha')
    captchaId.value = data.captcha_id
    currentCaptcha.value = data.captcha_text
    console.log('验证码获取成功:', { captchaId: data.captcha_id, text: data.captcha_text })
    // 不要清除错误消息，保持登录错误的显示
  } catch (err) {
    console.error('获取验证码失败:', err)
    error.value = '获取验证码失败，请刷新页面重试'
  }
}

// 绘制验证码
const drawCaptcha = () => {
  console.log('绘制验证码被调用')
  console.log('Canvas元素:', captchaCanvas.value)
  console.log('验证码文本:', currentCaptcha.value)

  if (!captchaCanvas.value) {
    console.error('Canvas元素不存在')
    error.value = '验证码加载失败，请刷新页面'
    return
  }

  if (!currentCaptcha.value) {
    console.error('验证码文本为空')
    error.value = '验证码加载失败，请刷新页面'
    return
  }

  const ctx = captchaCanvas.value.getContext('2d')
  if (!ctx) {
    console.error('无法获取Canvas上下文')
    error.value = '验证码绘制失败，请刷新页面'
    return
  }

  const width = captchaCanvas.value.width
  const height = captchaCanvas.value.height

  console.log('开始绘制验证码:', { width, height })

  // 清空画布
  ctx.clearRect(0, 0, width, height)
  ctx.fillStyle = '#f9fafb'
  ctx.fillRect(0, 0, width, height)

  // 添加干扰线
  for (let i = 0; i < 10; i++) {
    ctx.beginPath()
    ctx.moveTo(Math.random() * width, Math.random() * height)
    ctx.lineTo(Math.random() * width, Math.random() * height)
    ctx.strokeStyle = `rgba(100,100,100,${0.2 + Math.random() * 0.5})`
    ctx.stroke()
  }

  // 添加噪点
  for (let i = 0; i < 100; i++) {
    ctx.fillStyle = `rgba(0,0,0,${Math.random() * 0.5})`
    ctx.fillRect(Math.random() * width, Math.random() * height, 1, 1)
  }

  // 绘制验证码文字
  for (let i = 0; i < currentCaptcha.value.length; i++) {
    ctx.font = `${24 + Math.floor(Math.random() * 6)}px "Courier New", monospace`
    ctx.fillStyle = `rgb(${50 + Math.random() * 100}, ${30 + Math.random() * 80}, ${20 + Math.random() * 70})`
    const x = 12 + i * 20 + Math.random() * 6
    const y = 30 + Math.random() * 8
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate((Math.random() - 0.5) * 0.4)
    ctx.fillText(currentCaptcha.value[i], 0, 0)
    ctx.restore()
  }

  console.log('验证码绘制完成')
}

// 刷新验证码
const refreshCaptcha = () => {
  console.log('刷新验证码')
  captcha.value = ''
  // 不要清除错误消息，让用户能看到登录失败的原因
  fetchCaptcha()
}

// 处理登录
const handleLogin = async () => {
  if (isSubmitting.value) return

  error.value = ''
  loginSuccess.value = false

  if (!identifier.value.trim()) {
    error.value = '请输入用户名、UID、手机或电子邮箱'
    return
  }

  if (!password.value) {
    error.value = '请输入密码'
    return
  }

  if (!captcha.value.trim()) {
    error.value = '请输入图形验证码'
    return
  }

  isSubmitting.value = true
  loading.value = true

  try {
    const success = await authStore.loginWithIdentifier({
      identifier: identifier.value.trim(),
      password: password.value,
      captcha_id: captchaId.value,
      captcha: captcha.value.trim()
    })

    if (success) {
      // 登录成功，显示成功消息
      loginSuccess.value = true
      error.value = ''

      // 延迟跳转，让用户看到成功消息
      setTimeout(() => {
        const redirect = route.query.redirect as string || '/'
        router.push(redirect)
      }, 1500)
    } else {
      error.value = '登录失败：用户名或密码错误'
      refreshCaptcha()
    }
  } catch (err: any) {
    // 根据不同的错误类型显示具体的失败原因
    let errorMsg = '登录失败'

    if (err.response?.data?.detail) {
      const detail = err.response.data.detail

      // 根据后端返回的具体错误信息进行友好提示
      if (detail.includes('验证码') || detail.includes('captcha')) {
        errorMsg = '登录失败：图形验证码错误或已过期'
      } else if (detail.includes('用户不存在') || detail.includes('用户名或密码')) {
        errorMsg = '登录失败：用户名或密码错误'
      } else if (detail.includes('封禁') || detail.includes(' banned')) {
        errorMsg = '登录失败：账号已被封禁，请联系管理员'
      } else if (detail.includes('网络') || detail.includes('超时')) {
        errorMsg = '登录失败：网络连接超时，请检查网络连接'
      } else {
        errorMsg = `登录失败：${detail}`
      }
    } else if (err.message) {
      errorMsg = `登录失败：${err.message}`
    } else {
      errorMsg = '登录失败：服务器响应异常，请稍后重试'
    }

    error.value = errorMsg
    refreshCaptcha()
  } finally {
    isSubmitting.value = false
    loading.value = false
  }
}

// 组件挂载时获取验证码
onMounted(() => {
  console.log('Login组件已挂载，开始获取验证码')
  fetchCaptcha()
})

// 监听验证码文本变化，重新绘制
watch(currentCaptcha, () => {
  console.log('currentCaptcha变化，重新绘制验证码')
  drawCaptcha()
})
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">✨ Online Judge</h1>
      <div class="login-subtitle">登录账号</div>

      <!-- 登录表单 -->
      <form @submit.prevent="handleLogin" class="login-form">
        <!-- 用户标识符 -->
        <div class="form-group">
          <input
            v-model="identifier"
            type="text"
            class="form-input"
            placeholder="用户名、UID、手机或电子邮箱"
            autocomplete="off"
          />
        </div>

        <!-- 密码 -->
        <div class="form-group">
          <input
            v-model="password"
            type="password"
            class="form-input"
            placeholder="输入密码"
            autocomplete="current-password"
          />
        </div>

        <!-- 验证码 -->
        <div class="form-group">
          <div class="captcha-row">
            <input
              v-model="captcha"
              type="text"
              class="form-input captcha-input"
              placeholder="请输入图形验证码"
              autocomplete="off"
              maxlength="6"
            />
            <canvas
              ref="captchaCanvas"
              width="120"
              height="44"
              class="captcha-canvas"
              @click="refreshCaptcha"
            />
          </div>
        </div>

        <!-- 成功信息 -->
        <div v-if="loginSuccess" class="success-message">
          ✓ 登录成功！正在跳转...
        </div>

        <!-- 错误信息 -->
        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <!-- 调试信息 -->
        <div v-if="currentCaptcha" class="debug-info" style="font-size: 11px; color: #999; text-align: center; margin-top: 8px;">
          验证码已加载 (调试: {{ currentCaptcha.length }} 位)
        </div>

        <!-- 登录按钮 -->
        <button
          type="submit"
          :disabled="loading"
          class="login-btn"
        >
          {{ loading ? '登录中...' : '使用账户密码登录' }}
        </button>
      </form>

      <!-- 底部链接 -->
      <div class="footer-links">
        <router-link to="/register" class="footer-link">
          没有账号？
        </router-link>
        <router-link to="/forgot-password" class="footer-link">
          忘记密码？
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 页面容器 */
.login-page {
  min-height: 100vh;
  background: #f5f7fa;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
}

/* 登录卡片 */
.login-card {
  background: white;
  width: 400px;
  max-width: 90%;
  border-radius: 16px;
  padding: 32px 28px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* 标题 */
.login-title {
  font-size: 28px;
  text-align: center;
  color: #e74c3c;
  margin-bottom: 8px;
  font-weight: 700;
}

.login-subtitle {
  text-align: center;
  color: #5b6e8c;
  margin-bottom: 28px;
  font-size: 14px;
}

/* 表单样式 */
.login-form {
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
  border-color: #e74c3c;
  box-shadow: 0 0 0 2px rgba(231, 76, 60, 0.1);
  background: white;
}

.form-input::placeholder {
  color: #9ca3af;
}

/* 验证码行 */
.captcha-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.captcha-input {
  flex: 1;
}

.captcha-canvas {
  cursor: pointer;
  border-radius: 12px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  width: 120px;
  height: 44px;
  transition: border-color 0.2s;
}

.captcha-canvas:hover {
  border-color: #9ca3af;
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

/* 成功信息 */
.success-message {
  padding: 12px;
  border-radius: 12px;
  font-size: 14px;
  text-align: center;
  background: #d1fae5;
  color: #047857;
  font-weight: 600;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 登录按钮 */
.login-btn {
  width: 100%;
  padding: 12px;
  background: #e74c3c;
  border: none;
  border-radius: 40px;
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.login-btn:hover:not(:disabled) {
  background: #c0392b;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: notallowed;
}

/* 底部链接 */
.footer-links {
  display: flex;
  justify-content: space-between;
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
  textext-decoration: underline;
}

/* 响应式适配 */
@media (max-width: 480px) {
  .login-card {
    padding: 24px 20px;
  }

  .login-title {
    font-size: 24px;
  }

  .form-input {
    padding: 10px 14px;
    font-size: 14px;
  }

  .captcha-canvas {
    width: 100px;
    height: 36px;
  }

  .login-btn {
    padding: 10px;
    font-size: 15px;
  }

  .footer-links {
    flex-direction: column;
    gap: 12px;
    text-align: center;
  }
}
</style>
