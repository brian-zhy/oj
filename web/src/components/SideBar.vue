<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 当前激活的导航项
const activePath = ref(route.path)

// 监听路由变化
import { watch } from 'vue'
watch(() => route.path, (newPath) => {
  activePath.value = newPath
})

// 判断是否激活
const isActive = (path: string) => {
  // 精确匹配：主页、用户管理（避免 /admin/logs 误高亮 /admin）
  if (path === '/' || path === '/admin') {
    return activePath.value === path
  }
  return activePath.value.startsWith(path)
}

// 导航到指定路径
const navigateTo = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="nav-sidebar">
    <!-- 主菜单 第一部分（主页 ~ 评测记录） -->
    <div class="nav-group">
      <ul>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/') }"
            href="/"
            @click.prevent="navigateTo('/')"
          >
            <span class="nav-icon">
              <svg viewBox="0 0 576 512" width="20" height="20" fill="currentColor">
                <path d="M240 6.1c9.1-8.2 22.9-8.2 32 0l232 208c9.9 8.8 10.7 24 1.8 33.9s-24 10.7-33.9 1.8l-8-7.2 0 205.3c0 35.3-28.7 64-64 64l-288 0c-35.3 0-64-28.7-64-64l0-205.3-8 7.2c-9.9 8.8-25 8-33.9-1.8s-8-25 1.8-33.9L240 6.1zm16 50.1L96 199.7 96 448c0 8.8 7.2 16 16 16l48 0 0-104c0-39.8 32.2-72 72-72l48 0c39.8 0 72 32.2 72 72l0 104 48 0c8.8 0 16-7.2 16-16l0-248.3-160-143.4zM208 464l96 0 0-104c0-13.3-10.7-24-24-24l-48 0c-13.3 0-24 10.7-24 24l0 104z" />
              </svg>
            </span>
            <span class="nav-text">主页</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/courses') }"
            href="/courses"
            @click.prevent="navigateTo('/courses')"
          >
            <span class="nav-icon">
              <svg viewBox="0 0 576 512" width="20" height="20" fill="currentColor">
                <path d="M318.8 38.1C309 34.1 298.6 32 288 32s-21 2.1-30.8 6.1L14.8 137.9C5.8 141.6 0 150.3 0 160L0 456c0 13.3 10.7 24 24 24s24-10.7 24-24l0-260.2 48 19.8 0 168.5c0 53 86 96 192 96s192-43 192-96l0-168.5 81.2-33.4c9-3.7 14.8-12.4 14.8-22.1s-5.8-18.4-14.8-22.1L318.8 38.1zM144 384l0-148.7 113.2 46.6c9.8 4 20.2 6.1 30.8 6.1s21-2.1 30.8-6.1L432 235.3 432 384c0 .1 0 .1 0 .3s-.1.4-.3.9c-.4.9-1.3 2.7-3.4 5.2-4.4 5.2-12.6 11.9-26 18.6-26.8 13.4-67.1 23-114.3 23s-87.5-9.7-114.3-23c-13.4-6.7-21.6-13.4-26-18.6-2.1-2.5-3-4.3-3.4-5.2-.2-.5-.3-.8-.3-.9s0-.2 0-.3zM87.2 160L275.5 82.5c4-1.6 8.2-2.5 12.5-2.5s8.5.8 12.5 2.5L488.8 160 300.5 237.5c-4 1.6-8.2 2.5-12.5 2.5s-8.5-.8-12.5-2.5L87.2 160z" />
              </svg>
            </span>
            <span class="nav-text">网校</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/training') }"
            href="/training"
            @click.prevent="navigateTo('/training')"
          >
            <span class="nav-icon">
              <svg viewBox="0 0 384 512" width="20" height="20" fill="currentColor">
                <path d="M152 96l80 0c13.3 0 24-10.7 24-24s-10.7-24-24-24l-80 0c-13.3 0-24 10.7-24 24s10.7 24 24 24zm0 48c-37.1 0-67.6-28-71.6-64L64 80c-8.8 0-16 7.2-16 16l0 352c0 8.8 7.2 16 16 16l256 0c8.8 0 16-7.2 16-16l0-352c0-8.8-7.2-16-16-16l-16.4 0c-4 36-34.5 64-71.6 64l-80 0zM232 0c25 0 47 12.7 59.9 32L320 32c35.3 0 64 28.7 64 64l0 352c0 35.3-28.7 64-64 64L64 512c-35.3 0-64-28.7-64-64L0 96C0 60.7 28.7 32 64 32l28.1 0C105 12.7 127 0 152 0l80 0zM171.2 193.1c8.2 6.7 9.5 18.8 2.8 27l-45.3 56c-3.7 4.5-9.2 7.1-15 7.1s-11.3-2.7-14.9-7.2L73.9 244.9c-6.6-8.3-5.3-20.4 3-27s20.4-5.3 27 3l10 12.5 30.3-37.5c6.7-8.2 18.8-9.5 27-2.8zM192 256c0-13.3 10.7-24 24-24l64 0c13.3 0 24 10.7 24 24s-10.7 24-24 24l-64 0c-13.3 0-24-10.7-24-24zm-16 96c0-13.3 10.7-24 24-24l80 0c13.3 0 24 10.7 24 24s-10.7 24-24 24l-80 0c-13.3 0-24-10.7-24-24zm-64-32a32 32 0 1 1 0 64 32 32 0 1 1 0-64z" />
              </svg>
            </span>
            <span class="nav-text">训练题单</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/contests') }"
            href="/contests"
            @click.prevent="navigateTo('/contests')"
          >
            <span class="nav-icon">
              <svg viewBox="0 0 512 512" width="20" height="20" fill="currentColor">
                <path d="M488 56c0-13.3-10.7-24-24-24s-24 10.7-24 24l0 400c0 13.3 10.7 24 24 24s24-10.7 24-24l0-400zM360 128c-13.3 0-24 10.7-24 24l0 304c0 13.3 10.7 24 24 24s24-10.7 24-24l0-304c0-13.3-10.7-24-24-24zM280 248c0-13.3-10.7-24-24-24s-24 10.7-24 24l0 208c0 13.3 10.7 24 24 24s24-10.7 24-24l0-208zM152 320c-13.3 0-24 10.7-24 24l0 112c0 13.3 10.7 24 24 24s24-10.7 24-24l0-112c0-13.3-10.7-24-24-24zM48 384c-13.3 0-24 10.7-24 24l0 48c0 13.3 10.7 24 24 24s24-10.7 24-24l0-48c0-13.3-10.7-24-24-24z" />
              </svg>
            </span>
            <span class="nav-text">比赛</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/submissions') }"
            href="/submissions"
            @click.prevent="navigateTo('/submissions')"
          >
            <span class="nav-icon">
              <svg viewBox="0 0 576 512" width="20" height="20" fill="currentColor">
                <path d="M352.4 54l0 138 138 0C473 124.6 419.9 71.4 352.4 54zm-144 210l0-173.1c-74.6 26.4-128 97.5-128 181.1 0 106 86 192 192 192 24.6 0 48-4.6 69.5-12.9L225 309.9c-10.7-12.9-16.6-29.2-16.6-45.9zm333.9-55.9c2.3 17.5-12.2 31.9-29.9 31.9l-176 0c-17.7 0-32-14.3-32-32l0-176c0-17.7 14.4-32.2 31.9-29.9 107 14.2 191.8 99 206 206zM256.4 66.7l0 197.3c0 5.6 2 11 5.5 15.3L394 438.7c11.7 14.1 9.2 35.4-6.9 44.1-34.1 18.6-73.2 29.2-114.7 29.2-132.5 0-240-107.5-240-240 0-115.5 81.5-211.9 190.2-234.8 18.1-3.8 33.8 11 33.8 29.5zM541.7 288c18.5 0 33.3 15.7 29.5 33.8-10.2 48.4-35 91.4-69.6 124.2-12.3 11.7-31.6 9.2-42.4-3.9L374.9 340.4c-17.3-20.9-2.4-52.4 24.6-52.4l142.2 0z" />
              </svg>
            </span>
            <span class="nav-text">评测记录</span>
          </a>
        </li>
      </ul>
    </div>

    <!-- 分割线 -->
    <div class="divider"></div>

    <!-- 主菜单 第二部分（讨论区、文章广场） -->
    <div class="nav-group">
      <ul>
        <li v-if="authStore.isAuthenticated">
          <a
            class="nav-item"
            :class="{ 'active': isActive('/discuss') }"
            href="/discuss"
            @click.prevent="navigateTo('/discuss')"
          >
            <span class="nav-icon">
              <svg viewBox="0 0 576 512" width="20" height="20" fill="currentColor">
                <path d="M76.2 258.7c6.1-15.2 4-32.6-5.6-45.9-14.5-20.1-22.6-43.7-22.6-68.8 0-66.8 60.5-128 144-128s144 61.2 144 128-60.5 128-144 128c-15.9 0-31.1-2.3-45.3-6.5-10.3-3.1-21.4-2.5-31.4 1.5l-50.4 20.2 11.4-28.5zM0 144c0 35.8 11.6 69.1 31.7 96.8L1.9 315.2c-1.3 3.2-1.9 6.6-1.9 10 0 14.8 12 26.8 26.8 26.8 3.4 0 6.8-.7 10-1.9l96.3-38.5c18.6 5.5 38.4 8.4 58.9 8.4 106 0 192-78.8 192-176S298-32 192-32 0 46.8 0 144zM384 512c20.6 0 40.3-3 58.9-8.4l96.3 38.5c3.2 1.3 6.6 1.9 10 1.9 14.8 0 26.8-12 26.8-26.8 0-3.4-.7-6.8-1.9-10l-29.7-74.4c20-27.8 31.7-61.1 31.7-96.8 0-82.4-61.7-151.5-145-170.7-1.6 16.3-5.1 31.9-10.1 46.9 63.9 14.8 107.2 67.3 107.2 123.9 0 25.1-8.1 48.7-22.6 68.8-9.6 13.3-11.7 30.6-5.6 45.9l11.4 28.5-50.4-20.2c-10-4-21.1-4.5-31.4-1.5-14.2 4.2-29.4 6.5-45.3 6.5-72.2 0-127.1-45.7-140.7-101.2-15.6 3.2-31.7 5-48.1 5.2 16.4 81.9 94.7 144 188.8 144z" />
              </svg>
            </span>
            <span class="nav-text">讨论区</span>
          </a>
        </li>
        <li v-if="authStore.isAuthenticated">
          <a
            class="nav-item"
            :class="{ 'active': isActive('/articles') }"
            href="/articles"
            @click.prevent="navigateTo('/articles')"
          >
            <span class="nav-icon">
              <svg viewBox="0 0 512 512" width="20" height="20" fill="currentColor">
                <path d="M168 80c-13.3 0-24 10.7-24 24l0 304c0 8.4-1.4 16.5-4.1 24L440 432c13.3 0 24-10.7 24-24l0-304c0-13.3-10.7-24-24-24L168 80zM72 480c-39.8 0-72-32.2-72-72L0 112C0 98.7 10.7 88 24 88s24 10.7 24 24l0 296c0 13.3 10.7 24 24 24s24-10.7 24-24l0-304c0-39.8 32.2-72 72-72l272 0c39.8 0 72 32.2 72 72l0 304c0 39.8-32.2 72-72 72L72 480zM192 152c0-13.3 10.7-24 24-24l48 0c13.3 0 24 10.7 24 24l0 48c0 13.3-10.7 24-24 24l-48 0c-13.3 0-24-10.7-24-24l0-48zm152 24l48 0c13.3 0 24 10.7 24 24s-10.7 24-24 24l-48 0c-13.3 0-24-10.7-24-24s10.7-24 24-24zM216 256l176 0c13.3 0 24 10.7 24 24s-10.7 24-24 24l-176 0c-13.3 0-24-10.7-24-24s10.7-24 24-24zm0 80l176 0c13.3 0 24 10.7 24 24s-10.7 24-24 24l-176 0c-13.3 0-24-10.7-24-24s10.7-24 24-24z" />
              </svg>
            </span>
            <span class="nav-text">文章广场</span>
          </a>
        </li>
      </ul>
    </div>

    <!-- 分割线 -->
    <div class="divider"></div>

    <!-- 更多功能 -->
    <div class="nav-group">
      <span class="group-title">
        <span class="nav-icon"></span>
        <span class="nav-text">更多功能</span>
      </span>
      <ul>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/image') }"
            href="/image"
            @click.prevent="navigateTo('/image')"
          >
            <span class="nav-icon">🖼️</span>
            <span class="nav-text">图片上传</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/clipboard') }"
            href="/clipboard"
            @click.prevent="navigateTo('/clipboard')"
          >
            <span class="nav-icon">📋</span>
            <span class="nav-text">云剪贴板</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/themes') }"
            href="/themes"
            @click.prevent="navigateTo('/themes')"
          >
            <span class="nav-icon">🎨</span>
            <span class="nav-text">主题商店</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/ranking') }"
            href="/ranking"
            @click.prevent="navigateTo('/ranking')"
          >
            <span class="nav-icon">🏆</span>
            <span class="nav-text">排行榜</span>
          </a>
        </li>
      </ul>
    </div>

    <!-- 分割线 -->
    <div class="divider"></div>

    <!-- 相关链接 -->
    <div class="nav-group">
      <span class="group-title">
        <span class="nav-icon"></span>
        <span class="nav-text">相关链接</span>
      </span>
      <ul>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/help') }"
            href="/help"
            @click.prevent="navigateTo('/help')"
          >
            <span class="nav-icon">❓</span>
            <span class="nav-text">帮助中心</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/contact') }"
            href="/contact"
            @click.prevent="navigateTo('/contact')"
          >
            <span class="nav-icon">📧</span>
            <span class="nav-text">联系我们</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/rules') }"
            href="/rules"
            @click.prevent="navigateTo('/rules')"
          >
            <span class="nav-icon">📜</span>
            <span class="nav-text">社区规则</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/judgement') }"
            href="/judgement"
            @click.prevent="navigateTo('/judgement')"
          >
            <span class="nav-icon">⚖️</span>
            <span class="nav-text">陶片放逐</span>
          </a>
        </li>
        <li v-if="authStore.currentUser">
          <a
            class="nav-item"
            :class="{ 'active': isActive('/tickets') }"
            href="/tickets"
            @click.prevent="navigateTo('/tickets')"
          >
            <span class="nav-icon">🎫</span>
            <span class="nav-text">工单/反馈</span>
          </a>
        </li>
        <li v-if="authStore.currentUser && authStore.currentUser.can_manage_users">
          <a
            class="nav-item"
            :class="{ 'active': isActive('/admin/logs') }"
            href="/admin/logs"
            @click.prevent="navigateTo('/admin/logs')"
          >
            <span class="nav-icon">📜</span>
            <span class="nav-text">管理日志</span>
          </a>
        </li>
        <li v-if="authStore.currentUser && (authStore.currentUser.is_super_admin || authStore.currentUser.is_admin || authStore.currentUser.can_manage_users)">
          <a
            class="nav-item"
            :class="{ 'active': isActive('/admin') }"
            href="/admin"
            @click.prevent="navigateTo('/admin')"
          >
            <span class="nav-icon">👥</span>
            <span class="nav-text">用户管理</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            :class="{ 'active': isActive('/about') }"
            href="/about"
            @click.prevent="navigateTo('/about')"
          >
            <span class="nav-icon">ℹ️</span>
            <span class="nav-text">关于我们</span>
          </a>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
/* 侧边栏 */
.nav-sidebar {
  position: fixed;
  top: 50px;
  left: 0;
  height: calc(100vh - 50px);
  width: 64px;
  background: white;
  border-radius: 0;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.06);
  padding: 16px 0;
  transition: width 0.3s ease;
  overflow-y: auto;
  overflow-x: hidden;
  white-space: nowrap;
  z-index: 150;
}

.nav-sidebar::-webkit-scrollbar {
  width: 4px;
}

.nav-sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.nav-sidebar::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 4px;
}

.nav-sidebar::-webkit-scrollbar-thumb:hover {
  background: #aaa;
}

.nav-sidebar:hover {
  width: 260px;
}

/* 导航组 */
.nav-group {
  margin-bottom: 0;
}

.nav-group ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

/* 导航项 */
.nav-item,
.group-title {
  padding: 10px 16px;
  font-size: 14px;
  color: #2c3e50;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
  display: flex;
  align-items: center;
  text-decoration: none;
}

.nav-item:hover,
.group-title:hover {
  background: #f0f2f5;
  color: #e74c3c;
  text-decoration: none;
}

.nav-item.active {
  background: #f0f2f5;
  color: #e74c3c;
}

.nav-icon {
  width: 24px;
  text-align: center;
  font-size: 18px;
  flex-shrink: 0;
  margin-right: 12px;
}

.nav-icon svg {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

/* 分组标题 */
.group-title {
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  margin-top: 8px;
  display: flex;
  align-items: center;
  cursor: default;
  background: #f9fafb;
}

.group-title:first-of-type {
  border-top: none;
  margin-top: 0;
}

/* 导航文字 */
.nav-text {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.nav-sidebar:hover .nav-text {
  opacity: 1;
}

/* 分割线 */
.divider {
  height: 1px;
  background: #e9ecef;
  margin: 8px 0;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .nav-sidebar {
    position: relative;
    top: 0;
    left: 0;
    width: 100%;
    height: auto;
    padding: 12px 0;
    box-shadow: none;
    border-bottom: 1px solid #e5e7eb;
  }

  .nav-sidebar:hover {
    width: 100%;
  }

  .nav-sidebar::-webkit-scrollbar {
    width: 0;
  }

  .nav-text {
    opacity: 1;
  }

  .nav-group {
    margin-bottom: 0;
  }

  .divider {
    display: none;
  }

  .nav-group ul {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 2px;
    padding: 8px;
  }

  .nav-item,
  .group-title {
    padding: 8px 12px;
    font-size: 12px;
    flex-direction: column;
    text-align: center;
    gap: 4px;
  }

  .nav-icon {
    font-size: 16px;
    width: 20px;
    margin-right: 0;
  }

  .group-title {
    grid-column: 1 / -1;
    background: #e9ecef;
    margin-top: 0;
    border-top: none;
  }
}

@media (max-width: 600px) {
  .nav-group ul {
    grid-template-columns: repeat(3, 1fr);
  }

  .nav-icon {
    font-size: 14px;
    width: 18px;
  }

  .nav-item,
  .group-title {
    padding: 6px 8px;
    font-size: 11px;
  }
}
</style>
