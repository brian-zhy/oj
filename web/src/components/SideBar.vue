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
  if (path === '/' || path === '/admin/user') {
    return activePath.value === path
  }
  return activePath.value.startsWith(path)
}

// 移动端菜单展开状态（桌面端不受影响：恒为收起态，靠 hover 展开）
const mobileMenuOpen = ref(false)

// 导航到指定路径
const navigateTo = (path: string) => {
  // 移动端点完自动收起，避免菜单一直占着屏幕
  mobileMenuOpen.value = false
  router.push(path)
}

// 鼠标移出侧边栏时自动滚回顶部（与原站一致，仅桌面端宽侧交互）
const sidebarRef = ref<HTMLElement | null>(null)
const onSidebarLeave = () => {
  if (window.innerWidth > 900 && sidebarRef.value) {
    sidebarRef.value.scrollTop = 0
  }
}
</script>

<template>
  <!-- 移动端专用：默认收起菜单，点右下角的圆形悬浮按钮展开 -->
  <button
    type="button"
    class="mobile-menu-toggle"
    :aria-expanded="mobileMenuOpen"
    :aria-label="mobileMenuOpen ? '收起菜单' : '展开菜单'"
    :title="mobileMenuOpen ? '收起菜单' : '展开菜单'"
    @click="mobileMenuOpen = !mobileMenuOpen"
  >
    <i :class="mobileMenuOpen ? 'fa-solid fa-xmark' : 'fa-solid fa-bars'"></i>
  </button>

  <div
    ref="sidebarRef"
    class="nav-sidebar"
    :class="{ 'nav-sidebar--open': mobileMenuOpen }"
    @mouseleave="onSidebarLeave"
  >
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
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M575.8 255.5c0 18-15 32.1-32 32.1l-32 0 .7 160.2c0 2.7-.2 5.4-.5 8.1l0 16.2c0 22.1-17.9 40-40 40l-16 0c-1.1 0-2.2 0-3.3-.1c-1.4 .1-2.8 .1-4.2 .1L416 512l-24 0c-22.1 0-40-17.9-40-40l0-24 0-64c0-17.7-14.3-32-32-32l-64 0c-17.7 0-32 14.3-32 32l0 64 0 24c0 22.1-17.9 40-40 40l-24 0-31.9 0c-1.5 0-3-.1-4.5-.2c-1.2 .1-2.4 .2-3.6 .2l-16 0c-22.1 0-40-17.9-40-40l0-112c0-.9 0-1.9 .1-2.8l0-69.7-32 0c-18 0-32-14-32-32.1c0-9 3-17 10-24L266.4 8c7-7 15-8 22-8s15 2 21 7L564.8 231.5c8 7 12 15 11 24z"/></svg>
            </span>
            <span class="nav-text">主页</span>
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
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M192 0c-41.8 0-77.4 26.7-90.5 64L64 64C28.7 64 0 92.7 0 128L0 448c0 35.3 28.7 64 64 64l256 0c35.3 0 64-28.7 64-64l0-320c0-35.3-28.7-64-64-64l-37.5 0C269.4 26.7 233.8 0 192 0zm0 64a32 32 0 1 1 0 64 32 32 0 1 1 0-64zM72 272a24 24 0 1 1 48 0 24 24 0 1 1 -48 0zm104-16l128 0c8.8 0 16 7.2 16 16s-7.2 16-16 16l-128 0c-8.8 0-16-7.2-16-16s7.2-16 16-16zM72 368a24 24 0 1 1 48 0 24 24 0 1 1 -48 0zm88 0c0-8.8 7.2-16 16-16l128 0c8.8 0 16 7.2 16 16s-7.2 16-16 16l-128 0c-8.8 0-16-7.2-16-16z"/></svg>
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
            :class="{ 'active': isActive('/problems') }"
            href="/problems"
            @click.prevent="navigateTo('/problems')"
          >
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M96 0C43 0 0 43 0 96L0 416c0 53 43 96 96 96l288 0 32 0c17.7 0 32-14.3 32-32s-14.3-32-32-32l0-64c17.7 0 32-14.3 32-32l0-320c0-17.7-14.3-32-32-32L384 0 96 0zm0 384l256 0 0 64L96 448c-17.7 0-32-14.3-32-32s14.3-32 32-32zm32-240c0-8.8 7.2-16 16-16l192 0c8.8 0 16 7.2 16 16s-7.2 16-16 16l-192 0c-8.8 0-16-7.2-16-16zm16 48l192 0c8.8 0 16 7.2 16 16s-7.2 16-16 16l-192 0c-8.8 0-16-7.2-16-16s7.2-16 16-16z"/></svg>
            </span>
            <span class="nav-text">题库</span>
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
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M304 240l0-223.4c0-9 7-16.6 16-16.6C443.7 0 544 100.3 544 224c0 9-7.6 16-16.6 16L304 240zM32 272C32 150.7 122.1 50.3 239 34.3c9.2-1.3 17 6.1 17 15.4L256 288 412.5 444.5c6.7 6.7 6.2 17.7-1.5 23.1C371.8 495.6 323.8 512 272 512C139.5 512 32 404.6 32 272zm526.4 16c9.3 0 16.6 7.8 15.4 17c-7.7 55.9-34.6 105.6-73.9 142.3c-6 5.6-15.4 5.2-21.2-.7L320 288l238.4 0z"/></svg>
            </span>
            <span class="nav-text">评测记录</span>
          </a>
        </li>
      </ul>
    </div>


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
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M208 352c114.9 0 208-78.8 208-176S322.9 0 208 0S0 78.8 0 176c0 38.6 14.7 74.3 39.6 103.4c-3.5 9.4-8.7 17.7-14.2 24.7c-4.8 6.2-9.7 11-13.3 14.3c-1.8 1.6-3.3 2.9-4.3 3.7c-.5 .4-.9 .7-1.1 .8l-.2 .2s0 0 0 0s0 0 0 0C1 327.2-1.4 334.4 .8 340.9S9.1 352 16 352c21.8 0 43.8-5.6 62.1-12.5c9.2-3.5 17.8-7.4 25.2-11.4C134.1 343.3 169.8 352 208 352zM448 176c0 112.3-99.1 196.9-216.5 207C255.8 457.4 336.4 512 432 512c38.2 0 73.9-8.7 104.7-23.9c7.5 4 16 7.9 25.2 11.4c18.3 6.9 40.3 12.5 62.1 12.5c6.9 0 13.1-4.5 15.2-11.1c2.1-6.6-.2-13.8-5.8-17.9c0 0 0 0 0 0s0 0 0 0l-.2-.2c-.2-.2-.6-.4-1.1-.8c-1-.8-2.5-2-4.3-3.7c-3.6-3.3-8.5-8.1-13.3-14.3c-5.5-7-10.7-15.4-14.2-24.7c24.9-29 39.6-64.7 39.6-103.4c0-92.8-84.9-168.9-192.6-175.5c.4 5.1 .6 10.3 .6 15.5z"/></svg>
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
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M96 96c0-35.3 28.7-64 64-64l288 0c35.3 0 64 28.7 64 64l0 320c0 35.3-28.7 64-64 64L80 480c-44.2 0-80-35.8-80-80L0 128c0-17.7 14.3-32 32-32s32 14.3 32 32l0 272c0 8.8 7.2 16 16 16s16-7.2 16-16L96 96zm64 24l0 80c0 13.3 10.7 24 24 24l112 0c13.3 0 24-10.7 24-24l0-80c0-13.3-10.7-24-24-24L184 96c-13.3 0-24 10.7-24 24zm208-8c0 8.8 7.2 16 16 16l48 0c8.8 0 16-7.2 16-16s-7.2-16-16-16l-48 0c-8.8 0-16 7.2-16 16zm0 96c0 8.8 7.2 16 16 16l48 0c8.8 0 16-7.2 16-16s-7.2-16-16-16l-48 0c-8.8 0-16 7.2-16 16zM160 304c0 8.8 7.2 16 16 16l256 0c8.8 0 16-7.2 16-16s-7.2-16-16-16l-256 0c-8.8 0-16 7.2-16 16zm0 96c0 8.8 7.2 16 16 16l256 0c8.8 0 16-7.2 16-16s-7.2-16-16-16l-256 0c-8.8 0-16 7.2-16 16z"/></svg>
            </span>
            <span class="nav-text">文章广场</span>
          </a>
        </li>
        <li v-if="authStore.isAuthenticated">
          <a
            class="nav-item"
            :class="{ 'active': isActive('/teams') }"
            href="/teams"
            @click.prevent="navigateTo('/teams')"
          >
            <span class="nav-icon">
              <svg viewBox="0 0 640 512" width="20" height="20" fill="currentColor">
                <path d="M96 224a72 72 0 1 0 0-144 72 72 0 1 0 0 144zM32 416l0-16c0-53 43-96 96-96 28 0 53.3 12.1 70.8 31.3C165.4 375.6 144 427.5 144 485.5l0 26.5-96 0c-35.3 0-64-28.7-64-64l0-16c0-5.4 .7-10.7 2-15.7l46-1zM320 224a104 104 0 1 0 0-208 104 104 0 1 0 0 208zm0 32c-88.4 0-160 71.6-160 160l0 32c0 17.7 14.3 32 32 32l256 0c17.7 0 32-14.3 32-32l0-32c0-88.4-71.6-160-160-160zM612.5 400.5c-6.4-2.5-9.5-9.4-6.8-15.7 3.7-8.6 5.9-17.9 6.4-27.6 .3-6.9-4.6-13-11.5-13.7-11.4-1.2-22.5-4.4-32.6-9.3-5.5-2.7-12.2-.6-15 4.8-10.6 20.4-31.6 34.4-56.1 34.4-7.2 0-13.9-2.5-19.2-6.6-5.6-4.3-13.8-3.1-17.8 3-6.5 10-11.4 21.3-14.3 33.3-1.6 6.6 2.6 13.2 9.3 14.3 26.5 4.5 46.6 27.6 46.6 55.4 0 1.4 0 2.8-.1 4.2-0.5 6.8 5.1 12.5 11.9 12 5.4-.4 10.8-.4 16.2 0 6.8 .5 12.4-5.2 11.9-12-.1-1.4-.1-2.8-.1-4.2 0-24.2 15.4-44.8 36.9-52.6 5.6-2 8.9-7.9 7.4-13.6l27 .0z" />
              </svg>
            </span>
            <span class="nav-text">团队</span>
          </a>
        </li>
      </ul>
    </div>


    <!-- 更多功能（桌面端收缩时隐藏，展开后显示） -->
    <div class="nav-group nav-group--extra">
      <span class="group-title">
        <span class="nav-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><!--! Font Awesome Pro 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license (Commercial License) Copyright 2024 Fonticons, Inc. --><path d="M176 88l0 40 160 0 0-40c0-4.4-3.6-8-8-8L184 80c-4.4 0-8 3.6-8 8zm-48 40l0-40c0-30.9 25.1-56 56-56l144 0c30.9 0 56 25.1 56 56l0 40 28.1 0c12.7 0 24.9 5.1 33.9 14.1l51.9 51.9c9 9 14.1 21.2 14.1 33.9l0 92.1-128 0 0-32c0-17.7-14.3-32-32-32s-32 14.3-32 32l0 32-128 0 0-32c0-17.7-14.3-32-32-32s-32 14.3-32 32l0 32L0 320l0-92.1c0-12.7 5.1-24.9 14.1-33.9l51.9-51.9c9-9 21.2-14.1 33.9-14.1l28.1 0zM0 416l0-64 128 0c0 17.7 14.3 32 32 32s32-14.3 32-32l128 0c0 17.7 14.3 32 32 32s32-14.3 32-32l128 0 0 64c0 35.3-28.7 64-64 64L64 480c-35.3 0-64-28.7-64-64z"/></svg>
        </span>
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
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M144 480C64.5 480 0 415.5 0 336c0-62.8 40.2-116.2 96.2-135.9c-.1-2.7-.2-5.4-.2-8.1c0-88.4 71.6-160 160-160c59.3 0 111 32.2 138.7 80.2C409.9 102 428.3 96 448 96c53 0 96 43 96 96c0 12.2-2.3 23.8-6.4 34.6C596 238.4 640 290.1 640 352c0 70.7-57.3 128-128 128l-368 0zm79-217c-9.4 9.4-9.4 24.6 0 33.9s24.6 9.4 33.9 0l39-39L296 392c0 13.3 10.7 24 24 24s24-10.7 24-24l0-134.1 39 39c9.4 9.4 24.6 9.4 33.9 0s9.4-24.6 0-33.9l-80-80c-9.4-9.4-24.6-9.4-33.9 0l-80 80z"/></svg>
            </span>
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
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M192 0c-41.8 0-77.4 26.7-90.5 64L64 64C28.7 64 0 92.7 0 128L0 448c0 35.3 28.7 64 64 64l256 0c35.3 0 64-28.7 64-64l0-320c0-35.3-28.7-64-64-64l-37.5 0C269.4 26.7 233.8 0 192 0zm0 64a32 32 0 1 1 0 64 32 32 0 1 1 0-64zM112 192l160 0c8.8 0 16 7.2 16 16s-7.2 16-16 16l-160 0c-8.8 0-16-7.2-16-16s7.2-16 16-16z"/></svg>
            </span>
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
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M162.4 6c-1.5-3.6-5-6-8.9-6l-19 0c-3.9 0-7.5 2.4-8.9 6L104.9 57.7c-3.2 8-14.6 8-17.8 0L66.4 6c-1.5-3.6-5-6-8.9-6L48 0C21.5 0 0 21.5 0 48L0 224l0 22.4L0 256l9.6 0 364.8 0 9.6 0 0-9.6 0-22.4 0-176c0-26.5-21.5-48-48-48L230.5 0c-3.9 0-7.5 2.4-8.9 6L200.9 57.7c-3.2 8-14.6 8-17.8 0L162.4 6zM0 288l0 32c0 35.3 28.7 64 64 64l64 0 0 64c0 35.3 28.7 64 64 64s64-28.7 64-64l0-64 64 0c35.3 0 64-28.7 64-64l0-32L0 288zM192 432a16 16 0 1 1 0 32 16 16 0 1 1 0-32z"/></svg>
            </span>
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
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M32 0C49.7 0 64 14.3 64 32l0 16 69-17.2c38.1-9.5 78.3-5.1 113.5 12.5c46.3 23.2 100.8 23.2 147.1 0l9.6-4.8C423.8 28.1 448 43.1 448 66.1l0 279.7c0 13.3-8.3 25.3-20.8 30l-34.7 13c-46.2 17.3-97.6 14.6-141.7-7.4c-37.9-19-81.3-23.7-122.5-13.4L64 384l0 96c0 17.7-14.3 32-32 32s-32-14.3-32-32l0-80 0-66L0 64 0 32C0 14.3 14.3 0 32 0zM64 187.1l64-13.9 0 65.5L64 252.6 64 318l48.8-12.2c5.1-1.3 10.1-2.4 15.2-3.3l0-63.9 38.9-8.4c8.3-1.8 16.7-2.5 25.1-2.1l0-64c13.6 .4 27.2 2.6 40.4 6.4l23.6 6.9 0 66.7-41.7-12.3c-7.3-2.1-14.8-3.4-22.3-3.8l0 71.4c21.8 1.9 43.3 6.7 64 14.4l0-69.8 22.7 6.7c13.5 4 27.3 6.4 41.3 7.4l0-64.2c-7.8-.8-15.6-2.3-23.2-4.5l-40.8-12 0-62c-13-3.8-25.8-8.8-38.2-15c-8.2-4.1-16.9-7-25.8-8.8l0 72.4c-13-.4-26 .8-38.7 3.6L128 173.2 128 98 64 114l0 73.1zM320 335.7c16.8 1.5 33.9-.7 50-6.8l14-5.2 0-71.7-7.9 1.8c-18.4 4.3-37.3 5.7-56.1 4.5l0 77.4zm64-149.4l0-70.8c-20.9 6.1-42.4 9.1-64 9.1l0 69.4c13.9 1.4 28 .5 41.7-2.6l22.3-5.2z"/></svg>
            </span>
            <span class="nav-text">排行榜</span>
          </a>
        </li>
      </ul>
    </div>


    <!-- 相关链接（桌面端收缩时隐藏，展开后显示） -->
    <div class="nav-group nav-group--extra">
      <span class="group-title">
        <span class="nav-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512"><!--! Font Awesome Pro 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license (Commercial License) Copyright 2024 Fonticons, Inc. --><path d="M579.8 267.7c56.5-56.5 56.5-148 0-204.5c-50-50-128.8-56.5-186.3-15.4l-1.6 1.1c-14.4 10.3-17.7 30.3-7.4 44.6s30.3 17.7 44.6 7.4l1.6-1.1c32.1-22.9 76-19.3 103.8 8.6c31.5 31.5 31.5 82.5 0 114L422.3 334.8c-31.5 31.5-82.5 31.5-114 0c-27.9-27.9-31.5-71.8-8.6-103.8l1.1-1.6c10.3-14.4 6.9-34.4-7.4-44.6s-34.4-6.9-44.6 7.4l-1.1 1.6C206.5 251.2 213 330 263 380c56.5 56.5 148 56.5 204.5 0L579.8 267.7zM60.2 244.3c-56.5 56.5-56.5 148 0 204.5c50 50 128.8 56.5 186.3 15.4l1.6-1.1c14.4-10.3 17.7-30.3 7.4-44.6s-30.3-17.7-44.6-7.4l-1.6 1.1c-32.1 22.9-76 19.3-103.8-8.6C74 372 74 321 105.5 289.5L217.7 177.2c31.5-31.5 82.5-31.5 114 0c27.9 27.9 31.5 71.8 8.6 103.9l-1.1 1.6c-10.3 14.4-6.9 34.4 7.4 44.6s34.4 6.9 44.6-7.4l1.1-1.6C433.5 260.8 427 182 377 132c-56.5-56.5-148-56.5-204.5 0L60.2 244.3z"/></svg>
        </span>
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
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M256 512A256 256 0 1 0 256 0a256 256 0 1 0 0 512zM169.8 165.3c7.9-22.3 29.1-37.3 52.8-37.3l58.3 0c34.9 0 63.1 28.3 63.1 63.1c0 22.6-12.1 43.5-31.7 54.8L280 264.4c-.2 13-10.9 23.6-24 23.6c-13.3 0-24-10.7-24-24l0-13.5c0-8.6 4.6-16.5 12.1-20.8l44.3-25.4c4.7-2.7 7.6-7.7 7.6-13.1c0-8.4-6.8-15.1-15.1-15.1l-58.3 0c-3.4 0-6.4 2.1-7.5 5.3l-.4 1.2c-4.4 12.5-18.2 19-30.6 14.6s-19-18.2-14.6-30.6l.4-1.2zM224 352a32 32 0 1 1 64 0 32 32 0 1 1 -64 0z"/></svg>
            </span>
            <span class="nav-text">帮助中心</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            href="https://www.luogu.com.cn/team/136441"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M48 64C21.5 64 0 85.5 0 112c0 15.1 7.1 29.3 19.2 38.4L236.8 313.6c11.4 8.5 27 8.5 38.4 0L492.8 150.4c12.1-9.1 19.2-23.3 19.2-38.4c0-26.5-21.5-48-48-48L48 64zM0 176L0 384c0 35.3 28.7 64 64 64l384 0c35.3 0 64-28.7 64-64l0-208L294.4 339.2c-22.8 17.1-54 17.1-76.8 0L0 176z"/></svg>
            </span>
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
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M0 80l0 48c0 17.7 14.3 32 32 32l16 0 48 0 0-80c0-26.5-21.5-48-48-48S0 53.5 0 80zM112 32c10 13.4 16 30 16 48l0 304c0 35.3 28.7 64 64 64s64-28.7 64-64l0-5.3c0-32.4 26.3-58.7 58.7-58.7L480 320l0-192c0-53-43-96-96-96L112 32zM464 480c61.9 0 112-50.1 112-112c0-8.8-7.2-16-16-16l-245.3 0c-14.7 0-26.7 11.9-26.7 26.7l0 5.3c0 53-43 96-96 96l176 0 96 0z"/></svg>
            </span>
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
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M384 32l128 0c17.7 0 32 14.3 32 32s-14.3 32-32 32L398.4 96c-5.2 25.8-22.9 47.1-46.4 57.3L352 448l160 0c17.7 0 32 14.3 32 32s-14.3 32-32 32l-192 0-192 0c-17.7 0-32-14.3-32-32s14.3-32 32-32l160 0 0-294.7c-23.5-10.3-41.2-31.6-46.4-57.3L128 96c-17.7 0-32-14.3-32-32s14.3-32 32-32l128 0c14.6-19.4 37.8-32 64-32s49.4 12.6 64 32zm55.6 288l144.9 0L512 195.8 439.6 320zM512 416c-62.9 0-115.2-34-126-78.9c-2.6-11 1-22.3 6.7-32.1l95.2-163.2c5-8.6 14.2-13.8 24.1-13.8s19.1 5.3 24.1 13.8l95.2 163.2c5.7 9.8 9.3 21.1 6.7 32.1C627.2 382 574.9 416 512 416zM126.8 195.8L54.4 320l144.9 0L126.8 195.8zM.9 337.1c-2.6-11 1-22.3 6.7-32.1l95.2-163.2c5-8.6 14.2-13.8 24.1-13.8s19.1 5.3 24.1 13.8l95.2 163.2c5.7 9.8 9.3 21.1 6.7 32.1C242 382 189.7 416 126.8 416S11.7 382 .9 337.1z"/></svg>
            </span>
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
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 576 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M64 64C28.7 64 0 92.7 0 128l0 64c0 8.8 7.4 15.7 15.7 18.6C34.5 217.1 48 235 48 256s-13.5 38.9-32.3 45.4C7.4 304.3 0 311.2 0 320l0 64c0 35.3 28.7 64 64 64l448 0c35.3 0 64-28.7 64-64l0-64c0-8.8-7.4-15.7-15.7-18.6C541.5 294.9 528 277 528 256s13.5-38.9 32.3-45.4c8.3-2.9 15.7-9.8 15.7-18.6l0-64c0-35.3-28.7-64-64-64L64 64zm64 112l0 160c0 8.8 7.2 16 16 16l288 0c8.8 0 16-7.2 16-16l0-160c0-8.8-7.2-16-16-16l-288 0c-8.8 0-16 7.2-16 16zM96 160c0-17.7 14.3-32 32-32l320 0c17.7 0 32 14.3 32 32l0 192c0 17.7-14.3 32-32 32l-320 0c-17.7 0-32-14.3-32-32l0-192z"/></svg>
            </span>
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
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M75 75L41 41C25.9 25.9 0 36.6 0 57.9L0 168c0 13.3 10.7 24 24 24l110.1 0c21.4 0 32.1-25.9 17-41l-30.8-30.8C155 85.5 203 64 256 64c106 0 192 86 192 192s-86 192-192 192c-40.8 0-78.6-12.7-109.7-34.4c-14.5-10.1-34.4-6.6-44.6 7.9s-6.6 34.4 7.9 44.6C151.2 495 201.7 512 256 512c141.4 0 256-114.6 256-256S397.4 0 256 0C185.3 0 121.3 28.7 75 75zm181 53c-13.3 0-24 10.7-24 24l0 104c0 6.4 2.5 12.5 7 17l72 72c9.4 9.4 24.6 9.4 33.9 0s9.4-24.6 0-33.9l-65-65 0-94.1c0-13.3-10.7-24-24-24z"/></svg>
            </span>
            <span class="nav-text">管理日志</span>
          </a>
        </li>
        <li v-if="authStore.currentUser && (authStore.currentUser.is_super_admin || authStore.currentUser.is_admin || authStore.currentUser.can_manage_users)">
          <a
            class="nav-item"
            :class="{ 'active': isActive('/admin/user') }"
            href="/admin/user"
            @click.prevent="navigateTo('/admin/user')"
          >
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M144 0a80 80 0 1 1 0 160A80 80 0 1 1 144 0zM512 0a80 80 0 1 1 0 160A80 80 0 1 1 512 0zM0 298.7C0 239.8 47.8 192 106.7 192l42.7 0c15.9 0 31 3.5 44.6 9.7c-1.3 7.2-1.9 14.7-1.9 22.3c0 38.2 16.8 72.5 43.3 96c-.2 0-.4 0-.7 0L21.3 320C9.6 320 0 310.4 0 298.7zM405.3 320c-.2 0-.4 0-.7 0c26.6-23.5 43.3-57.8 43.3-96c0-7.6-.7-15-1.9-22.3c13.6-6.3 28.7-9.7 44.6-9.7l42.7 0C592.2 192 640 239.8 640 298.7c0 11.8-9.6 21.3-21.3 21.3l-213.3 0zM224 224a96 96 0 1 1 192 0 96 96 0 1 1 -192 0zM128 485.3C128 411.7 187.7 352 261.3 352l117.3 0C452.3 352 512 411.7 512 485.3c0 14.7-11.9 26.7-26.7 26.7l-330.7 0c-14.7 0-26.7-11.9-26.7-26.7z"/></svg>
            </span>
            <span class="nav-text">用户管理</span>
          </a>
        </li>
        <li>
          <a
            class="nav-item"
            href="https://www.luogu.com.cn/team/136441"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span class="nav-icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><!--! Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2024 Fonticons, Inc. --><path d="M256 512A256 256 0 1 0 256 0a256 256 0 1 0 0 512zM216 336l24 0 0-64-24 0c-13.3 0-24-10.7-24-24s10.7-24 24-24l48 0c13.3 0 24 10.7 24 24l0 88 8 0c13.3 0 24 10.7 24 24s-10.7 24-24 24l-80 0c-13.3 0-24-10.7-24-24s10.7-24 24-24zm40-208a32 32 0 1 1 0 64 32 32 0 1 1 0-64z"/></svg>
            </span>
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

.group-title {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #9ca3af;
  cursor: default;
  white-space: nowrap;
}

/* 桌面端收缩态（未 hover）：只保留「更多功能」以上的按钮，
   「更多功能」「相关链接」整组隐藏，展开后才出现 */
@media (min-width: 769px) {
  .nav-sidebar:not(:hover) .nav-group--extra {
    display: none;
  }
}

/* 展开态：图标隐藏，文字 + 细线显示 */
.nav-sidebar:hover .group-title .nav-icon {
  display: none;
}

.nav-sidebar:hover .group-title .nav-text {
  display: block;
}

/* 展开态：文字两侧加细线 */
@media (min-width: 769px) {
  .nav-sidebar:hover .group-title {
    gap: 8px;
  }
  .nav-sidebar:hover .group-title::before,
  .nav-sidebar:hover .group-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #e5e7eb;
  }
}

/* 左右两条细线 */
.group-title::before,
.group-title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e5e7eb;
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
  color: var(--primary);
  text-decoration: none;
}

.nav-item.active {
  background: #f0f2f5;
  color: var(--primary);
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

/* ===== 移动端菜单开关按钮（桌面端不显示） ===== */
.mobile-menu-toggle {
  display: none;
}

/* 响应式适配 */
@media (max-width: 768px) {
  /* 右下角圆形悬浮按钮（无文字，仅图标）；脱离文档流，展开/收起时始终可点 */
  .mobile-menu-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    position: fixed;
    right: 20px;
    /* 叠加 iOS 底部安全区，避免被 Home Indicator 压住 */
    bottom: calc(20px + env(safe-area-inset-bottom, 0px));
    z-index: 410;
    width: 52px;
    height: 52px;
    padding: 0;
    background: var(--primary);
    border: none;
    border-radius: 50%;
    color: #fff;
    font-size: 19px;
    line-height: 1;
    cursor: pointer;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.24);
    transition: transform 0.18s, box-shadow 0.18s;
    -webkit-tap-highlight-color: transparent;
  }

  .mobile-menu-toggle:hover {
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.3);
  }

  .mobile-menu-toggle:active {
    transform: scale(0.92);
  }

  /* 全屏悬浮菜单：脱离文档流浮在整页之上（不再把正文挤下去），
     默认淡出+上移收起，展开时平滑滑入 */
  .nav-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100%;
    height: 100%;
    padding: 24px 0 88px;      /* 底部留出右下角悬浮按钮的位置，避免遮挡最后一项 */
    background: #fff;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
    border-bottom: none;
    overflow-y: auto;
    overscroll-behavior: contain;
    z-index: 400;
    opacity: 0;
    visibility: hidden;
    transform: translateY(-10px);
    transition: opacity 0.28s ease, transform 0.28s ease, visibility 0.28s ease;
  }

  .nav-sidebar.nav-sidebar--open {
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
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

  .group-title .nav-text {
    display: block;   /* 移动端显示文字 */
  }
  .group-title .nav-icon {
    display: none;    /* 移动端不需要图标占位 */
  }
}

@media (max-width: 600px) {
  .nav-group ul {
    grid-template-columns: repeat(3, 1fr);
  }

  /* 窄屏把悬浮按钮略微收小 */
  .mobile-menu-toggle {
    right: 16px;
    bottom: calc(16px + env(safe-area-inset-bottom, 0px));
    width: 48px;
    height: 48px;
    font-size: 17px;
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
