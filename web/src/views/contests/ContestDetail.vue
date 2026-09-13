<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { contestsApi, type ContestItem, type RankRow } from '@/api/contests'
import { difficultyColor } from '@/utils/difficulty'
import { userNameColor } from '@/utils/userColor'
import { renderRichText } from '@/utils/markdown'

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

// 选项卡由 hash 驱动：默认说明，#problem 题目列表，#scoreboard 排行榜
const TABS = [
  { key: 'statement', label: '比赛说明' },
  { key: 'problem', label: '题目列表' },
  { key: 'scoreboard', label: '排行榜' },
] as const
type TabKey = typeof TABS[number]['key']

const activeTab = ref<TabKey>('statement')
const rankAliases = ref<string[]>([])
const rankRows = ref<RankRow[]>([])
const rankLoading = ref(false)
const rankDenied = ref(false)

const descriptionHtml = computed(() =>
  contest.value ? renderRichText(contest.value.description || '') : '')

const syncTabFromHash = () => {
  const h = (route.hash || '').replace('#', '')
  activeTab.value = (TABS.some(t => t.key === h) ? h : 'statement') as TabKey
  if (activeTab.value === 'scoreboard' && rankRows.value.length === 0 && !rankLoading.value) {
    loadRank()
  }
}

const switchTab = (key: TabKey) => {
  // 与当前 hash 相同则手动触发（watch 不触发）
  if (route.hash === `#${key}`) { syncTabFromHash(); return }
  router.push({ hash: `#${key}` })
}

const load = async () => {
  if (!Number.isFinite(contestId.value)) {
    error.value = '无效的比赛 ID'
    loading.value = false
    return
  }
  loading.value = true
  try {
    contest.value = await contestsApi.get(contestId.value)
    syncTabFromHash()
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
    contest.value = null
  } finally {
    loading.value = false
  }
}
watch(contestId, load)
watch(() => route.hash, syncTabFromHash)
onMounted(() => { load() })

const loadRank = async () => {
  rankLoading.value = true
  rankDenied.value = false
  try {
    const data = await contestsApi.rank(contestId.value)
    rankAliases.value = data.aliases
    rankRows.value = data.rows
  } catch (err: any) {
    rankDenied.value = true
  } finally {
    rankLoading.value = false
  }
}

const STATUS: Record<string, { text: string; cls: string }> = {
  running: { text: '进行中', cls: 'running' },
  pending: { text: '未开始', cls: 'pending' },
  ended: { text: '已结束', cls: 'ended' },
}
const fmt = (iso: string | null) => (iso ? iso.slice(0, 16).replace('T', ' ') : '—')

const doRegister = async () => {
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

// 题目/排行榜 tab 的访问控制（与后端 can_view_problems 一致）
const canViewProblems = computed(() => !!contest.value?.can_view_problems)
const denied = computed(() =>
  (activeTab.value === 'problem' || activeTab.value === 'scoreboard')
  && !!contest.value && !canViewProblems.value)

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
        <!-- 头部卡：标题 + 统计 + 选项卡 -->
        <div class="card head-card">
          <div class="head-top">
            <div class="title-row">
              <h1>{{ contest.title }}</h1>
              <span class="status-badge" :class="STATUS[contest.status].cls">{{ STATUS[contest.status].text }}</span>
            </div>
            <div class="head-stats">
              <div class="stat">
                <div class="stat-label">题数</div>
                <div class="stat-value">{{ contest.problem_count }}</div>
              </div>
              <div class="stat">
                <div class="stat-label">参赛人数</div>
                <div class="stat-value">{{ contest.participant_count }}</div>
              </div>
            </div>
          </div>
          <div class="tab-row">
            <div class="setting-nav">
              <span
                v-for="t in TABS"
                :key="t.key"
                class="nav-btn"
                :class="{
                  active: activeTab === t.key,
                  locked: t.key !== 'statement' && !canViewProblems
                }"
                @click="switchTab(t.key)"
              >
                {{ t.label }}
                <i
                  v-if="t.key !== 'statement' && !canViewProblems"
                  class="fa-solid fa-lock lock-ico"
                />
              </span>
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
                <span v-else-if="contest.is_participant" class="joined-tag"><i class="fa-solid fa-circle-check"></i> 已报名</span>
              </template>
            </div>
          </div>
        </div>

        <div v-if="actionMsg" class="action-msg">{{ actionMsg }}</div>

        <!-- 无权访问题目/排行榜 -->
        <div v-if="denied" class="card body-card denied-card">
          <i class="fa-solid fa-lock denied-ico"></i>
          <div class="denied-text">你无权进行此操作</div>
          <div class="denied-sub">
            {{ contest.status === 'pending'
              ? '比赛尚未开始，开始并报名后即可查看题目与排行榜'
              : '报名比赛后即可查看题目与排行榜' }}
          </div>
        </div>

        <!-- 比赛说明 -->
        <div v-else-if="activeTab === 'statement'" class="detail-grid">
          <div class="card body-card statement-card">
            <h4 class="section-title">比赛介绍</h4>
            <div v-if="contest.description" class="prose statement-body" v-html="descriptionHtml" />
            <div v-else class="empty small">主办方没有填写比赛说明</div>
          </div>
          <div class="side-col">
            <div class="card side-card">
              <div v-if="contest.status === 'running'" class="side-tip running-tip">比赛正在进行中</div>
              <div v-else-if="contest.status === 'ended'" class="side-tip ended-tip">比赛已经结束了</div>
              <div v-else class="side-tip pending-tip">比赛尚未开始</div>
              <div class="side-rows">
                <div class="side-row"><span>比赛编号</span><b>{{ contest.id }}</b></div>
                <div class="side-row"><span>举办者</span>
                  <router-link :to="`/user/${contest.owner.user_id}`" class="owner-link">{{ contest.owner.username }}</router-link>
                </div>
                <div class="side-row"><span>比赛类型</span>
                  <b>{{ contest.type_label }} · ACM</b>
                </div>
                <div v-if="contest.team_name" class="side-row"><span>举办团队</span>
                  <b>{{ contest.team_name }}</b>
                </div>
                <div class="side-row"><span>开始时间</span><b>{{ fmt(contest.start_time) }}</b></div>
                <div class="side-row"><span>结束时间</span><b>{{ fmt(contest.end_time) }}</b></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 题目列表 -->
        <div v-else-if="activeTab === 'problem'" class="card body-card">
          <h4 class="section-title">题目列表 <span class="member-count">（{{ contest.problems?.length || 0 }} 道）</span></h4>
          <div v-if="contest.status === 'running' && contest.is_participant" class="hint-bar">
            比赛进行中——从比赛页进入题目并提交，提交会计入比赛成绩
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
          <div v-else-if="rankDenied" class="empty small">你无权进行此操作</div>
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
.contest-detail-container { max-width: 1100px; margin: 0 auto; padding: 20px; }
.back-link { margin-bottom: 12px; }
.back-link a { color: var(--primary); font-size: 14px; cursor: pointer; text-decoration: none; }

.card { background: #fff; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 20px 26px; margin-bottom: 16px; }

.head-top { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 14px; }
.title-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.title-row h1 { color: var(--primary); font-size: 26px; margin: 0; }
.status-badge { font-size: 13px; padding: 3px 14px; border-radius: 20px; font-weight: 600; }
.status-badge.running { color: #fff; background: #52c41a; }
.status-badge.pending { color: #fff; background: #f39c11; }
.status-badge.ended { color: #8e9aaf; background: #eef1f5; }

.head-stats { display: flex; gap: 26px; }
.stat { text-align: center; }
.stat-label { font-size: 13px; color: #66708a; }
.stat-value { font-size: 20px; font-weight: 700; color: #2c3e50; }

.tab-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-top: 14px; border-bottom: 1px solid #f0f2f5; }
.setting-nav { display: flex; gap: 28px; flex-wrap: wrap; }
.nav-btn { position: relative; padding: 12px 0; font-size: 15px; color: #6c7a8e; cursor: pointer; user-select: none; }
.nav-btn::after { content: ''; position: absolute; bottom: 0; left: 50%; width: 0; height: 4px; background: #d0d7de; transform: translateX(-50%); transition: all .2s; }
.nav-btn:hover::after { width: calc(100% + 16px); left: -8px; transform: translateX(0); }
.nav-btn.active { color: var(--primary); }
.nav-btn.active::after { background: var(--primary); width: 100%; left: 0; transform: translateX(0); }
.nav-btn.locked { color: #b2bac6; }
.lock-ico { font-size: 11px; margin-left: 4px; opacity: .8; }
.head-actions { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.joined-tag { color: #52c41a; font-size: 13px; font-weight: 600; }

.action-msg { background: #eafaf1; color: #27ae60; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }

.detail-grid { display: grid; grid-template-columns: 1fr 300px; gap: 16px; align-items: start; }
.body-card { background: #fff; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 20px 26px; }
.side-col { display: flex; flex-direction: column; gap: 16px; }
.side-card { background: #fff; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 18px 22px; }
.side-tip { font-size: 14px; font-weight: 700; margin-bottom: 12px; }
.running-tip { color: #52c41a; }
.pending-tip { color: #f39c11; }
.ended-tip { color: #e74c3c; }
.side-rows { display: flex; flex-direction: column; gap: 10px; }
.side-row { display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #66708a; }
.side-row b { color: #2c3e50; font-weight: 600; }
.owner-link { color: var(--primary); font-weight: 600; text-decoration: none; }

.section-title { margin: 4px 0 14px; color: #2c3e50; }
.member-count { color: #999; font-weight: 400; font-size: 13px; }
.statement-body { min-height: 60px; }
.hint-bar { background: #eef6ff; color: #2b6cb0; border-radius: 8px; padding: 10px 14px; font-size: 13px; margin-bottom: 12px; }
.hint-bar.warn { background: #fff7e6; color: #ad6800; }

.denied-card { text-align: center; padding: 46px 20px; }
.denied-ico { font-size: 34px; color: #c2c9d4; margin-bottom: 12px; }
.denied-text { font-size: 17px; font-weight: 700; color: #2c3e50; }
.denied-sub { margin-top: 8px; color: #8e9aaf; font-size: 13px; }

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

@media (max-width: 860px) {
  .detail-grid { grid-template-columns: 1fr; }
}

/* ===== 手机端：容器横向内边距归零 + 卡片内边距收窄 ===== */
@media (max-width: 600px) {
  .contest-detail-container {
    padding: 16px 0;
  }

  .card,
  .body-card {
    padding: 14px;
  }

  .side-card {
    padding: 14px;
  }
}
</style>
