<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import apiClient from '@/api/client'

// 陶片放逐公共页专用：卡片式样式（深色头部）
// 仅展示目标用户与操作内容（操作管理员不在此页展示）
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

function letterAvatar(name: string): string {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2240%22 height=%2240%22 viewBox=%220 0 40 40%22%3E%3Crect width=%2240%22 height=%2240%22 fill=%22%23e74c3c%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22white%22 font-size=%2216%22%3E' +
    ch + '%3C/text%3E%3C/svg%3E'
}

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

interface ActionInfo {
  label: string
  color: string
  iconPath: string
}

const ICON_GRANT = 'M304 304c97.2 0 176 78.8 176 176l0 8c0 13.3-10.7 24-24 24s-24-10.7-24-24l0-8c0-70.7-57.3-128-128-128l-96 0c-70.7 0-128 57.3-128 128l0 8c0 13.3-10.7 24-24 24s-24-10.7-24-24l0-8c0-97.2 78.8-176 176-176l96 0zM528 80c13.3 0 24 10.7 24 24l0 48 48 0c13.3 0 24 10.7 24 24s-10.7 24-24 24l-48 0 0 48c0 13.3-10.7 24-24 24s-24-10.7-24-24l0-48-48 0c-13.3 0-24-10.7-24-24s10.7-24 24-24l48 0 0-48c0-13.3 10.7-24 24-24zM256 256a128 128 0 1 1 0-256 128 128 0 1 1 0 256zm0-208a80 80 0 1 0 0 160 80 80 0 1 0 0-160z'
const ICON_REVOKE = 'M304 304c97.2 0 176 78.8 176 176l0 8c0 13.3-10.7 24-24 24s-24-10.7-24-24l0-8c0-70.7-57.3-128-128-128l-96 0c-70.7 0-128 57.3-128 128l0 8c0 13.3-10.7 24-24 24s-24-10.7-24-24l0-8c0-97.2 78.8-176 176-176l96 0zm-48-48a128 128 0 1 1 0-256 128 128 0 1 1 0 256zm0-208a80 80 0 1 0 0 160 80 80 0 1 0 0-160zM600 152c13.3 0 24 10.7 24 24s-10.7 24-24 24l-144 0c-13.3 0-24-10.7-24-24s10.7-24 24-24l144 0z'
const ICON_BAN = 'M385.1 419.1L92.9 126.9c-28.1 35.5-44.9 80.3-44.9 129.1 0 114.9 93.1 208 208 208 48.8 0 93.7-16.8 129.1-44.9zm33.9-33.9c28.1-35.5 44.9-80.3 44.9-129.1 0-114.9-93.1-208-208-208-48.8 0-93.7 16.8-129.1 44.9L419.1 385.1zM0 256a256 256 0 1 1 512 0 256 256 0 1 1 -512 0z'
const ICON_ROTATE = 'M72 128l24 0 0 16c0 70.7 57.3 128 128 128s128-57.3 128-128l0-16 24 0c13.3 0 24-10.7 24-24s-10.7-24-24-24l-30.7 0c-10.4-53.7-31.9-112-68.3-112-9.6 0-19 3.9-27.5 8.2-8.2 4.1-18.4 7.8-25.5 7.8s-17.3-3.7-25.5-7.8c-8.5-4.3-17.9-8.2-27.5-8.2-36.4 0-57.8 58.3-68.3 112L72 80c-13.3 0-24 10.7-24 24s10.7 24 24 24zm152 0l80 0 0 16c0 44.2-35.8 80-80 80s-80-35.8-80-80l0-16 80 0zM193.5 304c-9.7 0-17.5 7.8-17.5 17.5 0 4.2 1.5 8.2 4.2 11.4l27.2 31.8-18.5 67.8-55.9-102C127 319.5 113.3 315 101.9 320.3 41.8 348.3 0 409.2 0 480l0 8c0 13.3 10.7 24 24 24s24-10.7 24-24l0-8c0-43.4 21.6-81.8 54.7-105L171 499.5c4.2 7.7 12.3 12.5 21 12.5l64 0c8.8 0 16.8-4.8 21-12.5L345.3 375c33.1 23.2 54.7 61.6 54.7 105l0 8c0 13.3 10.7 24 24 24s24-10.7 24-24l0-8c0-70.8-41.8-131.7-101.9-159.7-11.5-5.3-25.1-.9-31.2 10.2l-56.2 102.5-18.4-68.2 27.4-32c2.7-3.2 4.2-7.2 4.2-11.4 0-9.7-7.8-17.5-17.5-17.5l-61 0z'
const ICON_BROWN = 'M69.3 36l48 32c11 7.4 14 22.3 6.7 33.3s-22.3 14-33.3 6.7l-48-32c-11-7.4-14-22.3-6.7-33.3s22.3-14 33.3-6.7zM597.3 76l-48 32c-11 7.4-25.9 4.4-33.3-6.7s-4.4-25.9 6.7-33.3l48-32c11-7.4 25.9-4.4 33.3 6.7s4.4 25.9-6.7 33.3zM24 192l48 0c13.3 0 24 10.7 24 24s-10.7 24-24 24l-48 0c-13.3 0-24-10.7-24-24s10.7-24 24-24zm544 0l48 0c13.3 0 24 10.7 24 24s-10.7 24-24 24l-48 0c-13.3 0-24-10.7-24-24s10.7-24 24-24zM496 320c26.5 0 48 21.5 48 48l0 64c0 26.5-21.5 48-48 48l-352 0c-26.5 0-48-21.5-48-48l0-64c0-26.5 21.5-48 48-48l0-112c0-97.2 78.8-176 176-176s176 78.8 176 176l0 112zm-48 0l0-112c0-70.7-57.3-128-128-128S192 137.3 192 208l0 112 256 0zM144 432l352 0 0-64-352 0 0 64zM312 160c-22.1 0-40 17.9-40 40 0 13.3-10.7 24-24 24s-24-10.7-24-24c0-48.6 39.4-88 88-88 13.3 0 24 10.7 24 24s-10.7 24-24 24z'
const ICON_UNKNOWN = 'M256 0c-70.7 0-128 57.3-128 128 0 70.7 57.3 128 128 128s128-57.3 128-128C384 57.3 326.7 0 256 0zm0 64c35.3 0 64 28.7 64 64s-28.7 64-64 64-64-28.7-64-64S220.7 64 256 64zM128 384c0-70.7 57.3-128 128-128s128 57.3 128 128v32H128v-32z'

function getActionInfo(log: JudgementLog): ActionInfo {
  const action = log.action_type

  if (action === 'grant_normal') {
    return { label: '授予权限', color: '#52C41A', iconPath: ICON_GRANT }
  }
  if (action === 'revoke_normal') {
    return { label: '撤销权限', color: '#E74C3C', iconPath: ICON_REVOKE }
  }
  if (action === 'ostracism') {
    return { label: '陶片放逐', color: '#E67E22', iconPath: ICON_BAN }
  }
  if (action === 'admin_rotation') {
    return { label: '管理轮换', color: '#9D3DCF', iconPath: ICON_ROTATE }
  }
  if (action === 'unbrown') {
    return { label: '解除棕名', color: '#52C41A', iconPath: ICON_GRANT }
  }

  const perm = log.action_detail?.permission

  if (action === 'perm_update') {
    return { label: '管理轮换', color: '#9D3DCF', iconPath: ICON_ROTATE }
  }

  const managerPerms = ['is_admin', 'can_manage_users', 'can_manage_posts']
  if ((action === 'grant_perm' || action === 'revoke_perm') && managerPerms.includes(perm)) {
    return { label: '管理轮换', color: '#9D3DCF', iconPath: ICON_ROTATE }
  }

  if (action === 'brown_penalty') {
    return { label: '棕名惩罚', color: '#8d6e63', iconPath: ICON_BROWN }
  }

  if (action === 'ban' || (action === 'revoke_perm' && perm === 'is_banned')) {
    return { label: '用户封禁', color: '#E74C3C', iconPath: ICON_BAN }
  }

  if (action === 'unban' || action === 'grant_perm') {
    return { label: '授予权限', color: '#52C41A', iconPath: ICON_GRANT }
  }

  if (action === 'revoke_perm') {
    return { label: '撤销权限', color: '#E74C3C', iconPath: ICON_REVOKE }
  }

  return { label: '未知操作', color: '#718096', iconPath: ICON_UNKNOWN }
}

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

function isUnbrownAction(action_type: string): boolean {
  const t = (action_type || '').toLowerCase()
  return t === 'unbrown' || /unbrown|remove_brown|lift_brown|clear_brown|restore_color|brown_restored|penalty_expired|penalty_lifted|penalty_removed|unpenalty/.test(t)
}

interface PermChange {
  word: string
  cls: string
  name: string
}

interface RenderedLog {
  id: number
  info: ActionInfo
  time: string
  target: LogUser
  targetColor: string
  tagHtml: { text: string; color: string }[]
  avatar: string
  userLink: string
  changes: PermChange[]
  extraChange: string
  reason: string
}

const COLOR_RED = '#e74c3c'
const COLOR_PURPLE = '#9C3DCF'
const COLOR_BROWN = '#AD8B00'

function buildRenderedLog(log: JudgementLog): RenderedLog {
  const target: LogUser = log.target_user || {
    id: null, username: '已删除', avatar_url: '', user_tag: '',
    is_admin: false, is_banned: false, user_number: null,
    username_color: '', is_cheater: false,
  }

  const info = getActionInfo(log)
  const time = formatTime(log.created_at)

  const targetColor = target.is_cheater ? COLOR_BROWN : (target.is_admin ? COLOR_PURPLE : COLOR_RED)

  const tags: { text: string; color: string }[] = []
  if (target.user_tag) {
    tags.push({ text: target.user_tag, color: targetColor })
  } else if (target.is_admin) {
    tags.push({ text: '管理员', color: targetColor })
  }
  if (target.is_banned) {
    tags.push({ text: '已封禁', color: '#e53e3e' })
  }

  const avatar = target.avatar_url || letterAvatar(target.username)
  const userLink = target.user_number ? `/user/${target.user_number}` : '#'

  const changes: PermChange[] = []
  let extraChange = ''
  const d = log.action_detail || {}

  const permLine = (word: string, cls: string, name: string): PermChange =>
    ({ word, cls, name })

  if (['grant_normal', 'revoke_normal', 'ostracism', 'admin_rotation', 'unbrown'].includes(log.action_type)) {
    const cs = Array.isArray(d?.changes) ? d.changes : []
    cs.forEach((c: any) => {
      let isGrant: boolean
      if (c.permission === 'is_banned') {
        isGrant = (c.new_value === false)
      } else {
        isGrant = (c.new_value === true)
      }
      changes.push(permLine(isGrant ? '授予' : '撤销', isGrant ? 'lcolor--green-3' : 'lcolor--red-3', getPermName(c.permission)))
    })
  }
  else if (log.action_type === 'perm_update') {
    const cs = Array.isArray(d?.changes) ? d.changes : []
    cs.forEach((c: any) => {
      let isGrant: boolean
      if (c.permission === 'is_banned') {
        isGrant = (c.new_value === false)
      } else {
        isGrant = (c.new_value === true)
      }
      changes.push(permLine(isGrant ? '授予' : '撤销', isGrant ? 'lcolor--green-3' : 'lcolor--red-3', getPermName(c.permission)))
    })
  } else if (log.action_type === 'grant_perm' || log.action_type === 'revoke_perm') {
    let isGrant = log.action_type === 'grant_perm'
    const perm = d?.permission
    changes.push(permLine(isGrant ? '授予' : '撤销', isGrant ? 'lcolor--green-3' : 'lcolor--red-3', getPermName(perm)))
  } else if (log.action_type === 'ban') {
    changes.push(permLine('撤销', 'lcolor--red-3', '进入主站'))
  } else if (log.action_type === 'unban') {
    changes.push(permLine('授予', 'lcolor--green-3', '进入主站'))
  } else if (log.action_type === 'cheat') {
    extraChange = '学术不端惩罚'
  } else if (log.action_type === 'brown_penalty') {
    // 作弊惩罚：不显示标记文案，只显示原因
  } else if (log.action_type === 'manager_rotate') {
    const permName = d?.permission || '管理权限'
    extraChange = '授予 ' + permName + ' 权限（轮换）'
  } else {
    extraChange = info.label
  }

  return {
    id: log.id,
    info, time, target, targetColor, tagHtml: tags,
    avatar, userLink,
    changes, extraChange,
    reason: log.reason || '（无）',
  }
}

const renderedLogs = ref<RenderedLog[]>([])

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

async function deleteLog(id: number) {
  if (!canManageLogs.value || !id) return
  if (!confirm('永久删除这条陶片？此操作不可恢复。')) return
  try {
    await apiClient.delete(`/api/judgement/logs/${id}`)
    logs.value = logs.value.filter(l => l.id !== id)
    renderedLogs.value = logs.value.map(buildRenderedLog)
  } catch (err: any) {
    alert('删除失败：' + (err.response?.data?.detail || err.message || err))
  }
}

const showBackToTop = ref(false)

function onScroll() {
  showBackToTop.value = window.pageYOffset > 300
}

function backToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

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
    <div class="log-list">
        <div v-if="!loading && logs.length === 0 && !hasMore" class="empty-state">
          <p>没有更多陶片了</p>
        </div>
        <div v-else-if="loadError && logs.length === 0" class="empty-state">
          <div class="icon">⚠️</div>
          <p>加载失败，请刷新重试</p>
          <p class="err-detail">{{ loadError }}</p>
        </div>

        <div v-for="log in renderedLogs" :key="log.id" class="log-card">
          <div class="log-author">
            <div class="left">
              <b :style="{ color: log.info.color }">
                <svg class="log-icon" viewBox="0 0 640 512" fill="currentColor">
                  <path :d="log.info.iconPath" />
                </svg>
                {{ log.info.label }}
              </b>
            </div>
            <div class="time">
              {{ log.time }}<button
                v-if="canManageLogs"
                class="log-delete-btn"
                title="删除这条陶片"
                @click="deleteLog(log.id)"
              >删除</button>
            </div>
          </div>

          <div class="log-users">
            <router-link :to="log.userLink" class="log-user">
              <img
                :src="log.avatar"
                :alt="log.target.username"
                @error="(e) => (e.target as HTMLImageElement).src = letterAvatar(log.target.username)"
              >
              <span class="uname" :style="{ color: log.targetColor }">{{ log.target.username }}</span>
              <span
                v-for="(tag, i) in log.tagHtml"
                :key="i"
                class="user-tag-display"
                :style="{ backgroundColor: tag.color }"
              >{{ tag.text }}</span>
            </router-link>
          </div>

          <div class="log-content">
            <ul v-if="log.changes.length > 0 || log.extraChange">
              <li v-for="(change, i) in log.changes" :key="i">
                <span class="permission-change">
                  <span :class="change.cls">{{ change.word }}</span>
                  <span class="perm-name">{{ change.name }}</span>
                  权限
                </span>
              </li>
              <li v-if="log.extraChange">
                <span class="permission-change">{{ log.extraChange }}</span>
              </li>
            </ul>
            <p>{{ log.reason }}</p>
          </div>
        </div>
      </div>

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

      <button id="back-to-top" title="回到顶部" :style="{ display: showBackToTop ? 'block' : 'none' }" @click="backToTop">↑</button>
    </div>
</template>

<style scoped>
.log-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.log-card {
  background: #fafbfc;
  border-radius: 12px;
  padding: 16px 20px;
  border: 1px solid #edf2f7;
  transition: none;
}

.log-card:hover {
  background: #fafbfc;
  transform: none;
}

.log-author {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #F0F2F5;
  border-radius: 8px 8px 0 0;
  margin: -16px -20px 12px -20px;
}

.log-author .left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 0.95rem;
}

.log-author .left b {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
}

.log-author .left .log-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.log-author .time {
  font-size: 0.78rem;
  color: #7D7D7D;
  white-space: nowrap;
}

.lcolor--red-3 {
  color: #e74c3c;
}

.lcolor--green-3 {
  color: #38a169;
}

.lcolor--purple-3 {
  color: #9d3dcf;
}

.lcolor--orange-3 {
  color: #e67e22;
}

.log-users {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin: 6px 0 10px 0;
}

.log-user {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: #2c3e50;
  text-decoration: none;
}

.log-user:hover {
  color: #e74c3c;
}

.log-user img {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid #e2e8f0;
  flex-shrink: 0;
  background: #e74c3c;
}

.log-user .uname {
  font-weight: bold;
  font-size: 1em;
}

.user-tag-display {
  display: inline-block;
  border-radius: 2px;
  padding: 2px 9px;
  color: #fff;
  font-size: 11.5px;
  font-weight: 600;
  margin: 0;
  cursor: default;
  transition: filter 0.15s;
}

.user-tag-display:hover {
  filter: brightness(0.9);
}

.log-content {
  padding-left: 0;
}

.log-content ul {
  list-style: disc;
  padding-left: 1.5em;
  margin: 0 0 4px 0;
}

.log-content ul li {
  padding: 0;
  margin: 0;
}

.log-content .permission-change {
  font-size: 0.9rem;
  color: #2d3748;
}

.log-content .permission-change .lcolor--red-3 {
  color: #E74C3C;
}

.log-content .permission-change .lcolor--green-3 {
  color: #52C41A;
}

.log-content .permission-change .perm-name {
  display: inline-block;
  background: #E8E8E8;
  padding: 0 8px;
  border-radius: 4px;
  color: #575757;
  border: 1px solid #BFBFBF;
  margin: 0 4px;
}

.log-content p {
  margin: 4px 0 0 0;
  font-size: 0.88rem;
  color: #4a5568;
  padding-top: 8px;
}

.log-content p strong {
  color: #2d3748;
}

.log-delete-btn {
  margin-left: 8px;
  background: none;
  border: none;
  color: #e74c3c;
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}

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
  #back-to-top {
    bottom: 20px;
    right: 20px;
    width: 40px;
    height: 40px;
    font-size: 20px;
  }
}
</style>
