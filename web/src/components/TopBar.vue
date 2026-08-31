<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 验证码相关
const captchaCanvas = ref<HTMLCanvasElement | null>(null)
const currentCaptcha = ref('')

// 生成验证码
const generateCaptcha = () => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
  let captcha = ''
  for (let i = 0; i < 5; i++) captcha += chars[Math.floor(Math.random() * chars.length)]
  currentCaptcha.value = captcha.toUpperCase()

  if (captchaCanvas.value) {
    const ctx = captchaCanvas.value.getContext('2d')
    if (ctx) {
      const canvas = captchaCanvas.value

      // 清空画布
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = '#f9fafb'
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      // 添加干扰线
      for (let i = 0; i < 10; i++) {
        ctx.beginPath()
        ctx.moveTo(Math.random() * canvas.width, Math.random() * canvas.height)
        ctx.lineTo(Math.random() * canvas.width, Math.random() * canvas.height)
        ctx.strokeStyle = `rgba(100,100,100,${0.2 + Math.random() * 0.5})`
        ctx.stroke()
      }

      // 添加噪点
      for (let i = 0; i < 100; i++) {
        ctx.fillStyle = `rgba(0,0,0,${Math.random() * 0.5})`
        ctx.fillRect(Math.random() * canvas.width, Math.random() * canvas.height, 1, 1)
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
    }
  }
}

// 头像生成
const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

// 计算属性
const avatarUrl = computed(() => {
  return authStore.currentUser?.avatar_url || letterAvatar(authStore.currentUser?.username || 'U')
})

const displayName = computed(() => {
  return authStore.currentUser?.username || '用户'
})

const userNumber = computed(() => {
  return authStore.currentUser?.user_number || 0
})

const userId = computed(() => {
  return authStore.currentUser?.id || 0
})

// 下拉菜单
const showAvatarMenu = ref(false)
const showAdminMenu = ref(false)

// 未读通知数
const unreadCount = ref(0)

// 获取未读通知
const fetchUnreadCount = async () => {
  // TODO: 实现通知API
  // try {
  //   const response = await fetch('http://localhost:8000/notifications/unread')
  //   const data = await response.json()
  //   unreadCount.value = data.count
  // } catch (error) {
  //   console.error('获取通知失败:', error)
  // }
}

// 轮询通知
let notificationTimer: number | null = null

const startNotificationPolling = () => {
  if (notificationTimer) clearInterval(notificationTimer)
  notificationTimer = window.setInterval(() => {
    if (document.visibilityState === 'visible') {
      fetchUnreadCount()
    }
  }, 30000)
}

const stopNotificationPolling = () => {
  if (notificationTimer) {
    clearInterval(notificationTimer)
    notificationTimer = null
  }
}

// 登出
const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}

// 生命周期
onMounted(() => {
  if (authStore.isAuthenticated) {
    fetchUnreadCount()
    startNotificationPolling()
  }
})

onUnmounted(() => {
  stopNotificationPolling()
})

// 点击外部关闭菜单
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (!target.closest('.top-avatar-wrap') && !target.closest('.admin-gear')) {
    showAvatarMenu.value = false
    showAdminMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="topbar">
    <!-- Logo -->
    <a href="/" class="logo">✨ NLNOJ</a>

    <!-- 认证按钮区域 -->
    <div class="auth-buttons" v-if="!authStore.isAuthenticated">
      <a href="/login" class="auth-btn">登录</a>
      <a href="/register" class="auth-btn">注册</a>
    </div>

    <!-- 用户信息区域 -->
    <div class="auth-buttons" v-else>
      <!-- 头像下拉菜单 -->
      <div class="top-avatar-wrap">
        <a :href="`/user/${userNumber}`" :title="displayName">
          <img
            :src="avatarUrl"
            :alt="displayName"
            class="avatar-img"
            onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 40 40%27%3E%3Crect width=%2740%27 height=%2740%27 fill=%27%23e74c3c%27/%3E%3Ctext x=%2750%25%27 y=%2750%25%27 text-anchor=%27middle%27 dy=%27.3em%27 fill=%27white%27 font-size=%2716%27 font-family=%27Arial%27%3EU%3C/text%3E%3C/svg%3E'"
          />
        </a>
        <div class="top-avatar-menu">
          <a :href="`/user/${userNumber}`" class="top-avatar-menu-link">👤 个人主页</a>
          <button @click="handleLogout" class="auth-btn logout">登出</button>
        </div>
      </div>

      <!-- 通知铃铛 -->
      <a href="/user/notification" class="bell-icon">
        <svg viewBox="0 0 448 512" width="20" height="20">
          <path fill="currentColor" d="M224 0c-13.3 0-24 10.7-24 24l0 9.7C118.6 45.3 56 115.4 56 200l0 14.5c0 37.7-10 74.7-29 107.3L5.1 359.2C1.8 365 0 371.5 0 378.2 0 399.1 16.9 416 37.8 416l372.4 0c20.9 0 37.8-16.9 37.8-37.8 0-6.7-1.8-13.3-5.1-19L421 321.7c-19-32.6-29-69.6-29-107.3l0-14.5c0-84.6-62.6-154.7-144-166.3l0-9.7c0-13.3-10.7-24-24-24zM392.4 368l-336.9 0 12.9-22.1C91.7 306 104 260.6 104 214.5l0-14.5c0-66.3 53.7-120 120-120s120 53.7 120 120l0 14.5c0 46.2 12.3 91.5 35.5 131.4L392.4 368zM156.1 464c9.9 28 36.6 48 67.9 48s58-20 67.9-48l-135.8 0z"></path>
        </svg>
        <sup v-if="unreadCount > 0" class="bell-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</sup>
      </a>

      <!-- 管理后台入口（仅管理员可见，与原站一致的齿轮按钮） -->
      <router-link
        v-if="authStore.currentUser?.is_admin"
        to="/admin"
        class="admin-gear"
        title="进入管理后台"
      >⚙️</router-link>
    </div>
  </div>
</template>

<style scoped>
/* 顶部栏基础样式 */
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 12px 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  position: sticky;
  top: 0;
  z-index: 200;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  color: #e74c3c;
  text-decoration: none;
  cursor: pointer;
}

.logo:hover {
  color: #c0392b;
}

.auth-buttons {
  display: flex;
  gap: 16px;
  align-items: center;
}

.auth-btn {
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 30px;
  padding: 6px 20px;
  font-size: 14px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  transition: background 0.2s;
}

.auth-btn:hover {
  background: #c0392b;
  text-decoration: none;
  color: white;
}

.auth-btn.logout {
  background: #7f8c8d;
}

.auth-btn.logout:hover {
  background: #5a6a6a;
}

.bell-icon {
  position: relative;
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  color: #666;
  transition: color 0.2s;
}

.bell-icon:hover {
  color: #e74c3c;
}

.bell-badge {
  position: absolute;
  top: -8px;
  right: -12px;
  background-color: #e74c3c;
  color: white;
  font-size: 10px;
  font-weight: bold;
  min-width: 16px;
  height: 16px;
  border-radius: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.2);
  line-height: 1;
}

/* 头像下拉菜单 */
.top-avatar-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.top-avatar-menu {
  position: absolute;
  top: 100%;
  right: 0;
  min-width: 104px;
  background: #fff;
  border: 1px solid #eee;
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.14);
  padding: 6px;
  display: none;
  z-index: 300;
}

.top-avatar-wrap:hover .top-avatar-menu {
  display: block;
}

.top-avatar-menu .auth-btn.logout {
  display: block;
  width: 100%;
  text-align: center;
  border-radius: 6px;
  padding: 8px 0;
  box-sizing: border-box;
}

.top-avatar-menu-link {
  display: block;
  padding: 6px 12px;
  color: #2c3e50;
  font-size: 13px;
  text-decoration: none;
  border-radius: 4px;
  transition: background 0.15s;
}

.top-avatar-menu-link:hover {
  background: #f0f2f5;
  text-decoration: none;
}

.avatar-img {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  display: block;
  cursor: pointer;
  flex-shrink: 0;
}

.admin-gear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-left: 8px;
  color: #666;
  text-decoration: none;
  font-size: 18px;
  cursor: pointer;
  transition: color 0.2s;
}

.admin-gear:hover {
  color: #e74c3c;
}

@media (max-width: 600px) {
  .topbar {
    padding: 10px 16px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .logo {
    font-size: 1.2rem;
  }

  .auth-btn {
    padding: 4px 14px;
    font-size: 12px;
  }
}

@media (max-width: 400px) {
  .auth-btn {
    padding: 4px 10px;
    font-size: 11px;
  }
}
</style>
