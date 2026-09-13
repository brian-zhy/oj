<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { submissionsApi } from '@/api/submissions'
import { submissionStatusText, submissionStatusColor } from '@/utils/submissionStatus'
import { fmtDateTime } from '@/utils/datetime'
import type { Submission } from '@/types'

const router = useRouter()
const route = useRoute()

const PAGE_SIZE = 20

const problemFilter = computed(() => {
  const p = parseInt(route.query.problem_id as string, 10)
  return Number.isFinite(p) && p > 0 ? p : null
})

const page = computed({
  get: () => {
    const p = parseInt(route.query.page as string, 10)
    return Number.isFinite(p) && p > 0 ? p : 0
  },
  set: (v: number) => updateQuery({ page: v > 0 ? String(v) : undefined }),
})

const updateQuery = (patch: Record<string, string | undefined>) => {
  const merged: Record<string, string> = {}
  for (const [k, v] of Object.entries({ ...route.query, ...patch })) {
    if (v) merged[k] = String(v)
  }
  router.replace({ query: merged })
}

const items = ref<Submission[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

const fetchData = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = problemFilter.value
      ? await submissionsApi.listByProblem(problemFilter.value, {
          page: page.value,
          page_size: PAGE_SIZE,
        })
      : await submissionsApi.listMine({ page: page.value, page_size: PAGE_SIZE })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

watch(() => route.fullPath, fetchData)
onMounted(fetchData)
</script>

<template>
  <div class="submission-list-page">
    <div class="submission-list-container">
      <div class="page-head">
        <div>
          <h2 class="page-title">评测记录</h2>
          <p class="page-sub">
            {{ problemFilter ? `查看题目的全部提交记录` : '我的全部提交记录' }}
          </p>
        </div>
      </div>

      <div class="card">
        <div class="result-count">共 {{ total }} 条记录</div>

        <div v-if="error" class="empty">{{ error }}</div>
        <div v-else-if="!loading && items.length === 0" class="empty">暂无提交记录</div>

        <div v-else class="table-wrap">
          <table class="sub-table">
            <thead>
              <tr>
                <th>提交编号</th>
                <th>题目</th>
                <th v-if="problemFilter">提交者</th>
                <th>状态</th>
                <th>耗时</th>
                <th>内存</th>
                <th>语言</th>
                <th>提交时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in items" :key="s.id" class="row-click" @click="router.push(`/submissions/${s.id}`)">
                <td class="col-no">#{{ s.id }}</td>
                <td>
                  <span class="p-link" @click.stop="router.push(`/problems/${s.problem_id}`)">
                    {{ s.problem_number }} {{ s.problem_title }}
                  </span>
                </td>
                <td v-if="problemFilter" class="col-user">{{ s.user?.username }}</td>
                <td>
                  <span class="status-text" :style="{ color: submissionStatusColor(s.status) }">
                    {{ submissionStatusText(s.status) }}
                  </span>
                </td>
                <td class="col-num">{{ s.time_used === null || s.time_used === undefined ? '—' : s.time_used + ' ms' }}</td>
                <td class="col-num">{{ s.memory_used === null || s.memory_used === undefined ? '—' : (s.memory_used / 1024).toFixed(1) + ' MB' }}</td>
                <td>{{ s.language }}</td>
                <td class="col-time">{{ fmtDateTime(s.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination" v-if="pageCount > 1">
          <button class="page-btn" :disabled="page === 0" @click="page = page - 1">&laquo;</button>
          <span class="page-info">第 {{ page + 1 }} / {{ pageCount }} 页</span>
          <button class="page-btn" :disabled="page >= pageCount - 1" @click="page = page + 1">&raquo;</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.submission-list-page {
  min-height: 100vh;
  line-height: 1.5;
}

.submission-list-container {
  max-width: 1100px;
  margin: 0 auto;
}

.page-head {
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

.card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 20px 24px;
}

.result-count {
  color: #8a9aa8;
  font-size: 13px;
  margin-bottom: 8px;
}

.table-wrap {
  overflow-x: auto;
}

.sub-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.sub-table th {
  text-align: left;
  padding: 11px 12px;
  color: #8a9aa8;
  font-size: 13px;
  border-bottom: 2px solid #edf2f7;
  white-space: nowrap;
}

.sub-table td {
  padding: 13px 12px;
  border-bottom: 1px solid #f0f2f5;
}

.row-click {
  cursor: pointer;
  transition: background 0.15s;
}

.row-click:hover {
  background: #fafbfc;
}

.col-no {
  color: #8a9aa8;
  white-space: nowrap;
}

.col-user {
  font-weight: 600;
  white-space: nowrap;
}

.col-num,
.col-time {
  color: #5b6e8c;
  white-space: nowrap;
  font-size: 13px;
}

.p-link {
  color: #3498db;
  cursor: pointer;
}

.p-link:hover {
  text-decoration: underline;
}

.status-text {
  font-weight: 600;
  white-space: nowrap;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  padding: 18px 0 4px;
}

.page-btn {
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: #5b6e8c;
}

.empty {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

/* ===== 手机端：原本无任何媒体查询 ===== */
@media (max-width: 600px) {
  .card {
    padding: 16px 14px;
  }
}
</style>
