<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'
import { userNameColor as userColor } from '@/utils/userColor'
import { fmtDateTime } from '@/utils/datetime'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const CATEGORIES: Record<string, string> = {
  consult: '一般咨询',
  suggestion: '建议反馈',
  bug: 'Bug反馈',
  appeal: '账号申诉',
}

const STATUS: Record<string, { text: string; color: string; bg: string }> = {
  pending: { text: '待处理', color: '#00BCD4', bg: '#E0F7FA' },
  replied: { text: '待补充', color: '#FF9800', bg: '#FFF3E0' },
  processing: { text: '处理中', color: '#D4AC0D', bg: '#FDF6DD' },
  suspended: { text: '挂起', color: '#909399', bg: '#F4F4F5' },
  resolved: { text: '已完成', color: '#52C41A', bg: '#F0FAE5' },
  closed: { text: '已关闭', color: '#E74C3C', bg: '#FDECEC' },
  deleted: { text: '已删除', color: '#909399', bg: '#F4F4F5' },
}

const isStaff = computed(() => {
  const u = authStore.currentUser
  return !!u && (u.can_manage_users || u.is_admin || u.is_super_admin)
})

// scope 由 URL 决定：/tickets = 我的工单，/tickets/all = 全部工单（刷新后保持当前页签）
const scope = computed<'my' | 'all'>(() => (route.path === '/tickets/all' ? 'all' : 'my'))

// 筛选条件放入 URL query（刷新后保持）
const statusFilter = computed({
  get: () => (route.query.status as string) || '',
  set: (v: string) => updateQuery({ status: v || undefined }),
})
const categoryFilter = computed({
  get: () => {
    // 普通用户不提供「账号申诉」筛选（申诉类工单私密）
    const v = (route.query.category as string) || ''
    return !isStaff.value && v === 'appeal' ? '' : v
  },
  set: (v: string) => updateQuery({ category: v || undefined }),
})

// 普通用户的类别下拉不含「账号申诉」
const visibleCategories = computed(() => {
  const entries = { ...CATEGORIES }
  if (!isStaff.value) delete entries.appeal
  return entries
})

// 统一更新 URL query（空值移除，避免脏参数）
const updateQuery = (patch: Record<string, string | undefined>) => {
  const merged: Record<string, string> = {}
  for (const [k, v] of Object.entries({ ...route.query, ...patch })) {
    if (v) merged[k] = String(v)
  }
  router.replace({ query: merged })
}

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
    let url = `/api/tickets?scope=${scope.value}&page=${page.value}&page_size=20`
    if (statusFilter.value) url += `&status=${statusFilter.value}`
    if (categoryFilter.value) url += `&category=${categoryFilter.value}`
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

// 切换页签 = 切换路径（保留筛选条件）
const switchScope = (s: 'my' | 'all') => {
  router.push({ path: s === 'all' ? '/tickets/all' : '/tickets', query: route.query })
}

// 路径或筛选变化 → 重新加载
watch(() => route.fullPath, () => {
  page.value = 0
  hasMore.value = true
  tickets.value = []
  loadTickets(false)
})

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
        <button class="btn-new" @click="router.push('/tickets/new')"><i class="fa-solid fa-pen"></i> 提交工单</button>
      </div>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <div class="tabs">
          <button class="tab" :class="{ active: scope === 'my' }" @click="switchScope('my')">我的工单</button>
          <button class="tab" :class="{ active: scope === 'all' }" @click="switchScope('all')">全部工单</button>
        </div>
        <div class="filter-selects">
          <select v-model="categoryFilter" class="status-select">
            <option value="">全部类别</option>
            <option v-for="(name, key) in visibleCategories" :key="key" :value="key">{{ name }}</option>
          </select>
          <select v-model="statusFilter" class="status-select">
            <option value="">全部状态</option>
            <option v-for="(s, key) in STATUS" :key="key" :value="key">{{ s.text }}</option>
          </select>
        </div>
      </div>

      <!-- 列表 -->
      <div v-if="error && tickets.length === 0" class="empty">{{ error }}</div>
      <div v-else-if="!loading && tickets.length === 0" class="empty">暂无工单</div>

      <div v-else class="ticket-table-wrap">
        <table class="ticket-table">
          <thead>
            <tr>
              <th>编号</th>
              <th v-if="scope === 'all'">发起人</th>
              <th>标题</th>
              <th>类别</th>
              <th>状态</th>
              <th>最后活动</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tickets" :key="t.id" @click="router.push(`/tickets/${t.id}`)">
              <td class="col-no">{{ t.ticket_no }}</td>
              <td v-if="scope === 'all'" class="col-user" :style="{ color: userColor(t.creator) }">
                {{ t.creator?.username }}
              </td>
              <td class="col-title">{{ t.title }}</td>
              <td>{{ CATEGORIES[t.category] || t.category }}</td>
              <td>
                <span class="status-badge" :style="{ color: STATUS[t.status]?.color, backgroundColor: STATUS[t.status]?.bg }">
                  {{ STATUS[t.status]?.text || t.status }}
                </span>
              </td>
              <td class="col-time">{{ fmtDateTime(t.last_reply_at || t.created_at) }}</td>
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
  background: var(--primary);
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
  background: var(--primary-hover);
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
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.filter-selects {
  display: flex;
  gap: 8px;
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

.col-user {
  font-weight: 600;
  white-space: nowrap;
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
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

@media (max-width: 600px) {
  .page-head {
    flex-direction: column;
    align-items: flex-start;
  }

  /* 窄屏下 .filter-bar 原来是 flex 一行：两个下拉框固定占掉 204px，
     把 .tabs 挤到只剩 135px，每个 tab 仅 64px 宽，
     「我的工单」四个字被压成 4 行（高 94px）。改成上下两行、各占满宽度。 */
  .filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .tabs {
    gap: 6px;
  }

  /* flex:1 让两个 tab 等宽平分，而不是被内容挤扁 */
  .tab {
    flex: 1;
    padding: 7px 8px;
    white-space: nowrap;
  }

  .filter-selects {
    gap: 6px;
  }

  .status-select {
    flex: 1;
    min-width: 0;
    padding: 7px 8px;
  }

  /* 6 列表格在 375px 上是 491px 宽，而 .ticket-table-wrap 是 overflow:hidden，
     右侧 140px（状态 / 最后活动）被直接裁掉且无法查看。
     改成可横向滑动，并收紧单元格留白把需要滑动的距离压小。 */
  .ticket-table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .ticket-table {
    font-size: 13px;
  }

  .ticket-table th {
    padding: 10px 8px;
    font-size: 12px;
  }

  .ticket-table td {
    padding: 12px 8px;
  }

  .col-time {
    font-size: 11px;
  }

  /* 6 列全部保留的话，其余 5 列会吃掉 325px，标题只剩 26px 被压成竖排字。
     给标题一个下限，多出来的部分靠 .ticket-table-wrap 横向滑动查看。 */
  .col-title {
    min-width: 130px;
  }

  .status-badge {
    padding: 2px 8px;
  }

  .empty {
    padding: 40px 16px;
  }
}
</style>
