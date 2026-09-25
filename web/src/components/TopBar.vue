<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'
import UserAvatarStatus from '@/components/UserAvatarStatus.vue'

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

// 获取未读通知数量
const fetchUnreadCount = async () => {
  try {
    const data: any = await apiClient.get('/api/notifications/unread-count')
    unreadCount.value = data?.count || 0
  } catch {
    /* 静默失败（如网络抖动），下次轮询重试 */
  }
}

// 供其他组件在产生新通知后手动刷新红点
defineExpose({ fetchUnreadCount })

// 通知页里点掉一条 / 全部已读之后，角标要立刻跟着掉。
// 以前只能等下一次 30 秒轮询，于是会出现「消息已经读完了，角标还挂着」的假象。
// 用 window 事件而不是 ref 层层透传：顶栏和通知页中间隔着 router-view，
// 事件写法不用改 App.vue，也不影响 30 秒轮询这条兜底路径。
const handleNotificationsChanged = () => { fetchUnreadCount() }

onMounted(() => window.addEventListener('notifications:changed', handleNotificationsChanged))
onUnmounted(() => window.removeEventListener('notifications:changed', handleNotificationsChanged))

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
  if (!target.closest('.top-avatar-wrap') && !target.closest('.admin-menu-wrap')) {
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
    <a href="/" class="logo"><img src="/favicon.svg" width="30"> <span>NLNOJ</span></a>

    <!-- 认证按钮区域 -->
    <div class="auth-buttons" v-if="!authStore.isAuthenticated">
      <a href="/login" class="auth-btn">登录</a>
      <a href="/register" class="auth-btn">注册</a>
    </div>

    <!-- 用户信息区域 -->
    <div class="auth-buttons" v-else>
      <!-- 头像下拉菜单 -->
      <div class="top-avatar-wrap">
        <UserAvatarStatus :user="authStore.currentUser" :size="10">
          <a :href="`/user/${userNumber}`" :title="displayName">
            <img
              :src="avatarUrl"
              :alt="displayName"
              class="avatar-img"
              onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 40 40%27%3E%3Crect width=%2740%27 height=%2740%27 fill=%27%23e74c3c%27/%3E%3Ctext x=%2750%25%27 y=%2750%25%27 text-anchor=%27middle%27 dy=%27.3em%27 fill=%27white%27 font-size=%2716%27 font-family=%27Arial%27%3EU%3C/text%3E%3C/svg%3E'"
            />
          </a>
        </UserAvatarStatus>
        <div class="top-avatar-menu">
          <a :href="`/user/${userNumber}`" class="top-avatar-menu-link">个人主页</a>
          <button @click="handleLogout" class="auth-btn logout">登出</button>
        </div>
      </div>

      <!-- 通知铃铛 -->
      <a href="/user/notification" class="bell-icon">
        <i class='fa-solid fa-bell'></i>
        <sup v-if="unreadCount > 0" class="bell-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</sup>
      </a>

      <!-- 管理菜单（仅管理员可见） -->
      <div
        v-if="authStore.currentUser?.is_admin || authStore.currentUser?.is_super_admin"
        class="admin-menu-wrap"
      >
        <button
          class="admin-gear"
          title="管理菜单"
          aria-label="管理菜单"
          @click.stop="showAdminMenu = !showAdminMenu"
        ><i class='fa-solid fa-gear'></i></button>
        <div v-if="showAdminMenu" class="admin-menu">
          <router-link to="/admin/user" class="admin-menu-item" @click="showAdminMenu = false">
            <i class="fa-solid fa-users"></i> 用户管理
          </router-link>
          <router-link to="/admin/ads" class="admin-menu-item" @click="showAdminMenu = false">
            <i class="fa-solid fa-rectangle-ad"></i> 广告管理
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 顶部栏基础样式 */
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface-strong);
  backdrop-filter: blur(var(--surface-blur)) saturate(1.5);
  -webkit-backdrop-filter: blur(var(--surface-blur)) saturate(1.5);
  border: var(--border-width) solid var(--border-color);
  padding: 12px 24px;
  box-shadow: var(--shadow-card);
  position: sticky;
  top: 10px;
  z-index: 200;
  font-family: inherit;
  margin: 10px;
  border-radius: var(--radius-lg);
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--primary);
  text-decoration: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo:hover {
  color: var(--primary-hover);
}

.auth-buttons {
  display: flex;
  gap: 16px;
  align-items: center;
}

.auth-btn {
  background: var(--primary);
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
  background: var(--primary-hover);
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
  color: var(--primary-hover);
}

.bell-badge {
  position: absolute;
  top: -8px;
  right: -12px;
  background-color: var(--primary);
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
  border: 0;
  background: transparent;
  text-decoration: none;
  font-size: 18px;
  cursor: pointer;
  transition: color 0.2s;
}

.admin-gear:hover {
  color: var(--primary);
}

.admin-menu-wrap {
  position: relative;
  margin-left: 8px;
}

.admin-menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  min-width: 142px;
  padding: 6px;
  background: #fff;
  border: 1px solid #e6ebf2;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(31, 41, 55, 0.14);
  z-index: 210;
}

.admin-menu-item {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 9px 11px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #374151;
  font: inherit;
  font-size: 13px;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  box-sizing: border-box;
}

.admin-menu-item:hover {
  background: #f2f5ff;
  color: var(--primary);
}

.admin-menu-item i {
  width: 16px;
  text-align: center;
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
