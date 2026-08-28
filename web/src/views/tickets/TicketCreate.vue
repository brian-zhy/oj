<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const authStore = useAuthStore()

interface CategoryOption {
  key: string
  name: string
  desc: string
  icon: string
}

const CATEGORIES: CategoryOption[] = [
  { key: 'consult', name: '一般咨询', desc: '关于本站平台功能或相关事宜的询问', icon: '💬' },
  { key: 'suggestion', name: '建议反馈', desc: '为平台提供功能建议', icon: '💡' },
  { key: 'bug', name: 'Bug反馈', desc: '报告站点功能异常', icon: '🐞' },
  { key: 'appeal', name: '账号申诉', desc: '被封禁用户提交的账号申诉', icon: '🛡️' },
]

const isBanned = computed(() => authStore.currentUser?.is_banned === true)

const category = ref('')
const title = ref('')
const content = ref('')
const submitting = ref(false)
const error = ref('')

// 相似工单查询（标题防抖）
const similar = ref<any[]>([])
const showSimilar = ref(false)
let searchTimer: number | undefined

const onTitleInput = () => {
  window.clearTimeout(searchTimer)
  if (title.value.trim().length < 2) {
    similar.value = []
    showSimilar.value = false
    return
  }
  searchTimer = window.setTimeout(async () => {
    try {
      const data: any = await apiClient.get(`/tickets/similar?title=${encodeURIComponent(title.value.trim())}`)
      similar.value = data || []
      showSimilar.value = similar.value.length > 0
    } catch {
      similar.value = []
      showSimilar.value = false
    }
  }, 400)
}

const pickCategory = (key: string) => {
  // 封禁用户仅可提交账号申诉；未封禁用户不可提交申诉
  if (isBanned.value && key !== 'appeal') return
  if (!isBanned.value && key === 'appeal') return
  category.value = key
}

const submit = async () => {
  error.value = ''
  if (!category.value) {
    error.value = '请选择工单类别'
    return
  }
  if (title.value.trim().length < 3) {
    error.value = '标题至少 3 个字符，且应能体现主要需求'
    return
  }
  if (content.value.trim().length < 5) {
    error.value = '请填写工单内容（至少 5 个字符）'
    return
  }

  submitting.value = true
  try {
    const data: any = await apiClient.post('/tickets', {
      title: title.value.trim(),
      category: category.value,
      content: content.value.trim()
    })
    router.push(`/tickets/${data.id}`)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '提交失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="ticket-create-page">
    <div class="create-container">
      <h2 class="page-title">提交工单</h2>

      <!-- 规则提示 -->
      <div class="rules-card">
        <b>📋 工单规范</b>
        <ul>
          <li><b>一事一单</b>：每个工单仅反馈一个具体问题，多个问题请分别创建</li>
          <li><b>标题明确</b>：标题应体现主要需求，方便管理员快速识别分类</li>
          <li><b>遵守社区规范</b>：提交内容与回复均须遵守本站社区规范</li>
          <li><b>处理时效</b>：管理员通常会在 2 周内回复，特殊工单可能更久，请勿催促</li>
        </ul>
      </div>

      <!-- 类别选择 -->
      <div class="section-label">工单类别</div>
      <div class="category-grid">
        <div
          v-for="c in CATEGORIES"
          :key="c.key"
          class="category-card"
          :class="{
            selected: category === c.key,
            disabled: (isBanned && c.key !== 'appeal') || (!isBanned && c.key === 'appeal')
          }"
          @click="pickCategory(c.key)"
        >
          <div class="cat-icon">{{ c.icon }}</div>
          <div class="cat-name">{{ c.name }}</div>
          <div class="cat-desc">{{ c.desc }}</div>
        </div>
      </div>
      <p v-if="isBanned" class="ban-tip">⛔ 你当前处于封禁状态，仅可提交「账号申诉」工单。</p>

      <!-- 标题 -->
      <div class="section-label">标题 <span class="required">*</span></div>
      <div class="title-wrap">
        <input
          v-model="title"
          class="title-input"
          placeholder="简要描述问题（3-100 字）"
          maxlength="100"
          @input="onTitleInput"
          @focus="showSimilar = similar.length > 0"
          @blur="showSimilar = false"
        >
        <!-- 相似工单提示 -->
        <div v-if="showSimilar" class="similar-pop">
          <div class="similar-head">找到 {{ similar.length }} 条相似工单，或许已有解决方案：</div>
          <div
            v-for="t in similar"
            :key="t.id"
            class="similar-item"
            @mousedown.prevent="router.push(`/tickets/${t.id}`)"
          >
            <span class="similar-no">{{ t.ticket_no }}</span>
            <span class="similar-title">{{ t.title }}</span>
          </div>
        </div>
      </div>

      <!-- 内容 -->
      <div class="section-label">详细内容 <span class="required">*</span></div>
      <textarea
        v-model="content"
        class="content-input"
        rows="8"
        placeholder="请详细描述你的问题、建议或 Bug 的复现步骤……"
        maxlength="5000"
      ></textarea>

      <!-- 错误提示 -->
      <div v-if="error" class="error-tip">❌ {{ error }}</div>

      <div class="submit-bar">
        <button class="btn-submit" :disabled="submitting" @click="submit">
          {{ submitting ? '提交中...' : '提交工单' }}
        </button>
        <button class="btn-cancel" :disabled="submitting" @click="router.back()">取消</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ticket-create-page {
  min-height: 100vh;
  line-height: 1.6;
}

.create-container {
  max-width: 760px;
  margin: 0 auto;
}

.page-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 16px;
}

.rules-card {
  background: #fff7e6;
  border: 1px solid #ffe0b0;
  border-radius: 12px;
  padding: 14px 18px;
  font-size: 13px;
  color: #6b5b3e;
  margin-bottom: 20px;
}

.rules-card ul {
  margin: 8px 0 0;
  padding-left: 18px;
}

.rules-card li {
  margin: 3px 0;
}

.section-label {
  font-weight: 700;
  font-size: 14px;
  color: #2c3e50;
  margin: 18px 0 8px;
}

.required {
  color: #e74c3c;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.category-card {
  background: #fff;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.category-card:hover:not(.disabled) {
  border-color: #f0a08a;
}

.category-card.selected {
  border-color: #e74c3c;
  background: #fdf1ef;
}

.category-card.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.cat-icon {
  font-size: 22px;
}

.cat-name {
  font-weight: 700;
  font-size: 14px;
  color: #2c3e50;
  margin: 6px 0 2px;
}

.cat-desc {
  font-size: 12px;
  color: #8a9aa8;
}

.ban-tip {
  margin-top: 10px;
  color: #e74c3c;
  font-size: 13px;
}

.title-wrap {
  position: relative;
}

.title-input {
  width: 100%;
  padding: 11px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.title-input:focus {
  border-color: #e74c3c;
}

.similar-pop {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 20;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  margin-top: 4px;
  overflow: hidden;
}

.similar-head {
  padding: 8px 14px;
  font-size: 12px;
  color: #8a9aa8;
  background: #f8f9fc;
}

.similar-item {
  padding: 9px 14px;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  gap: 10px;
  align-items: center;
}

.similar-item:hover {
  background: #fdf1ef;
}

.similar-no {
  color: #8a9aa8;
  flex-shrink: 0;
}

.similar-title {
  color: #2c3e50;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.content-input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.content-input:focus {
  border-color: #e74c3c;
}

.error-tip {
  margin-top: 14px;
  color: #e74c3c;
  font-size: 13px;
}

.submit-bar {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.btn-submit {
  padding: 10px 34px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-submit:hover:not(:disabled) {
  background: #c0392b;
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  padding: 10px 28px;
  background: #f3f4f6;
  color: #4a5568;
  border: none;
  border-radius: 24px;
  font-size: 14px;
  cursor: pointer;
}
</style>
