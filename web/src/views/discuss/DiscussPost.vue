<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const post = ref<any>(null)
const loading = ref(true)
const error = ref('')

const replyContent = ref('')
const replySubmitting = ref(false)

const isLoggedIn = computed(() => authStore.isAuthenticated)

const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

const userColor = (u: any) => (u?.is_banned ? '#95a5a6' : u?.is_admin ? '#9C3DCF' : '#e74c3c')

const fmtTime = (iso: string) => (iso ? String(iso).replace('T', ' ').slice(0, 16) : '')

// 简易 Markdown 渲染（与犇犇一致）
const renderContent = (content: string) => {
  if (!content) return ''
  content = content.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
  content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  content = content.replace(/\*(.*?)\*/g, '<em>$1</em>')
  content = content.replace(/https?:\/\/[^\s]+/g, '<a href="$&" target="_blank">$&</a>')
  content = content.replace(/@([一-龥a-zA-Z0-9_.-]+)/g, '<span style="color:#e74c3c;font-weight:bold;">@$1</span>')
  content = content.replace(/\n/g, '<br>')
  return content
}

const loadPost = async () => {
  loading.value = true
  error.value = ''
  try {
    post.value = await apiClient.get(`/api/forum/posts/${route.params.id}`)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const submitReply = async () => {
  if (!replyContent.value.trim()) return
  replySubmitting.value = true
  try {
    await apiClient.post(`/api/forum/posts/${route.params.id}/comments`, {
      content: replyContent.value.trim()
    })
    replyContent.value = ''
    await loadPost()
  } catch (err: any) {
    alert(err.response?.data?.detail || '回复失败')
  } finally {
    replySubmitting.value = false
  }
}

const removePost = async () => {
  if (!confirm('确定删除这个帖子吗？回复将一并删除。')) return
  try {
    await apiClient.delete(`/api/forum/posts/${route.params.id}`)
    router.push('/discuss')
  } catch (err: any) {
    alert(err.response?.data?.detail || '删除失败')
  }
}

onMounted(() => loadPost())
</script>

<template>
  <div class="post-detail-page">
    <div class="detail-container">
      <div v-if="loading" class="state-box">加载中...</div>
      <div v-else-if="error" class="state-box error-text">❌ {{ error }}</div>

      <template v-else-if="post">
        <!-- 帖子主体 -->
        <div class="post-main card">
          <div class="post-title">{{ post.title }}</div>
          <div class="post-meta">
            <img
              :src="post.author?.avatar_url || letterAvatar(post.author?.username)"
              class="meta-avatar"
              :alt="post.author?.username"
            >
            <router-link
              :to="post.author?.user_number ? `/user/${post.author.user_number}` : '#'"
              class="post-author"
              :style="{ color: userColor(post.author) }"
            >{{ post.author?.username }}</router-link>
            <span
              v-if="post.author?.user_tag"
              class="user-tag-display"
              :style="{ backgroundColor: userColor(post.author) }"
            >{{ post.author.user_tag }}</span>
            <span class="post-forum">{{ post.forum_name }}</span>
            <span class="post-time">{{ fmtTime(post.created_at) }}</span>
            <button
              v-if="post.can_manage || post.is_author"
              class="post-delete"
              @click="removePost"
            >删除</button>
          </div>
          <div class="post-content" v-html="renderContent(post.content)"></div>
        </div>

        <!-- 回复列表 -->
        <div class="comments-head">回复（{{ post.comments.length }}）</div>
        <div v-if="post.comments.length === 0" class="state-box">暂无回复</div>
        <div v-else class="comments">
          <div v-for="(c, i) in post.comments" :key="c.id" class="comment-item card">
            <div class="comment-head">
              <img
                :src="c.author?.avatar_url || letterAvatar(c.author?.username)"
                class="meta-avatar"
                :alt="c.author?.username"
              >
              <router-link
                :to="c.author?.user_number ? `/user/${c.author.user_number}` : '#'"
                class="post-author"
                :style="{ color: userColor(c.author) }"
              >{{ c.author?.username }}</router-link>
              <span
                v-if="c.author?.user_tag"
                class="user-tag-display"
                :style="{ backgroundColor: userColor(c.author) }"
              >{{ c.author.user_tag }}</span>
              <span class="comment-floor">#{{ Number(i) + 1 }}</span>
              <span class="comment-time">{{ fmtTime(c.created_at) }}</span>
            </div>
            <div class="comment-content" v-html="renderContent(c.content)"></div>
          </div>
        </div>

        <!-- 回复框 -->
        <div v-if="isLoggedIn" class="reply-box card">
          <div class="reply-box-head">发表回复</div>
          <textarea
            v-model="replyContent"
            rows="4"
            class="reply-textarea"
            placeholder="请输入回复内容……"
            maxlength="10000"
          ></textarea>
          <div class="reply-actions">
            <button class="btn-submit" :disabled="replySubmitting || !replyContent.trim()" @click="submitReply">
              {{ replySubmitting ? '发送中...' : '回复' }}
            </button>
          </div>
        </div>
        <div v-else class="state-box">
          <router-link to="/login" class="link">登录</router-link> 后即可回复
        </div>

        <div class="back-bar">
          <button class="btn-back" @click="router.push('/discuss')">← 返回讨论区</button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.post-detail-page {
  min-height: 100vh;
  line-height: 1.6;
}

.detail-container {
  max-width: 860px;
  margin: 0 auto;
}

.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 18px 22px;
}

.state-box {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  background: #fff;
  border-radius: 12px;
}

.error-text {
  color: #e74c3c;
}

.link {
  color: #e74c3c;
  margin: 0 4px;
}

.post-main {
  margin-bottom: 16px;
}

.post-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 10px;
  word-break: break-word;
}

.post-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 13px;
  color: #8a9aa8;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f2f5;
  margin-bottom: 12px;
}

.meta-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  object-fit: cover;
  background: #f0f2f5;
}

.post-author {
  font-weight: 700;
  text-decoration: none;
}

.user-tag-display {
  display: inline-block;
  border-radius: 2px;
  padding: 1px 8px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}

.post-forum {
  background: #f0f2f5;
  padding: 1px 10px;
  border-radius: 12px;
  font-size: 12px;
  color: #575757;
}

.post-delete {
  margin-left: auto;
  background: none;
  border: none;
  color: #c0c8d0;
  font-size: 12px;
  cursor: pointer;
}

.post-delete:hover {
  color: #e74c3c;
}

.post-content {
  color: #2d3748;
  font-size: 14px;
  word-break: break-word;
}

.post-content :deep(pre) {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
}

.post-content :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}

.comments-head {
  font-weight: 700;
  font-size: 15px;
  color: #8a9aa8;
  margin-bottom: 10px;
  padding: 0 4px;
}

.comments {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.comment-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.comment-floor {
  color: #c0c8d0;
  font-size: 12px;
}

.comment-time {
  color: #a0aec0;
  font-size: 12px;
  margin-left: auto;
}

.comment-content {
  color: #2d3748;
  font-size: 14px;
  word-break: break-word;
}

.comment-content :deep(pre) {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
}

.reply-box-head {
  font-size: 13px;
  color: #8a9aa8;
  margin-bottom: 10px;
}

.reply-textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}

.reply-textarea:focus {
  border-color: #e74c3c;
}

.reply-actions {
  margin-top: 10px;
  text-align: right;
}

.btn-submit {
  padding: 8px 28px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.back-bar {
  margin-top: 16px;
}

.btn-back {
  padding: 8px 22px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.btn-back:hover {
  color: #e74c3c;
  border-color: #e74c3c;
}
</style>
