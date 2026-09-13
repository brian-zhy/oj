<script setup lang="ts">
/**
 * 犇犇列表（只读版）—— 用于用户主页的「动态」标签页。
 *
 * 与首页的犇犇模块同源但做了精简：
 *   - 没有发布框，没有「全部 / 我的」切换
 *   - 没有「举报 / 回复」按钮（那是首页才需要的互动操作）
 *   - 只保留「删除」，且仅当这条犇犇是当前登录用户自己发的
 *     （是否本人由后端返回的 is_owner 决定，前端不做判断）
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import apiClient from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { userNameColor } from '@/utils/userColor'
import { renderRichText as renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  /** 要展示谁的动态（用户的 user_number，不是数据库主键） */
  userNumber: number
}>()

const PAGE_SIZE = 20

const authStore = useAuthStore()
const list = ref<any[]>([])
const loading = ref(false)
const hasMore = ref(true)
const lastId = ref<number | null>(null)
const failed = ref(false)

const sentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

const isSelf = computed(
  () => authStore.currentUser?.user_number === props.userNumber,
)
const isEmpty = computed(() => !loading.value && !failed.value && list.value.length === 0)
const emptyText = computed(() =>
  isSelf.value ? '你还没有发过动态' : 'TA 还没有发过动态',
)
const sentinelText = computed(() => {
  if (failed.value) return '加载出错，请刷新页面重试'
  if (loading.value) return '加载中...'
  if (list.value.length === 0) return ''
  return hasMore.value ? '滚动加载更多...' : '没有更多动态了'
})

/* ---------------- 展示用的小工具（与首页保持一致） ---------------- */

const getUserDisplayColor = (user: any) => userNameColor(user)

const getUserTagDisplay = (user: any) => {
  if (!user) return ''
  if (user.is_cheater) {
    return user.is_admin ? user.user_tag || '管理员' : '作弊者'
  }
  return user.user_tag || ''
}

const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

const getUserAvatar = (item: any) => item.avatar_url || letterAvatar(item.username)

const formatTime = (dateStr: string) => new Date(dateStr).toLocaleString('zh-CN')

/* ---------------- 加载 ---------------- */

async function loadMore(reset = false) {
  if (loading.value) return
  if (!reset && !hasMore.value) return

  if (reset) {
    list.value = []
    lastId.value = null
    hasMore.value = true
    failed.value = false
  }

  loading.value = true
  try {
    let url = `/benben?limit=${PAGE_SIZE}&user_number=${props.userNumber}`
    if (lastId.value) url += `&before_id=${lastId.value}`

    const data = (await apiClient.get(url)) as any[]

    if (data && data.length > 0) {
      list.value = reset ? data : [...list.value, ...data]
      lastId.value = data[data.length - 1].id
      hasMore.value = data.length === PAGE_SIZE
    } else {
      hasMore.value = false
    }
  } catch (err) {
    console.error(err)
    failed.value = true
  } finally {
    loading.value = false
  }
}

/* ---------------- 删除（仅本人的犇犇会显示按钮） ---------------- */

async function remove(item: any) {
  try {
    await apiClient.delete(`/benben/${item.id}`)
    // 本地移除即可，不用整页重拉（列表会闪一下）
    list.value = list.value.filter((x) => x.id !== item.id)
  } catch (err: any) {
    alert('删除失败：' + (err.response?.data?.detail || err.message || '未知错误'))
  }
}

/* ---------------- 滚动到底自动加载 ---------------- */

function setupObserver() {
  if (!sentinelRef.value) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) void loadMore(false)
    },
    { rootMargin: '120px' },
  )
  observer.observe(sentinelRef.value)
}

onMounted(() => {
  void loadMore(true)
  setupObserver()
})

// 在用户主页之间跳转时组件不会重建，得手动重新拉
watch(
  () => props.userNumber,
  () => {
    if (sentinelRef.value) observer?.unobserve(sentinelRef.value)
    void loadMore(true).then(setupObserver)
  },
)

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})
</script>

<template>
  <div class="benben-feed">
    <div v-if="isEmpty" class="benben-empty">{{ emptyText }}</div>

    <div class="benben-list">
      <div v-for="item in list" :key="item.id" class="benben-item">
        <div class="benben-avatar">
          <router-link :to="`/user/${item.user_number}`">
            <img
              :src="getUserAvatar(item)"
              :alt="item.username"
              @error="($event.target as HTMLImageElement).src = letterAvatar(item.username)"
            >
          </router-link>
        </div>

        <div class="benben-content">
          <div class="benben-item-header">
            <div class="post-author">
              <span class="benben-user">
                <router-link
                  :to="`/user/${item.user_number}`"
                  class="benben-username"
                  :style="{ color: getUserDisplayColor(item) }"
                >{{ item.username }}</router-link><span
                  v-if="getUserTagDisplay(item)"
                  class="user-tag-display"
                  :style="{ backgroundColor: getUserDisplayColor(item) }"
                >{{ getUserTagDisplay(item) }}</span>
              </span>
              <span class="benben-time">{{ formatTime(item.created_at) }}</span>
            </div>

            <!-- 只有本人发的犇犇才给删除按钮 -->
            <div v-if="item.is_owner" class="benben-actions">
              <button class="benben-delete" @click="remove(item)">删除</button>
            </div>
          </div>

          <div class="benben-text prose" v-html="renderMarkdown(item.content)" />

          <div v-if="item.reply_to_username" class="benben-reply-hint">
            <i class="fa-solid fa-reply" /> 回复了 @{{ item.reply_to_username }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="sentinelText" ref="sentinelRef" class="feed-sentinel">
      {{ sentinelText }}
    </div>
  </div>
</template>

<style scoped>
.benben-empty {
  padding: 48px 0;
  text-align: center;
  font-size: 14px;
  color: #a0aec0;
}

.benben-list {
  margin-top: 4px;
}

.benben-item {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  position: relative;
}

.benben-avatar {
  flex-shrink: 0;
  width: 40px;
  margin-top: 8px;
}

.benben-avatar a {
  display: block;
}

.benben-avatar img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  background: #f0f2f5;
}

.benben-content {
  flex: 1;
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 16px;
  padding: 8px 16px;
  position: relative;
}

.benben-content::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 16px;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 8px 8px 8px 0;
  border-color: transparent #f0f2f5 transparent transparent;
  z-index: 1;
}

.benben-content::after {
  content: '';
  position: absolute;
  left: -9px;
  top: 16px;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 8px 8px 8px 0;
  border-color: transparent #e9ecef transparent transparent;
  z-index: 0;
}

.benben-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  background: #f0f2f5;
  padding: 6px 12px;
  margin: -12px -16px 12px -16px;
  border-radius: 16px 16px 0 0;
}

.post-author {
  display: flex;
  align-items: center;
  gap: 4px 8px;
  flex-wrap: wrap;
}

.benben-user {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
}

.benben-username {
  font-weight: bold;
  color: #333;
  text-decoration: none;
  font-size: 14px;
  vertical-align: middle;
}

.benben-username:hover {
  color: var(--primary);
}

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
}

.user-tag-display:hover {
  filter: brightness(0.9);
}

.benben-time {
  font-size: 12px;
  color: #999;
}

.benben-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.benben-delete {
  background: none;
  border: none;
  color: #999;
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}

.benben-delete:hover {
  color: var(--primary);
}

.benben-text {
  word-break: break-word;
}

.benben-text :deep(pre) {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 12px;
  overflow-x: auto;
  margin: 8px 0;
}

.benben-text :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.benben-text :deep(a) {
  color: var(--primary);
  text-decoration: none;
}

.benben-text :deep(a:hover) {
  text-decoration: underline;
}

.benben-reply-hint {
  font-size: 12px;
  color: #90a0b4;
  margin-top: 6px;
}

.feed-sentinel {
  padding: 14px 0;
  text-align: center;
  font-size: 12px;
  color: #a0aec0;
}
</style>
