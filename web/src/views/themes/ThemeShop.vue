<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const authStore = useAuthStore()
const me = computed(() => authStore.currentUser)

// 内置渐变预设（key 与后端 _ALLOWED_THEME_PRESETS 一致）
const PRESETS: Record<string, { name: string; css: string }> = {
  dawn: { name: '晨曦', css: 'linear-gradient(135deg, #ffd8a8 0%, #ff9db8 50%, #a8c8ff 100%)' },
  ocean: { name: '深海', css: 'linear-gradient(160deg, #0f3057 0%, #00587a 55%, #008891 100%)' },
  dusk: { name: '暮色', css: 'linear-gradient(160deg, #2b1b4d 0%, #7a3b8f 55%, #ff7e5f 100%)' },
  sakura: { name: '樱色', css: 'linear-gradient(150deg, #ffe3ec 0%, #ffc7de 55%, #ffd8b1 100%)' },
}

const enabled = computed(() => !!me.value?.theme_enabled)
const currentBg = computed(() => me.value?.theme_background || '')

const isPreset = (bg: string) => bg.startsWith('preset:')
const presetKey = (bg: string) => bg.split(':')[1] || ''
const presetCss = (bg: string) => PRESETS[presetKey(bg)]?.css || ''
const presetName = (bg: string) => PRESETS[presetKey(bg)]?.name || ''

// 预览样式：叠一层与全站一致的暗遮罩，模拟实际浏览效果
const previewStyle = computed(() => {
  const bg = currentBg.value
  if (!bg) return {}
  if (isPreset(bg)) {
    return { backgroundImage: `linear-gradient(rgba(15,23,52,.38), rgba(15,23,52,.38)), ${presetCss(bg)}` }
  }
  return {
    backgroundImage: `linear-gradient(rgba(15,23,52,.42), rgba(15,23,52,.42)), url(${bg})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
  }
})

const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const acting = ref(false)
const msg = ref('')

const pickFile = () => fileInput.value?.click()

const onFileChange = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    msg.value = '图片不能超过 5MB'
    return
  }
  uploading.value = true
  msg.value = ''
  try {
    const form = new FormData()
    form.append('file', file)
    await apiClient.post('/api/users/me/theme/background', form)
    msg.value = '背景已上传并启用'
    await authStore.syncCurrentUser()
  } catch (err: any) {
    msg.value = err.response?.data?.detail || '上传失败'
  } finally {
    uploading.value = false
  }
}

// 乐观更新：先改本地状态立即生效（背景切换不等网络往返），失败再回滚。
// 之前每次都等 syncCurrentUser 往返，点击内置配色会有明显的「卡一下」。
const patchLocal = (bg: string | null, on: boolean | null) => {
  const me = authStore.currentUser
  if (!me) return false
  me.theme_background = bg
  if (on !== null) me.theme_enabled = on
  return true
}

const applyPreset = async (key: string) => {
  const me = authStore.currentUser
  if (!me) return
  const prev = { bg: me.theme_background, on: me.theme_enabled }
  patchLocal(`preset:${key}`, true)
  acting.value = true
  msg.value = ''
  try {
    await apiClient.put('/api/users/me/theme', { background: `preset:${key}` })
  } catch (err: any) {
    me.theme_background = prev.bg
    me.theme_enabled = prev.on
    msg.value = err.response?.data?.detail || '设置失败'
  } finally {
    acting.value = false
  }
}

const toggleEnabled = async () => {
  const me = authStore.currentUser
  if (!me) return
  const prev = me.theme_enabled
  me.theme_enabled = !prev
  acting.value = true
  msg.value = ''
  try {
    await apiClient.put('/api/users/me/theme', { enabled: !prev })
  } catch (err: any) {
    me.theme_enabled = prev
    msg.value = err.response?.data?.detail || '操作失败'
  } finally {
    acting.value = false
  }
}

const resetTheme = async () => {
  const me = authStore.currentUser
  if (!me) return
  const prev = { bg: me.theme_background, on: me.theme_enabled }
  patchLocal(null, false)
  acting.value = true
  msg.value = ''
  try {
    await apiClient.put('/api/users/me/theme', { background: null })
    msg.value = '已恢复默认主题'
  } catch (err: any) {
    me.theme_background = prev.bg
    me.theme_enabled = prev.on
    msg.value = err.response?.data?.detail || '操作失败'
  } finally {
    acting.value = false
  }
}

onMounted(() => {
  if (!me.value) void authStore.syncCurrentUser()
})
</script>

<template>
  <div class="theme-page">
    <div class="theme-container">
      <div class="theme-head card">
        <div>
          <h2 class="page-title">主题商店</h2>
          <p class="page-sub">上传自定义背景图或选择内置配色，应用后全站背景随你而变。主题仅自己可见。</p>
        </div>
        <div class="status-box" :class="{ on: enabled }">
          <div class="status-label">当前状态</div>
          <div class="status-value">{{ enabled ? '已启用' : '未启用' }}</div>
        </div>
      </div>

      <div v-if="msg" class="action-msg">{{ msg }}</div>

      <div class="card section">
        <h3 class="section-title">预览</h3>
        <div class="preview" :style="previewStyle">
          <div class="preview-card">全站卡片将像这样浮在你的背景上</div>
        </div>
        <div class="ops">
          <button class="btn primary" :disabled="uploading" @click="pickFile">
            {{ uploading ? '上传中…' : currentBg && !isPreset(currentBg) ? '更换自定义图片' : '上传自定义图片' }}
          </button>
          <button
            v-if="currentBg"
            class="btn"
            :disabled="acting"
            @click="toggleEnabled"
          >{{ enabled ? '停用主题' : '启用主题' }}</button>
          <button class="btn ghost" :disabled="acting || !currentBg" @click="resetTheme">恢复默认</button>
          <input ref="fileInput" type="file" accept=".jpg,.jpeg,.png,.gif,.webp" hidden @change="onFileChange">
        </div>
        <p class="tip">支持 jpg / png / gif / webp，不超过 5MB。主题只影响你自己的浏览效果。</p>
      </div>

      <div class="card section">
        <h3 class="section-title">内置配色</h3>
        <div class="preset-grid">
          <button
            v-for="(p, key) in PRESETS"
            :key="key"
            class="preset"
            :class="{ active: isPreset(currentBg) && presetKey(currentBg) === key }"
            :style="{ backgroundImage: p.css }"
            :disabled="acting"
            @click="applyPreset(String(key))"
          >
            <span class="preset-name">{{ p.name }}</span>
            <span v-if="isPreset(currentBg) && presetKey(currentBg) === key" class="preset-check">✓ 使用中</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.theme-page { min-height: calc(100vh - 60px - 80px); }
.theme-container { max-width: 860px; margin: 0 auto; padding: 4px 0 24px; display: flex; flex-direction: column; gap: 16px; }

.theme-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px; padding: 20px 26px; }
.page-title { color: var(--primary); font-size: 22px; margin: 0; }
.page-sub { color: var(--text-sub); font-size: 13px; margin: 6px 0 0; }
.status-box { text-align: center; background: #f2f4f7; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 10px 26px; }
.status-box.on { background: #f0faf4; border-color: #cdebd6; }
.status-label { font-size: 12px; color: var(--text-sub); }
.status-value { font-size: 22px; font-weight: 800; color: #66708c; }
.status-box.on .status-value { color: #27ae60; }

.action-msg { background: #eafaf1; color: #27ae60; padding: 10px 16px; border-radius: var(--radius-sm); font-size: 14px; }

.section { padding: 20px 24px; }
.section-title { color: var(--text-main); font-size: 15px; margin: 0 0 14px; }

.preview {
  height: 240px;
  border-radius: var(--radius-md);
  border: var(--border-width) solid var(--border-color);
  background-color: var(--bg-page);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.preview-card {
  background: var(--surface);
  backdrop-filter: blur(var(--surface-blur)) saturate(1.5);
  -webkit-backdrop-filter: blur(var(--surface-blur)) saturate(1.5);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: 22px 34px;
  color: var(--text-main);
  font-size: 14px;
  font-weight: 700;
}

.ops { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
.btn { border: var(--border-width) solid var(--border-color); background: var(--surface-strong); color: #4a5568; border-radius: 22px; padding: 9px 24px; font-size: 14px; font-weight: 700; cursor: pointer; }
.btn:hover:not(:disabled) { box-shadow: var(--shadow-card); }
.btn.primary { background: var(--primary); border-color: var(--primary); color: #fff; }
.btn.primary:hover:not(:disabled) { background: var(--primary-hover); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.tip { color: var(--text-sub); font-size: 12px; margin: 12px 0 0; }

.preset-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.preset {
  position: relative;
  height: 84px;
  border-radius: var(--radius-md);
  border: 2px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: flex-end;
  padding: 10px 12px;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.preset:hover { transform: translateY(-2px); box-shadow: var(--shadow-card-hover); }
.preset.active { border-color: var(--primary); }
.preset-name { color: #fff; font-weight: 800; font-size: 14px; text-shadow: 0 1px 4px rgba(0,0,0,.45); }
.preset-check { position: absolute; top: 8px; right: 10px; background: rgba(255,255,255,.9); color: var(--primary); font-size: 11px; font-weight: 800; border-radius: 10px; padding: 2px 8px; }

@media (max-width: 600px) {
  .theme-container { padding: 2px 0 18px; }
}
</style>
