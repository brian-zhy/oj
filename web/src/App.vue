<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import TopBar from './components/TopBar.vue'
import SideBar from './components/SideBar.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isNavigating = ref(false)

router.beforeEach(() => {
  isNavigating.value = true
})
router.afterEach(() => {
  isNavigating.value = false
})
router.onError(() => {
  isNavigating.value = false
})

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
    <div class="route-loading-bar" :class="{ active: isNavigating }" aria-hidden="true"></div>
    <!-- 顶部导航栏 -->
    <TopBar v-if="showNav" />

    <!-- 侧边导航栏 -->
    <SideBar v-if="showSidebar" />

    <!-- 主内容区域 -->
    <main :class="['main-content', { 'with-sidebar': showSidebar }]">
      <router-view v-slot="{ Component, route }">
        <Transition name="route" mode="out-in">
          <Suspense timeout="0">
            <component :is="Component" :key="route.fullPath" />
            <template #fallback>
              <div class="route-loading-screen" role="status" aria-live="polite">
                <span class="loading-spinner"></span>
                <span>页面加载中...</span>
              </div>
            </template>
          </Suspense>
        </Transition>
      </router-view>
    </main>

    <!-- 页脚 -->
    <footer v-if="showNav" class="page-footer">
      <div class="footer-content">
        <p class="footer-text">Copyright © 2026 NLNOJ Team</p>
	<p class="footer-text"><a href="http://beian.miit.gov.cn/" target="_blank">蜀ICP备2026036126号</a> | <a href="https://icp.gov.moe/?keyword=20262482" target="_blank">萌ICP备20262482号</a></p>
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
  font-family: inherit;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  min-height: 100vh;
  background: #f5f7fa;
}

.route-loading-bar {
  position: fixed;
  z-index: 3000;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  pointer-events: none;
  opacity: 0;
  background: linear-gradient(90deg, var(--primary), var(--accent), var(--primary));
  background-size: 200% 100%;
  transform: scaleX(0);
  transform-origin: left;
  transition: opacity 0.18s ease, transform 0.2s ease;
}

.route-loading-bar.active {
  opacity: 1;
  transform: scaleX(0.82);
  animation: loading-bar-sweep 1.15s ease-in-out infinite;
}

.route-loading-screen {
  min-height: calc(100vh - 180px);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #7d8aa0;
  font-size: 13px;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid #dce3f2;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spinner-rotate 0.72s linear infinite;
}

@keyframes loading-bar-sweep {
  0% { background-position: 100% 0; transform: scaleX(0.2); }
  55% { transform: scaleX(0.78); }
  100% { background-position: -100% 0; transform: scaleX(0.94); }
}

@keyframes spinner-rotate {
  to { transform: rotate(360deg); }
}

button,
a,
input,
textarea,
select {
  transition: color 0.18s ease, background-color 0.18s ease, border-color 0.18s ease,
    box-shadow 0.18s ease, opacity 0.18s ease, transform 0.18s ease;
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

.route-enter-active,
.route-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.route-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.route-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
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
  /* 手机端整页留白收紧。
     这里是「第一层」：各页面自己的 *-container / .card 还在下面叠加，
     三层加起来才是用户看到的留白，改一层不管另外两层等于白干。 */
  .main-content,
  .main-content.with-sidebar {
    padding: 12px;
  }

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
