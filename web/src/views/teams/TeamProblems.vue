<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { teamsApi, type TeamProblemItem } from '@/api/teams'
import { difficultyColor } from '@/utils/difficulty'

const router = useRouter()
const problems = ref<(TeamProblemItem & { team_name: string })[]>([])
const loading = ref(true)
const error = ref('')

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await teamsApi.myProblems()
    problems.value = data.items
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="team-problems-page">
    <div class="team-problems-container">
      <div class="page-head">
        <h2 class="page-title">团队题目</h2>
        <p class="page-sub">你所在团队的全部私有题（T 编号），仅团队成员可见</p>
      </div>

      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="error" class="empty">{{ error }}</div>
      <div v-else-if="problems.length === 0" class="empty">
        还没有可看的团队题目——加入团队后，团队管理员出题即可在这里看到
      </div>

      <div v-else class="problem-list">
        <div
          v-for="p in problems"
          :key="p.id"
          class="problem-item"
          @click="router.push(`/problem/${p.problem_number}`)"
        >
          <span class="prob-no">{{ p.problem_number }}</span>
          <span class="prob-title">{{ p.title }}</span>
          <span class="prob-team">{{ p.team_name }}</span>
          <span class="prob-stats">{{ p.solved_count }} / {{ p.submit_count }}</span>
          <span class="diff-badge" :style="{ background: difficultyColor(p.difficulty) }">
            {{ p.difficulty }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.team-problems-page { background: #f5f7fa; min-height: calc(100vh - 60px); }
.team-problems-container { max-width: 1000px; margin: 0 auto; padding: 24px 20px; }
.page-head { margin-bottom: 16px; }
.page-title { color: var(--primary); font-size: 22px; margin: 0; }
.page-sub { color: #8e9aaf; font-size: 13px; margin: 6px 0 0; }

.problem-list { display: flex; flex-direction: column; gap: 10px; }
.problem-item { display: flex; align-items: center; gap: 14px; background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 13px 18px; cursor: pointer; transition: transform .12s, box-shadow .12s; }
.problem-item:hover { transform: translateY(-1px); box-shadow: 0 5px 14px rgba(0,0,0,.09); }
.prob-no { font-weight: 700; color: var(--primary); min-width: 52px; font-size: 14px; }
.prob-title { flex: 1; color: #2c3e50; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.prob-team { color: #13c2c2; background: #e6fffb; font-size: 12px; padding: 2px 10px; border-radius: 20px; flex-shrink: 0; }
.prob-stats { color: #8e9aaf; font-size: 13px; flex-shrink: 0; }
.diff-badge { color: #fff; font-size: 12px; padding: 2px 10px; border-radius: 4px; font-weight: 600; flex-shrink: 0; }

.empty { text-align: center; color: #999; padding: 48px 0; background: #fff; border-radius: 12px; }

/* ===== 手机端：容器内边距收敛，条目内边距收窄 ===== */
@media (max-width: 600px) {
  .team-problems-container {
    padding: 16px 0;
  }

  .problem-item {
    padding: 12px 14px;
  }
}
</style>
