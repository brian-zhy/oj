<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { problemsApi } from '@/api/problems'
import { contestsApi, type ContestItem } from '@/api/contests'
import { renderRichText } from '@/utils/markdown'
import { difficultyColor } from '@/utils/difficulty'
import { userNameColor } from '@/utils/userColor'
import type { Problem } from '@/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

// 严格只认题目管理权限
const canManage = computed(() => !!authStore.currentUser?.can_manage_problems)

const problem = ref<Problem | null>(null)
const loading = ref(true)
const error = ref('')

const problemId = computed(() => parseInt(route.params.id as string, 10))
// 统一题号入口：/problem/P1001 或 /problem/T10（团队私有题）
const problemCode = computed(() => (route.params.code as string || '').toUpperCase())

// ==================== 比赛上下文 ====================
// 从比赛页点题目进来时 URL 上带着 ?contest=N，**这个参数必须一路传到提交页**：
// 后端靠它把提交归到某场比赛，丢了就不会计分（排行榜会全员 0 分）。
// 曾经这个页面既不读、也不往下传，导致从比赛里提交永远不计成绩。
const contestId = computed(() => {
  const v = parseInt(route.query.contest as string, 10)
  return Number.isFinite(v) && v > 0 ? v : null
})

// 仅用于展示横幅；取不到（未报名 / 已删除等）就静默不显示，不影响做题
const contest = ref<ContestItem | null>(null)

const loadContest = async () => {
  if (contestId.value === null) {
    contest.value = null
    return
  }
  try {
    contest.value = await contestsApi.get(contestId.value)
  } catch {
    contest.value = null
  }
}

// 提交页靠 ?contest= 判断是否计分，这里提前把状态说清楚
// （比赛未开始/已结束时后端会直接拒收，不如先提醒）
const contestHint = computed(() => {
  const c = contest.value
  if (!c) return ''
  if (c.status === 'running') return '本次提交将计入比赛成绩'
  if (c.status === 'pending') return '比赛尚未开始，现在提交不计成绩'
  return '比赛已结束，提交不计成绩'
})

// 把整个 query 原样带过去（不只 contest，以后加新上下文参数也不用再改这里）
const openSubmit = () => {
  if (!problem.value) return
  router.push({ path: `/problems/${problem.value.id}/submit`, query: route.query })
}

const loadProblemByCode = async (code: string) => {
  try {
    loading.value = true
    error.value = ''
    problem.value = await problemsApi.getByCode(code)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
    problem.value = null
  } finally {
    loading.value = false
  }
}

const descriptionHtml = computed(() =>
  problem.value ? renderRichText(problem.value.description) : ''
)
const backgroundHtml = computed(() =>
  problem.value ? renderRichText(problem.value.background || '') : ''
)
const inputFormatHtml = computed(() =>
  problem.value ? renderRichText(problem.value.input_format || '') : ''
)
const outputFormatHtml = computed(() =>
  problem.value ? renderRichText(problem.value.output_format || '') : ''
)
const hintHtml = computed(() =>
  problem.value ? renderRichText(problem.value.hint || '') : ''
)

// 有任一扩展分节时，描述也加上「题目描述」小节标题（洛谷习惯）
const hasSections = computed(() => {
  const p = problem.value
  if (!p) return false
  return !!(p.background || p.input_format || p.output_format || p.hint || (p.samples && p.samples.length))
})

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
watch(problemCode, (code) => { if (code) loadProblemByCode(code) })
watch(contestId, loadContest)
onMounted(() => {
  if (problemCode.value) loadProblemByCode(problemCode.value)
  else loadProblem()
  loadContest()
})
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
        <!-- 比赛模式横幅：提醒当前提交会计入哪场比赛（以前这个状态完全不可见） -->
        <div
          v-if="contest"
          class="contest-banner"
          :class="{ 'is-warn': contest.status !== 'running' }"
        >
          <i class="fa-solid fa-trophy" />
          <span>比赛模式</span>
          <router-link :to="`/contest/${contest.id}`" class="cb-link">{{ contest.title }}</router-link>
          <span class="cb-text">{{ contestHint }}</span>
        </div>

        <div class="card">
          <!-- 题头 -->
          <div class="p-head">
            <span class="p-number">{{ problem.problem_number }}</span>
            <h1 class="p-title">{{ problem.title }}</h1>
            <span class="diff-badge" :style="{ background: difficultyColor(problem.difficulty) }">
              {{ problem.difficulty }}
            </span>
            <span v-if="!problem.is_public" class="draft-badge">未公开</span>
            <span v-if="canManage" class="head-ops">
              <button class="btn-op" @click="router.push(`/problems/${problem.id}/edit`)">编辑</button>
            </span>
          </div>

          <!-- 操作行 -->
          <div class="p-actions">
            <button class="btn-primary" @click="openSubmit">提交代码</button>
            <button class="btn-op" @click="router.push(`/submissions?problem_id=${problem.id}`)">提交记录</button>
          </div>

          <!-- 限制与统计 -->
          <div class="p-limits">
            <span>时间限制：<b>{{ problem.time_limit }} ms</b></span>
            <span>内存限制：<b>{{ problem.memory_limit }} MB</b></span>
            <span v-if="problem.source">来源：<b>{{ problem.source }}</b></span>
            <span v-if="problem.author">
              出题人：<router-link
                :to="`/user/${problem.author.user_number}`"
                class="author-link"
                :style="{ color: userNameColor(problem.author) }"
              >{{ problem.author.username }}</router-link>
            </span>
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
          <template v-if="hasSections">
            <template v-if="problem.background">
              <div class="section-head">题目背景</div>
              <div class="prose p-body" v-html="backgroundHtml"></div>
            </template>
            <template v-if="problem.description">
              <div class="section-head">题目描述</div>
              <div class="prose p-body" v-html="descriptionHtml"></div>
            </template>
            <template v-if="problem.input_format">
              <div class="section-head">输入格式</div>
              <div class="prose p-body" v-html="inputFormatHtml"></div>
            </template>
            <template v-if="problem.output_format">
              <div class="section-head">输出格式</div>
              <div class="prose p-body" v-html="outputFormatHtml"></div>
            </template>
            <template v-if="problem.samples && problem.samples.length">
              <div class="section-head">样例</div>
              <div v-for="(s, i) in problem.samples" :key="i" class="sample-block">
                <div class="sample-title">样例 #{{ i + 1 }}</div>
                <div class="sample-io">
                  <div class="io-box">
                    <div class="io-label">
                      <span>输入</span>
                      <button type="button" class="code-copy code-copy-light" data-copy>
                        <i class="fa-solid fa-copy" /><span data-copy-label>复制</span>
                      </button>
                    </div>
                    <pre>{{ s.input }}</pre>
                  </div>
                  <div class="io-box">
                    <div class="io-label">
                      <span>输出</span>
                      <button type="button" class="code-copy code-copy-light" data-copy>
                        <i class="fa-solid fa-copy" /><span data-copy-label>复制</span>
                      </button>
                    </div>
                    <pre>{{ s.output }}</pre>
                  </div>
                </div>
              </div>
            </template>
            <template v-if="problem.hint">
              <div class="section-head">提示说明</div>
              <div class="prose p-body" v-html="hintHtml"></div>
            </template>
          </template>
          <div v-else class="prose p-body" v-html="descriptionHtml"></div>
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

/* ===== 比赛模式横幅 ===== */
.contest-banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  background: #eef5ff;
  border: 1px solid #cfe3ff;
  border-radius: 12px;
  padding: 10px 16px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #3a5a80;
}

.contest-banner i {
  color: var(--primary);
}

/* 比赛未开始 / 已结束时换成暖色，和「会计分」区分开 */
.contest-banner.is-warn {
  background: #fdf3f1;
  border-color: #f6d5cd;
  color: #a1432f;
}

.contest-banner.is-warn i {
  color: #c0392b;
}

.cb-link {
  color: var(--primary);
  font-weight: 700;
  text-decoration: none;
}

.cb-link:hover {
  text-decoration: underline;
}

.is-warn .cb-link {
  color: #a1432f;
}

.cb-text {
  color: #7b8aa0;
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

.head-ops {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.btn-op {
  padding: 6px 18px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 18px;
  font-size: 12px;
  color: #4a5568;
  cursor: pointer;
}

.btn-op:hover {
  border-color: #3498db;
  color: #3498db;
}

.btn-op.danger {
  color: var(--primary);
  border-color: #f5b7b1;
}

.btn-op.danger:hover {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
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

.p-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.btn-primary {
  padding: 9px 28px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 22px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:hover {
  background: var(--primary-hover);
}

.author-link {
  font-weight: 700;
  text-decoration: none;
}
.author-link:hover { text-decoration: underline; }

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

.section-head {
  font-size: 1.05rem;
  font-weight: 700;
  color: #2c3e50;
  border-bottom: 1px solid #edf2f7;
  padding-bottom: 8px;
  margin-bottom: 12px;
}

.sample-block {
  margin-bottom: 16px;
}

.sample-title {
  font-size: 13px;
  font-weight: 600;
  color: #5b6e8c;
  margin-bottom: 6px;
}

.sample-io {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.io-box {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
}

.io-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: #f7fafc;
  color: #8a9aa8;
  font-size: 12px;
  padding: 4px 8px 4px 12px;
  border-bottom: 1px solid #edf2f7;
}

.io-box pre {
  margin: 0;
  padding: 10px 12px;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
  color: #2c3e50;
  min-height: 42px;
}

@media (max-width: 600px) {
  .sample-io {
    grid-template-columns: 1fr;
  }
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
  background: var(--primary);
  border-color: var(--primary);
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
