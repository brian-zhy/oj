<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api/client'
import { fmtDateTime } from '@/utils/datetime'
import { renderMentionText } from '@/utils/markdown'

const router = useRouter()

const TYPE: Record<string, { icon: string; color: string }> = {
  mention: { icon: 'fa-solid fa-at', color: '#2a8eff' },
  reply: { icon: 'fa-solid fa-comment', color: '#3498db' },
  status: { icon: 'fa-solid fa-rotate', color: '#E6A23C' },
  assign: { icon: 'fa-solid fa-user', color: '#9C3DCF' },
  team: { icon: 'fa-solid fa-people-group', color: '#13C2C2' },
}

// 「被 @」只代表提及，与「被回复」是两回事，所以分成不同标签页。
// key 与后端 /notifications?group= 的取值一一对应
const GROUPS = [
  { key: 'all', label: '全部', empty: '暂无通知' },
  { key: 'mention', label: '@我的', empty: '暂无提及' },
  { key: 'reply', label: '回复我的', empty: '暂无回复' },
  { key: 'system', label: '系统通知', empty: '暂无系统通知' },
]

const notifications = ref<any[]>([])
const page = ref(0)
const loading = ref(false)
const hasMore = ref(true)
const error = ref('')
const group = ref('all')
const unreadByGroup = ref<Record<string, number>>({})
const unreadCount = computed(() => unreadByGroup.value.all || 0)
const forceUnread = new Set<number>()

/// 标签页上的未读数红点（全部/系统通知的不单独显示，只靠大数字说明）
const groupBadge = (key: string) => (key === 'all' ? 0 : unreadByGroup.value[key] || 0)

const emptyText = computed(() =>
  GROUPS.find(g => g.key === group.value)?.empty || '暂无通知',
)

const loadUnread = async () => {
  try {
    const data: any = await apiClient.get('/api/notifications/unread-count')
    unreadByGroup.value = { all: data?.count || 0, ...(data?.by_group || {}) }
  } catch {
    /* 顶栏红点失败不影响列表 */
  }
}

const loadNotifications = async (append = false) => {
  if (loading.value || !hasMore.value) return
  loading.value = true
  error.value = ''
  // 切标签时不要把上一个标签的请求结果写进来
  const requested = group.value
  try {
    const data: any = await apiClient.get(
      `/api/notifications?page=${page.value}&page_size=20&group=${encodeURIComponent(requested)}`,
    )
    if (group.value !== requested) return
    const list = Array.isArray(data?.notifications) ? data.notifications : []
    const listWithLocalHighlight = list.map((n: any) => ({
      ...n,
      forceUnread: forceUnread.has(n.id),
    }))
    notifications.value = append
      ? [...notifications.value, ...listWithLocalHighlight]
      : listWithLocalHighlight
    page.value++
    hasMore.value = list.length >= 20
  } catch (err: any) {
    if (group.value !== requested) return
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const switchGroup = (key: string) => {
  if (group.value === key) return
  group.value = key
  notifications.value = []
  page.value = 0
  hasMore.value = true
  loadNotifications(false)
}

/**
 * 读掉消息后立刻让顶栏角标跟上。
 * 不做这件事的话，页面自己的计数已经清了，顶栏却还挂着旧数字，
 * 最长要 30 秒（下一次轮询）才追上，看起来就像没标记已读。
 */
const emitUnreadChanged = () => {
  window.dispatchEvent(new CustomEvent('notifications:changed'))
}

const markAllRead = async () => {
  const unreadIds = notifications.value.filter(n => !n.is_read).map(n => n.id)
  unreadIds.forEach(id => forceUnread.add(id))

  try {
    await apiClient.put('/api/notifications/read-all')
    notifications.value = notifications.value.map(n => ({
      ...n,
      is_read: true,
      forceUnread: forceUnread.has(n.id),
    }))
    unreadByGroup.value = {}
    emitUnreadChanged()
  } catch {
    /* 忽略 */
  }
}

/** 通知的跳转地址：新的通知都带 link，工单类兼容旧的 ticket_id 字段 */
const notificationTarget = (n: any): string | null => {
  if (n.link) return n.link
  if (n.ticket_id) return `/tickets/${n.ticket_id}`
  return null
}

const openNotification = async (n: any) => {
  if (!n.is_read || n.forceUnread) {
    try {
      await apiClient.put(`/api/notifications/${n.id}/read`)
      n.is_read = true
      n.forceUnread = false
      forceUnread.delete(n.id)
      const g = n.type === 'mention' ? 'mention' : n.type === 'reply' ? 'reply' : 'system'
      if (unreadByGroup.value.all > 0) unreadByGroup.value.all--
      if (unreadByGroup.value[g] > 0) unreadByGroup.value[g]--
      emitUnreadChanged()
    } catch {
      /* 忽略 */
    }
  }
  const target = notificationTarget(n)
  if (target) router.push(target)
}

onMounted(async () => {
  loadUnread()
  await loadNotifications(false)
  await markAllRead()
})
</script>

<template>
  <div class="notifications-page">
    <div class="notifications-container">
      <div class="page-head">
        <div>
          <h2 class="page-title">消息通知</h2>
          <p v-if="unreadCount > 0" class="page-sub">{{ unreadCount }} 条未读</p>
        </div>
      </div>

      <!-- 分类标签页：「@我的」和「回复我的」是分开的，
           被 @ 只代表提及，不代表对方回复了你 -->
      <div class="group-tabs">
        <button
          v-for="g in GROUPS"
          :key="g.key"
          class="group-tab"
          :class="{ active: group === g.key }"
          @click="switchGroup(g.key)"
        >
          {{ g.label }}
          <span v-if="groupBadge(g.key) > 0" class="tab-badge">{{ groupBadge(g.key) }}</span>
        </button>
      </div>

      <div v-if="error" class="empty">{{ error }}</div>
      <div v-else-if="!loading && notifications.length === 0" class="empty">
        {{ emptyText }}
      </div>

      <div v-else class="notification-list">
        <div
          v-for="n in notifications"
          :key="n.id"
          class="notification-item"
          :class="{ unread: !n.is_read || n.forceUnread }"
          @click="openNotification(n)"
        >
          <span class="n-icon" :style="{ color: TYPE[n.type]?.color }"><i :class="TYPE[n.type]?.icon || 'fa-solid fa-bell'"></i></span>
          <div class="n-body">
            <div class="n-content">
              <span v-if="!n.is_read || n.forceUnread" class="unread-dot"></span>
              <!-- 文案里的 @用户名 渲染成指向用户主页的链接 -->
              <span v-html="renderMentionText(n.content)"></span>
            </div>
            <div class="n-time">{{ fmtDateTime(n.created_at, '') }}</div>
          </div>
          <span v-if="notificationTarget(n)" class="n-go">›</span>
        </div>
      </div>

      <div class="load-more-wrap">
        <button v-if="hasMore && notifications.length" class="btn-more" :disabled="loading" @click="loadNotifications(true)">
          {{ loading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notifications-page {
  min-height: 100vh;
  line-height: 1.5;
}

.notifications-container {
  max-width: 760px;
  margin: 0 auto;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.page-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #2c3e50;
}

.page-sub {
  color: var(--primary);
  font-size: 13px;
  margin-top: 4px;
}

.btn-read-all {
  padding: 7px 18px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.btn-read-all:hover {
  color: var(--primary);
  border-color: var(--primary);
}

/* ===== 分类标签页 ===== */
.group-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.group-tab {
  position: relative;
  padding: 7px 18px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 20px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.group-tab:hover {
  color: var(--primary);
  border-color: var(--primary);
}

.group-tab.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.tab-badge {
  display: inline-block;
  min-width: 16px;
  padding: 0 4px;
  margin-left: 5px;
  border-radius: 8px;
  background: #f56c6c;
  color: #fff;
  font-size: 11px;
  line-height: 16px;
  text-align: center;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.notification-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--surface);
  backdrop-filter: blur(var(--surface-blur)) saturate(1.5);
  backdrop-filter: blur(var(--surface-blur)) saturate(1.5);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: 14px 18px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.notification-item:hover {
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}

/* 未读底色：主色 #4a4ae0 的浅色调，比已读的白底明显一档。
   原来那个是旧红色主题的暖奶油色 #fdf6ee，放在蓝紫站里色调不对。 */
.notification-item.unread {
  background: #f0f1fd;
}

.n-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.n-body {
  flex: 1;
  min-width: 0;
}

.n-content {
  font-size: 14px;
  color: #2d3748;
  word-break: break-word;
}

.unread-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: var(--primary);
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.n-time {
  font-size: 12px;
  color: #a0aec0;
  margin-top: 3px;
}

.n-go {
  color: #c0c8d0;
  font-size: 20px;
  flex-shrink: 0;
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
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

/* ===== 手机端 ===== */
@media (max-width: 600px) {
  .notification-item {
    padding: 12px 14px;
  }

  /* 四个标签在窄屏上放不下，横向滑动，不要挤压换行 */
  .group-tab {
    padding: 7px 14px;
  }
}
</style>
