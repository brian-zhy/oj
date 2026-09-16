<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api/client'

interface AdItem {
  image: string
  link: string
}

const router = useRouter()
const MAX_ADS = 6
const DEFAULT_IMAGE = '/welcome.png'

const ads = ref<AdItem[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const saved = ref(false)
const previewIndex = ref(0)

const canAdd = computed(() => ads.value.length < MAX_ADS)
const previewAd = computed(() => ads.value[previewIndex.value])

const loadAds = async () => {
  loading.value = true
  error.value = ''
  try {
    const data: any = await apiClient.get('/api/home-ads')
    const items = Array.isArray(data?.ads) ? data.ads : []
    ads.value = items.map((item: any) => ({
      image: item.image || '',
      link: item.link || '',
    }))
    previewIndex.value = 0
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '广告加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

const addAd = () => {
  if (!canAdd.value) return
  ads.value.push({ image: '', link: '/' })
  previewIndex.value = ads.value.length - 1
  saved.value = false
}

const removeAd = (index: number) => {
  ads.value.splice(index, 1)
  if (previewIndex.value >= ads.value.length) previewIndex.value = Math.max(0, ads.value.length - 1)
  saved.value = false
}

const moveAd = (index: number, direction: -1 | 1) => {
  const target = index + direction
  if (target < 0 || target >= ads.value.length) return
  const current = ads.value[index]
  ads.value[index] = ads.value[target]
  ads.value[target] = current
  previewIndex.value = target
  saved.value = false
}

const saveAds = async () => {
  error.value = ''
  saved.value = false
  const invalid = ads.value.findIndex(ad => !ad.image.trim() || !ad.link.trim())
  if (invalid >= 0) {
    error.value = `请先完善第 ${invalid + 1} 个广告的图片地址和跳转链接`
    previewIndex.value = invalid
    return
  }

  saving.value = true
  try {
    await apiClient.put('/api/home-ads', ads.value.map(ad => ({
      image: ad.image.trim(),
      link: ad.link.trim(),
    })))
    await loadAds()
    saved.value = true
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '保存失败，请稍后重试'
  } finally {
    saving.value = false
  }
}

const previewImage = (event: Event) => {
  const image = event.target as HTMLImageElement
  image.src = DEFAULT_IMAGE
}

onMounted(loadAds)
</script>

<template>
  <div class="ads-page">
    <header class="ads-header">
      <div>
        <button class="back-button" title="返回首页" @click="router.push('/')">
          <i class="fa-solid fa-arrow-left"></i>
        </button>
        <div class="ads-heading">
          <p class="eyebrow">ADMIN / HOMEPAGE</p>
          <h1>广告管理</h1>
          <p class="ads-subtitle">配置首页轮播内容，最多 {{ MAX_ADS }} 张。保存后立即生效。</p>
        </div>
      </div>
      <div class="ads-header-actions">
        <span class="ads-count">{{ ads.length }} / {{ MAX_ADS }}</span>
        <button class="save-button" :disabled="saving || loading" @click="saveAds">
          <i class="fa-solid fa-check"></i>
          {{ saving ? '保存中...' : '保存全部' }}
        </button>
      </div>
    </header>

    <div v-if="error" class="notice error-notice">
      <i class="fa-solid fa-circle-exclamation"></i>{{ error }}
    </div>
    <div v-if="saved" class="notice success-notice">
      <i class="fa-solid fa-circle-check"></i>广告配置已保存
    </div>

    <div v-if="loading" class="loading-state">正在加载广告配置...</div>
    <main v-else class="ads-layout">
      <section class="ads-editor-panel">
        <div class="section-heading">
          <div>
            <h2>轮播内容</h2>
            <p>直接在卡片内编辑，顺序就是首页的播放顺序。</p>
          </div>
          <button class="add-button" :disabled="!canAdd" @click="addAd">
            <i class="fa-solid fa-plus"></i> 添加广告
          </button>
        </div>

        <div v-if="ads.length" class="ad-list">
          <article
            v-for="(ad, index) in ads"
            :key="index"
            class="ad-edit-card"
            :class="{ selected: previewIndex === index }"
            @click="previewIndex = index"
          >
            <div class="card-index">{{ String(index + 1).padStart(2, '0') }}</div>
            <div class="card-preview">
              <img :src="ad.image || DEFAULT_IMAGE" alt="广告预览" @error="previewImage">
            </div>
            <div class="card-fields">
              <label>
                <span>图片地址</span>
                <input v-model="ad.image" type="text" placeholder="https://... 或 /uploads/banner.png" @click.stop>
              </label>
              <label>
                <span>跳转链接</span>
                <input v-model="ad.link" type="text" placeholder="/contest/1 或 https://..." @click.stop>
              </label>
            </div>
            <div class="card-actions" @click.stop>
              <button title="上移" :disabled="index === 0" @click="moveAd(index, -1)"><i class="fa-solid fa-chevron-up"></i></button>
              <button title="下移" :disabled="index === ads.length - 1" @click="moveAd(index, 1)"><i class="fa-solid fa-chevron-down"></i></button>
              <button class="delete-action" title="删除" @click="removeAd(index)"><i class="fa-solid fa-trash"></i></button>
            </div>
          </article>
        </div>
        <div v-else class="empty-editor">
          <i class="fa-regular fa-images"></i>
          <strong>还没有广告</strong>
          <span>添加一张图片，首页就会拥有第一帧内容。</span>
          <button class="add-button" @click="addAd"><i class="fa-solid fa-plus"></i> 添加第一张</button>
        </div>
      </section>

      <aside class="ads-preview-panel">
        <div class="section-heading compact-heading">
          <div>
            <h2>实时预览</h2>
            <p>点击左侧卡片切换预览</p>
          </div>
          <span class="live-badge"><span></span> LIVE</span>
        </div>
        <div class="preview-stage">
          <div v-if="previewAd" class="preview-frame">
            <img :src="previewAd.image || DEFAULT_IMAGE" alt="当前广告" @error="previewImage">
            <div class="preview-overlay">
              <span>第 {{ previewIndex + 1 }} / {{ ads.length }} 张</span>
              <span>{{ previewAd.link || '尚未设置链接' }}</span>
            </div>
          </div>
          <div v-else class="preview-empty">添加广告后查看预览</div>
        </div>
        <p class="preview-note"><i class="fa-solid fa-circle-info"></i> 首页会以 320px 高度展示，并自动平滑切换。</p>
      </aside>
    </main>
  </div>
</template>

<style scoped>
.ads-page {
  min-height: 100vh;
  padding: 34px clamp(18px, 4vw, 64px) 60px;
  color: #263449;
  background: #f5f7fb;
}

.ads-header {
  max-width: 1320px;
  margin: 0 auto 26px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
}

.ads-header > div:first-child {
  display: flex;
  gap: 16px;
}

.back-button,
.card-actions button {
  border: 1px solid #dce3ee;
  background: #fff;
  color: #617089;
  cursor: pointer;
}

.back-button {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  font-size: 16px;
}

.back-button:hover,
.card-actions button:hover:not(:disabled) {
  color: var(--primary);
  border-color: var(--primary);
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--primary);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.5px;
}

.ads-heading h1 {
  margin: 0;
  color: #1f2c41;
  font-size: 30px;
  line-height: 1.2;
}

.ads-subtitle,
.section-heading p {
  margin: 7px 0 0;
  color: #8190a5;
  font-size: 13px;
}

.ads-header-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.ads-count {
  color: #75839a;
  font-size: 13px;
  font-weight: 700;
}

.save-button,
.add-button {
  border: 0;
  border-radius: 10px;
  background: var(--primary);
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
}

.save-button {
  padding: 11px 18px;
}

.add-button {
  padding: 9px 14px;
  font-size: 13px;
}

.save-button:hover,
.add-button:hover:not(:disabled) {
  filter: brightness(1.08);
}

.save-button:disabled,
.add-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.notice,
.loading-state {
  max-width: 1320px;
  margin: 0 auto 16px;
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 13px;
}

.notice i {
  margin-right: 8px;
}

.error-notice {
  background: #fff1f0;
  color: #c0392b;
}

.success-notice {
  background: #edfbf3;
  color: #198754;
}

.loading-state {
  background: #fff;
  color: #8290a4;
  text-align: center;
}

.ads-layout {
  max-width: 1320px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.8fr);
  gap: 20px;
  align-items: start;
}

.ads-editor-panel,
.ads-preview-panel {
  padding: 22px;
  border: 1px solid #e5eaf2;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(42, 58, 83, 0.05);
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 18px;
}

.section-heading h2 {
  margin: 0;
  color: #28364c;
  font-size: 17px;
}

.ad-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ad-edit-card {
  display: grid;
  grid-template-columns: 34px 128px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border: 1px solid #e7ecf3;
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
}

.ad-edit-card:hover,
.ad-edit-card.selected {
  border-color: #aebaf4;
  box-shadow: 0 5px 16px rgba(80, 91, 190, 0.1);
}

.ad-edit-card.selected {
  transform: translateX(2px);
}

.card-index {
  color: var(--primary);
  font-size: 12px;
  font-weight: 800;
}

.card-preview {
  width: 128px;
  height: 72px;
  overflow: hidden;
  border-radius: 8px;
  background: #edf1f8;
}

.card-preview img,
.preview-frame img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.card-fields {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.card-fields label {
  display: grid;
  grid-template-columns: 68px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}

.card-fields label span,
.ad-field span {
  color: #8290a4;
  font-size: 11px;
}

.card-fields input {
  min-width: 0;
  width: 100%;
  padding: 7px 9px;
  border: 1px solid #dbe3ef;
  border-radius: 7px;
  color: #334158;
  font: inherit;
  font-size: 12px;
  box-sizing: border-box;
}

.card-fields input:focus {
  outline: 2px solid rgba(92, 101, 207, 0.16);
  border-color: var(--primary);
}

.card-actions {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.card-actions button {
  width: 28px;
  height: 26px;
  border-radius: 6px;
  font-size: 11px;
}

.card-actions button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.card-actions .delete-action {
  color: #c0392b;
}

.empty-editor {
  display: flex;
  min-height: 260px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border: 1px dashed #d5deeb;
  border-radius: 12px;
  color: #8491a4;
  font-size: 13px;
}

.empty-editor i {
  color: #b4bfd0;
  font-size: 30px;
}

.empty-editor strong {
  color: #526078;
}

.empty-editor .add-button {
  margin-top: 8px;
}

.compact-heading {
  align-items: flex-start;
}

.live-badge {
  color: #24a36a;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 1px;
}

.live-badge span {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 5px;
  border-radius: 50%;
  background: #2bb673;
  vertical-align: 1px;
}

.preview-stage {
  padding: 10px;
  border-radius: 12px;
  background: #eef2f8;
}

.preview-frame {
  width: 100%;
  aspect-ratio: 16 / 7;
  overflow: hidden;
  position: relative;
  border-radius: 9px;
  background: #dfe6f2;
}

.preview-overlay {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 10px;
  background: linear-gradient(transparent, rgba(20, 29, 44, 0.78));
  color: #fff;
  font-size: 11px;
}

.preview-overlay span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-empty {
  display: grid;
  min-height: 180px;
  place-items: center;
  color: #8996aa;
  font-size: 13px;
}

.preview-note {
  margin: 14px 2px 0;
  color: #8794a8;
  font-size: 12px;
  line-height: 1.5;
}

.preview-note i {
  margin-right: 6px;
  color: var(--primary);
}

@media (max-width: 900px) {
  .ads-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .ads-page {
    padding: 22px 12px 40px;
  }

  .ads-header {
    flex-direction: column;
  }

  .ads-header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .ad-edit-card {
    grid-template-columns: 26px 88px minmax(0, 1fr) auto;
    gap: 9px;
    padding: 9px;
  }

  .card-preview {
    width: 88px;
    height: 58px;
  }

  .card-fields label {
    display: block;
  }

  .card-fields label span {
    display: block;
    margin-bottom: 3px;
  }
}
</style>
