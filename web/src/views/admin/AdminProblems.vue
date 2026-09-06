<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Swal from 'sweetalert2'
import { useAuthStore } from '@/stores/auth'
import { problemsApi } from '@/api/problems'
import { renderRichText } from '@/utils/markdown'
import { DIFFICULTY_LIST, difficultyColor } from '@/utils/difficulty'
import type { Problem, ProblemDifficulty, ProblemListItem } from '@/types'

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

// ===== 新建 / 编辑表单 =====
const showForm = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)

const emptyForm = () => ({
  title: '',
  difficulty: '暂无评定' as ProblemDifficulty,
  source: '',
  tagsInput: '',
  time_limit: 1000,
  memory_limit: 128,
  is_public: true,
  description: '',
})

const form = ref(emptyForm())

const previewHtml = computed(() => renderRichText(form.value.description))

const openCreate = () => {
  editingId.value = null
  form.value = emptyForm()
  showForm.value = true
}

const openEdit = (p: ProblemListItem | Problem) => {
  // 列表项无 description，需拉详情
  problemsApi
    .get(p.id)
    .then((full) => {
      editingId.value = p.id
      form.value = {
        title: full.title,
        difficulty: full.difficulty,
        source: full.source || '',
        tagsInput: (full.tags || []).join(','),
        time_limit: full.time_limit,
        memory_limit: full.memory_limit,
        is_public: full.is_public,
        description: full.description || '',
      }
      showForm.value = true
    })
    .catch((err: any) => {
      Swal.fire('加载失败', err.response?.data?.detail || '请重试', 'error')
    })
}

const saveForm = async () => {
  if (!form.value.title.trim()) {
    Swal.fire('请填写题目名称', '', 'warning')
    return
  }
  const payload = {
    title: form.value.title.trim(),
    difficulty: form.value.difficulty,
    source: form.value.source.trim() || null,
    tags: form.value.tagsInput
      .split(/[,，]/)
      .map((t) => t.trim())
      .filter(Boolean),
    time_limit: Number(form.value.time_limit),
    memory_limit: Number(form.value.memory_limit),
    is_public: form.value.is_public,
    description: form.value.description,
  }
  saving.value = true
  try {
    if (editingId.value === null) {
      await problemsApi.create(payload)
      Swal.fire({ icon: 'success', title: '创建成功', timer: 1200, showConfirmButton: false })
    } else {
      await problemsApi.update(editingId.value, payload)
      Swal.fire({ icon: 'success', title: '保存成功', timer: 1200, showConfirmButton: false })
    }
    showForm.value = false
    loadList()
  } catch (err: any) {
    Swal.fire('保存失败', err.response?.data?.detail || '请重试', 'error')
  } finally {
    saving.value = false
  }
}

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
        <button class="btn-new" @click="openCreate">＋ 新建题目</button>
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
                <span class="action-link" @click="openEdit(p)">编辑</span>
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

    <!-- 新建 / 编辑弹层 -->
    <div v-if="showForm" class="modal-mask" @click.self="showForm = false">
      <div class="modal">
        <div class="modal-header">{{ editingId === null ? '新建题目' : '编辑题目' }}</div>

        <div class="form-grid">
          <label class="form-item">
            <span class="form-label">题目名称 *</span>
            <input v-model="form.title" class="form-input" placeholder="例如：A+B Problem" />
          </label>
          <label class="form-item">
            <span class="form-label">难度</span>
            <select v-model="form.difficulty" class="form-input">
              <option v-for="d in DIFFICULTY_LIST" :key="d" :value="d">{{ d }}</option>
            </select>
          </label>
          <label class="form-item">
            <span class="form-label">来源</span>
            <input v-model="form.source" class="form-input" placeholder="例如：NOIP / 洛谷 / 自拟" />
          </label>
          <label class="form-item">
            <span class="form-label">算法标签（逗号分隔，最多 10 个）</span>
            <input v-model="form.tagsInput" class="form-input" placeholder="例如：模拟, 前缀和, 动态规划" />
          </label>
          <label class="form-item">
            <span class="form-label">时间限制 (ms)</span>
            <input v-model.number="form.time_limit" type="number" class="form-input" min="100" max="60000" />
          </label>
          <label class="form-item">
            <span class="form-label">内存限制 (MB)</span>
            <input v-model.number="form.memory_limit" type="number" class="form-input" min="16" max="1024" />
          </label>
        </div>

        <label class="form-item">
          <span class="form-label">题面（Markdown，支持 $公式$ 与样例代码块）</span>
          <textarea v-model="form.description" class="form-textarea" rows="10"
            placeholder="## 题目描述&#10;...&#10;## 输入格式&#10;...&#10;## 样例&#10;```input1&#10;1 2&#10;```&#10;```output1&#10;3&#10;```"
          ></textarea>
        </label>

        <div v-if="form.description" class="preview-box">
          <div class="preview-title">预览</div>
          <div class="prose preview-body" v-html="previewHtml"></div>
        </div>

        <label class="checkbox-line">
          <input v-model="form.is_public" type="checkbox" />
          公开（取消勾选则为草稿，仅题目管理可见）
        </label>

        <div class="modal-footer">
          <button class="btn-cancel" @click="showForm = false">取消</button>
          <button class="btn-save" :disabled="saving" @click="saveForm">
            {{ saving ? '保存中...' : '保存' }}
          </button>
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

/* ===== 弹层 ===== */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 16px;
  overflow-y: auto;
  z-index: 300;
}

.modal {
  background: #fff;
  border-radius: 16px;
  width: 860px;
  max-width: 100%;
  padding: 24px 28px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18);
}

.modal-header {
  font-size: 1.15rem;
  font-weight: 700;
  color: #2c3e50;
  border-left: 4px solid #e74c3c;
  padding-left: 10px;
  margin-bottom: 18px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px 16px;
  margin-bottom: 12px;
}

.form-item {
  display: block;
  margin-bottom: 12px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #5b6e8c;
  margin-bottom: 4px;
}

.form-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #2c3e50;
  outline: none;
}

.form-input:focus {
  border-color: #e74c3c;
}

.form-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  font-family: ui-monospace, Consolas, monospace;
  color: #2c3e50;
  outline: none;
  resize: vertical;
}

.form-textarea:focus {
  border-color: #e74c3c;
}

.preview-box {
  border: 1px solid #edf2f7;
  border-radius: 10px;
  margin-bottom: 12px;
  overflow: hidden;
}

.preview-title {
  background: #f7fafc;
  color: #8a9aa8;
  font-size: 12px;
  padding: 6px 12px;
  border-bottom: 1px solid #edf2f7;
}

.preview-body {
  padding: 12px 16px;
  max-height: 320px;
  overflow-y: auto;
}

.checkbox-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #4a5568;
  margin-bottom: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.btn-cancel {
  padding: 9px 22px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 22px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.btn-save {
  padding: 9px 28px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 22px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-save:hover:not(:disabled) {
  background: #c0392b;
}

.btn-save:disabled {
  opacity: 0.6;
}

@media (max-width: 700px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
