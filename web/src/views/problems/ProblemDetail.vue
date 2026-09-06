<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { problemsApi } from '@/api/problems'
import { renderRichText } from '@/utils/markdown'
import { difficultyColor } from '@/utils/difficulty'
import type { Problem } from '@/types'

const route = useRoute()
const router = useRouter()

const problem = ref<Problem | null>(null)
const loading = ref(true)
const error = ref('')

const problemId = computed(() => parseInt(route.params.id as string, 10))

const descriptionHtml = computed(() =>
  problem.value ? renderRichText(problem.value.description) : ''
)

const loadProblem = async () => {
  if (!Number.isFinite(problemId.value)) return
  try {
    loading.value = true
    error.value = ''
    problem.value = await problemsApi.get(problemId.value)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
    problem.value = null
  } finally {
    loading.value = false
  }
}

watch(problemId, loadProblem)
onMounted(loadProblem)
</script>

<template>
  <div class="problem-detail-page">
    <div class="problem-detail-container">
      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="error" class="empty">
        {{ error }}
        <div class="empty-actions">
          <button class="btn-back" @click="router.push('/problems')">返回题库</button>
        </div>
      </div>

      <template v-else-if="problem">
        <div class="card">
          <!-- 题头 -->
          <div class="p-head">
            <span class="p-number">{{ problem.problem_number }}</span>
            <h1 class="p-title">{{ problem.title }}</h1>
            <span class="diff-badge" :style="{ background: difficultyColor(problem.difficulty) }">
              {{ problem.difficulty }}
            </span>
            <span v-if="!problem.is_public" class="draft-badge">未公开</span>
          </div>

          <!-- 限制与统计 -->
          <div class="p-limits">
            <span>时间限制：<b>{{ problem.time_limit }} ms</b></span>
            <span>内存限制：<b>{{ problem.memory_limit }} MB</b></span>
            <span v-if="problem.source">来源：<b>{{ problem.source }}</b></span>
            <span>提交：<b>{{ problem.submit_count }}</b></span>
            <span>通过：<b>{{ problem.solved_count }}</b></span>
            <span>通过率：<b>{{ problem.pass_rate === null ? '暂无' : problem.pass_rate + '%' }}</b></span>
          </div>

          <!-- 标签 -->
          <div v-if="problem.tags && problem.tags.length" class="p-tags">
            <RouterLink
              v-for="t in problem.tags"
              :key="t"
              class="tag-badge"
              :to="{ path: '/problems', query: { tag: t } }"
            >{{ t }}</RouterLink>
          </div>
        </div>

        <!-- 题面 -->
        <div class="card">
          <div class="prose p-body" v-html="descriptionHtml"></div>
        </div>

        <div class="back-row">
          <button class="btn-back" @click="router.push('/problems')">← 返回题库</button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.problem-detail-page {
  min-height: 100vh;
  line-height: 1.5;
}

.problem-detail-container {
  max-width: 1000px;
  margin: 0 auto;
}

.card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 24px 28px;
  margin-bottom: 16px;
}

.p-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.p-number {
  color: #8a9aa8;
  font-weight: 700;
  font-size: 1.1rem;
}

.p-title {
  font-size: 1.35rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
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

.draft-badge {
  padding: 2px 10px;
  border-radius: 4px;
  background: #f4f4f5;
  color: #909399;
  font-size: 12px;
}

.p-limits {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #f0f2f5;
  color: #5b6e8c;
  font-size: 13px;
}

.p-limits b {
  color: #2c3e50;
}

.p-tags {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 20px;
  background: #f0f4f8;
  color: #5b6e8c;
  font-size: 12px;
  text-decoration: none;
}

.tag-badge:hover {
  background: #e2e8f0;
}

.p-body {
  color: #2c3e50;
}

.back-row {
  text-align: center;
  padding: 4px 0 12px;
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

.empty {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  background: #fff;
  border-radius: 16px;
}

.empty-actions {
  margin-top: 16px;
}
</style>
