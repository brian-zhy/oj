<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { contestsApi, type ContestItem, type RankRow } from '@/api/contests'
import { difficultyColor } from '@/utils/difficulty'
import { userNameColor } from '@/utils/userColor'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isLoggedIn = computed(() => authStore.isAuthenticated)

const contestId = computed(() => parseInt(route.params.id as string, 10))
const contest = ref<ContestItem | null>(null)
const loading = ref(true)
const error = ref('')
const acting = ref(false)
const actionMsg = ref('')

const tab = ref<'overview' | 'rank'>('overview')
const rankAliases = ref<string[]>([])
const rankRows = ref<RankRow[]>([])
const rankLoading = ref(false)

const load = async () => {
  if (!Number.isFinite(contestId.value)) {
    error.value = '无效的比赛 ID'
    loading.value = false
    return
  }
  loading.value = true
  try {
    contest.value = await contestsApi.get(contestId.value)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
    contest.value = null
  } finally {
    loading.value = false
  }
}
watch(contestId, load)
onMounted(load)

const loadRank = async () => {
  rankLoading.value = true
  try {
    const data = await contestsApi.rank(contestId.value)
    rankAliases.value = data.aliases
    rankRows.value = data.rows
  } finally {
    rankLoading.value = false
  }
}

const switchTab = (t: 'overview' | 'rank') => {
  tab.value = t
  if (t === 'rank' && rankRows.value.length === 0 && !rankLoading.value) loadRank()
}

const STATUS: Record<string, { text: string; cls: string }> = {
  running: { text: '进行中', cls: 'running' },
  pending: { text: '未开始', cls: 'pending' },
  ended: { text: '已结束', cls: 'ended' },
}
const fmt = (iso: string | null) => (iso ? iso.slice(0, 16).replace('T', ' ') : '—')

const doRegister = async () => {
  // 邀请赛需先输入邀请码
  let inviteCode: string | undefined
  if (contest.value?.visibility === 'private') {
    inviteCode = window.prompt('这是一场邀请赛，请输入邀请码：') || ''
    if (!inviteCode) return
  }
  acting.value = true
  actionMsg.value = ''
  try {
    await contestsApi.register(contestId.value, inviteCode)
    actionMsg.value = '报名成功'
    await load()
  } catch (err: any) {
    actionMsg.value = err.response?.data?.detail || '报名失败'
  } finally {
    acting.value = false
  }
}

const doDelete = async () => {
  if (!contest.value) return
  if (!confirm(`确定删除比赛「${contest.value.title}」吗？此操作不可恢复。`)) return
  acting.value = true
  try {
    await contestsApi.remove(contestId.value)
    router.push('/contests')
  } catch (err: any) {
    actionMsg.value = err.response?.data?.detail || '删除失败'
    acting.value = false
  }
}

const openProblem = (pid: number) => {
  if (!contest.value) return
  // 进行中带比赛上下文提交；其余直接看题
  router.push(`/problems/${pid}?contest=${contest.value.id}`)
}

const userColor = (u: Record<string, any>) => userNameColor(u)
</script>

<template>
  <div class="contest-detail-page">
    <div class="contest-detail-container">
      <div class="back-link">
        <a @click.prevent="router.push('/contests')" href="#">← 返回比赛列表</a>
      </div>

      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="error" class="empty">{{ error }}</div>

      <template v-else-if="contest">
        <div class="card head-card">
          <div class="title-row">
            <h1>{{ contest.title }}</h1>
            <span class="status-badge" :class="STATUS[contest.status].cls">{{ STATUS[contest.status].text }}</span>
          </div>
          <div v-if="contest.description" class="c-desc">{{ contest.description }}</div>
          <div class="c-meta">
            <span><i class="fa-solid fa-stopwatch"></i> {{ fmt(contest.start_time) }} ~ {{ fmt(contest.end_time) }}</span>
            <span><i class="fa-solid fa-clipboard-list"></i> {{ contest.problem_count }} 题</span>
            <span><i class="fa-solid fa-user-group"></i> {{ contest.participant_count }} 人报名</span>
            <span>发起人：<b>{{ contest.owner.username }}</b></span>
            <span>赛制：ACM（通过数优先，罚时其次）</span>
          </div>
          <div class="tab-row">
            <div class="setting-nav">
              <span class="nav-btn" :class="{ active: tab === 'overview' }" @click="switchTab('overview')">概览</span>
              <span class="nav-btn" :class="{ active: tab === 'rank' }" @click="switchTab('rank')">排行榜</span>
            </div>
            <div class="head-actions">
              <button
                v-if="contest.is_owner || contest.can_manage"
                class="btn-danger"
                :disabled="acting"
                @click="doDelete"
              >删除比赛</button>
              <template v-if="isLoggedIn">
                <button
                  v-if="!contest.is_participant && contest.status !== 'ended'"
                  class="btn-primary"
                  :disabled="acting"
                  @click="doRegister"
                >{{ acting ? '处理中...' : '报名比赛' }}</button>
                <span v-else-if="contest.is_participant" class="joined-tag">已报名</span>
              </template>
            </div>
          </div>
        </div>

        <div v-if="actionMsg" class="action-msg">{{ actionMsg }}</div>

        <!-- 概览 -->
        <div v-if="tab === 'overview'" class="card body-card">
          <h4 class="section-title">比赛题目</h4>
          <div v-if="contest.status === 'pending'" class="hint-bar">
            比赛尚未开始，题目内容将在开始后可见
          </div>
          <div v-if="contest.problems && contest.problems.length" class="cp-list">
            <div
              v-for="p in contest.problems"
              :key="p.problem_id"
              class="cp-item"
              @click="openProblem(p.problem_id)"
            >
              <span class="cp-alias">{{ p.alias }}</span>
              <span class="cp-title">{{ p.title }}</span>
              <span class="diff-badge" :style="{ background: difficultyColor(p.difficulty) }">{{ p.difficulty }}</span>
            </div>
          </div>
          <div v-else class="empty small">比赛暂未配置题目</div>
          <div v-if="contest.status === 'running' && !contest.is_participant" class="hint-bar warn">
            你尚未报名，报名后提交才会计入比赛成绩
          </div>
        </div>

        <!-- 排行榜 -->
        <div v-else class="card body-card">
          <h4 class="section-title">排行榜 <span class="member-count">（{{ rankRows.length }} 人）</span></h4>
          <div v-if="rankLoading" class="empty small">加载中...</div>
          <div v-else-if="rankRows.length === 0" class="empty small">还没有人报名</div>
          <div v-else class="rank-wrap">
            <table class="rank-table">
              <thead>
                <tr>
                  <th class="col-rank">排名</th>
                  <th class="col-user">选手</th>
                  <th class="col-solved">通过数</th>
                  <th class="col-penalty">罚时</th>
                  <th v-for="a in rankAliases" :key="a" class="col-prob">{{ a }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in rankRows" :key="r.user.user_id">
                  <td class="col-rank">{{ r.rank }}</td>
                  <td class="col-user">
                    <router-link :to="`/user/${r.user.user_number}`" class="u-link" :style="{ color: userColor(r.user) }">
                      {{ r.user.username }}
                    </router-link>
                  </td>
                  <td class="col-solved">{{ r.solved }}</td>
                  <td class="col-penalty">{{ r.penalty }}</td>
                  <td v-for="a in rankAliases" :key="a" class="col-prob">
                    <template v-if="r.detail[a]?.solved">
                      <span class="cell solved">
                        {{ r.detail[a].minutes }}′
                        <em v-if="r.detail[a].tries">({{ r.detail[a].tries }})</em>
                      </span>
                    </template>
                    <span v-else-if="r.detail[a]?.tries" class="cell tried">{{ r.detail[a].tries }}</span>
                    <span v-else class="cell none">·</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.contest-detail-page { background: #f5f7fa; min-height: calc(100vh - 60px); }
.contest-detail-container { max-width: 1000px; margin: 0 auto; padding: 20px; }
.back-link { margin-bottom: 12px; }
.back-link a { color: var(--primary); font-size: 14px; cursor: pointer; text-decoration: none; }

.card { background: #fff; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 20px 26px; margin-bottom: 16px; }
.title-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.title-row h1 { color: var(--primary); font-size: 24px; margin: 0; }
.status-badge { font-size: 13px; padding: 3px 14px; border-radius: 20px; font-weight: 600; }
.status-badge.running { color: #fff; background: #52c41a; }
.status-badge.pending { color: #fff; background: #f39c11; }
.status-badge.ended { color: #8e9aaf; background: #eef1f5; }
.c-desc { margin-top: 8px; color: #66708a; font-size: 14px; white-space: pre-wrap; }
.c-meta { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px 18px; color: #66708a; font-size: 13px; }
.c-meta b { color: #2c3e50; }

.tab-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-top: 12px; border-bottom: 1px solid #f0f2f5; }
.setting-nav { display: flex; gap: 28px; }
.nav-btn { position: relative; padding: 12px 0; font-size: 15px; color: #6c7a8e; cursor: pointer; }
.nav-btn::after { content: ''; position: absolute; bottom: 0; left: 50%; width: 0; height: 4px; background: #d0d7de; transform: translateX(-50%); transition: all .2s; }
.nav-btn:hover::after { width: calc(100% + 16px); left: -8px; transform: translateX(0); }
.nav-btn.active { color: var(--primary); }
.nav-btn.active::after { background: var(--primary); width: 100%; left: 0; transform: translateX(0); }
.head-actions { display: flex; align-items: center; gap: 10px; }
.joined-tag { color: #52c41a; font-size: 13px; font-weight: 600; }

.action-msg { background: #eafaf1; color: #27ae60; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }

.section-title { margin: 4px 0 14px; color: #2c3e50; }
.member-count { color: #999; font-weight: 400; font-size: 13px; }
.hint-bar { background: #eef6ff; color: #2b6cb0; border-radius: 8px; padding: 10px 14px; font-size: 13px; margin-bottom: 12px; }
.hint-bar.warn { background: #fff7e6; color: #ad6800; }

.cp-list { display: flex; flex-direction: column; gap: 8px; }
.cp-item { display: flex; align-items: center; gap: 12px; background: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; padding: 10px 14px; cursor: pointer; }
.cp-item:hover { border-color: #f0b6b0; background: #fff8f7; }
.cp-alias { font-weight: 700; color: var(--primary); min-width: 28px; }
.cp-title { flex: 1; color: #2c3e50; font-size: 14px; }
.diff-badge { color: #fff; font-size: 12px; padding: 2px 10px; border-radius: 4px; font-weight: 600; }

.rank-wrap { overflow-x: auto; }
.rank-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.rank-table th, .rank-table td { padding: 9px 10px; border-bottom: 1px solid #f0f2f5; text-align: center; }
.rank-table th { color: #66708a; font-weight: 600; background: #fafbfc; }
.col-user { text-align: left !important; }
.u-link { font-weight: 700; text-decoration: none; }
.cell { display: inline-block; min-width: 44px; padding: 2px 8px; border-radius: 6px; }
.cell.solved { background: #eafaf1; color: #27ae60; font-weight: 700; }
.cell.solved em { font-style: normal; color: #e67e22; font-size: 12px; }
.cell.tried { background: #fdedec; color: #e74c3c; }
.cell.none { color: #ccc; }

.btn-primary { background: var(--primary); color: #fff; border: none; border-radius: 8px; padding: 8px 20px; font-weight: 600; cursor: pointer; font-size: 14px; }
.btn-danger { background: transparent; color: #e74c3c; border: 1px solid #e74c3c; border-radius: 8px; padding: 8px 20px; font-weight: 600; cursor: pointer; font-size: 14px; }
button:disabled { opacity: .6; cursor: not-allowed; }
.empty { text-align: center; color: #999; padding: 30px 0; }
.empty.small { padding: 14px 0; font-size: 13px; }
</style>
