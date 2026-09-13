<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { contestsApi, type ContestItem } from '@/api/contests'

const router = useRouter()
const authStore = useAuthStore()
const isLoggedIn = computed(() => authStore.isAuthenticated)
const canManage = computed(() => {
  const u = authStore.currentUser
  return !!u && (u.is_super_admin || u.is_admin || u.can_manage_problems)
})

const contests = ref<ContestItem[]>([])
const loading = ref(true)
const error = ref('')

const load = async () => {
  loading.value = true
  try {
    const data = await contestsApi.list()
    contests.value = data.items
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const STATUS: Record<string, { text: string; cls: string }> = {
  running: { text: '进行中', cls: 'running' },
  pending: { text: '未开始', cls: 'pending' },
  ended: { text: '已结束', cls: 'ended' },
}
const fmt = (iso: string | null) =>
  iso ? iso.slice(0, 16).replace('T', ' ') : '—'





onMounted(load)
</script>

<template>
  <div class="contests-page">
    <div class="contests-container">
      <div class="page-head">
        <h2 class="page-title">比赛</h2>
        <button v-if="canManage" class="btn-primary" @click="router.push('/contests/new')"><i class="fa-solid fa-plus"></i> 创建比赛</button>
      </div>

      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="error" class="empty">{{ error }}</div>
      <div v-else-if="contests.length === 0" class="empty">还没有比赛</div>

      <div v-else class="contest-list">
        <div
          v-for="c in contests"
          :key="c.id"
          class="contest-card"
          @click="router.push(`/contest/${c.id}`)"
        >
          <div class="c-main">
            <div class="c-title-row">
              <span class="c-title">{{ c.title }}</span>
              <span class="status-badge" :class="STATUS[c.status].cls">{{ STATUS[c.status].text }}</span>
            </div>
            <div v-if="c.description" class="c-desc">{{ c.description }}</div>
            <div class="c-meta">
              <span><i class="fa-solid fa-stopwatch"></i> {{ fmt(c.start_time) }} ~ {{ fmt(c.end_time) }}</span>
              <span><i class="fa-solid fa-clipboard-list"></i> {{ c.problem_count }} 题</span>
              <span><i class="fa-solid fa-user-group"></i> {{ c.participant_count }} 人报名</span>
              <span>发起人：<b>{{ c.owner.username }}</b></span>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.contests-page { background: #f5f7fa; min-height: calc(100vh - 60px); }
.contests-container { max-width: 900px; margin: 0 auto; padding: 24px 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-title { color: var(--primary); font-size: 22px; margin: 0; }

.contest-list { display: flex; flex-direction: column; gap: 12px; }
.contest-card { background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 16px 20px; cursor: pointer; transition: transform .12s, box-shadow .12s; }
.contest-card:hover { transform: translateY(-1px); box-shadow: 0 5px 14px rgba(0,0,0,.09); }
.c-title-row { display: flex; align-items: center; gap: 10px; }
.c-title { font-size: 16px; font-weight: 700; color: #2c3e50; }
.status-badge { font-size: 12px; padding: 2px 12px; border-radius: 20px; font-weight: 600; }
.status-badge.running { color: #fff; background: #52c41a; }
.status-badge.pending { color: #fff; background: #f39c11; }
.status-badge.ended { color: #8e9aaf; background: #eef1f5; }
.c-desc { margin-top: 6px; color: #8e9aaf; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.c-meta { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px 18px; color: #66708a; font-size: 13px; }
.c-meta b { color: #2c3e50; }

.btn-primary { background: var(--primary); color: #fff; border: none; border-radius: 8px; padding: 8px 20px; font-weight: 600; cursor: pointer; font-size: 14px; }
.btn-secondary { background: #eee; color: #333; border: none; border-radius: 8px; padding: 8px 20px; font-weight: 600; cursor: pointer; font-size: 14px; }
.empty { text-align: center; color: #999; padding: 48px 0; background: #fff; border-radius: 12px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 999; display: flex; justify-content: center; align-items: center; }
.modal-box { background: #fff; border-radius: 14px; width: 92%; max-width: 560px; max-height: 88vh; overflow-y: auto; padding: 24px 28px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.modal-header h3 { margin: 0; font-size: 18px; color: #262626; }
.modal-close { background: none; border: none; font-size: 20px; color: #8e9aaf; cursor: pointer; }
.form-item { display: block; margin-bottom: 12px; }
.form-label { display: block; font-size: 13px; font-weight: 600; color: #4b4b4b; margin-bottom: 6px; }
.form-input { width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid #dce0e6; border-radius: 8px; font-size: 14px; outline: none; font-family: inherit; resize: vertical; }
.form-input:focus { border-color: var(--primary); }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pool { max-height: 200px; overflow-y: auto; border: 1px solid #eef1f5; border-radius: 8px; padding: 8px 12px; display: flex; flex-direction: column; gap: 4px; }
.pool-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #1f2a3a; cursor: pointer; }
.pool-item input { accent-color: var(--primary); }
.hint { font-size: 13px; color: #8e9aaf; }
.form-error { color: #e74c3c; font-size: 13px; margin-top: 8px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 12px; margin-top: 10px; }
</style>
