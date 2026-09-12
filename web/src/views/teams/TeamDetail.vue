<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { teamsApi, type TeamDetailItem, type TeamMemberItem, type TeamJoinRequestItem } from '@/api/teams'
import { userNameColor } from '@/utils/userColor'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isLoggedIn = computed(() => authStore.isAuthenticated)

const teamId = computed(() => parseInt(route.params.id as string, 10))
const team = ref<TeamDetailItem | null>(null)
const loading = ref(true)
const error = ref('')
const acting = ref(false)
const actionMsg = ref('')

// 选项卡（参照 Jason227 站：概览可用，其余占位）
const TABS = ['概览', '题目', '作业', '题单', '比赛', '成员', '文件']
const activeTab = ref('概览')

const load = async () => {
  if (!Number.isFinite(teamId.value)) {
    error.value = '无效的团队 ID'
    loading.value = false
    return
  }
  loading.value = true
  error.value = ''
  try {
    team.value = await teamsApi.get(teamId.value)
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
    team.value = null
  } finally {
    loading.value = false
  }
}
watch(teamId, load)
onMounted(load)

const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

const userColor = (u: TeamMemberItem['user']) => userNameColor(u)
const userTag = (u: TeamMemberItem['user']) => {
  if (!u) return ''
  if (u.is_cheater) return u.is_admin ? (u.user_tag || '管理员') : '作弊者'
  return u.user_tag || ''
}
const fmtDate = (iso: string | null) => (iso ? iso.slice(0, 10) : '未知')

const roleText = (role: string) =>
  role === 'owner' ? '团队主' : role === 'admin' ? '管理员' : ''

// ===== 操作：申请加入 / 退出 / 解散 =====
const doAction = async (fn: () => Promise<unknown>, okMsg: string) => {
  acting.value = true
  actionMsg.value = ''
  try {
    await fn()
    actionMsg.value = okMsg
    await load()
  } catch (err: any) {
    actionMsg.value = err.response?.data?.detail || '操作失败'
  } finally {
    acting.value = false
  }
}

const joinTeam = () => doAction(() => teamsApi.join(teamId.value), '申请已提交，等待团队管理员审核')
const leaveTeam = () => {
  if (!confirm('确定退出该团队吗？')) return
  doAction(() => teamsApi.leave(teamId.value), '已退出')
}
const dissolveTeam = () => {
  if (!confirm('确定解散该团队吗？所有成员将被移除，此操作不可恢复。')) return
  doAction(async () => {
    await teamsApi.dissolve(teamId.value)
    router.push('/teams')
  }, '已解散')
}

// ===== 管理成员弹窗 =====
const showManage = ref(false)
const manageTarget = ref<TeamMemberItem | null>(null)
const manageNote = ref('')
const manageAdmin = ref(false)
const manageSaving = ref(false)
const manageError = ref('')

const canManage = computed(() => !!team.value?.is_team_admin)

const openManage = (m: TeamMemberItem) => {
  if (!canManage.value || m.role === 'owner') return
  manageTarget.value = m
  manageNote.value = m.note || ''
  manageAdmin.value = m.role === 'admin'
  manageError.value = ''
  showManage.value = true
}

const saveManage = async () => {
  if (!manageTarget.value || !team.value) return
  manageSaving.value = true
  manageError.value = ''
  try {
    await teamsApi.updateMember(team.value.id, manageTarget.value.user_id, {
      role: manageAdmin.value ? 'admin' : 'member',
      note: manageNote.value.trim() || undefined,
    })
    showManage.value = false
    await load()
  } catch (err: any) {
    manageError.value = err.response?.data?.detail || '保存失败'
  } finally {
    manageSaving.value = false
  }
}

const removeMember = async () => {
  if (!manageTarget.value || !team.value) return
  if (!confirm(`确定将 ${manageTarget.value.user.username} 移出团队吗？`)) return
  manageSaving.value = true
  try {
    await teamsApi.removeMember(team.value.id, manageTarget.value.user_id)
    showManage.value = false
    await load()
  } catch (err: any) {
    manageError.value = err.response?.data?.detail || '移除失败'
  } finally {
    manageSaving.value = false
  }
}

const transferTeam = async () => {
  if (!manageTarget.value || !team.value) return
  const name = manageTarget.value.user.username
  if (!confirm(`确定把团队「${team.value.name}」转让给 ${name} 吗？\n转让后你将变为普通成员，此操作不可撤销。`)) return
  manageSaving.value = true
  try {
    await teamsApi.transfer(team.value.id, manageTarget.value.user_id)
    showManage.value = false
    await load()
  } catch (err: any) {
    manageError.value = err.response?.data?.detail || '转让失败'
  } finally {
    manageSaving.value = false
  }
}

// ===== 入队申请审核 =====
const showRequests = ref(false)
const requestItems = ref<TeamJoinRequestItem[]>([])
const requestsLoading = ref(false)
const requestsError = ref('')
const processingReq = ref<number | null>(null)

const openRequests = async () => {
  showRequests.value = true
  requestsLoading.value = true
  requestsError.value = ''
  try {
    const data = await teamsApi.requests(teamId.value)
    requestItems.value = data.items
  } catch (err: any) {
    requestsError.value = err.response?.data?.detail || '加载失败'
  } finally {
    requestsLoading.value = false
  }
}

const handleRequest = async (userId: number, approve: boolean) => {
  processingReq.value = userId
  try {
    if (approve) {
      await teamsApi.approveRequest(teamId.value, userId)
    } else {
      await teamsApi.rejectRequest(teamId.value, userId)
    }
    requestItems.value = requestItems.value.filter(r => r.user_id !== userId)
    await load()
  } catch (err: any) {
    requestsError.value = err.response?.data?.detail || '操作失败'
  } finally {
    processingReq.value = null
  }
}
</script>

<template>
  <div class="team-detail-page">
    <div class="team-detail-container">
      <div class="back-link">
        <a @click.prevent="router.push('/teams')" href="#">← 返回团队列表</a>
      </div>

      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="error" class="empty">{{ error }}</div>

      <template v-else-if="team">
        <!-- 团队头卡 -->
        <div class="card head-card">
          <div class="title-row">
            <h1>{{ team.name }}</h1>
            <div class="team-stats">
              <span class="stat-label">队员人数</span>
              <span class="stat-label">创建时间</span>
              <span class="stat-value">{{ team.member_count }}</span>
              <span class="stat-value">{{ fmtDate(team.created_at) }}</span>
            </div>
          </div>
          <div v-if="team.description" class="team-desc">{{ team.description }}</div>
          <div class="tab-row">
            <div class="setting-nav">
              <span
                v-for="t in TABS"
                :key="t"
                class="nav-btn"
                :class="{ active: activeTab === t }"
                @click="activeTab = t"
              >{{ t }}</span>
            </div>
            <div class="head-actions">
              <template v-if="isLoggedIn">
                <button
                  v-if="team.is_team_admin"
                  class="btn-secondary"
                  @click="openRequests"
                >入队申请（{{ team.pending_count }}）</button>
                <button v-if="team.is_owner" class="btn-danger" :disabled="acting" @click="dissolveTeam">解散团队</button>
                <button v-else-if="team.is_member" class="btn-secondary" :disabled="acting" @click="leaveTeam">退出团队</button>
                <button v-else-if="team.is_pending" class="btn-secondary" disabled>审核中…</button>
                <button v-else class="btn-primary" :disabled="acting" @click="joinTeam">
                  {{ acting ? '处理中...' : '申请加入' }}
                </button>
              </template>
              <router-link v-else class="btn-secondary" to="/login">登录后可申请</router-link>
            </div>
          </div>
        </div>

        <div v-if="actionMsg" class="action-msg">{{ actionMsg }}</div>

        <!-- 概览 / 占位选项卡 -->
        <div v-if="activeTab === '概览' || activeTab === '成员'" class="card body-card">
          <h4 class="section-title">团队成员 <span class="member-count">（{{ team.member_count }} 人）</span></h4>
          <div class="member-grid">
            <div
              v-for="m in team.members"
              :key="m.user_id"
              class="member-item"
              :class="{ manageable: canManage && m.role !== 'owner' }"
              @click="openManage(m)"
            >
              <div class="member-left">
                <img class="member-avatar" :src="m.user.avatar_url || letterAvatar(m.user.username)" alt="" />
                <span class="member-name">
                  <router-link :to="`/user/${m.user.user_number}`" class="username-link" :style="{ color: userColor(m.user) }">
                    {{ m.note ? `${m.note}（${m.user.username}）` : m.user.username }}
                  </router-link>
                  <span v-if="userTag(m.user)" class="user-tag" :style="{ background: userColor(m.user) }">{{ userTag(m.user) }}</span>
                </span>
              </div>
              <span v-if="m.role !== 'member'" class="role-tag" :class="m.role">{{ roleText(m.role) }}</span>
              <span v-else-if="canManage && m.role === 'member'" class="manage-hint">管理</span>
            </div>
          </div>
        </div>

        <div v-else class="card body-card">
          <div class="empty">「{{ activeTab }}」功能开发中，敬请期待</div>
        </div>

        <!-- 入队申请审核弹窗 -->
        <div v-if="showRequests" class="modal-overlay" @click.self="showRequests = false">
          <div class="modal-box">
            <div class="modal-header">
              <h3>入队申请（{{ requestItems.length }}）</h3>
              <button class="modal-close" @click="showRequests = false">✕</button>
            </div>
            <div v-if="requestsLoading" class="empty small">加载中...</div>
            <div v-else-if="requestsError" class="form-error">{{ requestsError }}</div>
            <div v-else-if="requestItems.length === 0" class="empty small">暂无待审核申请</div>
            <div v-else class="request-list">
              <div v-for="r in requestItems" :key="r.user_id" class="request-item">
                <div class="member-left">
                  <img class="member-avatar" :src="r.user.avatar_url || letterAvatar(r.user.username)" alt="" />
                  <router-link :to="`/user/${r.user.user_number}`" class="username-link" :style="{ color: userColor(r.user) }">
                    {{ r.user.username }}
                  </router-link>
                </div>
                <div class="request-actions">
                  <button class="btn-primary small" :disabled="processingReq === r.user_id" @click="handleRequest(r.user_id, true)">通过</button>
                  <button class="btn-secondary small" :disabled="processingReq === r.user_id" @click="handleRequest(r.user_id, false)">拒绝</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 管理成员弹窗 -->
        <div v-if="showManage" class="modal-overlay" @click.self="showManage = false">
          <div class="modal-box">
            <div class="modal-header">
              <h3>成员信息</h3>
              <button class="modal-close" @click="showManage = false">✕</button>
            </div>
            <div class="modal-body" v-if="manageTarget">
              <div class="field-row">
                <span class="field-label">成员</span>
                <div class="field-value">
                  <router-link :to="`/user/${manageTarget.user.user_number}`" :style="{ color: userColor(manageTarget.user), fontWeight: 600 }">
                    {{ manageTarget.user.username }}
                  </router-link>
                </div>
              </div>
              <div class="field-row">
                <span class="field-label">备注名</span>
                <div class="field-value">
                  <input v-model="manageNote" class="form-input" maxlength="50" placeholder="团队内显示的备注名" />
                </div>
              </div>
              <div class="field-row">
                <span class="field-label">权限</span>
                <div class="field-value">
                  <label class="checkbox-label">
                    <input v-model="manageAdmin" type="checkbox" />
                    团队管理员 <span class="hint">（可管理团队成员）</span>
                  </label>
                </div>
              </div>
              <div v-if="manageError" class="form-error">{{ manageError }}</div>
            </div>
            <div class="modal-footer three">
              <button class="btn-danger-outline" :disabled="manageSaving" @click="removeMember">移出团队</button>
              <button
                v-if="team?.is_owner"
                class="btn-danger-outline"
                :disabled="manageSaving"
                @click="transferTeam"
              >转让团队</button>
              <span class="spacer"></span>
              <button class="btn-secondary" @click="showManage = false">取消</button>
              <button class="btn-primary" :disabled="manageSaving" @click="saveManage">
                {{ manageSaving ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.team-detail-page { background: #f5f7fa; min-height: calc(100vh - 60px); }
.team-detail-container { max-width: 1000px; margin: 0 auto; padding: 20px; }
.back-link { margin-bottom: 12px; }
.back-link a { color: var(--primary); font-size: 14px; cursor: pointer; text-decoration: none; }
.back-link a:hover { text-decoration: underline; }

.card { background: #fff; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 20px 26px; margin-bottom: 16px; }
.title-row { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.title-row h1 { color: var(--primary); font-size: 24px; margin: 0; }
.team-desc { margin-top: 8px; color: #66708a; font-size: 14px; white-space: pre-wrap; }

.team-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 20px; }
.stat-label { color: #333; font-size: 14px; text-align: center; }
.stat-value { color: #333; font-weight: 600; font-size: 14px; text-align: center; }

.tab-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-top: 6px; border-bottom: 1px solid #f0f2f5; padding-bottom: 0; }
.setting-nav { display: flex; gap: 28px; flex-wrap: wrap; }
.nav-btn { position: relative; padding: 12px 0; font-size: 15px; color: #6c7a8e; cursor: pointer; }
.nav-btn::after { content: ''; position: absolute; bottom: 0; left: 50%; width: 0; height: 4px; background: #d0d7de; transform: translateX(-50%); transition: all .2s; }
.nav-btn:hover::after { width: calc(100% + 16px); left: -8px; transform: translateX(0); }
.nav-btn.active { color: var(--primary); }
.nav-btn.active::after { background: var(--primary); width: 100%; left: 0; transform: translateX(0); }
.head-actions { display: flex; gap: 10px; flex-shrink: 0; }

.action-msg { background: #eafaf1; color: #27ae60; padding: 10px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; }

.section-title { margin: 4px 0 14px; color: #2c3e50; }
.member-count { color: #999; font-weight: 400; font-size: 13px; }
.member-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.member-item { background: #fafafa; border: 1px solid #e8e8e8; border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; min-height: 48px; gap: 8px; }
.member-item.manageable { cursor: pointer; }
.member-item.manageable:hover { border-color: #f0b6b0; background: #fff8f7; }
.member-left { display: flex; align-items: center; gap: 10px; overflow: hidden; min-width: 0; }
.member-avatar { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
.member-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.username-link { font-weight: 700; font-size: 14px; text-decoration: none; }
.username-link:hover { text-decoration: underline; }
.user-tag { display: inline-block; border-radius: 2px; padding: 2px 8px; color: #fff; font-size: 11px; font-weight: 600; margin-left: 4px; vertical-align: middle; }
.role-tag { flex-shrink: 0; font-size: 12px; padding: 2px 14px; border-radius: 20px; font-weight: 600; }
.role-tag.owner { color: #fff; background: #ffc116; }
.role-tag.admin { color: var(--primary); background: #fef0ef; }
.manage-hint { flex-shrink: 0; font-size: 12px; color: #c2c9d4; }

.empty { text-align: center; color: #999; padding: 40px 0; }

.btn-primary { background: var(--primary); color: #fff; border: none; border-radius: 8px; padding: 8px 20px; font-weight: 600; cursor: pointer; font-size: 14px; }
.btn-primary:hover { background: var(--primary-hover); }
.btn-secondary { background: #eee; color: #333; border: none; border-radius: 8px; padding: 8px 20px; font-weight: 600; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }
.btn-danger { background: transparent; color: var(--primary); border: 1px solid var(--primary); border-radius: 8px; padding: 8px 20px; font-weight: 600; cursor: pointer; font-size: 14px; }
.btn-danger-outline { background: none; color: var(--primary); border: none; font-size: 13px; cursor: pointer; }
button:disabled { opacity: .6; cursor: not-allowed; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 999; display: flex; justify-content: center; align-items: center; }
.modal-box { background: #fff; border-radius: 14px; width: 90%; max-width: 440px; padding: 24px 28px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.modal-header h3 { margin: 0; font-size: 18px; color: #262626; }
.modal-close { background: none; border: none; font-size: 20px; color: #8e9aaf; cursor: pointer; }
.field-row { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f0f2f5; }
.field-label { width: 64px; flex-shrink: 0; font-size: 14px; color: #4b4b4b; font-weight: 600; }
.field-value { flex: 1; font-size: 14px; }
.form-input { width: 100%; box-sizing: border-box; padding: 7px 10px; border: 1px solid #dce0e6; border-radius: 8px; font-size: 14px; outline: none; }
.form-input:focus { border-color: var(--primary); }
.checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.checkbox-label input { accent-color: var(--primary); }
.hint { font-size: 12px; color: #8e9aaf; }
.form-error { color: var(--primary); font-size: 13px; margin-top: 10px; }
.modal-footer { display: flex; align-items: center; gap: 12px; margin-top: 16px; padding-top: 14px; border-top: 1px solid #f0f2f5; }
.modal-footer.three .spacer { flex: 1; }

.request-list { max-height: 320px; overflow-y: auto; }
.request-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f0f2f5; }
.request-item:last-child { border-bottom: none; }
.request-actions { display: flex; gap: 8px; }
.btn-primary.small, .btn-secondary.small { padding: 5px 14px; font-size: 13px; }
.empty.small { padding: 16px 0; font-size: 13px; }

@media (max-width: 640px) {
  .member-grid { grid-template-columns: 1fr; }
  .team-stats { grid-template-columns: 1fr; text-align: left; }
  .title-row h1 { font-size: 20px; }
}
</style>
