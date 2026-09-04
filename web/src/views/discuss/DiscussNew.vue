<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const authStore = useAuthStore()
const isMuted = computed(() => authStore.currentUser?.can_speak === false)

const FORUMS = [
  { key: 'siteaffairs', name: '站务版', desc: '站点事务与公告讨论' },
  { key: 'problem', name: '题目总版', desc: '题目相关讨论' },
  { key: 'academics', name: '学术版', desc: '算法与学术交流' },
  { key: 'relevantaffairs', name: '灌水区', desc: '轻松闲聊' },
]

const forum = ref('')
const title = ref('')
const content = ref('')
const submitting = ref(false)
const error = ref('')

const submit = async () => {
  error.value = ''
  if (isMuted.value) {
    error.value = '你已被禁言，无法发布帖子'
    return
  }
  if (!forum.value) {
    error.value = '请选择版块'
    return
  }
  if (title.value.trim().length < 3) {
    error.value = '标题至少 3 个字符'
    return
  }
  if (!content.value.trim()) {
    error.value = '请填写正文内容'
    return
  }

  submitting.value = true
  try {
    const data: any = await apiClient.post('/api/forum/posts', {
      title: title.value.trim(),
      content: content.value.trim(),
      forum: forum.value
    })
    router.push(`/discuss/${data.id}`)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '发布失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="post-new-page">
    <div class="new-container">
      <h2 class="page-title">发布帖子</h2>
      <div v-if="isMuted" class="mute-tip">⛔ 你已被禁言，无法发布帖子，如有疑问请通过工单联系我们。</div>

      <div class="section-label">选择版块 <span class="required">*</span></div>
      <div class="forum-grid">
        <div
          v-for="f in FORUMS"
          :key="f.key"
          class="forum-card"
          :class="{ selected: forum === f.key }"
          @click="forum = f.key"
        >
          <div class="forum-name">{{ f.name }}</div>
          <div class="forum-desc">{{ f.desc }}</div>
        </div>
      </div>

      <div class="section-label">标题 <span class="required">*</span></div>
      <input
        v-model="title"
        class="title-input"
        placeholder="简要概括帖子主题（3-100 字）"
        maxlength="100"
      >

      <div class="section-label">正文 <span class="required">*</span></div>
      <textarea
        v-model="content"
        class="content-input"
        rows="10"
        placeholder="支持简单 Markdown：**粗体**、*斜体*、```代码块```、@提及"
        maxlength="20000"
      ></textarea>

      <div v-if="error" class="error-tip">❌ {{ error }}</div>

      <div class="submit-bar">
        <button class="btn-submit" :disabled="submitting || isMuted" @click="submit">
          {{ submitting ? '发布中...' : '发布帖子' }}
        </button>
        <button class="btn-cancel" :disabled="submitting" @click="router.back()">取消</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.post-new-page {
  min-height: 100vh;
  line-height: 1.6;
}

.new-container {
  max-width: 760px;
  margin: 0 auto;
}

.page-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 16px;
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

.forum-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.forum-card {
  background: #fff;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.forum-card:hover {
  border-color: #f0a08a;
}

.forum-card.selected {
  border-color: #e74c3c;
  background: #fdf1ef;
}

.forum-name {
  font-weight: 700;
  font-size: 14px;
  color: #2c3e50;
  margin-bottom: 4px;
}

.forum-desc {
  font-size: 12px;
  color: #8a9aa8;
}

.title-input {
  width: 100%;
  padding: 11px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.title-input:focus {
  border-color: #e74c3c;
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
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.content-input:focus {
  border-color: #e74c3c;
}

.error-tip {
  margin-top: 14px;
  color: #e74c3c;
  font-size: 13px;
}

.mute-tip {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 13px;
  margin-bottom: 16px;
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
