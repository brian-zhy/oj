<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import TopBar from './components/TopBar.vue'
import SideBar from './components/SideBar.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 判断是否显示导航栏
const showNav = computed(() => {
  // 登录注册页面不显示导航栏
  return !['Login', 'Register'].includes(route.name as string)
})

// 判断是否显示侧边栏
const showSidebar = computed(() => {
  return showNav.value
})

// 监听路由变化，恢复认证状态
watch(() => route.path, async () => {
  if (!authStore.accessToken && localStorage.getItem('accessToken')) {
    authStore.restoreState()
  }

  // 确保用户信息是最新的
  if (authStore.accessToken && !authStore.currentUser) {
    try {
      await authStore.fetchCurrentUser()
    } catch (error) {
      console.error('恢复用户信息失败:', error)
    }
  }
}, { immediate: true })

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div id="app">
    <!-- 顶部导航栏 -->
    <TopBar v-if="showNav" />

    <!-- 侧边导航栏 -->
    <SideBar v-if="showSidebar" />

    <!-- 主内容区域 -->
    <main :class="['main-content', { 'with-sidebar': showSidebar }]">
      <router-view />
    </main>

    <!-- 页脚 -->
    <footer v-if="showNav" class="page-footer">
      <div class="footer-content">
        <p class="footer-text">© 2025 Jason227 - 基于原项目重构</p>
        <p class="footer-text">基于 FastAPI + Vue 3 + Tailwind CSS 构建</p>
      </div>
    </footer>
  </div>
</template>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  min-height: 100vh;
  background: #f5f7fa;
}

/* 链接样式 */
a {
  color: inherit;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

/* 按钮重置 */
button {
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
}

/* 输入框重置 */
input, textarea, select {
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>

<style scoped>
/* 主内容区域 */
.main-content {
  min-height: calc(100vh - 60px - 80px); /* 减去顶部导航和页脚高度 */
  padding: 20px;
  transition: all 0.3s ease;
}

.main-content.with-sidebar {
  margin-left: 64px; /* 为侧边栏留出空间 */
  padding-top: 20px;
}

/* 桌面端适配 */
@media (min-width: 768px) {
  .main-content.with-sidebar {
    padding: 24px;
  }
}

/* 移动端适配 */
@media (max-width: 767px) {
  .main-content {
    padding: 16px;
  }

  .main-content.with-sidebar {
    margin-left: 0;
  }
}

/* 页脚 */
.page-footer {
  background: white;
  border-top: 1px solid #e5e7eb;
  padding: 20px 24px;
  text-align: center;
  margin-top: 20px;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
}

.footer-text {
  color: #6b7280;
  font-size: 14px;
  margin: 4px 0;
}

/* 响应式页脚 */
@media (max-width: 600px) {
  .page-footer {
    padding: 16px;
  }

  .footer-text {
    font-size: 12px;
  }
}

/* 登录注册页面特殊处理 */
.main-content:not(.with-sidebar) {
  margin-left: 0;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
