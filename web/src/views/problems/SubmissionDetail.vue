<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CodeEditor from '@/components/CodeEditor.vue'
import { submissionsApi } from '@/api/submissions'
import {
  submissionStatusText,
  submissionStatusColor,
  caseStatusText,
} from '@/utils/submissionStatus'
import { fmtDateTime } from '@/utils/datetime'
import type { Submission } from '@/types'

const route = useRoute()
const router = useRouter()

const sub = ref<Submission | null>(null)
const loading = ref(true)
const error = ref('')
let pollTimer: number | null = null
let pollCount = 0

const isJudging = computed(() =>
  !!sub.value && (sub.value.status === 'pending' || sub.value.status === 'judging')
)

const monacoLang = computed(() => {
  const l = sub.value?.language
  return l === 'python3' ? 'python' : l ?? 'cpp'
})

const load = async () => {
  const id = parseInt(route.params.id as string, 10)
  if (!Number.isFinite(id)) return
  try {
    sub.value = await submissionsApi.get(id)
    error.value = ''
    schedulePoll()
  } catch (err: any) {
    error.value = err.response?.data?.detail || '加载失败'
    sub.value = null
    loading.value = false
  }
}

// 评测中每 1.5s 轮询，最多 120 次（3 分钟）
const schedulePoll = () => {
  loading.value = false
  if (!isJudging.value || pollCount >= 120) return
  pollCount++
  pollTimer = window.setTimeout(async () => {
    try {
      const id = parseInt(route.params.id as string, 10)
      sub.value = await submissionsApi.get(id)
    } catch { /* 忽略单次轮询失败 */ }
    schedulePoll()
  }, 1500)
}

onMounted(load)
onBeforeUnmount(() => {
  if (pollTimer) window.clearTimeout(pollTimer)
})
</script>

<template>
  <div class="submission-detail-page">
    <div class="submission-detail-container">
      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="error" class="empty">{{ error }}</div>

      <template v-else-if="sub">
        <div class="card">
          <div class="d-head">
            <span class="d-title">提交 #{{ sub.id }}</span>
            <span class="status-badge" :style="{ color: submissionStatusColor(sub.status) }">
              {{ submissionStatusText(sub.status) }}
            </span>
            <span v-if="isJudging" class="judging-tip">评测中，结果稍后自动刷新…</span>
          </div>
          <div class="d-meta">
            <span>题目：<a class="p-link" @click="router.push(`/problems/${sub.problem_id}`)">
              {{ sub.problem_number }} {{ sub.problem_title }}
            </a></span>
            <span>提交者：<b>{{ sub.user?.username }}</b></span>
            <span>语言：<b>{{ sub.language }}</b></span>
            <span>提交时间：<b>{{ fmtDateTime(sub.created_at) }}</b></span>
          </div>
        </div>

        <!-- 评测结果 -->
        <div class="card">
          <div class="section-title">评测结果</div>
          <div v-if="isJudging" class="empty small">等待评测结果…</div>
          <template v-else>
            <div class="result-summary">
              <div class="result-item">
                <span class="result-label">得分</span>
                <span class="result-value">{{ sub.score }}</span>
              </div>
              <div class="result-item">
                <span class="result-label">耗时</span>
                <span class="result-value">{{ sub.time_used === null || sub.time_used === undefined ? '—' : sub.time_used + ' ms' }}</span>
              </div>
              <div class="result-item">
                <span class="result-label">内存</span>
                <span class="result-value">{{ sub.memory_used === null || sub.memory_used === undefined ? '—' : (sub.memory_used / 1024).toFixed(1) + ' MB' }}</span>
              </div>
            </div>

            <div v-if="sub.error_message" class="error-box">
              <div class="error-title">错误信息</div>
              <pre>{{ sub.error_message }}</pre>
            </div>

            <table v-if="sub.test_results && sub.test_results.length" class="case-table">
              <thead>
                <tr><th>测试点</th><th>状态</th><th>耗时</th><th>内存</th></tr>
              </thead>
              <tbody>
                <tr v-for="r in sub.test_results" :key="r.case">
                  <td>#{{ r.case }}</td>
                  <td :style="{ color: r.status === 'accepted' ? '#52c41a' : '#e74c3c', fontWeight: 600 }">
                    {{ caseStatusText(r.status) }}
                  </td>
                  <td>{{ r.time }} ms</td>
                  <td>{{ (r.memory / 1024).toFixed(1) }} MB</td>
                </tr>
              </tbody>
            </table>
          </template>
        </div>

        <!-- 源代码 -->
        <div class="card" v-if="sub.code_visible && sub.code !== undefined">
          <div class="section-title">源代码</div>
          <CodeEditor :model-value="sub.code" :language="monacoLang" readonly height="360px" />
        </div>
        <div class="card" v-else-if="!sub.code_visible">
          <div class="section-title">源代码</div>
          <div class="empty small">无权查看他人提交的代码</div>
        </div>

        <div class="back-row">
          <button class="btn-back" @click="router.back()">← 返回</button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.submission-detail-page {
  min-height: 100vh;
  line-height: 1.5;
}

.submission-detail-container {
  max-width: 1000px;
  margin: 0 auto;
}

.card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 20px 24px;
  margin-bottom: 16px;
}

.d-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.d-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #2c3e50;
}

.status-badge {
  font-size: 1rem;
  font-weight: 700;
}

.judging-tip {
  color: #8a9aa8;
  font-size: 12px;
}

.d-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  margin-top: 10px;
  color: #5b6e8c;
  font-size: 13px;
}

.d-meta b {
  color: #2c3e50;
}

.p-link {
  color: #3498db;
  cursor: pointer;
}

.p-link:hover {
  text-decoration: underline;
}

.section-title {
  font-size: 1.02rem;
  font-weight: 700;
  color: #2c3e50;
  border-left: 4px solid #e74c3c;
  padding-left: 10px;
  margin-bottom: 14px;
}

.result-summary {
  display: flex;
  gap: 32px;
  margin-bottom: 16px;
}

.result-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-label {
  color: #8a9aa8;
  font-size: 12px;
}

.result-value {
  font-size: 1.3rem;
  font-weight: 700;
  color: #2c3e50;
}

.error-box {
  border: 1px solid #f5b7b1;
  background: #fdf2f0;
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.error-title {
  color: #e74c3c;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}

.error-box pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  color: #c0392b;
  max-height: 300px;
  overflow-y: auto;
}

.case-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.case-table th {
  text-align: left;
  padding: 9px 12px;
  color: #8a9aa8;
  border-bottom: 2px solid #edf2f7;
}

.case-table td {
  padding: 9px 12px;
  border-bottom: 1px solid #f0f2f5;
}

.empty {
  text-align: center;
  padding: 40px 20px;
  color: #999;
}

.empty.small {
  padding: 16px;
}

.back-row {
  text-align: center;
  padding: 4px 0 20px;
}

.btn-back {
  padding: 8px 24px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 22px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.btn-back:hover {
  background: #e74c3c;
  border-color: #e74c3c;
  color: #fff;
}
</style>
