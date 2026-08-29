<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const authStore = useAuthStore()

const FORUMS: Record<string, string> = {
  all: '全部',
  siteaffairs: '站务版',
  problem: '题目总版',
  academics: '学术版',
  relevantaffairs: '灌水区',
}

const forumKeys = Object.keys(FORUMS)

const currentForum = ref('all')
const posts = ref<any[]>([])
const page = ref(0)
const loading = ref(false)
const hasMore = ref(true)
const error = ref('')

const isStaff = computed(() => {
  const u = authStore.currentUser
  return !!u && (u.can_manage_posts || u.is_admin || u.is_super_admin)
})

const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

const userColor = (u: any) => (u?.is_banned ? '#95a5a6' : u?.is_admin ? '#9C3DCF' : '#e74c3c')

const relTime = (iso: string) => {
  if (!iso) return ''
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 172800000) {
    const d = Math.floor(diff / 86400)
    if (d === 1) return '昨天'
    if (d === 2) return '前天'
    if (d < 30) return `${d} 天前`
  }
  return new Date(iso).toLocaleDateString('zh-CN')
}

const loadPosts = async (append = false) => {
  if (loading.value || !hasMore.value) return
  loading.value = true
  error.value = ''
  try {
    let url = `/api/forum/posts?page=${page.value}&page_size=30`
    if (currentForum.value !== 'all') url += `&forum=${currentForum.value}`
    const data: any = await apiClient.get(url)
    const list = Array.isArray(data?.posts) ? data.posts : []
    posts.value = append ? [...posts.value, ...list] : list
    page.value++
    hasMore.value = list.length >= 30
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const switchForum = (f: string) => {
  currentForum.value = f
  page.value = 0
  hasMore.value = true
  posts.value = []
  loadPosts(false)
}

const removePost = async (id: number) => {
  if (!confirm('确定删除这个帖子吗？回复将一并删除。')) return
  try {
    await apiClient.delete(`/api/forum/posts/${id}`)
    posts.value = posts.value.filter(p => p.id !== id)
  } catch (err: any) {
    alert(err.response?.data?.detail || '删除失败')
  }
}

const canDelete = (p: any) =>
  isStaff.value || (authStore.currentUser && p.author?.user_id === authStore.currentUser.id)

onMounted(() => loadPosts(false))
</script>

<template>
  <div class="discuss-page">
    <div class="discuss-container">
      <!-- 头部 -->
      <div class="page-head">
        <div>
          <h2 class="page-title">讨论区</h2>
          <p class="page-sub">文明发言，理性讨论</p>
        </div>
        <button class="btn-new" @click="router.push('/discuss/new')">✏️ 发布帖子</button>
      </div>

      <!-- 版块筛选 -->
      <div class="forum-tabs">
        <button
          v-for="(name, key) in FORUMS"
          :key="key"
          class="forum-tab"
          :class="{ active: currentForum === key }"
          @click="switchForum(key)"
        >{{ name }}</button>
      </div>

      <!-- 帖子列表 -->
      <div v-if="error && posts.length === 0" class="empty">{{ error }}</div>
      <div v-else-if="!loading && posts.length === 0" class="empty">暂无帖子，来发第一贴吧</div>

      <div v-else class="post-list">
        <div v-for="p in posts" :key="p.id" class="post-card" @click="router.push(`/discuss/${p.id}`)">
          <div class="post-avatar">
            <img
              :src="p.author?.avatar_url || letterAvatar(p.author?.username)"
              :alt="p.author?.username"
              @error="($event.target as HTMLImageElement).src = letterAvatar(p.author?.username)"
            >
          </div>
          <div class="post-main">
            <div class="post-title">{{ p.title }}</div>
            <div class="post-meta">
              <router-link
                :to="p.author?.user_number ? `/user/${p.author.user_number}` : '#'"
                class="post-author"
                :style="{ color: userColor(p.author) }"
                @click.stop
              >{{ p.author?.username }}</router-link>
              <span
                v-if="p.author?.user_tag"
                class="user-tag-display"
                :style="{ backgroundColor: userColor(p.author) }"
              >{{ p.author.user_tag }}</span>
              <span class="post-forum">{{ p.forum_name }}</span>
              <span class="post-time">{{ relTime(p.created_at) }}</span>
              <span class="post-replies">{{ p.reply_count }} 回复</span>
              <button
                v-if="canDelete(p)"
                class="post-delete"
                title="删除帖子"
                @click.stop="removePost(p.id)"
              >删除</button>
            </div>
          </div>
        </div>
      </div>

      <div class="load-more-wrap">
        <button v-if="hasMore && posts.length" class="btn-more" :disabled="loading" @click="loadPosts(true)">
          {{ loading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.discuss-page {
  min-height: 100vh;
  line-height: 1.5;
}

.discuss-container {
  max-width: 1000px;
  margin: 0 auto;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
}

.page-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #2c3e50;
}

.page-sub {
  color: #8a9aa8;
  font-size: 13px;
  margin-top: 4px;
}

.btn-new {
  padding: 9px 22px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.btn-new:hover {
  background: #c0392b;
}

.forum-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.forum-tab {
  padding: 7px 20px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  color: #4a5568;
  transition: all 0.2s;
}

.forum-tab.active {
  background: #e74c3c;
  border-color: #e74c3c;
  color: #fff;
}

.post-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.post-card {
  display: flex;
  gap: 14px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 16px 18px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.post-card:hover {
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}

.post-avatar img {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  object-fit: cover;
  background: #f0f2f5;
}

.post-main {
  flex: 1;
  min-width: 0;
}

.post-title {
  font-weight: 700;
  font-size: 15px;
  color: #2c3e50;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.post-card:hover .post-title {
  color: #e74c3c;
}

.post-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 13px;
  color: #8a9aa8;
}

.post-author {
  font-weight: 600;
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

.post-replies {
  margin-left: auto;
}

.post-delete {
  background: none;
  border: none;
  color: #c0c8d0;
  font-size: 12px;
  cursor: pointer;
}

.post-delete:hover {
  color: #e74c3c;
}

.empty {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  background: #fff;
  border-radius: 12px;
}

.load-more-wrap {
  text-align: center;
  padding: 16px 0;
}

.btn-more {
  padding: 9px 36px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 22px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.btn-more:hover:not(:disabled) {
  background: #e74c3c;
  border-color: #e74c3c;
  color: #fff;
}
</style>
