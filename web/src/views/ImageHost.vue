<script setup lang="ts">
/**
 * 图床：上传图片 → 拿到可分享的直链。
 *
 * 空间规则参照洛谷：
 *   带水印且体积 ≤ 500KB → 占用「普通空间」（默认 50MB）
 *   其余（无水印，或体积 > 500KB）→ 占用「高级空间」（默认 10MB）
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Swal from 'sweetalert2'
import { imagesApi, type ImageListParams } from '@/api/images'
import { copyText } from '@/utils/codeCopy'
import { fmtDateTime } from '@/utils/datetime'
import type { HostedImage, ImageQuota, WatermarkMode } from '@/types'

const PAGE_SIZE = 24

const files = ref<HostedImage[]>([])
const quota = ref<ImageQuota | null>(null)
const total = ref(0)
const page = ref(1)
const loading = ref(true)

const uploading = ref(false)
const uploadedCount = ref(0)
const uploadTotal = ref(0)
const dragging = ref(false)

const filter = ref<'all' | 'premium' | 'basic' | 'locked'>('all')
const FILTERS = [
  { key: 'all' as const, label: '全部' },
  { key: 'premium' as const, label: '高级空间' },
  { key: 'basic' as const, label: '普通空间' },
  { key: 'locked' as const, label: '已锁定' },
]
// 上传时是否叠加站点文字水印（加水印的图占普通空间）
const watermarkMode = ref<WatermarkMode>('none')
const keyword = ref('')
const copiedId = ref<number | null>(null)

const fileInput = ref<HTMLInputElement | null>(null)
let searchTimer: ReturnType<typeof setTimeout> | undefined
let copiedTimer: ReturnType<typeof setTimeout> | undefined

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

const usedPercent = computed(() => {
  const q = quota.value
  if (!q || !q.premium_quota) return 0
  return Math.min(100, (q.premium_used / q.premium_quota) * 100)
})

const basicPercent = computed(() => {
  const q = quota.value
  if (!q || !q.basic_quota) return 0
  return Math.min(100, (q.basic_used / q.basic_quota) * 100)
})

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

/* ---------------- 数据加载 ---------------- */

async function load() {
  loading.value = true
  try {
    const params: ImageListParams = { page: page.value, page_size: PAGE_SIZE }
    if (filter.value === 'premium') params.premium = true
    if (filter.value === 'basic') params.premium = false
    if (filter.value === 'locked') params.locked = true
    if (keyword.value.trim()) params.q = keyword.value.trim()

    const [list, q] = await Promise.all([imagesApi.list(params), imagesApi.quota()])
    files.value = list.items
    total.value = list.total
    quota.value = q
  } catch (err: any) {
    Swal.fire('加载失败', err.response?.data?.detail || '请刷新页面重试', 'error')
  } finally {
    loading.value = false
  }
}

watch(filter, () => {
  page.value = 1
  void load()
})

// 搜索做 300ms 防抖，避免每敲一个字就请求
watch(keyword, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    void load()
  }, 300)
})

function goPage(p: number) {
  if (p < 1 || p > totalPages.value || p === page.value) return
  page.value = p
  void load()
}

/* ---------------- 上传 ---------------- */

function pick() {
  if (uploading.value) return
  fileInput.value?.click()
}

function onPick(e: Event) {
  const input = e.target as HTMLInputElement
  const picked = Array.from(input.files ?? [])
  // 复位，保证连续选同一批文件也能再次触发
  input.value = ''
  if (picked.length) void uploadAll(picked)
}

function onDrop(e: DragEvent) {
  dragging.value = false
  if (uploading.value) return
  const dropped = Array.from(e.dataTransfer?.files ?? [])
  if (dropped.length) void uploadAll(dropped)
}

async function uploadAll(list: File[]) {
  const images = list.filter((f) => f.type.startsWith('image/'))
  if (images.length === 0) {
    Swal.fire('仅支持图片文件', '请选择 jpg / png / gif / webp 图片', 'warning')
    return
  }

  uploading.value = true
  uploadTotal.value = images.length
  uploadedCount.value = 0

  const failures: string[] = []
  for (const file of images) {
    try {
      await imagesApi.upload(file, watermarkMode.value)
      uploadedCount.value++
    } catch (err: any) {
      // 配额不足 / 体积超限 / 格式不符都会走到这里，错误信息由后端给出
      failures.push(`${file.name}：${err.response?.data?.detail || '上传失败'}`)
    }
  }

  uploading.value = false
  page.value = 1
  await load()

  if (failures.length) {
    Swal.fire({
      icon: 'error',
      title: `${failures.length} 张图片上传失败`,
      html: failures.map((f) => `<div style="text-align:left">${f}</div>`).join(''),
    })
  }
}

/* ---------------- 单张操作 ---------------- */

async function copyLink(img: HostedImage) {
  const ok = await copyText(new URL(img.url, window.location.origin).href)
  if (!ok) {
    Swal.fire('复制失败', '请手动复制图片地址', 'error')
    return
  }
  copiedId.value = img.id
  clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => {
    copiedId.value = null
  }, 1600)
}

async function toggleLock(img: HostedImage) {
  try {
    const updated = await imagesApi.toggleLock(img.id)
    img.is_locked = updated.is_locked
    // 「已锁定」筛选下解锁后应从列表移除
    if (filter.value === 'locked' && !updated.is_locked) await load()
  } catch (err: any) {
    Swal.fire('操作失败', err.response?.data?.detail || '请重试', 'error')
  }
}

async function remove(img: HostedImage) {
  const res = await Swal.fire({
    title: '删除这张图片？',
    text: '删除后直链立即失效，且不可恢复。',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    confirmButtonColor: '#e74c3c',
  })
  if (!res.isConfirmed) return

  try {
    await imagesApi.remove(img.id)
    // 删掉当前页最后一张时回退一页
    if (files.value.length === 1 && page.value > 1) page.value--
    await load()
  } catch (err: any) {
    Swal.fire('删除失败', err.response?.data?.detail || '请重试', 'error')
  }
}

onMounted(load)

onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  clearTimeout(copiedTimer)
})
</script>

<template>
  <div class="image-page">
    <div class="page-container">
      <h1 class="page-title">图床</h1>

      <div class="top-row">
        <!-- 上传区 -->
        <div
          class="card drop-card"
          :class="{ 'is-dragging': dragging, 'is-busy': uploading }"
          @click="pick"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <i class="fa-solid fa-cloud-arrow-up drop-icon" />
          <p class="drop-main">点此处选择图片，或将图片拖至此处</p>
          <p class="drop-hint">
            支持 jpg / png / gif / webp；单个不超过 10MB。<br>
            体积大于 {{ quota ? Math.round(quota.premium_threshold / 1024) : 500 }}KB
            或无水印的图片将占用高级空间。
          </p>

          <div v-if="uploading" class="upload-progress">
            上传中… {{ uploadedCount }} / {{ uploadTotal }}
          </div>

          <!-- 水印：参照洛谷，只盖站点名文字（无 logo 素材） -->
          <div class="watermark-row" @click.stop>
            <span class="wm-label">水印</span>
            <label class="wm-item">
              <input v-model="watermarkMode" type="radio" name="wm" value="none">
              无水印
            </label>
            <label class="wm-item">
              <input v-model="watermarkMode" type="radio" name="wm" value="text">
              站点水印
            </label>
            <span class="wm-hint">
              加水印的图片占用普通空间（{{ fmtSize(quota?.basic_quota ?? 0) }}）
            </span>
          </div>

          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            multiple
            class="file-input"
            @change="onPick"
          >
        </div>

        <!-- 空间统计 -->
        <div class="card quota-card">
          <div class="quota-row">
            <span class="quota-key">已上传总数</span>
            <span class="quota-val">{{ quota?.total_count ?? 0 }} 张</span>
          </div>

          <div class="quota-key">高级空间</div>
          <div class="quota-bar">
            <div
              class="quota-bar-fill"
              :class="{ 'is-warn': usedPercent >= 80 }"
              :style="{ width: usedPercent + '%' }"
            />
          </div>
          <div class="quota-num">
            {{ fmtSize(quota?.premium_used ?? 0) }} / {{ fmtSize(quota?.premium_quota ?? 0) }}
          </div>

          <div class="quota-key">普通空间</div>
          <div class="quota-bar">
            <div
              class="quota-bar-fill is-basic"
              :class="{ 'is-warn': basicPercent >= 80 }"
              :style="{ width: basicPercent + '%' }"
            />
          </div>
          <div class="quota-num">
            {{ fmtSize(quota?.basic_used ?? 0) }} / {{ fmtSize(quota?.basic_quota ?? 0) }}
          </div>

          <ul class="quota-rules">
            <li>图床功能仅限本站站内交流及学术功能使用</li>
            <li>上传的图片必须遵守相关法律法规与符合社会道德</li>
            <li>严禁上传涉政或淫秽擦边图片</li>
          </ul>
        </div>
      </div>

      <!-- 图片列表 -->
      <div class="card list-card">
        <div class="list-head">
          <span class="list-title">图片列表</span>
          <div class="list-tools">
            <button
              v-for="f in FILTERS"
              :key="f.key"
              type="button"
              class="chip"
              :class="{ 'is-active': filter === f.key }"
              @click="filter = f.key"
            >
              {{ f.label }}
            </button>
            <input
              v-model="keyword"
              class="search"
              type="search"
              placeholder="按文件名搜索"
            >
          </div>
        </div>

        <div v-if="loading" class="state-box">加载中…</div>
        <div v-else-if="files.length === 0" class="state-box">
          {{ keyword || filter !== 'all' ? '没有符合条件的图片' : '还没有上传过图片' }}
        </div>

        <div v-else class="img-grid">
          <div v-for="img in files" :key="img.id" class="img-card">
            <a
              class="img-thumb"
              :href="img.url"
              target="_blank"
              rel="noopener noreferrer"
              :title="img.original_name || ''"
            >
              <img :src="img.url" :alt="img.original_name || '图片'" loading="lazy">
            </a>

            <div class="img-meta">
              <div class="img-time">{{ fmtDateTime(img.created_at) }}</div>
              <div class="img-size">
                {{ fmtSize(img.size_bytes) }}
                <i
                  v-if="img.watermark !== 'none'"
                  class="fa-solid fa-droplet badge-wm"
                  title="已加水印，占用普通空间"
                />
                <i v-if="img.is_premium" class="fa-solid fa-gem badge-hd" title="占用高级空间" />
                <i v-if="img.is_locked" class="fa-solid fa-lock badge-lock" title="已锁定，不可删除" />
              </div>
            </div>

            <div class="img-actions">
              <button type="button" class="act" title="复制图片链接" @click="copyLink(img)">
                <i :class="copiedId === img.id ? 'fa-solid fa-check' : 'fa-solid fa-link'" />
                {{ copiedId === img.id ? '已复制' : '复制' }}
              </button>
              <button type="button" class="act" @click="toggleLock(img)">
                <i :class="img.is_locked ? 'fa-solid fa-lock-open' : 'fa-solid fa-lock'" />
                {{ img.is_locked ? '解锁' : '锁定' }}
              </button>
              <button
                type="button"
                class="act act-danger"
                :disabled="img.is_locked"
                :title="img.is_locked ? '已锁定，需先解锁' : '删除'"
                @click="remove(img)"
              >
                <i class="fa-solid fa-trash-can" />删除
              </button>
            </div>
          </div>
        </div>

        <div v-if="!loading && totalPages > 1" class="pager">
          <button type="button" class="pg" :disabled="page <= 1" @click="goPage(page - 1)">
            上一页
          </button>
          <span class="pg-info">{{ page }} / {{ totalPages }}（共 {{ total }} 张）</span>
          <button
            type="button"
            class="pg"
            :disabled="page >= totalPages"
            @click="goPage(page + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.image-page {
  padding: 16px 16px 40px;
}

.page-container {
  max-width: 1100px;
  margin: 0 auto;
}

.page-title {
  font-size: 20px;
  color: #2c3e50;
  margin: 4px 0 14px;
}

.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.top-row {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 14px;
  margin-bottom: 14px;
}

/* ---------- 上传区 ---------- */
.drop-card {
  padding: 26px 20px 16px;
  text-align: center;
  border: 2px dashed transparent;
  cursor: pointer;
  transition: border-color 0.18s, background-color 0.18s;
}

.drop-card:hover {
  border-color: #c8d8ee;
}

.drop-card.is-dragging {
  border-color: var(--primary);
  background: #f2f8ff;
}

.drop-card.is-busy {
  cursor: default;
}

.drop-icon {
  font-size: 40px;
  color: var(--primary);
}

.drop-main {
  margin: 10px 0 6px;
  font-size: 15px;
  color: #2c3e50;
}

.drop-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
  color: #90a0b4;
}

.upload-progress {
  margin-top: 10px;
  font-size: 13px;
  color: var(--primary);
  font-weight: 600;
}

.watermark-row {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid #eef2f7;
  font-size: 13px;
  color: #4a5568;
  cursor: default;
}

.wm-label {
  color: #8a9aa8;
  font-size: 12px;
}

.wm-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.wm-item.is-disabled {
  color: #b6c0cd;
}

.wm-hint {
  font-size: 11px;
  color: #a0aec0;
}

.file-input {
  display: none;
}

/* ---------- 空间统计 ---------- */
.quota-card {
  padding: 18px;
}

.quota-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 16px;
}

.quota-key {
  font-size: 13px;
  color: #8a9aa8;
}

.quota-val {
  font-size: 18px;
  font-weight: 700;
  color: #2c3e50;
}

.quota-bar {
  height: 8px;
  margin: 6px 0;
  border-radius: 4px;
  background: #eef2f7;
  overflow: hidden;
}

.quota-bar-fill {
  height: 100%;
  border-radius: 4px;
  background: var(--primary);
  transition: width 0.25s;
}

.quota-bar-fill.is-warn {
  background: #e74c3c;
}

.quota-bar-fill.is-basic {
  background: #3fae8f;
}

.quota-bar-fill.is-basic.is-warn {
  background: #e74c3c;
}

.quota-num {
  font-size: 12px;
  color: #90a0b4;
  margin-bottom: 14px;
}

.quota-rules {
  margin: 0;
  padding-left: 16px;
  font-size: 12px;
  line-height: 1.8;
  color: #c0392b;
}

/* ---------- 列表 ---------- */
.list-card {
  padding: 16px 18px 20px;
}

.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
}

.list-title {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
}

.list-tools {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.chip {
  padding: 4px 12px;
  font-size: 12px;
  color: #607089;
  background: #f4f7fb;
  border: 1px solid #e3eaf3;
  border-radius: 14px;
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s, border-color 0.15s;
}

.chip:hover {
  background: #e9f1fb;
}

.chip.is-active {
  color: #fff;
  background: var(--primary);
  border-color: var(--primary);
}

.search {
  width: 150px;
  padding: 5px 10px;
  font-size: 12px;
  border: 1px solid #e3eaf3;
  border-radius: 14px;
  outline: none;
}

.search:focus {
  border-color: var(--primary);
}

.state-box {
  padding: 40px 0;
  text-align: center;
  font-size: 13px;
  color: #a0aec0;
}

.img-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 14px;
}

.img-card {
  border: 1px solid #eef2f7;
  border-radius: 10px;
  overflow: hidden;
  transition: box-shadow 0.18s, border-color 0.18s;
}

.img-card:hover {
  border-color: #dbe6f3;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.07);
}

.img-thumb {
  display: block;
  height: 130px;
  background:
    repeating-conic-gradient(#f7f9fc 0% 25%, #eef2f7 0% 50%) 50% / 16px 16px;
}

.img-thumb img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.img-meta {
  padding: 8px 10px 0;
}

.img-time {
  font-size: 11px;
  color: #90a0b4;
}

.img-size {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #4a5568;
  margin-top: 2px;
}

.badge-hd {
  color: #b8860b;
  font-size: 11px;
}

.badge-wm {
  color: #3fae8f;
  font-size: 11px;
}

.badge-lock {
  color: #8a9aa8;
  font-size: 11px;
}

.img-actions {
  display: flex;
  gap: 4px;
  padding: 8px 10px 10px;
}

.act {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 5px 0;
  font-size: 11px;
  /* 卡片较窄时不允许折行，“复制链/接”这类断字很难看 */
  white-space: nowrap;
  color: #607089;
  background: #f7fafc;
  border: 1px solid #e8eef5;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s;
}

.act:hover:not(:disabled) {
  color: var(--primary);
  background: #eef5ff;
}

.act:disabled {
  color: #c3ccd8;
  cursor: not-allowed;
}

.act-danger:hover:not(:disabled) {
  color: #e74c3c;
  background: #fdf2f0;
}

/* ---------- 分页 ---------- */
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 18px;
}

.pg {
  padding: 5px 14px;
  font-size: 12px;
  color: #4a5568;
  background: #f4f7fb;
  border: 1px solid #e3eaf3;
  border-radius: 6px;
  cursor: pointer;
}

.pg:disabled {
  color: #c3ccd8;
  cursor: not-allowed;
}

.pg-info {
  font-size: 12px;
  color: #90a0b4;
}

@media (max-width: 860px) {
  .top-row {
    grid-template-columns: 1fr;
  }

  .img-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
}
</style>
