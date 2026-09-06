<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Swal from 'sweetalert2'
import { useAuthStore } from '@/stores/auth'
import { problemsApi } from '@/api/problems'
import { difficultyColor } from '@/utils/difficulty'
import type { ProblemListItem } from '@/types'

const router = useRouter()
const authStore = useAuthStore()

const canManage = computed(() => {
  const u = authStore.currentUser
  return !!u && (u.can_manage_problems || u.is_admin || u.is_super_admin)
})

// ===== 列表 =====
const items = ref<ProblemListItem[]>([])
const total = ref(0)
const page = ref(0)
const loading = ref(false)
const error = ref('')
const keyword = ref('')

const PAGE_SIZE = 20

const loadList = async () => {
  if (!canManage.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await problemsApi.list({
      page: page.value,
      page_size: PAGE_SIZE,
      keyword: keyword.value.trim() || undefined,
      all: true, // 管理页可见草稿
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const doSearch = () => {
  page.value = 0
  loadList()
}

const goPage = (p: number) => {
  page.value = p
  loadList()
}

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

// ===== 编辑 / 删除 =====
const doDelete = (p: ProblemListItem) => {
  Swal.fire({
    title: '删除题目',
    text: `确定删除 ${p.problem_number}「${p.title}」吗？此操作不可恢复。`,
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    confirmButtonColor: '#e74c3c',
  }).then(async (r) => {
    if (!r.isConfirmed) return
    try {
      await problemsApi.remove(p.id)
      Swal.fire({ icon: 'success', title: '已删除', timer: 1200, showConfirmButton: false })
      loadList()
    } catch (err: any) {
      Swal.fire('删除失败', err.response?.data?.detail || '请重试', 'error')
    }
  })
}

onMounted(loadList)
</script>

<template>
  <div class="admin-problems-page">
    <div class="card">
      <div class="card-header">题目管理</div>

      <!-- 工具栏 -->
      <div class="toolbar">
        <button class="btn-new" @click="router.push('/problems/new')">＋ 新建题目</button>
        <div class="search-wrap">
          <input
            v-model="keyword"
            class="search-input"
            placeholder="搜索题号或题目名称"
            @keyup.enter="doSearch"
          />
          <button class="btn-search" @click="doSearch">搜索</button>
        </div>
      </div>

      <div class="result-count">共 {{ total }} 道题目</div>

      <!-- 列表 -->
      <div v-if="error" class="empty">{{ error }}</div>
      <div v-else-if="!loading && items.length === 0" class="empty">还没有题目，点「新建题目」添加第一题</div>

      <div v-else class="table-wrap">
        <table class="problem-table">
          <thead>
            <tr>
              <th>题号</th>
              <th>题目名称</th>
              <th>难度</th>
              <th>来源</th>
              <th>标签</th>
              <th>状态</th>
              <th class="col-ops">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in items" :key="p.id">
              <td class="col-pid">{{ p.problem_number }}</td>
              <td class="col-title">{{ p.title }}</td>
              <td>
                <span class="diff-badge" :style="{ background: difficultyColor(p.difficulty) }">
                  {{ p.difficulty }}
                </span>
              </td>
              <td class="col-source">{{ p.source || '-' }}</td>
              <td class="col-tags">
                <span v-if="p.tags && p.tags.length">{{ p.tags.join('、') }}</span>
                <span v-else class="muted">-</span>
              </td>
              <td>
                <span class="state-badge" :class="p.is_public ? 'public' : 'draft'">
                  {{ p.is_public ? '已公开' : '草稿' }}
                </span>
              </td>
              <td class="col-ops">
                <span class="action-link" @click="router.push(`/problems/${p.id}/edit`)">编辑</span>
                <span class="action-sep">|</span>
                <span class="action-link red" @click="doDelete(p)">删除</span>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="pagination" v-if="pageCount > 1">
          <button class="page-btn" :disabled="page === 0" @click="goPage(page - 1)">&laquo;</button>
          <span class="page-info">第 {{ page + 1 }} / {{ pageCount }} 页</span>
          <button class="page-btn" :disabled="page >= pageCount - 1" @click="goPage(page + 1)">&raquo;</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-problems-page {
  max-width: 1400px;
  margin: 0 auto;
}

.card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 20px 24px;
  margin-bottom: 24px;
}

.card-header {
  font-size: 1.25rem;
  font-weight: 600;
  border-left: 4px solid #e74c3c;
  padding-left: 12px;
  margin-bottom: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
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
}

.btn-new:hover {
  background: #c0392b;
}

.search-wrap {
  display: flex;
  gap: 8px;
}

.search-input {
  width: 240px;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
}

.search-input:focus {
  border-color: #e74c3c;
}

.btn-search {
  padding: 8px 18px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
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
  padding: 12px;
  border-bottom: 1px solid #f0f2f5;
}

.problem-table tbody tr:hover {
  background: #fafbfc;
}

.col-pid {
  color: #8a9aa8;
  white-space: nowrap;
}

.col-title {
  font-weight: 600;
  color: #2c3e50;
}

.col-source {
  white-space: nowrap;
}

.col-tags {
  max-width: 260px;
}

.col-ops {
  white-space: nowrap;
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

.state-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.state-badge.public {
  background: #f0fae5;
  color: #52c41a;
}

.state-badge.draft {
  background: #f4f4f5;
  color: #909399;
}

.action-link {
  color: #3498db;
  cursor: pointer;
}

.action-link:hover {
  text-decoration: underline;
}

.action-link.red {
  color: #e74c3c;
}

.action-sep {
  color: #d7dee5;
  margin: 0 6px;
}

.muted {
  color: #b6c2cf;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  padding: 16px 0 4px;
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
  padding: 50px 20px;
  color: #999;
}
</style>
