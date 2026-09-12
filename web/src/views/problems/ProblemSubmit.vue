<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Swal from 'sweetalert2'
import CodeEditor from '@/components/CodeEditor.vue'
import { problemsApi } from '@/api/problems'
import { submissionsApi } from '@/api/submissions'
import { difficultyColor } from '@/utils/difficulty'
import type { Problem, Submission } from '@/types'

const route = useRoute()
const router = useRouter()

const problemId = computed(() => parseInt(route.params.id as string, 10))
// 比赛上下文：从比赛详情页进入提交时（/problems/:id?contest=N），提交计入比赛
const contestId = computed(() => {
  const v = parseInt(route.query.contest as string, 10)
  return Number.isFinite(v) && v > 0 ? v : null
})
const problem = ref<Problem | null>(null)
const loading = ref(true)

const LANGUAGES = [
  { value: 'cpp', label: 'C++ (g++, C++14)', monaco: 'cpp' },
  { value: 'c', label: 'C (gcc)', monaco: 'c' },
  { value: 'python3', label: 'Python 3', monaco: 'python' },
]

const language = ref('cpp')
const monacoLang = computed(() => LANGUAGES.find((l) => l.value === language.value)?.monaco ?? 'cpp')
const code = ref('')

const DEFAULT_CODE: Record<string, string> = {
  cpp: '#include <iostream>\nusing namespace std;\n\nint main() {\n    \n    return 0;\n}\n',
  c: '#include <stdio.h>\n\nint main() {\n    \n    return 0;\n}\n',
  python3: '',
}

const submitting = ref(false)
// 是否回填了上次提交的代码（用于给用户一个提示）
const restoredFromLast = ref(false)

const loadProblem = async () => {
  try {
    problem.value = await problemsApi.get(problemId.value)
  } catch (err: any) {
    Swal.fire('题目不存在', err.response?.data?.detail || '', 'error').then(() =>
      router.push('/problems')
    )
  }
}

// 我在这题的最后一次提交（从未提交 / 请求异常都按「无」处理）
const fetchLastSubmission = async (): Promise<Submission | null> => {
  try {
    return await submissionsApi.getMyLast(problemId.value)
  } catch {
    return null
  }
}

const submit = async () => {
  if (!code.value.trim()) {
    Swal.fire('请填写代码', '', 'warning')
    return
  }
  submitting.value = true
  try {
    const sub = await submissionsApi.create(problemId.value, {
      code: code.value,
      language: language.value,
      contest_id: contestId.value ?? undefined,
    })
    router.push(`/submissions/${sub.id}`)
  } catch (err: any) {
    Swal.fire('提交失败', err.response?.data?.detail || '请重试', 'error')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  // 并行拉取题目与上次提交；有上次提交则回填代码与语言，否则用默认模板。
  // 等两者都就绪再结束 loading，避免编辑器先渲染模板再被覆盖（闪一下）
  const [, last] = await Promise.all([loadProblem(), fetchLastSubmission()])
  if (last?.code) {
    if (LANGUAGES.some((l) => l.value === last.language)) {
      language.value = last.language
    }
    code.value = last.code
    restoredFromLast.value = true
  } else {
    code.value = DEFAULT_CODE[language.value] ?? ''
  }
  loading.value = false
})
</script>

<template>
  <div class="problem-submit-page">
    <div class="problem-submit-container">
      <div v-if="loading" class="empty">加载中...</div>

      <template v-else-if="problem">
        <!-- 题头 -->
        <div class="card">
          <div class="p-head">
            <span class="p-number">{{ problem.problem_number }}</span>
            <h2 class="p-title">{{ problem.title }}</h2>
            <span class="diff-badge" :style="{ background: difficultyColor(problem.difficulty) }">
              {{ problem.difficulty }}
            </span>
          </div>
          <div class="p-limits">
            <span>时间限制：<b>{{ problem.time_limit }} ms</b></span>
            <span>内存限制：<b>{{ problem.memory_limit }} MB</b></span>
            <span v-if="contestId" class="contest-tag"><i class="fa-solid fa-trophy"></i> 比赛模式：本次提交计入比赛成绩</span>
          </div>
        </div>

        <!-- 提交区 -->
        <div class="card">
          <div class="submit-toolbar">
            <label class="lang-label">
              语言
              <select v-model="language" class="lang-select">
                <option v-for="l in LANGUAGES" :key="l.value" :value="l.value">{{ l.label }}</option>
              </select>
            </label>
            <div class="toolbar-actions">
              <button class="btn-ghost" @click="router.push(`/problems/${problem.id}`)">查看题目</button>
              <button class="btn-ghost" @click="router.push(`/submissions?problem_id=${problem.id}`)">提交记录</button>
              <button class="btn-submit" :disabled="submitting" @click="submit">
                {{ submitting ? '提交中...' : '提交评测' }}
              </button>
            </div>
          </div>

          <CodeEditor v-model="code" :language="monacoLang" height="480px" />

          <p class="tip"><template v-if="restoredFromLast">已载入你上次提交的代码。<br /></template>支持 C++14 / C / Python 3；评测在隔离沙箱中运行，每个测试点限时 {{ problem.time_limit }} ms。</p>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.problem-submit-page {
  min-height: 100vh;
  line-height: 1.5;
}

.problem-submit-container {
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

.p-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.p-number {
  color: #8a9aa8;
  font-weight: 700;
}

.p-title {
  font-size: 1.2rem;
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
}

.p-limits {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  margin-top: 10px;
  color: #5b6e8c;
  font-size: 13px;
}

.p-limits b {
  color: #2c3e50;
}

.contest-tag {
  color: #ad6800;
  background: #fff7e6;
  padding: 2px 10px;
  border-radius: 12px;
}

.submit-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.lang-label {
  font-size: 13px;
  color: #5b6e8c;
  display: flex;
  align-items: center;
  gap: 8px;
}

.lang-select {
  padding: 7px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #2c3e50;
  background: #fff;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
}

.btn-ghost {
  padding: 8px 18px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 20px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.btn-ghost:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.btn-submit {
  padding: 8px 26px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-submit:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-submit:disabled {
  opacity: 0.6;
}

.tip {
  margin-top: 10px;
  color: #8a9aa8;
  font-size: 12px;
}

.empty {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  background: #fff;
  border-radius: 16px;
}
</style>
