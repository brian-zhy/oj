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

// 编辑已发布帖子（仅秩序管理）
const editingPost = ref(false)
const editTitle = ref('')
const editContent = ref('')
const editSaving = ref(false)

const startEditPost = () => {
  editTitle.value = post.value.title
  editContent.value = post.value.content
  editingPost.value = true
}

const cancelEditPost = () => {
  editingPost.value = false
}

const saveEditPost = async () => {
  if (!editTitle.value.trim() || editTitle.value.trim().length < 3) {
    alert('标题至少 3 个字符')
    return
  }
  if (!editContent.value.trim()) {
    alert('正文不能为空')
    return
  }
  editSaving.value = true
  try {
    const res: any = await apiClient.put(`/api/forum/posts/${route.params.id}`, {
      title: editTitle.value.trim(),
      content: editContent.value.trim()
    })
    post.value.title = res.title
    post.value.content = res.content
    editingPost.value = false
  } catch (err: any) {
    alert(err.response?.data?.detail || '保存失败')
  } finally {
    editSaving.value = false
  }
}

// 置顶/锁定（仅秩序管理）——乐观更新，失败回滚
const togglePinPost = async () => {
  const target = !post.value.is_pinned
  post.value.is_pinned = target
  try {
    const res: any = await apiClient.put(`/api/forum/posts/${route.params.id}/moderate`, { is_pinned: target })
    post.value.is_pinned = res.is_pinned
  } catch (err: any) {
    post.value.is_pinned = !target
    alert(err.response?.data?.detail || err.message || '操作失败')
  }
}

const toggleLockPost = async () => {
  const target = !post.value.is_locked
  post.value.is_locked = target
  try {
    const res: any = await apiClient.put(`/api/forum/posts/${route.params.id}/moderate`, { is_locked: target })
    post.value.is_locked = res.is_locked
  } catch (err: any) {
    post.value.is_locked = !target
    alert(err.response?.data?.detail || err.message || '操作失败')
  }
}

const isLoggedIn = computed(() => authStore.isAuthenticated)
const isMuted = computed(() => authStore.currentUser?.can_speak === false)

const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

const userColor = (u: any) => (u?.is_banned ? '#95a5a6' : u?.is_admin ? '#9C3DCF' : '#e74c3c')

const fmtTime = (iso: string) => {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// 富文本渲染（Markdown + LaTeX 公式）
import { renderRichText } from '@/utils/markdown'
const renderContent = (content: string) => renderRichText(content)

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

// 举报（占位）
const reportPost = () => {
  alert('举报功能暂未开放，如有问题请通过工单联系我们')
}

onMounted(() => loadPost())
</script>

<template>
  <div class="post-detail-page">
    <div class="detail-container">
      <div v-if="loading" class="state-box">加载中...</div>
      <div v-else-if="error" class="state-box error-text">❌ {{ error }}</div>

      <template v-else-if="post">
        <!-- ===== 左主栏：标题/作者/正文/回复 ===== -->
        <div class="main-col">
          <div class="post-head-card">
            <h1 class="post-title">{{ post.title }}</h1>
            <span v-if="post.is_pinned" class="pin-badge">置顶</span>
            <span v-if="post.is_locked" class="lock-badge">🔒 已锁定</span>
            <div class="author-line">
              <img
                :src="post.author?.avatar_url || letterAvatar(post.author?.username)"
                class="author-avatar"
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
              <span v-if="post.author?.is_admin" class="staff-badge">管理员</span>
              <span class="post-time">发表于 {{ fmtTime(post.created_at) }}</span>
              <button
                v-if="post.can_manage || post.is_author"
                class="head-btn danger"
                @click="removePost"
              >删除</button>
            </div>
          </div>

          <!-- 正文卡片 -->
          <div class="content-card prose" v-html="renderContent(post.content)"></div>

          <!-- 回复列表 -->
          <div class="comments-head">回复（{{ post.comments.length }}）</div>
          <div v-if="post.comments.length === 0" class="state-box">暂无回复</div>
          <div v-else class="comments">
            <div v-for="(c, i) in post.comments" :key="c.id" class="comment-item">
              <div class="comment-head">
                <img
                  :src="c.author?.avatar_url || letterAvatar(c.author?.username)"
                  class="comment-avatar"
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
              <div class="comment-content prose" v-html="renderContent(c.content)"></div>
            </div>
          </div>

          <!-- 回复框 -->
          <div v-if="isLoggedIn && isMuted" class="state-box">⛔ 你已被禁言，无法回复</div>
          <div v-else-if="isLoggedIn && post.is_locked" class="state-box">🔒 该帖子已锁定，无法回复</div>
          <div v-else-if="isLoggedIn" class="reply-box">
            <div class="reply-box-head">发表回复</div>
            <textarea
              v-model="replyContent"
              rows="4"
              class="reply-textarea"
              placeholder="支持 Markdown：**粗体**、*斜体*、```代码块```、$公式$"
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
        </div>

        <!-- ===== 右侧信息栏 ===== -->
        <aside class="side-col">
          <div class="info-card">
            <div class="info-card-title">帖子信息</div>

            <div class="side-row">
              <span class="side-label">创建者</span>
              <span class="side-value">
                <img
                  :src="post.author?.avatar_url || letterAvatar(post.author?.username)"
                  class="side-avatar"
                  :alt="post.author?.username"
                >
                <router-link
                  :to="post.author?.user_number ? `/user/${post.author.user_number}` : '#'"
                  class="post-author"
                  :style="{ color: userColor(post.author) }"
                >{{ post.author?.username }}</router-link>
              </span>
            </div>

            <div class="side-row">
              <span class="side-label">发帖时间</span>
              <span class="side-value">{{ fmtTime(post.created_at) }}</span>
            </div>

            <div class="side-row">
              <span class="side-label">所属板块</span>
              <span class="side-value forum-text">{{ post.forum_name }}</span>
            </div>

            <div class="side-row">
              <span class="side-label">状态</span>
              <span class="side-value">
                <span v-if="post.is_pinned" class="pin-badge">置顶中</span>
                <span v-if="post.is_locked" class="lock-badge-side">已锁定</span>
                <span v-if="!post.is_pinned && !post.is_locked">正常</span>
              </span>
            </div>

            <!-- 管理操作（仅秩序管理） -->
            <template v-if="post.can_manage">
              <div class="side-divider"></div>
              <div class="side-label manage-title">管理操作</div>
              <button class="side-action-btn" @click="togglePinPost">
                {{ post.is_pinned ? '📌 取消置顶' : '📌 置顶' }}
              </button>
              <button class="side-action-btn" @click="toggleLockPost">
                {{ post.is_locked ? '🔓 解锁' : '🔒 锁定' }}
              </button>
            </template>

            <div class="side-divider"></div>
            <button class="report-btn" @click="reportPost">🚩 举报</button>
          </div>
        </aside>
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
  max-width: 1100px;
  margin: 0 auto;
}

/* ===== 双栏布局 ===== */
.detail-container {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 16px;
  align-items: start;
}

.main-col {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.side-col {
  position: sticky;
  top: 70px;
}

/* ===== 标题与作者 ===== */
.post-head-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 20px 24px 14px;
}

.post-title {
  font-size: 1.55rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 12px;
  word-break: break-word;
  line-height: 1.4;
}

.pin-badge {
  display: inline-block;
  background: #e74c3c;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 4px;
  margin-right: 8px;
  vertical-align: middle;
}

.lock-badge-side {
  display: inline-block;
  background: #e67e22;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 4px;
  margin-right: 8px;
  vertical-align: middle;
}

.author-line {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 14px;
  color: #8a9aa8;
}

.author-avatar {
  width: 36px;
  height: 36px;
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

.staff-badge {
  background: #e74c3c;
  color: #fff;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.post-time {
  color: #a0aec0;
  font-size: 13px;
}

.head-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: #c0c8d0;
  font-size: 12px;
  cursor: pointer;
}

.head-btn:hover {
  color: #e74c3c;
}

/* ===== 正文卡片 ===== */
.content-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 20px 24px;
  color: #2d3748;
  font-size: 15px;
  word-break: break-word;
}

.content-card :deep(pre) {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
}

.content-card :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}

.content-card :deep(a) {
  color: #e74c3c;
}

/* ===== 右侧信息卡 ===== */
.side-col {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.info-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-card-title {
  font-weight: 700;
  font-size: 14px;
  color: #2c3e50;
  padding-bottom: 10px;
  border-bottom: 1px solid #eef1f5;
}

.side-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.side-label {
  color: #8a9aa8;
  flex-shrink: 0;
}

.side-value {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #2c3e50;
  font-weight: 600;
  text-align: right;
}

.side-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  object-fit: cover;
  background: #f0f2f5;
}

.forum-text {
  color: #3498db;
}

.side-divider {
  height: 1px;
  background: #eef1f5;
  margin: 2px 0;
}

.manage-title {
  font-size: 13px;
  font-weight: 700;
  color: #47536b;
}

.side-action-btn {
  padding: 8px 14px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.side-action-btn:hover {
  border-color: #e74c3c;
  color: #e74c3c;
}

.report-btn {
  margin-top: 4px;
  padding: 8px 14px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #e74c3c;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.report-btn:hover {
  border-color: #e74c3c;
  background: #fdf1ef;
}

/* ===== 回复 ===== */
.comments-head {
  font-weight: 700;
  font-size: 15px;
  color: #2c3e50;
  margin-bottom: 10px;
}

.comments {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.comment-item {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 14px 18px;
}

.comment-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.comment-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  object-fit: cover;
  background: #f0f2f5;
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

/* ===== 回复框 ===== */
.reply-box {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 16px 18px;
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

.state-box {
  text-align: center;
  padding: 40px 20px;
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

/* ===== 响应式：窄屏单列 ===== */
@media (max-width: 900px) {
  .detail-container {
    grid-template-columns: 1fr;
  }

  .side-col {
    position: static;
  }
}
</style>
