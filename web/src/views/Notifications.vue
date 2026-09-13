<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api/client'
import { fmtDateTime } from '@/utils/datetime'

const router = useRouter()

const TYPE: Record<string, { icon: string; color: string }> = {
  reply: { icon: 'fa-solid fa-comment', color: '#3498db' },
  status: { icon: 'fa-solid fa-rotate', color: '#E6A23C' },
  assign: { icon: 'fa-solid fa-user', color: '#9C3DCF' },
  team: { icon: 'fa-solid fa-people-group', color: '#13C2C2' },
}

const notifications = ref<any[]>([])
const page = ref(0)
const loading = ref(false)
const hasMore = ref(true)
const error = ref('')
const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)

const loadNotifications = async (append = false) => {
  if (loading.value || !hasMore.value) return
  loading.value = true
  error.value = ''
  try {
    const data: any = await apiClient.get(`/api/notifications?page=${page.value}&page_size=20`)
    const list = Array.isArray(data?.notifications) ? data.notifications : []
    notifications.value = append ? [...notifications.value, ...list] : list
    page.value++
    hasMore.value = list.length >= 20
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const markAllRead = async () => {
  try {
    await apiClient.put('/api/notifications/read-all')
    notifications.value = notifications.value.map(n => ({ ...n, is_read: true }))
  } catch {
    /* 忽略 */
  }
}

const openNotification = async (n: any) => {
  if (!n.is_read) {
    try {
      await apiClient.put(`/api/notifications/${n.id}/read`)
      n.is_read = true
    } catch {
      /* 忽略 */
    }
  }
  if (n.ticket_id) router.push(`/tickets/${n.ticket_id}`)
}

onMounted(() => loadNotifications(false))
</script>

<template>
  <div class="notifications-page">
    <div class="notifications-container">
      <div class="page-head">
        <div>
          <h2 class="page-title">消息通知</h2>
          <p v-if="unreadCount > 0" class="page-sub">{{ unreadCount }} 条未读</p>
        </div>
        <button v-if="unreadCount > 0" class="btn-read-all" @click="markAllRead">全部已读</button>
      </div>

      <div v-if="error" class="empty">{{ error }}</div>
      <div v-else-if="!loading && notifications.length === 0" class="empty">暂无通知</div>

      <div v-else class="notification-list">
        <div
          v-for="n in notifications"
          :key="n.id"
          class="notification-item"
          :class="{ unread: !n.is_read }"
          @click="openNotification(n)"
        >
          <span class="n-icon" :style="{ color: TYPE[n.type]?.color }"><i :class="TYPE[n.type]?.icon || 'fa-solid fa-bell'"></i></span>
          <div class="n-body">
            <div class="n-content">
              <span v-if="!n.is_read" class="unread-dot"></span>
              {{ n.content }}
            </div>
            <div class="n-time">{{ fmtDateTime(n.created_at, '') }}</div>
          </div>
          <span v-if="n.ticket_id" class="n-go">›</span>
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

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.notification-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 14px 18px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.notification-item:hover {
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}

.notification-item.unread {
  background: #fdf6ee;
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

/* ===== 手机端：原本无任何媒体查询 ===== */
@media (max-width: 600px) {
  .notification-item {
    padding: 12px 14px;
  }
}
</style>
