<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import apiClient from '@/api/client'

// showAdmin：是否显示操作管理员（陶片放逐公共页不显示，管理日志页显示）
const props = defineProps<{ showAdmin?: boolean }>()

// ================================================================
// 1. 状态（每页30条，倒序分页加载）
// ================================================================
const PAGE_SIZE = 30

interface LogUser {
  id: number | null
  username: string
  avatar_url: string
  user_tag: string
  is_admin: boolean
  is_banned: boolean
  user_number: number | null
  username_color: string
  is_cheater: boolean
}

interface JudgementLog {
  id: number
  admin_id: number
  target_user_id: number
  action_type: string
  action_detail: any
  reason: string
  created_at: string
  target_user: LogUser
  admin: LogUser
}

const logs = ref<JudgementLog[]>([])
const page = ref(0)
const loading = ref(false)
const hasMore = ref(true)
const canManageLogs = ref(false)
const loadError = ref('')

// ================================================================
// 2. 工具函数
// ================================================================
function formatTime(iso: string): string {
  if (!iso) return '未知时间'
  try {
    const d = new Date(iso)
    const pad = (n: number) => String(n).padStart(2, '0')
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' +
      pad(d.getHours()) + ':' + pad(d.getMinutes())
  } catch {
    return '未知时间'
  }
}

const COLOR_RED = '#e74c3c'
const COLOR_PURPLE = '#9C3DCF'
const COLOR_BROWN = '#AD8B00'
const COLOR_BANNED = '#95a5a6'

function getUserColor(user: LogUser): string {
  if (user.is_banned) return COLOR_BANNED
  if (user.is_cheater) return COLOR_BROWN
  if (user.is_admin) return COLOR_PURPLE
  return COLOR_RED
}

// ================================================================
// 3. 权限名称映射
// ================================================================
function getPermName(perm: string): string {
  const map: Record<string, string> = {
    'is_admin': '进入后台',
    'can_manage_users': '用户管理',
    'can_manage_posts': '秩序管理',
    'can_speak': '自由发言',
    'is_banned': '进入主站',
    'is_cheater': '学术不端',
  }
  return map[perm] || perm || '未知权限'
}

// 判断是否为"解除棕名"类操作（本页不展示，只展示处罚本身）
function isUnbrownAction(action_type: string): boolean {
  const t = (action_type || '').toLowerCase()
  return t === 'unbrown' || /unbrown|remove_brown|lift_brown|clear_brown|restore_color|brown_restored|penalty_expired|penalty_lifted|penalty_removed|unpenalty/.test(t)
}

// ================================================================
// 4. 权限变更（与陶片放逐页一致：撤销红字/授予绿字 + 灰底权限名，管理轮换紫字）
// ================================================================
interface PermChange {
  word: string
  cls: string
  name: string
}

function permLine(word: string, perm: string): PermChange {
  const isGrant = word === '授予'
  return {
    word,
    cls: isGrant ? 'lcolor--green-3' : 'lcolor--red-3',
    name: getPermName(perm),
  }
}

function buildBadges(log: JudgementLog): { changes: PermChange[]; extra: string } {
  const d = log.action_detail || {}
  const changes: PermChange[] = []
  let extra = ''

  if (['grant_normal', 'revoke_normal', 'ostracism', 'admin_rotation', 'unbrown', 'perm_update'].includes(log.action_type)) {
    const cs = Array.isArray(d?.changes) ? d.changes : []
    cs.forEach((c: any) => {
      // is_banned 的值语义相反（false = 解封/授予）
      const isGrant = c.permission === 'is_banned' ? c.new_value === false : c.new_value === true
      changes.push(permLine(isGrant ? '授予' : '撤销', c.permission))
    })
  } else if (log.action_type === 'grant_perm' || log.action_type === 'revoke_perm') {
    const perm = d?.permission
    const line = permLine(log.action_type === 'grant_perm' ? '授予' : '撤销', perm)
    const managerPerms = ['is_admin', 'can_manage_users', 'can_manage_posts']
    if (managerPerms.includes(perm)) {
      line.cls = 'lcolor--purple-3'
    }
    changes.push(line)
  } else if (log.action_type === 'ban') {
    changes.push(permLine('撤销', 'is_banned'))
  } else if (log.action_type === 'unban') {
    changes.push(permLine('授予', 'is_banned'))
  } else if (log.action_type === 'brown_penalty') {
    extra = '学术不端惩罚'
  } else if (log.action_type === 'manager_rotate') {
    extra = `授予 ${d?.permission || '管理'} 权限（轮换）`
  } else {
    extra = '管理操作'
  }

  return { changes, extra }
}

// ================================================================
// 5. 单条日志渲染数据
// ================================================================
interface RenderedLog {
  id: number
  time: string
  admin: LogUser
  adminColor: string
  target: LogUser
  targetColor: string
  changes: PermChange[]
  extra: string
  reason: string
}

function buildRenderedLog(log: JudgementLog): RenderedLog {
  const admin: LogUser = log.admin || {
    id: null, username: '未知', avatar_url: '', user_tag: '',
    is_admin: true, is_banned: false, user_number: null,
    username_color: '', is_cheater: false,
  }
  const target: LogUser = log.target_user || {
    id: null, username: '已删除用户', avatar_url: '', user_tag: '',
    is_admin: false, is_banned: false, user_number: null,
    username_color: '', is_cheater: false,
  }

  const { changes, extra } = buildBadges(log)

  return {
    id: log.id,
    time: formatTime(log.created_at),
    admin,
    adminColor: getUserColor(admin),
    target,
    targetColor: getUserColor(target),
    changes,
    extra,
    reason: log.reason || '（无）',
  }
}

const renderedLogs = ref<RenderedLog[]>([])

// ================================================================
// 6. 加载日志
// ================================================================
async function loadLogs(append = false) {
  if (loading.value || !hasMore.value) return
  loading.value = true

  try {
    const data: any = await apiClient.get(`/api/judgement/logs?page=${page.value}&page_size=${PAGE_SIZE}`)
    canManageLogs.value = !!data.can_manage

    const fetched: JudgementLog[] = data.logs || []

    if (fetched.length === 0) {
      hasMore.value = false
      return
    }

    // 过滤掉"解除棕名"类记录：本页只展示处罚本身，不展示解除
    const visibleLogs = fetched.filter(l => !isUnbrownAction(l.action_type))

    if (append) {
      logs.value = [...logs.value, ...visibleLogs]
    } else {
      logs.value = visibleLogs
    }
    renderedLogs.value = logs.value.map(buildRenderedLog)

    page.value++
    hasMore.value = !!data.has_more
  } catch (err: any) {
    console.error('加载失败:', err)
    loadError.value = err.response?.data?.detail || err.message || ''
  } finally {
    loading.value = false
  }
}

// ================================================================
// 7. 删除陶片（仅秩序管理权限）
// ================================================================
async function deleteLog(id: number) {
  if (!canManageLogs.value || !id) return
  if (!confirm('永久删除这条管理日志？此操作不可恢复。')) return
  try {
    await apiClient.delete(`/api/judgement/logs/${id}`)
    logs.value = logs.value.filter(l => l.id !== id)
    renderedLogs.value = logs.value.map(buildRenderedLog)
  } catch (err: any) {
    alert('删除失败：' + (err.response?.data?.detail || err.message || err))
  }
}

// ================================================================
// 8. 回到顶部
// ================================================================
const showBackToTop = ref(false)

function onScroll() {
  showBackToTop.value = window.pageYOffset > 300
}

function backToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// ================================================================
// 9. 初始化
// ================================================================
onMounted(() => {
  loadLogs(false)
  window.addEventListener('scroll', onScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <div class="judgement-log-list">
    <!-- 空状态 / 错误 -->
    <div v-if="!loading && renderedLogs.length === 0 && !hasMore" class="empty-state">
      <p>暂无管理日志</p>
    </div>
    <div v-else-if="loadError && renderedLogs.length === 0" class="empty-state">
      <div class="icon">⚠️</div>
      <p>加载失败，请刷新重试</p>
      <p class="err-detail">{{ loadError }}</p>
    </div>

    <!-- ===== 日志行列表（截图样式） ===== -->
    <div class="log-rows">
      <div v-for="log in renderedLogs" :key="log.id" class="log-row">
        <!-- 时间 -->
        <span class="log-time">{{ log.time }}</span>

        <!-- 操作人（仅管理日志页显示） -->
        <template v-if="props.showAdmin">
          <router-link
            :to="log.admin.user_number ? `/user/${log.admin.user_number}` : '#'"
            class="log-user"
            :style="{ color: log.adminColor }"
          >{{ log.admin.username }}</router-link>
          <span
            v-if="log.admin.user_tag"
            class="user-tag-display"
            :style="{ backgroundColor: log.adminColor }"
          >{{ log.admin.user_tag }}</span>
          <span class="log-arrow">→</span>
        </template>

        <!-- 目标用户 -->
        <router-link
          :to="log.target.user_number ? `/user/${log.target.user_number}` : '#'"
          class="log-user"
          :style="{ color: log.targetColor }"
        >{{ log.target.username }}</router-link>
        <span
          v-if="log.target.user_tag"
          class="user-tag-display"
          :style="{ backgroundColor: log.targetColor }"
        >{{ log.target.user_tag }}</span>

        <!-- 权限变更（与陶片放逐页一致的撤销/授予样式） -->
        <span
          v-for="(change, i) in log.changes"
          :key="'c' + i"
          class="permission-change"
        >
          <span :class="change.cls">{{ change.word }}</span>
          <span class="perm-name">{{ change.name }}</span>
          权限
        </span>
        <span v-if="log.extra" class="permission-change">{{ log.extra }}</span>

        <!-- 原因 -->
        <span class="log-reason">{{ log.reason }}</span>

        <!-- 删除（仅秩序管理权限） -->
        <button
          v-if="canManageLogs"
          class="log-delete-btn"
          title="删除这条日志"
          @click="deleteLog(log.id)"
        >删除</button>
      </div>
    </div>

    <!-- ===== 加载更多 ===== -->
    <div class="load-more-wrap">
      <button
        id="load-more"
        :disabled="loading"
        :class="{ loading: loading }"
        :style="{ display: hasMore ? 'inline-flex' : 'none' }"
        @click="loadLogs(true)"
      >
        <span class="spinner"></span>
        <span class="text">加载更多</span>
      </button>
    </div>

    <!-- ===== 回到顶部 ===== -->
    <button id="back-to-top" title="回到顶部" :style="{ display: showBackToTop ? 'block' : 'none' }" @click="backToTop">↑</button>
  </div>
</template>

<style scoped>
/* ===== 日志行列表 ===== */
.log-rows {
  display: flex;
  flex-direction: column;
}

.log-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 14px 8px;
  border-bottom: 1px solid #f0f2f5;
  font-size: 14px;
  line-height: 1.5;
}

.log-row:last-child {
  border-bottom: none;
}

.log-row:hover {
  background: #fafbfc;
}

.log-time {
  color: #8a9aa8;
  font-size: 13px;
  flex-shrink: 0;
  min-width: 130px;
}

.log-user {
  font-weight: 600;
  text-decoration: none;
}

.log-user:hover {
  text-decoration: underline;
}

.log-arrow {
  color: #c0c8d0;
  flex-shrink: 0;
}

/* 权限变更（撤销/授予） */
.permission-change {
  font-size: 14px;
  color: #2d3748;
  white-space: nowrap;
  flex-shrink: 0;
}

.lcolor--red-3 {
  color: #e74c3c;
  font-weight: 600;
}

.lcolor--green-3 {
  color: #52C41A;
  font-weight: 600;
}

.lcolor--purple-3 {
  color: #9d3dcf;
  font-weight: 600;
}

.perm-name {
  display: inline-block;
  background: #e8e8e8;
  padding: 1px 8px;
  border-radius: 4px;
  color: #575757;
  border: 1px solid #bfbfbf;
  margin: 0 4px;
}

.log-reason {
  color: #2c3e50;
  flex: 1;
  min-width: 160px;
  word-break: break-word;
}

.log-delete-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: #c0c8d0;
  font-size: 12px;
  cursor: pointer;
  padding: 0 4px;
  flex-shrink: 0;
  transition: color 0.2s;
}

.log-delete-btn:hover {
  color: #e74c3c;
}

.user-tag-display {
  display: inline-block;
  border-radius: 2px;
  padding: 2px 8px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  cursor: default;
  transition: filter 0.15s;
}

.user-tag-display:hover {
  filter: brightness(0.9);
}

/* ===== 空状态 & 加载更多 ===== */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-state .icon {
  font-size: 3rem;
  margin-bottom: 12px;
  opacity: 0.5;
}

.err-detail {
  font-size: 0.8rem;
  color: #ccc;
  margin-top: 8px;
}

.load-more-wrap {
  text-align: center;
  padding: 12px 0 4px;
}

#load-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 40px;
  border-radius: 24px;
  border: 1px solid #e2e8f0;
  background: transparent;
  font-size: 0.9rem;
  font-weight: 500;
  color: #4a5568;
  cursor: pointer;
  transition: all 0.2s;
}

#load-more:hover:not(:disabled) {
  background: #e74c3c;
  border-color: #e74c3c;
  color: #fff;
  box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);
}

#load-more:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

#load-more .spinner {
  display: none;
  width: 18px;
  height: 18px;
  border: 2px solid #e2e8f0;
  border-top-color: #e74c3c;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

#load-more.loading .spinner {
  display: inline-block;
}

#load-more.loading .text {
  opacity: 0.6;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ===== 回到顶部 ===== */
#back-to-top {
  position: fixed;
  bottom: 30px;
  right: 30px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  font-size: 24px;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  z-index: 999;
  transition: opacity 0.3s, transform 0.3s;
}

#back-to-top:hover {
  background: #c0392b;
  transform: scale(1.1);
}

@media (max-width: 600px) {
  .log-time {
    min-width: 0;
  }

  .log-reason {
    min-width: 100%;
  }

  #back-to-top {
    bottom: 20px;
    right: 20px;
    width: 40px;
    height: 40px;
    font-size: 20px;
  }
}
</style>
