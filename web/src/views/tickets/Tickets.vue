<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const authStore = useAuthStore()

const CATEGORIES: Record<string, string> = {
  consult: '一般咨询',
  suggestion: '建议反馈',
  bug: 'Bug反馈',
  appeal: '账号申诉',
}

const STATUS: Record<string, { text: string; color: string }> = {
  pending: { text: '待处理', color: '#E6A23C' },
  replied: { text: '待补充', color: '#3498db' },
  processing: { text: '处理中', color: '#3498db' },
  suspended: { text: '挂起', color: '#909399' },
  resolved: { text: '已完成', color: '#52C41A' },
  closed: { text: '已关闭', color: '#909399' },
  deleted: { text: '已删除', color: '#e74c3c' },
}

const isStaff = computed(() => {
  const u = authStore.currentUser
  return !!u && (u.can_manage_users || u.is_admin || u.is_super_admin)
})

const scope = ref<'my' | 'all'>('my')
const statusFilter = ref('')
const tickets = ref<any[]>([])
const page = ref(0)
const loading = ref(false)
const hasMore = ref(true)
const error = ref('')

const loadTickets = async (append = false) => {
  if (loading.value || !hasMore.value) return
  loading.value = true
  error.value = ''
  try {
    let url = `/tickets?scope=${scope.value}&page=${page.value}&page_size=20`
    if (statusFilter.value) url += `&status=${statusFilter.value}`
    const data: any = await apiClient.get(url)
    // 响应校验：防止被劫持/改写的请求返回非预期内容
    const list = Array.isArray(data?.tickets) ? data.tickets : []
    tickets.value = append ? [...tickets.value, ...list] : list
    page.value++
    hasMore.value = list.length >= 20
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const switchScope = (s: 'my' | 'all') => {
  scope.value = s
  page.value = 0
  hasMore.value = true
  tickets.value = []
  loadTickets(false)
}

const changeFilter = () => {
  page.value = 0
  hasMore.value = true
  tickets.value = []
  loadTickets(false)
}

const fmtTime = (iso: string) => (iso ? String(iso).replace('T', ' ').slice(0, 16) : '—')

onMounted(() => loadTickets(false))
</script>

<template>
  <div class="tickets-page">
    <div class="tickets-container">
      <!-- 头部 -->
      <div class="page-head">
        <div>
          <h2 class="page-title">工单中心</h2>
          <p class="page-sub">一事一单，标题明确；管理员通常会在 2 周内回复，请勿催促。</p>
        </div>
        <button class="btn-new" @click="router.push('/tickets/new')">✏️ 提交工单</button>
      </div>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <div class="tabs">
          <button class="tab" :class="{ active: scope === 'my' }" @click="switchScope('my')">我的工单</button>
          <button v-if="isStaff" class="tab" :class="{ active: scope === 'all' }" @click="switchScope('all')">全部工单</button>
        </div>
        <select v-model="statusFilter" class="status-select" @change="changeFilter">
          <option value="">全部状态</option>
          <option v-for="(s, key) in STATUS" :key="key" :value="key">{{ s.text }}</option>
        </select>
      </div>

      <!-- 列表 -->
      <div v-if="error && tickets.length === 0" class="empty">{{ error }}</div>
      <div v-else-if="!loading && tickets.length === 0" class="empty">暂无工单</div>

      <div v-else class="ticket-table-wrap">
        <table class="ticket-table">
          <thead>
            <tr>
              <th>编号</th>
              <th>标题</th>
              <th>类别</th>
              <th>状态</th>
              <th>最后活动</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tickets" :key="t.id" @click="router.push(`/tickets/${t.id}`)">
              <td class="col-no">{{ t.ticket_no }}</td>
              <td class="col-title">{{ t.title }}</td>
              <td>{{ CATEGORIES[t.category] || t.category }}</td>
              <td>
                <span class="status-badge" :style="{ backgroundColor: STATUS[t.status]?.color }">
                  {{ STATUS[t.status]?.text || t.status }}
                </span>
              </td>
              <td class="col-time">{{ fmtTime(t.last_reply_at || t.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="load-more-wrap">
        <button v-if="hasMore" class="btn-more" :disabled="loading" @click="loadTickets(true)">
          {{ loading ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tickets-page {
  min-height: 100vh;
  line-height: 1.5;
}

.tickets-container {
  max-width: 1100px;
  margin: 0 auto;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
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
  transition: background 0.2s;
  white-space: nowrap;
}

.btn-new:hover {
  background: #c0392b;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.tabs {
  display: flex;
  gap: 8px;
}

.tab {
  padding: 7px 20px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  color: #4a5568;
  transition: all 0.2s;
}

.tab.active {
  background: #e74c3c;
  border-color: #e74c3c;
  color: #fff;
}

.status-select {
  padding: 7px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #4a5568;
  background: #fff;
}

.ticket-table-wrap {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.ticket-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.ticket-table th {
  text-align: left;
  padding: 11px 16px;
  color: #8a9aa8;
  font-size: 13px;
  border-bottom: 2px solid #edf2f7;
  white-space: nowrap;
}

.ticket-table td {
  padding: 13px 16px;
  border-bottom: 1px solid #f0f2f5;
}

.ticket-table tbody tr {
  cursor: pointer;
  transition: background 0.15s;
}

.ticket-table tbody tr:hover {
  background: #fafbfc;
}

.col-no {
  color: #8a9aa8;
  white-space: nowrap;
}

.col-title {
  font-weight: 600;
  color: #2c3e50;
}

.col-time {
  color: #8a9aa8;
  font-size: 13px;
  white-space: nowrap;
}

.status-badge {
  display: inline-block;
  padding: 2px 12px;
  border-radius: 20px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
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

@media (max-width: 600px) {
  .page-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
