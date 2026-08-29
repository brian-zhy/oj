<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 默认封面（与原站一致的图片）
const DEFAULT_COVER = 'https://cdn.luogu.org/images/bg/fe/DSCF0530-shrink.jpg'
const LAZY_TEXT = '这个家伙很懒，什么也没有留下'

// ==================== 用户数据 ====================
const profile = ref<any>(null)
const loading = ref(true)
const error = ref('')

// ==================== 工具 ====================
const COLOR_RED = '#e74c3c'
const COLOR_PURPLE = '#9C3DCF'
const COLOR_BROWN = '#AD8B00'

const getUserDisplayColor = (user: any) => {
  if (!user) return COLOR_RED
  if (user.is_cheater) return COLOR_BROWN
  if (user.is_admin) return COLOR_PURPLE
  return COLOR_RED
}

const getUserTagDisplay = (user: any) => {
  if (!user) return ''
  if (user.is_cheater) {
    return user.is_admin ? (user.user_tag || '管理员') : '作弊者'
  }
  return user.user_tag || ''
}

const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

// 注册时间显示（取日期部分）
const formatRegDate = (dateStr: string) => {
  if (!dateStr) return ''
  return String(dateStr).split('T')[0]
}

// ==================== 计算属性 ====================
const currentUser = computed(() => authStore.currentUser)
// 封面URL（当前后端暂无封面字段，固定使用默认封面）
const coverUrl = ref('')
const isOwner = computed(() =>
  !!currentUser.value && !!profile.value && currentUser.value.id === profile.value.id
)
const displayName = computed(() => profile.value?.username || '用户')
const avatarDisplay = computed(() => profile.value?.avatar_url || letterAvatar(displayName.value))
const color = computed(() => getUserDisplayColor(profile.value))
const tagText = computed(() => getUserTagDisplay(profile.value))
const coverStyle = computed(() => ({ backgroundImage: `url('${coverUrl.value || DEFAULT_COVER}')` }))

// 用户类型文本
const userTypeText = computed(() => {
  const u = profile.value
  if (!u) return ''
  return u.is_admin ? '管理员' : u.is_cheater ? '作弊者' : '普通用户'
})

// 是否处于封禁状态
const isBanned = computed(() => profile.value?.is_banned === true)

// ==================== 选项卡 ====================
const TABS = ['主页', '动态', '专栏', '练习', '关注', '我的', '题库', '收藏']
const activeTab = ref('主页')
const switchTab = (tab: string) => {
  activeTab.value = tab
}

// ==================== 签名编辑 ====================
const sloganEditing = ref(false)
const sloganValue = ref('')
const sloganInputRef = ref<HTMLInputElement | null>(null)

const startEditSlogan = () => {
  if (!isOwner.value || isBanned.value) return
  sloganValue.value = profile.value.bio || ''
  sloganEditing.value = true
  nextTick(() => {
    sloganInputRef.value?.focus()
    sloganInputRef.value?.select()
  })
}

const finishEditSlogan = async (cancel = false) => {
  if (!sloganEditing.value) return
  sloganEditing.value = false
  if (cancel) return

  const val = sloganValue.value.trim()
  const original = profile.value.bio || ''
  // 无变化则不请求
  if (val === original) return

  try {
    await apiClient.put('/users/me/profile', { bio: val })
    profile.value.bio = val
  } catch (err: any) {
    alert('保存失败：' + (err.response?.data?.detail || err.message || '未知错误'))
  }
}

const onSloganKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter') {
    e.preventDefault()
    ;(e.target as HTMLInputElement).blur()
  }
  if (e.key === 'Escape') {
    e.preventDefault()
    finishEditSlogan(true)
  }
}

// ==================== 关注按钮 ====================
// 关注功能暂无后端支持
const isFollowing = ref(false)

const handleFollowButton = () => {
  if (!authStore.isAuthenticated) {
    router.push('/login')
    return
  }
  alert('关注功能暂未开放')
}

// ==================== 封面更换 ====================
const showCoverOverlay = ref(false)
const selectedFile = ref<File | null>(null)
const uploadFeedback = ref('')
const uploadFeedbackColor = ref('#999')
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const openCoverUpload = () => {
  showCoverOverlay.value = true
  selectedFile.value = null
  uploadFeedback.value = ''
  if (fileInputRef.value) fileInputRef.value.value = ''
}

const closeCoverUpload = () => {
  showCoverOverlay.value = false
  selectedFile.value = null
  uploadFeedback.value = ''
}

const pickFile = () => {
  fileInputRef.value?.click()
}

const onDragOver = (e: DragEvent) => {
  ;(e.currentTarget as HTMLElement).style.borderColor = '#e74c3c'
}

const onDragLeave = (e: DragEvent) => {
  ;(e.currentTarget as HTMLElement).style.borderColor = '#ddd'
}

const onDropEvent = (e: DragEvent) => {
  ;(e.currentTarget as HTMLElement).style.borderColor = '#ddd'
  onDrop(e)
}

const setFile = (file: File) => {
  if (file.type.startsWith('image/')) {
    selectedFile.value = file
    uploadFeedback.value = `✅ 已选择: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`
    uploadFeedbackColor.value = '#27ae60'
  } else {
    selectedFile.value = null
    uploadFeedback.value = '❌ 请选择图片文件'
    uploadFeedbackColor.value = '#e74c3c'
  }
}

const onFileChange = (e: Event) => {
  const files = (e.target as HTMLInputElement).files
  if (files && files.length) setFile(files[0])
}

const onDrop = (e: DragEvent) => {
  if (e.dataTransfer && e.dataTransfer.files.length) {
    setFile(e.dataTransfer.files[0])
  }
}

const uploadCover = async () => {
  if (!selectedFile.value) return
  uploading.value = true
  const previousCover = coverUrl.value || ''
  let success = false

  try {
    const fd = new FormData()
    fd.append('file', selectedFile.value)
    // 加时间戳参数绕开浏览器缓存的跳转劫持
    const res: any = await apiClient.post(`/users/me/cover?_t=${Date.now()}`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    coverUrl.value = res.cover_url
    success = true
  } catch (err: any) {
    // 请求报错时向服务端核实真实结果——请求可能被代理/插件改写，但实际已成功
    try {
      const me: any = await apiClient.get(`/users/number/${route.params.id}?_t=${Date.now()}`)
      if (me?.cover_url && me.cover_url !== previousCover) {
        coverUrl.value = me.cover_url
        success = true
      }
    } catch {
      /* 核实也失败则维持失败判定 */
    }
    if (!success) {
      uploading.value = false
      uploadFeedback.value = '❌ ' + (err.response?.data?.detail || '上传失败，请稍后重试')
      uploadFeedbackColor.value = '#e74c3c'
      return
    }
  }

  uploading.value = false
  uploadFeedback.value = '✅ 封面更新成功！'
  uploadFeedbackColor.value = '#27ae60'
  setTimeout(closeCoverUpload, 1200)
}

// ==================== 加载用户信息 ====================
const loadUserProfile = async () => {
  loading.value = true
  error.value = ''

  try {
    // 与原站语义一致：URL 中的数字为用户编号（user_number）
    const data: any = await apiClient.get(`/users/number/${route.params.id}`)
    profile.value = data
    coverUrl.value = data.cover_url || ''
    document.title = `${data.username} 的个人主页 - Jason227`
  } catch (err: any) {
    console.error('加载用户信息失败:', err)
    error.value = err.response?.status === 404 ? '用户不存在' : '加载失败: ' + (err.message || '未知错误')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadUserProfile()
})
</script>

<template>
  <div class="user-page">
    <div class="user-container">
      <!-- 加载中 -->
      <div v-if="loading" class="loading-box">加载中...</div>

      <!-- 出错 -->
      <div v-else-if="error" class="loading-box error-text">❌ {{ error }}</div>

      <template v-else-if="profile">
        <!-- ===== 封禁视图 ===== -->
        <div v-if="isBanned" class="user-header banned-header">
          <div class="user-header-bg" :style="coverStyle"></div>
          <div class="user-header-content" style="justify-content:center;text-align:center;">
            <div style="color:#fff;text-shadow:0 2px 12px rgba(0,0,0,0.6);">
              <div style="font-size:48px;margin-bottom:8px;">⛔</div>
              <h1 style="font-size:1.75rem;margin:0;">该用户已被封禁</h1>
            </div>
          </div>
        </div>

        <!-- ===== 正常视图 ===== -->
        <template v-else>
          <!-- 用户头部（封面） -->
          <div class="user-header">
            <div class="user-header-bg" :style="coverStyle"></div>

            <!-- 右上角更换封面按钮（仅本人） -->
            <span v-if="isOwner" class="btn-action-cover" title="更换封面" @click.stop.prevent="openCoverUpload">
              <svg viewBox="0 0 384 512" width="16" height="16">
                <path d="M162.4 6c-1.5-3.6-5-6-8.9-6l-19 0c-3.9 0-7.5 2.4-8.9 6L104.9 57.7c-3.2 8-14.6 8-17.8 0L66.4 6c-1.5-3.6-5-6-8.9-6L48 0C21.5 0 0 21.5 0 48l0 208 384 0 0-208c0-26.5-21.5-48-48-48L230.5 0c-3.9 0-7.5 2.4-8.9 6L200.9 57.7c-3.2 8-14.6 8-17.8 0L162.4 6zM0 304l0 16c0 35.3 28.7 64 64 64l64 0 0 64c0 35.3 28.7 64 64 64s64-28.7 64-64l0-64 64 0c35.3 0 64-28.7 64-64l0-16-384 0zM192 464c-8.8 0-16-7.2-16-16s7.2-16 16-16 16 7.2 16 16-7.2 16-16 16z"/>
              </svg>
            </span>

            <div class="user-header-content">
              <div class="user-header-avatar">
                <img
                  :src="avatarDisplay"
                  :alt="displayName"
                  @error="($event.target as HTMLImageElement).src = letterAvatar(displayName)"
                >
              </div>

              <div class="user-header-info">
                <div class="user-header-name">
                  <h1 :style="{ color }">{{ displayName }}</h1>
                  <span
                    v-if="tagText"
                    class="user-tag-display"
                    :style="{ backgroundColor: color }"
                  >{{ tagText }}</span>
                </div>

                <div class="header-row">
                  <div class="follow-stats">
                    <span>关注 <span class="num">0</span></span>
                    <span>粉丝 <span class="num">0</span></span>
                  </div>
                  <!-- 关注按钮（非本人显示） -->
                  <a
                    v-if="!isOwner && !authStore.isAuthenticated"
                    href="/login"
                    class="follow-btn following"
                    style="background:#7f8c8d;text-decoration:none;display:inline-block;"
                    @click.prevent="handleFollowButton"
                  >登录后关注</a>
                  <button
                    v-else-if="!isOwner"
                    class="follow-btn"
                    :class="{ following: isFollowing }"
                    @click="handleFollowButton"
                  >{{ isFollowing ? '取消关注' : '关注' }}</button>
                </div>

                <div class="header-row slogan-row">
                  <template v-if="sloganEditing">
                    <input
                      ref="sloganInputRef"
                      v-model="sloganValue"
                      class="slogan-editor-input"
                      :placeholder="LAZY_TEXT"
                      maxlength="500"
                      @blur="finishEditSlogan()"
                      @keydown="onSloganKeydown"
                    >
                  </template>
                  <template v-else>
                    <div
                      class="user-header-slogan"
                      :class="{ empty: !profile.bio }"
                      :data-editable="isOwner ? 'true' : 'false'"
                      @dblclick="startEditSlogan"
                    >{{ profile.bio?.trim() || LAZY_TEXT }}</div>
                  </template>

                  <!-- 个人设置按钮（仅本人） -->
                  <router-link v-if="isOwner" to="/profile" class="btn-luogu-setting">
                    <svg viewBox="0 0 640 512" width="16" height="16" fill="currentColor">
                      <path d="M256.5 8a120 120 0 1 1 0 240 120 120 0 1 1 0-240zM226.7 304l59.4 0 1.5 0c-12.9 26.8-7.8 58.2 11.5 79.5-20.2 22.3-24.8 55.8-9.4 83.4l22.5 40.4c.9 1.6 1.9 3.2 2.9 4.7l-237 0c-16.4 0-29.7-13.3-29.7-29.7 0-98.5 79.8-178.3 178.3-178.3zm205.9-56.4c0-13.3 10.7-24 24-24l48 0c13.3 0 24 10.7 24 24l0 6.1c0 18.9 24.1 32.8 40.5 23.4l5-2.9c11.6-6.7 26.5-2.6 33 9.1l22.4 40.2c6.2 11.2 2.6 25.2-8.2 32l-4.7 2.9c-16.2 10.1-16.2 39.9 0 50.1l4.6 2.9c10.8 6.8 14.5 20.8 8.3 32L607 483.8c-6.5 11.7-21.4 15.9-33 9.1l-4.9-2.9c-16.4-9.5-40.5 4.5-40.5 23.4l0 6.1c0 13.3-10.7 24-24 24l-48 0c-13.3 0-24-10.7-24-24l0-5.9c0-19-24.2-33-40.7-23.5l-4.8 2.8c-11.6 6.7-26.4 2.6-33-9.1l-22.6-40.4c-6.2-11.2-2.6-25.3 8.3-32.1l4.4-2.7c16.3-10.1 16.3-40.1 0-50.2l-4.5-2.8c-10.9-6.8-14.5-20.9-8.3-32.1l22.5-40.3c6.5-11.7 21.4-15.8 32.9-9.1l4.8 2.8c16.5 9.5 40.7-4.5 40.7-23.5l0-5.9zm99.9 136.2a52 52 0 1 0 -104 0 52 52 0 1 0 104 0z"/>
                    </svg>
                    个人设置
                  </router-link>
                </div>
              </div>
            </div>
          </div>

          <!-- ===== 选项卡导航 ===== -->
          <div class="new-card">
            <div class="profile-tabs">
              <nav class="tab-nav">
                <button
                  v-for="tab in TABS"
                  :key="tab"
                  class="tab-btn"
                  :class="{ active: activeTab === tab }"
                  @click="switchTab(tab)"
                >{{ tab }}</button>
              </nav>
            </div>
          </div>

          <!-- ===== 信息卡片 ===== -->
          <div class="l-card">
            <div class="l-flex-info-row">
              <span>用户编号</span>
              <div class="right">{{ profile.user_number }}</div>
            </div>
            <div class="l-flex-info-row">
              <span>用户类型</span>
              <div class="right">{{ userTypeText }}</div>
            </div>
            <div class="l-flex-info-row">
              <span>注册时间</span>
              <div class="right"><time :datetime="profile.created_at">{{ formatRegDate(profile.created_at) }}</time></div>
            </div>
          </div>
        </template>
      </template>
    </div>

    <!-- ===== 封面更换浮层 ===== -->
    <div v-show="showCoverOverlay" class="cover-upload-overlay active" @click.self="closeCoverUpload">
      <div class="cover-upload-panel">
        <h2>🖼️ 更换封面</h2>
        <div
          class="upload-area"
          @click="pickFile"
          @dragover.prevent="onDragOver"
          @dragleave="onDragLeave"
          @drop.prevent="onDropEvent"
        >
          <input ref="fileInputRef" type="file" accept="image/*" style="display:none;" @change="onFileChange">
          <div class="hint">点击选择图片，或拖拽到此处<br><strong>建议尺寸 1800×600px</strong></div>
        </div>
        <div class="lfe-caption">
          ⚠️ 为了文字可读性，请勿使用浅色背景图。
        </div>
        <div class="panel-actions">
          <button class="btn-cancel-cover" @click="closeCoverUpload">取消</button>
          <button class="btn-upload-cover" :disabled="!selectedFile || uploading" @click="uploadCover">
            {{ uploading ? '⏳ 上传中…' : '上传' }}
          </button>
        </div>
        <div class="cover-feedback">{{ uploadFeedback }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ===== 页面容器 ===== */
.user-page {
  min-height: 100vh;
  line-height: 1.5;
}

.user-container {
  max-width: 1400px;
  margin: 0 auto;
}

.loading-box {
  text-align: center;
  padding: 40px;
  color: #999;
  font-size: 16px;
}

.error-text {
  color: #e74c3c;
}

/* ===== 用户头部（封面）===== */
.user-header {
  position: relative;
  border-radius: 16px 16px 0 0;
  overflow: hidden;
  margin-bottom: 0;
  background: #1a1a2e;
  min-height: 250px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.banned-header {
  min-height: 160px;
}

.user-header-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  transition: opacity 0.3s;
}

.user-header-content {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  padding: 20px 32px 24px;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
}

.user-header-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  border: none;
  box-shadow: none;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-header-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.user-header-info {
  flex: 1;
  min-width: 200px;
  color: #fff;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.user-header-name {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.user-header-name h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0;
  letter-spacing: 0.5px;
}

.header-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.slogan-row {
  margin-top: 6px;
}

.follow-stats {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #fff;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.follow-stats span {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
}

.follow-stats .num {
  font-weight: 700;
  font-size: 1.1em;
}

.follow-btn {
  padding: 4px 18px;
  border-radius: 30px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.25s;
  background: #e74c3c;
  color: #fff;
  font-family: inherit;
}

.follow-btn.following {
  background: #7f8c8d;
}

.follow-btn:not(:disabled):hover {
  transform: scale(1.04);
}

/* ===== 右上角更换封面按钮 ===== */
.btn-action-cover {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 10;
  color: #404040;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.25s;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.55);
}

.btn-action-cover svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}

.btn-action-cover:hover {
  color: #fff;
  background: rgba(0, 0, 0, 0.45);
}

/* ===== 个人设置按钮 ===== */
.btn-luogu-setting {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 15px;
  border-radius: 5px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  font-size: 0.875em;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.25s, transform 0.2s, border-color 0.25s, box-shadow 0.25s;
  user-select: none;
  font-family: inherit;
  line-height: 1.5;
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: auto;
}

.btn-luogu-setting:hover {
  background: rgba(255, 255, 255, 0.18);
  border-color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
}

.btn-luogu-setting:active {
  transform: scale(0.96) translateY(0);
  background: rgba(255, 255, 255, 0.12);
}

/* ===== 签名 ===== */
.user-header-slogan {
  font-size: 1.1rem;
  opacity: 0.92;
  max-width: 600px;
  word-break: break-word;
  white-space: pre-wrap;
  line-height: 1.6;
  min-height: 28px;
  margin-top: -2px;
  padding: 0 0 2px 0;
  border-radius: 0;
  display: block;
  transition: background 0.2s, color 0.3s;
  color: #fff;
  font-style: normal;
  text-align: left;
}

.user-header-slogan[data-editable='true'] {
  cursor: pointer;
}

.slogan-editor-input {
  border: 1px solid #e74c3c;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 16px;
  width: 100%;
  max-width: 500px;
  min-width: 100px;
  outline: none;
  background: #fff;
  color: #2c3e50;
  font-family: inherit;
  box-sizing: border-box;
}

.slogan-editor-input:focus {
  border-color: #e74c3c;
  box-shadow: 0 0 0 2px rgba(231, 76, 60, 0.2);
}

/* ===== 选项卡导航卡片 ===== */
.new-card {
  border-radius: 0 0 16px 16px;
  margin-bottom: 24px;
  padding: 0 30px 0 40px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  height: 60px;
  display: flex;
  align-items: stretch;
}

.profile-tabs {
  width: 100%;
}

.tab-nav {
  display: flex;
  gap: 32px;
  height: 100%;
  align-items: stretch;
  width: 100%;
}

.tab-nav .tab-btn {
  position: relative;
  background: none;
  border: none;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  color: #404040;
  padding: 0;
  text-decoration: none;
  transition: color 0.25s;
  font-family: inherit;
  line-height: 1.4;
  white-space: nowrap;
  display: flex;
  align-items: center;
  height: 100%;
}

.tab-nav .tab-btn::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 5px;
  background: #d0d7de;
  transition: all 0.3s ease;
  transform: translateX(-50%);
}

.tab-nav .tab-btn:hover::after {
  width: calc(100% + 16px);
  left: -8px;
  transform: translateX(0);
}

.tab-nav .tab-btn.active {
  color: #e74c3c;
  cursor: default;
}

.tab-nav .tab-btn.active::after {
  background: #e74c3c;
  width: 100%;
  left: 0;
  transform: translateX(0);
  height: 5px;
}

.tab-nav .tab-btn.active:hover::after {
  width: calc(100% + 16px);
  left: -8px;
  height: 5px;
}

/* ===== 信息卡片 ===== */
.l-card {
  background: #fff;
  border-radius: 16px;
  padding: 18px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  margin-bottom: 24px;
}

.l-flex-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.l-flex-info-row:last-child {
  border-bottom: none;
}

.l-flex-info-row span {
  font-size: 14px;
  color: #404040;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.l-flex-info-row .right {
  font-size: 14px;
  color: #2c3e50;
  font-weight: 500;
  text-align: right;
  word-break: break-all;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.l-flex-info-row .right time {
  color: #2c3e50;
}

/* ===== 身份标签 ===== */
.user-tag-display {
  display: inline-block;
  border-radius: 2px;
  padding: 2px 9px;
  color: #fff;
  font-size: 11.5px;
  font-weight: 600;
  margin: 0 0 0 4px;
  cursor: default;
  transition: filter 0.15s;
  vertical-align: middle;
  text-shadow: none;
}

.user-tag-display:hover {
  filter: brightness(0.9);
}

/* ===== 封面更换浮层 ===== */
.cover-upload-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
  justify-content: center;
  align-items: center;
  backdrop-filter: blur(4px);
}

.cover-upload-overlay.active {
  display: flex;
}

.cover-upload-panel {
  background: #fff;
  border-radius: 20px;
  padding: 32px 40px;
  max-width: 480px;
  width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.cover-upload-panel h2 {
  font-size: 1.3rem;
  margin-bottom: 16px;
  color: #2c3e50;
}

.cover-upload-panel .upload-area {
  border: 2px dashed #ddd;
  border-radius: 12px;
  padding: 30px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
  margin-bottom: 12px;
}

.cover-upload-panel .upload-area:hover {
  border-color: #e74c3c;
}

.cover-upload-panel .upload-area .hint {
  font-size: 14px;
  color: #999;
}

.cover-upload-panel .upload-area .hint strong {
  color: #e74c3c;
}

.cover-upload-panel .lfe-caption {
  font-size: 13px;
  color: #888;
  line-height: 1.6;
  margin: 12px 0;
}

.cover-upload-panel .panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

.cover-upload-panel .panel-actions button {
  padding: 8px 24px;
  border-radius: 30px;
  border: none;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.cover-upload-panel .panel-actions .btn-cancel-cover {
  background: #e9ecef;
  color: #555;
}

.cover-upload-panel .panel-actions .btn-cancel-cover:hover {
  background: #dde0e3;
}

.cover-upload-panel .panel-actions .btn-upload-cover {
  background: #e74c3c;
  color: #fff;
}

.cover-upload-panel .panel-actions .btn-upload-cover:hover:not(:disabled) {
  background: #c0392b;
}

.cover-upload-panel .panel-actions .btn-upload-cover:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cover-feedback {
  margin-top: 10px;
  font-size: 13px;
  color: v-bind('uploadFeedbackColor');
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .user-header {
    min-height: 220px;
  }

  .user-header-content {
    padding: 16px 24px 20px;
    gap: 6px;
  }

  .user-header-name h1 {
    font-size: 1.5rem;
  }

  .user-header-avatar {
    width: 64px;
    height: 64px;
  }

  .slogan-editor-input {
    max-width: 100%;
    min-width: 120px;
  }

  .tab-nav {
    gap: 16px;
  }

  .tab-nav .tab-btn {
    font-size: 14px;
    padding: 8px 0 10px 0;
  }

  .new-card {
    padding: 0 16px 10px;
  }
}

@media (max-width: 600px) {
  .user-header {
    min-height: 180px;
  }

  .user-header-content {
    padding: 12px 16px;
    gap: 4px;
  }

  .user-header-avatar {
    width: 56px;
    height: 56px;
  }

  .user-header-name h1 {
    font-size: 1.3rem;
  }

  .user-header-slogan {
    font-size: 0.95rem;
    padding: 4px 12px;
  }

  .cover-upload-panel {
    padding: 24px 20px;
  }

  .slogan-editor-input {
    font-size: 14px;
    padding: 2px 4px;
    min-width: 100px;
  }

  .tab-nav {
    gap: 10px;
  }

  .tab-nav .tab-btn {
    font-size: 13px;
    padding: 6px 0 8px 0;
  }

  .new-card {
    padding: 0 12px 8px;
  }
}
</style>
