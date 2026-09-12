<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { problemsApi } from '@/api/problems'
import type { ProblemListItem } from '@/types'
import { DIFFICULTY_LIST, difficultyColor } from '@/utils/difficulty'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 严格只认题目管理权限
const canManage = computed(() => !!authStore.currentUser?.can_manage_problems)

const PAGE_SIZE = 20

// 筛选条件放入 URL query（刷新 / 后退均保持），与 Tickets.vue 同一套路
const difficultyFilter = computed({
  get: () => (route.query.difficulty as string) || '',
  set: (v: string) => updateQuery({ difficulty: v || undefined }),
})
const sourceFilter = computed({
  get: () => (route.query.source as string) || '',
  set: (v: string) => updateQuery({ source: v || undefined }),
})

// 关键词是「应用后」才进 URL：输入框是本地态，点搜索 / 回车才生效
const keywordInput = ref((route.query.keyword as string) || '')

// 页码（0-based，与后端一致）
const page = computed({
  get: () => {
    const p = parseInt(route.query.page as string, 10)
    return Number.isFinite(p) && p > 0 ? p : 0
  },
  set: (v: number) => updateQuery({ page: v > 0 ? String(v) : undefined }),
})

// 统一更新 URL query（空值移除，避免脏参数）
const updateQuery = (patch: Record<string, string | undefined>) => {
  const merged: Record<string, string> = {}
  for (const [k, v] of Object.entries({ ...route.query, ...patch })) {
    if (v) merged[k] = String(v)
  }
  router.replace({ query: merged })
}

const applyFilters = () => {
  // 搜索视为回到第一页
  const merged: Record<string, string> = {}
  for (const [k, v] of Object.entries({
    difficulty: difficultyFilter.value,
    source: sourceFilter.value,
    keyword: keywordInput.value.trim(),
  })) {
    if (v) merged[k] = String(v)
  }
  router.replace({ query: merged })
}

const resetFilters = () => {
  keywordInput.value = ''
  router.replace({ query: {} })
}

const items = ref<ProblemListItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const sources = ref<string[]>([])

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

// 数字分页：首尾 + 当前页邻域，超过窗口画省略号（-1 哨兵）
const pagesToShow = computed<number[]>(() => {
  const n = pageCount.value
  const cur = page.value
  if (n <= 7) return Array.from({ length: n }, (_, i) => i)
  const wanted = new Set<number>([0, n - 1, cur - 1, cur, cur + 1])
  const arr = [...wanted].filter((p) => p >= 0 && p < n).sort((a, b) => a - b)
  const out: number[] = []
  let prev = -2
  for (const p of arr) {
    if (prev !== -2 && p - prev > 1) out.push(-1)
    out.push(p)
    prev = p
  }
  return out
})

const fetchData = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await problemsApi.list({
      page: page.value,
      page_size: PAGE_SIZE,
      difficulty: difficultyFilter.value || undefined,
      source: sourceFilter.value || undefined,
      keyword: (route.query.keyword as string) || undefined,
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const loadSources = async () => {
  try {
    sources.value = await problemsApi.sources()
  } catch {
    sources.value = []
  }
}

watch(
  () => route.fullPath,
  () => {
    // URL 变化（含前进后退）→ 同步输入框并重新拉取
    keywordInput.value = (route.query.keyword as string) || ''
    fetchData()
  }
)

onMounted(() => {
  fetchData()
  loadSources()
})
</script>

<template>
  <div class="problem-list-page">
    <div class="problem-list-container">
      <!-- 头部 -->
      <div class="page-head">
        <div>
          <h2 class="page-title">题库</h2>
          <p class="page-sub">按难度、来源或关键词查找题目，点击题名查看题面。</p>
        </div>
        <button v-if="canManage" class="btn-new" @click="router.push('/problems/new')">＋ 新建题目</button>
      </div>

      <div class="card">
        <!-- 筛选栏 -->
        <div class="filter-bar">
          <select v-model="difficultyFilter" class="filter-select">
            <option value="">全部难度</option>
            <option v-for="d in DIFFICULTY_LIST" :key="d" :value="d">{{ d }}</option>
          </select>
          <select v-model="sourceFilter" class="filter-select">
            <option value="">全部来源</option>
            <option v-for="s in sources" :key="s" :value="s">{{ s }}</option>
          </select>
          <input
            v-model="keywordInput"
            class="filter-input"
            placeholder="搜索题号或题目名称"
            @keyup.enter="applyFilters"
          />
          <button class="btn-search" @click="applyFilters">搜索</button>
          <button class="btn-reset" @click="resetFilters">重置</button>
        </div>

        <div class="result-count">共 {{ total }} 条记录</div>

        <!-- 列表 -->
        <div v-if="error" class="empty">{{ error }}</div>
        <div v-else-if="!loading && items.length === 0" class="empty">暂无题目</div>

        <div v-else class="table-wrap">
          <table class="problem-table">
            <thead>
              <tr>
                <th class="col-pid">题号</th>
                <th>题目名称</th>
                <th class="col-tags">算法标签</th>
                <th class="col-diff">难度</th>
                <th class="col-rate">通过率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in items" :key="p.id">
                <td class="col-pid">
                  <RouterLink class="p-link" :to="`/problems/${p.id}`">{{ p.problem_number }}</RouterLink>
                </td>
                <td>
                  <RouterLink class="p-link p-title" :to="`/problems/${p.id}`">{{ p.title }}</RouterLink>
                </td>
                <td class="col-tags">
                  <template v-if="p.tags && p.tags.length">
                    <RouterLink
                      v-for="t in p.tags"
                      :key="t"
                      class="tag-badge"
                      :to="{ path: '/problems', query: { tag: t } }"
                    >{{ t }}</RouterLink>
                  </template>
                  <span v-else class="muted">-</span>
                </td>
                <td class="col-diff">
                  <span class="diff-badge" :style="{ background: difficultyColor(p.difficulty) }">
                    {{ p.difficulty }}
                  </span>
                </td>
                <td class="col-rate">
                  <template v-if="p.pass_rate !== null">
                    <div class="rate-line">
                      <div class="rate-bar">
                        <div class="rate-fill" :style="{ width: p.pass_rate + '%' }"></div>
                      </div>
                      <span class="rate-text">{{ p.pass_rate }}%</span>
                    </div>
                  </template>
                  <span v-else class="muted">暂无</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 数字分页 -->
        <div class="pagination" v-if="pageCount > 1">
          <button class="page-btn" :disabled="page === 0" @click="page = page - 1">&laquo;</button>
          <template v-for="(n, i) in pagesToShow" :key="i">
            <span v-if="n === -1" class="page-ellipsis">…</span>
            <button v-else class="page-btn" :class="{ active: n === page }" @click="page = n">
              {{ n + 1 }}
            </button>
          </template>
          <button class="page-btn" :disabled="page >= pageCount - 1" @click="page = page + 1">&raquo;</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.problem-list-page {
  min-height: 100vh;
  line-height: 1.5;
}

.problem-list-container {
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

.btn-new {
  padding: 9px 22px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.btn-new:hover {
  background: var(--primary-hover);
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

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #4a5568;
  background: #fff;
}

.filter-input {
  flex: 1;
  min-width: 180px;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #4a5568;
  outline: none;
}

.filter-input:focus {
  border-color: var(--primary);
}

.btn-search {
  padding: 8px 22px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-search:hover {
  background: var(--primary-hover);
}

.btn-reset {
  padding: 8px 18px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.btn-reset:hover {
  background: #f5f7fa;
}

.result-count {
  color: #8a9aa8;
  font-size: 13px;
  margin-bottom: 8px;
}

.table-wrap {
  overflow-x: auto;
}

.problem-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.problem-table th {
  text-align: left;
  padding: 11px 12px;
  color: #8a9aa8;
  font-size: 13px;
  border-bottom: 2px solid #edf2f7;
  white-space: nowrap;
}

.problem-table td {
  padding: 13px 12px;
  border-bottom: 1px solid #f0f2f5;
}

.problem-table tbody tr {
  transition: background 0.15s;
}

.problem-table tbody tr:hover {
  background: #fafbfc;
}

.col-pid {
  white-space: nowrap;
}

.col-tags {
  max-width: 320px;
}

.col-diff,
.col-rate {
  white-space: nowrap;
}

.p-link {
  color: #3498db;
  text-decoration: none;
}

.p-link:hover {
  text-decoration: underline;
}

.p-title {
  font-weight: 600;
  color: #2c3e50;
}

.p-title:hover {
  color: var(--primary);
}

.tag-badge {
  display: inline-block;
  margin: 1px 4px 1px 0;
  padding: 2px 10px;
  border-radius: 20px;
  background: #f0f4f8;
  color: #5b6e8c;
  font-size: 12px;
  text-decoration: none;
  white-space: nowrap;
}

.tag-badge:hover {
  background: #e2e8f0;
}

.diff-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.rate-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rate-bar {
  width: 70px;
  height: 8px;
  background: #edf2f7;
  border-radius: 4px;
  overflow: hidden;
}

.rate-fill {
  height: 100%;
  background: #52c41a;
  border-radius: 4px;
}

.rate-text {
  font-size: 12px;
  color: #5b6e8c;
}

.muted {
  color: #b6c2cf;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  padding: 18px 0 4px;
}

.page-btn {
  min-width: 32px;
  padding: 6px 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.page-btn:hover:not(:disabled):not(.active) {
  border-color: var(--primary);
  color: var(--primary);
}

.page-btn.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
  font-weight: 600;
}

.page-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.page-ellipsis {
  color: #8a9aa8;
  padding: 0 2px;
}

.empty {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

@media (max-width: 600px) {
  .card {
    padding: 14px;
  }
}
</style>
