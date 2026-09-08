<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Swal from 'sweetalert2'
import { problemsApi } from '@/api/problems'
import { testCasesApi } from '@/api/submissions'
import { renderRichText } from '@/utils/markdown'
import { DIFFICULTY_LIST } from '@/utils/difficulty'
import type { ProblemDifficulty, ProblemSample, TestCaseItem } from '@/types'

const route = useRoute()
const router = useRouter()

const editingId = computed(() => {
  const id = parseInt(route.params.id as string, 10)
  return Number.isFinite(id) ? id : null
})

// ===== 表单 =====
const form = reactive({
  title: '',
  difficulty: '暂无评定' as ProblemDifficulty,
  source: '',
  tagsInput: '',
  time_limit: 1000,
  memory_limit: 128,
  is_public: false,
  background: '',
  description: '',
  input_format: '',
  output_format: '',
  hint: '',
})
const samples = ref<ProblemSample[]>([])

// 洛谷式分节：每节都是「编辑器 + 实时预览」
const SECTIONS = [
  { key: 'background', label: '题目背景', placeholder: '题目背景（可留空）。例如：最近世界杯开始了，小B迫不及待想去看足球比赛。' },
  { key: 'description', label: '题目描述', placeholder: '题目描述。支持 Markdown 与 $LaTeX$ 公式。' },
  { key: 'input_format', label: '输入格式', placeholder: '输入格式说明。' },
  { key: 'output_format', label: '输出格式', placeholder: '输出格式说明。' },
  { key: 'hint', label: '提示说明', placeholder: '样例解释、数据范围等（可留空）。' },
] as const

type SectionKey = (typeof SECTIONS)[number]['key']

const previewOf = (key: SectionKey) => renderRichText(form[key] || '')

// ===== 加载（编辑模式） =====
const loading = ref(true)
const loadProblem = async () => {
  if (editingId.value === null) {
    loading.value = false
    return
  }
  try {
    const p = await problemsApi.get(editingId.value)
    form.title = p.title
    form.difficulty = p.difficulty
    form.source = p.source || ''
    form.tagsInput = (p.tags || []).join(',')
    form.time_limit = p.time_limit
    form.memory_limit = p.memory_limit
    form.is_public = p.is_public
    form.background = p.background || ''
    form.description = p.description || ''
    form.input_format = p.input_format || ''
    form.output_format = p.output_format || ''
    form.hint = p.hint || ''
    samples.value = (p.samples || []).map((s) => ({ input: s.input || '', output: s.output || '' }))
    loadTestCases()
  } catch (err: any) {
    Swal.fire('加载失败', err.response?.data?.detail || '请重试', 'error')
  } finally {
    loading.value = false
  }
}

// ===== 样例组 =====
const addSample = () => samples.value.push({ input: '', output: '' })
const removeSample = (i: number) => samples.value.splice(i, 1)

// ===== 测试点（评测用，建题后管理） =====
const testCases = ref<TestCaseItem[]>([])
const newCase = reactive({ input_data: '', expected_output: '' })

const loadTestCases = async () => {
  if (editingId.value === null) return
  try {
    testCases.value = await testCasesApi.list(editingId.value)
  } catch {
    testCases.value = []
  }
}

const addCase = async () => {
  if (editingId.value === null) return
  if (!newCase.input_data && !newCase.expected_output) {
    Swal.fire('请填写测试点内容', '', 'warning')
    return
  }
  try {
    await testCasesApi.create(editingId.value, {
      input_data: newCase.input_data,
      expected_output: newCase.expected_output,
    })
    newCase.input_data = ''
    newCase.expected_output = ''
    loadTestCases()
  } catch (err: any) {
    Swal.fire('添加失败', err.response?.data?.detail || '请重试', 'error')
  }
}

const removeCase = async (id: number) => {
  if (editingId.value === null) return
  try {
    await testCasesApi.remove(editingId.value, id)
    loadTestCases()
  } catch (err: any) {
    Swal.fire('删除失败', err.response?.data?.detail || '请重试', 'error')
  }
}

// ===== 保存 =====
const saving = ref(false)
const save = async () => {
  if (!form.title.trim()) {
    Swal.fire('请填写题目名称', '', 'warning')
    return
  }
  const payload = {
    title: form.title.trim(),
    difficulty: form.difficulty,
    source: form.source.trim() || null,
    tags: form.tagsInput
      .split(/[,，]/)
      .map((t) => t.trim())
      .filter(Boolean),
    time_limit: Number(form.time_limit),
    memory_limit: Number(form.memory_limit),
    is_public: form.is_public,
    background: form.background,
    description: form.description,
    input_format: form.input_format,
    output_format: form.output_format,
    hint: form.hint,
    samples: samples.value.map((s) => ({ input: s.input, output: s.output })),
  }
  saving.value = true
  try {
    if (editingId.value === null) {
      const created = await problemsApi.create(payload)
      await Swal.fire({ icon: 'success', title: '创建成功', timer: 1200, showConfirmButton: false })
      router.push(`/problems/${created.id}`)
    } else {
      await problemsApi.update(editingId.value, payload)
      await Swal.fire({ icon: 'success', title: '保存成功', timer: 1200, showConfirmButton: false })
      router.push(`/problems/${editingId.value}`)
    }
  } catch (err: any) {
    Swal.fire('保存失败', err.response?.data?.detail || '请重试', 'error')
  } finally {
    saving.value = false
  }
}

// ===== 删除（仅编辑模式） =====
const doDelete = () => {
  if (editingId.value === null) return
  Swal.fire({
    title: '删除题目',
    text: '删除后不可恢复，确定吗？',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    confirmButtonColor: '#e74c3c',
  }).then(async (r) => {
    if (!r.isConfirmed || editingId.value === null) return
    try {
      await problemsApi.remove(editingId.value)
      Swal.fire({ icon: 'success', title: '已删除', timer: 1200, showConfirmButton: false })
      router.push('/problems')
    } catch (err: any) {
      Swal.fire('删除失败', err.response?.data?.detail || '请重试', 'error')
    }
  })
}

onMounted(loadProblem)
</script>

<template>
  <div class="problem-edit-page">
    <div class="problem-edit-container">
      <!-- 头部 -->
      <div class="card head-card">
        <div class="head-row">
          <h2 class="page-title">
            {{ editingId === null ? '新建题目' : `编辑 P${1000 + editingId}` }}
          </h2>
          <div class="head-actions">
            <button v-if="editingId !== null" class="btn-ghost" @click="router.push(`/problems/${editingId}`)">查看题目</button>
            <button v-if="editingId !== null" class="btn-danger" @click="doDelete">删除题目</button>
            <button class="btn-primary" :disabled="saving" @click="save">
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>

      <div v-if="loading" class="empty">加载中...</div>

      <template v-else>
        <!-- 题目设置 -->
        <div class="card">
          <div class="section-title">题目设置</div>
          <div class="form-grid">
            <label class="form-item span-2">
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
            <label class="form-item span-2">
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
            <label class="form-item">
              <span class="form-label">题目状态</span>
              <select v-model="form.is_public" class="form-input">
                <option :value="false">隐藏（草稿，仅题目管理可见）</option>
                <option :value="true">公开</option>
              </select>
            </label>
          </div>
        </div>

        <!-- 题面设置 -->
        <div class="card">
          <div class="section-title">题面设置</div>

          <div v-for="s in SECTIONS" :key="s.key" class="md-section">
            <div class="md-label">{{ s.label }}</div>
            <div class="md-editor">
              <textarea
                v-model="form[s.key]"
                class="md-textarea"
                rows="6"
                :placeholder="s.placeholder"
              ></textarea>
              <div class="md-preview">
                <div class="prose preview-body" v-html="previewOf(s.key)"></div>
              </div>
            </div>
          </div>

          <!-- 样例组 -->
          <div class="md-section">
            <div class="md-label">样例</div>
            <div v-for="(s, i) in samples" :key="i" class="sample-group">
              <div class="sample-head">
                <span class="sample-name">样例组 #{{ i + 1 }}</span>
                <span class="action-link red" @click="removeSample(i)">删除此组</span>
              </div>
              <div class="sample-grid">
                <textarea v-model="s.input" class="md-textarea plain" rows="4" placeholder="样例输入"></textarea>
                <textarea v-model="s.output" class="md-textarea plain" rows="4" placeholder="样例输出"></textarea>
              </div>
            </div>
            <button class="btn-ghost add-sample" @click="addSample">＋ 添加样例组</button>
          </div>
        </div>

        <!-- 测试数据（评测用） -->
        <div class="card">
          <div class="section-title">测试数据</div>
          <template v-if="editingId !== null">
            <p class="tc-tip">评测用测试点：提交的代码将逐点运行并与期望输出比对（忽略行尾空白）。至少添加 1 个测试点，否则该题无法提交评测。</p>
            <div v-for="(tc, i) in testCases" :key="tc.id" class="sample-group">
              <div class="sample-head">
                <span class="sample-name">测试点 #{{ i + 1 }}</span>
                <span class="action-link red" @click="removeCase(tc.id)">删除</span>
              </div>
              <div class="sample-grid">
                <textarea class="md-textarea plain" rows="3" readonly :value="tc.input_data" placeholder="输入"></textarea>
                <textarea class="md-textarea plain" rows="3" readonly :value="tc.expected_output" placeholder="期望输出"></textarea>
              </div>
            </div>
            <div v-if="testCases.length === 0" class="tc-empty">暂无测试点</div>
            <div class="tc-add">
              <div class="tc-label">新增测试点</div>
              <div class="sample-grid">
                <textarea v-model="newCase.input_data" class="md-textarea plain" rows="3" placeholder="测试点输入"></textarea>
                <textarea v-model="newCase.expected_output" class="md-textarea plain" rows="3" placeholder="期望输出"></textarea>
              </div>
              <button class="btn-ghost add-sample" @click="addCase">＋ 添加测试点</button>
            </div>
          </template>
          <p v-else class="tc-tip">题目创建后即可在这里添加评测测试点。</p>
        </div>

        <div class="save-row">
          <button class="btn-primary big" :disabled="saving" @click="save">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.problem-edit-page {
  min-height: 100vh;
  line-height: 1.5;
}

.problem-edit-container {
  max-width: 1100px;
  margin: 0 auto;
}

.card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 20px 24px;
  margin-bottom: 16px;
}

.head-card {
  padding: 16px 24px;
}

.head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.page-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
}

.head-actions {
  display: flex;
  gap: 10px;
}

.btn-primary {
  padding: 8px 26px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 22px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background: #c0392b;
}

.btn-primary.big {
  padding: 11px 46px;
  font-size: 14px;
}

.btn-primary:disabled {
  opacity: 0.6;
}

.btn-ghost {
  padding: 8px 20px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 22px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.btn-ghost:hover {
  border-color: #e74c3c;
  color: #e74c3c;
}

.btn-danger {
  padding: 8px 20px;
  border: 1px solid #e74c3c;
  background: #fff;
  border-radius: 22px;
  font-size: 13px;
  color: #e74c3c;
  cursor: pointer;
}

.btn-danger:hover {
  background: #e74c3c;
  color: #fff;
}

.section-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #2c3e50;
  border-left: 4px solid #e74c3c;
  padding-left: 10px;
  margin-bottom: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 4px 16px;
}

.form-item {
  display: block;
  margin-bottom: 12px;
}

.span-2 {
  grid-column: span 2;
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
  background: #fff;
}

.form-input:focus {
  border-color: #e74c3c;
}

/* 分节编辑器 */
.md-section {
  margin-bottom: 22px;
}

.md-label {
  font-size: 13px;
  font-weight: 600;
  color: #5b6e8c;
  margin-bottom: 6px;
}

.md-editor {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
}

.md-textarea {
  width: 100%;
  height: 100%;
  min-height: 120px;
  box-sizing: border-box;
  padding: 10px 12px;
  border: none;
  outline: none;
  resize: vertical;
  font-size: 13px;
  font-family: ui-monospace, Consolas, monospace;
  color: #2c3e50;
  background: #fcfdff;
}

.md-textarea.plain {
  border-radius: 0;
  background: #fff;
}

.md-preview {
  border-left: 1px solid #e2e8f0;
  background: #fff;
  padding: 10px 14px;
  min-height: 120px;
  max-height: 480px;
  overflow-y: auto;
}

.preview-body :deep(pre) {
  background: #f6f8fa;
  border-radius: 6px;
  padding: 10px 12px;
  overflow-x: auto;
}

/* 样例组 */
.sample-group {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
}

.sample-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.sample-name {
  font-size: 13px;
  font-weight: 600;
  color: #2c3e50;
}

.sample-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.add-sample {
  border-radius: 8px;
}

.tc-tip {
  color: #8a9aa8;
  font-size: 12px;
  margin-bottom: 12px;
}

.tc-empty {
  color: #b6c2cf;
  font-size: 13px;
  padding: 8px 0 12px;
}

.tc-add {
  margin-top: 4px;
}

.tc-label {
  font-size: 13px;
  color: #5b6e8c;
  margin-bottom: 6px;
}

.action-link.red {
  color: #e74c3c;
  cursor: pointer;
  font-size: 12px;
}

.action-link.red:hover {
  text-decoration: underline;
}

.save-row {
  text-align: center;
  padding: 4px 0 20px;
}

.empty {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  background: #fff;
  border-radius: 16px;
}

@media (max-width: 760px) {
  .md-editor,
  .sample-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .span-2 {
    grid-column: span 1;
  }

  .md-preview {
    border-left: none;
    border-top: 1px solid #e2e8f0;
  }
}
</style>
