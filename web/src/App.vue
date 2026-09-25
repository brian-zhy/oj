<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import * as session from './utils/session'
import TopBar from './components/TopBar.vue'
import SideBar from './components/SideBar.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isNavigating = ref(false)
const DEFAULT_PAGE_TITLE = 'NLNOJ - 新一代社交型 Online Judge 平台'
const routeTitleMap: Record<string, string> = {
  Home: '首页',
  Login: '登录',
  Register: '注册',
  ForgotPassword: '找回密码',
  ResetPassword: '重设密码',
  Profile: '我的主页',
  UserDetail: '用户主页',
  Notifications: '消息通知',
  Admin: '管理后台',
  AdminAds: '广告管理',
  Judgement: '陶片放逐',
  Discuss: '讨论区',
  DiscussNew: '发帖',
  TeamList: '团队',
  Tickets: '工单',
  ProblemList: '题库',
  ProblemDetail: '题目详情',
  SubmissionList: '提交记录',
  ContestList: '比赛'
}

const resolvePageTitle = () => {
  const explicit = typeof route.meta.title === 'string' ? route.meta.title.trim() : ''
  const fallback = routeTitleMap[String(route.name)] || String(route.name || '首页')
  const title = String(explicit || fallback)
  return `${title} - ${DEFAULT_PAGE_TITLE}`
}

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
// 用户资料的补拉交给路由守卫统一处理，这里不再重复请求 /auth/me
watch(() => route.path, () => {
  document.title = resolvePageTitle()

  if (!authStore.accessToken && session.hasSession()) {
    authStore.restoreState()
  }
}, { immediate: true })

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}

// ===== 用户主题背景（主题商店设置，只影响自己的浏览效果） =====
// 与 ThemeShop.vue / 后端 _ALLOWED_THEME_PRESETS 保持同一组 key
const PRESET_GRADIENTS: Record<string, string> = {
  dawn: 'linear-gradient(135deg, #ffd8a8 0%, #ff9db8 50%, #a8c8ff 100%)',
  ocean: 'linear-gradient(160deg, #0f3057 0%, #00587a 55%, #008891 100%)',
  dusk: 'linear-gradient(160deg, #2b1b4d 0%, #7a3b8f 55%, #ff7e5f 100%)',
  sakura: 'linear-gradient(150deg, #ffe3ec 0%, #ffc7de 55%, #ffd8b1 100%)',
}
const themeStyle = computed(() => {
  const me = authStore.currentUser
  if (!me?.theme_enabled || !me.theme_background) return undefined
  const bg = me.theme_background
  if (bg.startsWith('preset:')) {
    const css = PRESET_GRADIENTS[bg.split(':')[1]]
    if (!css) return undefined
    return { backgroundImage: `linear-gradient(rgba(15,23,52,.38), rgba(15,23,52,.38)), ${css}` }
  }
  return {
    backgroundImage: `linear-gradient(rgba(15,23,52,.42), rgba(15,23,52,.42)), url(${bg})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
  }
})
</script>

<template>
  <div id="app">
    <div class="app-background" :style="themeStyle" aria-hidden="true"></div>
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
  background: var(--bg-page);
}

/* 页面背景层：光斑/主题图独立成 fixed 图层。
   不用 background-attachment:fixed —— 那会让每帧滚动/重绘都全屏
   重采样（叠加全站 backdrop-filter 时点击切换主题肉眼可见地卡），
   独立图层只合成一次，卡片毛玻璃对它采样也快得多。 */
.app-background {
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background:
    radial-gradient(560px 420px at 12% 8%, var(--bg-page-glow-1), transparent 70%),
    radial-gradient(620px 460px at 88% 18%, var(--bg-page-glow-2), transparent 70%),
    radial-gradient(720px 520px at 50% 96%, var(--bg-page-glow-3), transparent 70%),
    var(--bg-page);
}

#app {
  min-height: 100vh;
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

/* 页面跳转过渡：淡入 + 轻微上浮回正，顺滑曲线（配合顶部加载条） */
.route-enter-active,
.route-leave-active {
  transition: opacity 0.28s cubic-bezier(0.22, 0.61, 0.36, 1),
    transform 0.28s cubic-bezier(0.22, 0.61, 0.36, 1);
}

.route-enter-from {
  opacity: 0;
  transform: translateY(14px) scale(0.992);
}

.route-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.996);
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
  background: var(--surface);
  backdrop-filter: blur(var(--surface-blur)) saturate(1.5);
  -webkit-backdrop-filter: blur(var(--surface-blur)) saturate(1.5);
  border-top: var(--border-width) solid var(--border-color);
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
