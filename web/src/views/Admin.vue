<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'
import Swal from 'sweetalert2'

const authStore = useAuthStore()

// ===== 常量定义（与目标项目完全一致） =====
const COLOR_RED = '#e74c3c'
const COLOR_PURPLE = '#9C3DCF'
const COLOR_BROWN = '#AD8B00'
const ONLINE_THRESHOLD = 60

// ===== 状态管理 =====
const users = ref<any[]>([])
const loading = ref(false)
const searchQuery = ref('')
const currentUser = ref<any>(null)
const currentProfile = ref<any>(null)
const pendingChanges = ref<Record<number, any>>({})

// ===== 筛选状态（与目标项目完全一致） =====
interface FilterStates {
  admin: 'off' | 'has' | 'no'
  user_mgmt: 'off' | 'has' | 'no'
  post_mgmt: 'off' | 'has' | 'no'
  enter_site: 'off' | 'has' | 'no'
  cheater: 'off' | 'has' | 'no'
  speak: 'off' | 'has' | 'no'
  status: 'off' | 'online' | 'offline'
}

const filterStates = ref<FilterStates>({
  admin: 'off',
  user_mgmt: 'off',
  post_mgmt: 'off',
  enter_site: 'off',
  cheater: 'off',
  speak: 'off',
  status: 'off'
})

// ===== 计算属性 =====
const canAccessAdmin = computed(() => {
  const user = authStore.currentUser
  return user && (user.is_super_admin || user.is_admin || user.can_manage_users)
})

// 是否为一号超管（参考项目 isSuperAdmin 判断：user_number === 1 且超管）
const isSuperAdmin = computed(() => {
  const p = currentProfile.value
  return !!(p && p.user_number === 1 && p.is_super_admin === true)
})

const isSuper = computed(() => {
  const p = currentProfile.value
  return p?.is_super_admin === true
})

const filteredUsers = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  return users.value.filter(user => {
    let match = true
    if (keyword) {
      const userNumber = String(user.user_number)
      const username = (user.username || '').toLowerCase()
      const remark = (user.remark || '').toLowerCase()
      const tag = (user.user_tag || '').toLowerCase()
      const roleLabel = user.is_admin ? '管理员' : '普通用户'

      if (userNumber !== keyword &&
          username !== keyword &&
          remark !== keyword &&
          tag !== keyword &&
          roleLabel !== keyword) {
        match = false
      }
    }

    if (match) {
      for (const key in filterStates.value) {
        const state = filterStates.value[key as keyof FilterStates]
        if (state === 'off') continue

        let hasPermission = false
        if (key === 'status') {
          if (state === 'online') hasPermission = isUserOnline(user)
          else if (state === 'offline') hasPermission = !isUserOnline(user)
        } else {
          switch (key) {
            case 'admin':
              hasPermission = user.is_admin
              break
            case 'user_mgmt':
              hasPermission = user.can_manage_users
              break
            case 'post_mgmt':
              hasPermission = user.can_manage_posts
              break
            case 'enter_site':
              hasPermission = !user.is_banned
              break
            case 'cheater':
              hasPermission = user.is_cheater
              break
            case 'speak':
              hasPermission = user.can_speak !== false
              break
          }

          if (state === 'has' && !hasPermission) { match = false; break }
          if (state === 'no' && hasPermission) { match = false; break }
        }

        if (key === 'status') {
          if (state === 'online' && !hasPermission) { match = false; break }
          if (state === 'offline' && !hasPermission) { match = false; break }
        }
      }
    }

    return match
  })
})

// ===== 工具函数（与目标项目完全一致） =====
function formatTime(iso: string): string {
  if (!iso) return '未知'
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

function letterAvatar(name: string): string {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

function getUserDisplayColor(user: any): string {
  if (user?.is_cheater) return COLOR_BROWN
  if (user?.is_admin) return COLOR_PURPLE
  return COLOR_RED
}

function isUserOnline(user: any): boolean {
  if (!user.last_seen) return false
  try {
    const last = new Date(user.last_seen)
    const now = new Date()
    return (now.getTime() - last.getTime()) <= ONLINE_THRESHOLD * 1000
  } catch {
    return false
  }
}

function canModifyUser(targetUser: any): boolean {
  if (!currentProfile.value) return false
  if (currentProfile.value.user_number === 1 && currentProfile.value.is_super_admin) return true
  if (targetUser.user_number === currentProfile.value.user_number) return false
  if (targetUser.is_super_admin) return false
  if (currentProfile.value.can_manage_users) return true
  return false
}

// 权限修改：不能修改自己的权限
function canModifyPermissions(targetUser: any): boolean {
  if (!currentProfile.value) return false
  if (targetUser.user_number === currentProfile.value.user_number) return false
  return canModifyUser(targetUser)
}

// 超级管理是固定身份：任何人都不可修改（只读展示）
function canToggleField(field: string): boolean {
  return field !== 'is_super_admin'
}

// ===== OI/XCPC等级徽章（与目标项目完全一致） =====
function getCcfBadgeHtml(ccfLevel: number, user: any): string {
  if (user && user.show_ccf_badge === false) return ''
  if (!ccfLevel) return ''
  if (ccfLevel >= 11) {
    return `<svg class="svg-inline--fa fa-badge-check rainbow-badge" style="width: 16px; height: 16px; vertical-align: middle;">
      <path fill="currentColor" d="M0 256C0 292.8 20.7 324.8 51.1 340.9 41 373.8 49 411 75 437s63.3 34 96.1 23.9C187.2 491.3 219.2 512 256 512s68.8-20.7 84.9-51.1C373.8 471 411 463 437 437s34-63.3 23.9-96.1C491.3 324.8 512 292.8 512 256s-20.7-68.8-51.1-84.9C471 138.2 463 101 437 75s-63.3-34-96.1-23.9C324.8 20.7 292.8 0 256 0s-68.8 20.7-84.9 51.1C138.2 41 101 49 75 75s-34 63.3-23.9 96.1C20.7 187.2 0 219.2 0 256z"/>
    </svg>`
  }
  if (!ccfLevel || ccfLevel < 1 || ccfLevel > 10) return ''

  let color = ''
  if (ccfLevel >= 1 && ccfLevel <= 5) color = '#52C41A'
  else if (ccfLevel >= 6 && ccfLevel <= 7) color = '#3498DB'
  else if (ccfLevel >= 8 && ccfLevel <= 10) color = '#FFC116'

  return `<svg class="svg-inline--fa fa-badge-check" style="width: 16px; height: 16px; vertical-align: middle;">
    <path class="fa-secondary" fill="${color}" d="M0 256C0 292.8 20.7 324.8 51.1 340.9 41 373.8 49 411 75 437s63.3 34 96.1 23.9C187.2 491.3 219.2 512 256 512s68.8-20.7 84.9-51.1C373.8 471 411 463 437 437s34-63.3 23.9-96.1C491.3 324.8 512 292.8 512 256s-20.7-68.8-51.1-84.9C471 138.2 463 101 437 75s-63.3-34-96.1-23.9C324.8 20.7 292.8 0 256 0s-68.8 20.7-84.9 51.1C138.2 41 101 49 75 75s-34 63.3-23.9 96.1C20.7 187.2 0 219.2 0 256z"/>
    <path class="fa-primary" fill="#ffffff" d="M328.7 155.5c7.8-10.7 22.8-13.1 33.5-5.3 10.7 7.8 13.1 22.8 5.3 33.5L244.7 352.7c-4.2 5.7-10.7 9.4-17.8 9.8-7.1 .5-14-2.2-18.9-7.3l-55.7-57.6c-9.2-9.5-9-24.7 .6-33.9 9.5-9.2 24.7-8.9 33.9 .6l35.8 37 106.1-145.8z"/>
  </svg>`
}

function getXcpcBalloonHtml(level: number, user: any): string {
  if (user && user.show_xcpc_badge === false) return ''
  if (!level) return ''
  let color = ''
  if (level >= 1 && level <= 5) {
    color = '#52C41A'
  } else if (level >= 6 && level <= 7) {
    color = '#3498DB'
  } else if (level >= 8 && level <= 10) {
    color = '#FFC116'
  }
  if (level >= 11) {
    return `<svg class="svg-inline--fa fa-balloon rainbow-badge" style="width: 16px; height: 16px; vertical-align: middle; margin-left: 2px;">
      <path class="fa-primary" fill="currentColor" d="M56 176c0 13.3 10.7 24 24 24s24-10.7 24-24c0-39.8 32.2-72 72-72 13.3 0 24-10.7 24-24s-10.7-24-24-24C109.7 56 56 109.7 56 176z"></path>
      <path class="fa-secondary" fill="currentColor" d="M0 192C0 86 86 0 192 0S384 86 384 192c0 128-160 240-160 240l27.9 41.8c2.7 4 4.1 8.8 4.1 13.6 0 13.6-11 24.6-24.6 24.6l-78.9 0c-13.6 0-24.6-11-24.6-24.6 0-4.8 1.4-9.6 4.1-13.6L160 432S0 320 0 192z"></path>
    </svg>`
  }
  return `<svg class="svg-inline--fa fa-balloon" style="width: 16px; height: 16px; vertical-align: middle; margin-left: 2px;">
    <path class="fa-secondary" fill="#ffffff" d="M56 176c0 13.3 10.7 24 24 24s24-10.7 24-24c0-39.8 32.2-72 72-72 13.3 0 24-10.7 24-24s-10.7-24-24-24C109.7 56 56 109.7 56 176z"></path>
    <path class="fa-primary" fill="${color}" d="M0 192C0 86 86 0 192 0S384 86 384 192c0 128-160 240-160 240l27.9 41.8c2.7 4 4.1 8.8 4.1 13.6 0 13.6-11 24.6-24.6 24.6l-78.9 0c-13.6 0-24.6-11-24.6-24.6 0-4.8 1.4-9.6 4.1-13.6L160 432S0 320 0 192z"></path>
  </svg>`
}

// ===== 筛选功能（与目标项目完全一致） =====
function toggleFilterTag(key: keyof FilterStates) {
  if (key === 'status') {
    const current = filterStates.value[key] || 'off'
    if (current === 'off') filterStates.value[key] = 'online'
    else if (current === 'online') filterStates.value[key] = 'offline'
    else if (current === 'offline') filterStates.value[key] = 'off'
  } else {
    const current = filterStates.value[key] || 'off'
    if (current === 'off') filterStates.value[key] = 'has'
    else if (current === 'has') filterStates.value[key] = 'no'
    else if (current === 'no') filterStates.value[key] = 'off'
  }
}

function getFilterLabel(key: keyof FilterStates): string {
  const labels: Record<string, string> = {
    admin: '进入后台',
    user_mgmt: '用户管理',
    post_mgmt: '秩序管理',
    enter_site: '进入主站',
    cheater: '学术不端',
    speak: '自由发言',
    status: '状态'
  }
  return labels[key] || key
}

function getFilterTagClass(key: keyof FilterStates): string {
  const state = filterStates.value[key] || 'off'
  let classes = 'filter-tag'
  if (state === 'has') classes += ' active-green'
  else if (state === 'no') classes += ' active-red'
  else if (key === 'status') {
    if (state === 'online') classes += ' active-online'
    else if (state === 'offline') classes += ' active-offline'
  }
  return classes
}

// ===== 权限修改（与目标项目完全一致：本地待确认 + SweetAlert2 输入原因） =====
function toggleLocalPermission(userNumber: number, field: string, currentValue: boolean) {
  if (!canToggleField(field)) return
  if (!pendingChanges.value[userNumber]) pendingChanges.value[userNumber] = {}
  if (pendingChanges.value[userNumber][field] !== undefined) {
    delete pendingChanges.value[userNumber][field]
  } else {
    pendingChanges.value[userNumber][field] = !currentValue
  }
  if (Object.keys(pendingChanges.value[userNumber]).length === 0) {
    delete pendingChanges.value[userNumber]
  }
}

// 分析权限变更类型（与目标项目 analyzePermissionChanges 一致）
function analyzePermissionChanges(changes: any) {
  const normalPerms = ['can_speak']
  const adminPerms = ['is_super_admin', 'is_admin', 'can_manage_users', 'can_manage_posts']

  let normalGrants: any[] = []
  let normalRevokes: any[] = []
  let adminGrants: any[] = []
  let adminRevokes: any[] = []

  for (const [field, value] of Object.entries(changes)) {
    const changeInfo = { permission: field, new_value: value }

    if (field === 'is_banned') {
      if (value === false) { normalGrants.push(changeInfo) } else { normalRevokes.push(changeInfo) }
    } else if (normalPerms.includes(field)) {
      if (value === true) { normalGrants.push(changeInfo) } else { normalRevokes.push(changeInfo) }
    } else if (adminPerms.includes(field)) {
      if (value === true) { adminGrants.push(changeInfo) } else { adminRevokes.push(changeInfo) }
    }
  }

  return { normalGrants, normalRevokes, adminGrants, adminRevokes }
}

// SweetAlert2 输入原因（与目标项目 promptReason 一致）
async function promptReason(operationName: string): Promise<string | undefined> {
  const { value: reason } = await Swal.fire({
    title: `请输入 ${operationName} 的原因`,
    html: `<textarea id="swal-textarea" class="swal2-textarea" rows="3" style="width:100%;max-width:460px;text-align:left;margin:0 auto;display:block;"></textarea>`,
    showCancelButton: true,
    confirmButtonText: '操作',
    cancelButtonText: '取消',
    focusConfirm: false,
    preConfirm: () => {
      const textarea = document.getElementById('swal-textarea') as HTMLTextAreaElement | null
      const value = textarea ? textarea.value.trim() : ''
      if (!value) { Swal.showValidationMessage('原因不能为空！'); return false }
      return value
    }
  })
  return reason
}

// 更新用户字段（权限修改：记录陶片放逐日志）
async function updateUserField(userNumber: number, changes: any, reason?: string) {
  await apiClient.post(`/api/admin/users/${userNumber}/permissions`, {
    changes,
    reason
  })
}

// 更新用户资料（双击编辑：用户名/标签/备注）
async function updateUserProfile(userNumber: number, updateData: any) {
  const data: any = await apiClient.put(`/api/admin/users/${userNumber}`, updateData)
  const target = users.value.find(u => u.user_number === userNumber)
  if (target && data) Object.assign(target, data)
}

// 确认修改（与目标项目 applyUserChanges 一致）
async function applyUserChanges(userNumber: number) {
  const targetUser = users.value.find(u => u.user_number === userNumber)
  if (targetUser && !canModifyPermissions(targetUser)) {
    Swal.fire({ icon: 'warning', title: '无效操作', text: '不能修改自己的权限' })
    return
  }
  const changes = pendingChanges.value[userNumber]
  if (!changes || Object.keys(changes).length === 0) {
    Swal.fire({ icon: 'info', title: '没有待修改的权限', timer: 1200 })
    return
  }
  const reason = await promptReason('确认修改权限')
  if (!reason) return

  const onlyCheaterChange = Object.keys(changes).length === 1 && changes.is_cheater !== undefined
  const onlyBannedChange = Object.keys(changes).length === 1 && changes.is_banned !== undefined

  const { normalGrants, normalRevokes, adminGrants, adminRevokes } = analyzePermissionChanges(changes)

  const hasNormalChanges = normalGrants.length > 0 || normalRevokes.length > 0
  const hasAdminChanges = adminGrants.length > 0 || adminRevokes.length > 0

  if (hasNormalChanges && hasAdminChanges) {
    Swal.fire({
      icon: 'warning',
      title: '无效操作',
      text: '不能同时修改普通权限和管理权限，请分别操作'
    })
    return
  }

  let actionLabel = ''

  if (onlyCheaterChange) {
    actionLabel = changes.is_cheater ? '棕名惩罚' : '解除棕名'
  } else if (onlyBannedChange) {
    actionLabel = changes.is_banned === false ? '授予权限' : '用户封禁'
  } else if (hasNormalChanges) {
    if (normalGrants.length > 0 && normalRevokes.length === 0) {
      actionLabel = '授予权限'
    } else if (normalRevokes.length > 0 && normalGrants.length === 0) {
      actionLabel = '撤销权限'
    } else {
      actionLabel = '陶片放逐'
    }
  } else if (hasAdminChanges) {
    actionLabel = '管理轮换'
  }

  try {
    // 超级管理是固定身份：剔除任何针对它的修改
    const submitChanges = { ...changes }
    delete submitChanges.is_super_admin
    if (Object.keys(submitChanges).length === 0) {
      delete pendingChanges.value[userNumber]
      await loadUsers()
      return
    }
    await updateUserField(userNumber, submitChanges, reason)
    delete pendingChanges.value[userNumber]
    await loadUsers()

    Swal.fire({
      icon: 'success',
      title: '修改成功',
      text: `${actionLabel}操作已完成`,
      timer: 1500
    })
  } catch (err: any) {
    Swal.fire({ icon: 'error', title: '更新失败', text: err.response?.data?.detail || err.message || '未知错误' })
  }
}

// ===== 行内编辑（双击，Vue 响应式管理编辑态，避免手写 DOM 破坏渲染） =====
const editing = ref<null | { field: 'username' | 'user_tag' | 'remark'; userNumber: number }>(null)
const editingValue = ref('')

function startEdit(field: 'username' | 'user_tag' | 'remark', user: any) {
  if (!canModifyUser(user)) return
  if (field === 'user_tag' && user.is_cheater) return
  editing.value = { field, userNumber: user.user_number }
  editingValue.value = field === 'username'
    ? (user.username || '未命名')
    : field === 'user_tag'
      ? (user.user_tag || '')
      : (user.remark || '')
  nextTick(() => {
    const input = document.querySelector('.editable-field-input') as HTMLInputElement | null
    if (input) { input.focus(); input.select() }
  })
}

function cancelEdit() {
  editing.value = null
  editingValue.value = ''
}

async function saveEdit(user: any) {
  if (!editing.value) return
  const field = editing.value.field
  let val = editingValue.value.trim()
  const original = field === 'username'
    ? (user.username || '未命名')
    : field === 'user_tag'
      ? (user.user_tag || '')
      : (user.remark || '')
  cancelEdit()
  if (val === original) return
  // 标签：管理员留空时默认"管理员"（与目标项目一致）
  if (field === 'user_tag' && user.is_admin && val === '') val = '管理员'
  try {
    await updateUserProfile(user.user_number, { [field]: val || null })
    await loadUsers()
  } catch { /* 静默，数据未变 */ }
}

// 双击头像上传（与目标项目一致）
function uploadAvatar(user: any) {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.style.display = 'none'
  document.body.appendChild(input)
  input.addEventListener('change', async () => {
    const file = input.files?.[0]
    if (!file) { input.remove(); return }
    try {
      const fd = new FormData()
      fd.append('file', file)
      const data: any = await apiClient.post(`/api/admin/users/${user.user_number}/avatar`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      const target = users.value.find(u => u.user_number === user.user_number)
      if (target) target.avatar_url = data.avatar_url
    } catch { /* 静默 */ } finally { input.remove() }
  })
  input.click()
}

// ===== 用户列表加载 =====
async function loadUsers() {
  if (!canAccessAdmin.value) return

  loading.value = true
  try {
    const data = await apiClient.get('/api/admin/users')
    users.value = (data as any) || []
    currentUser.value = authStore.currentUser
    currentProfile.value = authStore.currentUser
    // 重新加载后重置筛选（与目标项目一致）
    Object.keys(filterStates.value).forEach(k => {
      ;(filterStates.value as any)[k] = 'off'
    })
  } catch (error: any) {
    console.error('加载用户列表失败:', error)
    Swal.fire({ icon: 'error', title: '加载失败', text: error.response?.data?.detail || error.message })
  } finally {
    loading.value = false
  }
}

// ===== 选择功能 =====
const selectedUsers = ref<Set<number>>(new Set())

function toggleUserSelection(userNumber: number) {
  if (selectedUsers.value.has(userNumber)) {
    selectedUsers.value.delete(userNumber)
  } else {
    selectedUsers.value.add(userNumber)
  }
}

function toggleSelectAll(e: Event) {
  const checked = (e.target as HTMLInputElement).checked
  if (!checked) {
    selectedUsers.value.clear()
  } else {
    filteredUsers.value.forEach(user => {
      if (canModifyPermissions(user)) selectedUsers.value.add(user.user_number)
    })
  }
}

// ===== 批量操作（与目标项目 batchAction 一致） =====
async function batchAction(actionName: string, updateObj: any) {
  const ids = Array.from(selectedUsers.value)
  if (ids.length === 0) return
  const targetUsers = ids
    .map(id => users.value.find(u => u.user_number === id))
    .filter(u => u && canModifyPermissions(u))
  if (targetUsers.length === 0) return
  const reason = await promptReason(actionName)
  if (!reason) return
  try {
    const filteredIds = targetUsers.map(u => u.user_number)
    await apiClient.post('/api/admin/users/batch', {
      user_numbers: filteredIds,
      updates: updateObj,
      reason
    })
    selectedUsers.value.clear()
    await loadUsers()
  } catch (error: any) {
    Swal.fire({ icon: 'error', title: '批量操作失败', text: error.response?.data?.detail || error.message })
  }
}

// ===== 重置密码（SweetAlert2，仅 UID=2 可用） =====
async function resetPassword(userId: number, username: string) {
  const result = await Swal.fire({
    title: `重置 ${username} 的密码`,
    input: 'password',
    inputAttributes: { autocomplete: 'new-password' },
    showCancelButton: true,
    confirmButtonText: '确认重置',
    cancelButtonText: '取消',
    preConfirm: (value) => {
      if (!value) {
        Swal.showValidationMessage('请填写完整')
        return false
      }
      if (value.length < 6) {
        Swal.showValidationMessage('密码长度过短或过长')
        return false
      }
      return value
    }
  })

  if (result.isConfirmed) {
    const newPassword = result.value
    try {
      await apiClient.post(`/api/admin/users/id/${userId}/reset-password`, { password: newPassword })
      await Swal.fire({
        icon: 'success',
        title: '重置成功',
        text: `用户 ${username} 的密码已重置`,
        timer: 1500
      })
    } catch (err: any) {
      Swal.fire({
        icon: 'error',
        title: '重置失败',
        text: err.response?.data?.detail || err.message || '未知错误'
      })
    }
  }
}

// ===== 心跳上报（与目标项目 updateLastSeen 一致） =====
let heartbeatTimer: number | undefined

async function updateLastSeen() {
  if (!authStore.isAuthenticated) return
  try {
    await apiClient.post('/api/users/me/seen')
  } catch { /* 静默 */ }
}

// ===== 生命周期 =====
onMounted(async () => {
  // 刷新页面时认证状态是异步恢复的：先确保 currentUser 就绪再加载列表
  if (!authStore.currentUser && authStore.accessToken) {
    try {
      await authStore.fetchCurrentUser()
    } catch { /* 失败时由路由守卫处理 */ }
  }
  if (canAccessAdmin.value) {
    await loadUsers()
    await updateLastSeen()
    heartbeatTimer = window.setInterval(updateLastSeen, 30000)
  }
})

onUnmounted(() => {
  if (heartbeatTimer) clearInterval(heartbeatTimer)
})
</script>

<template>
  <div class="admin-page">
    <!-- ===== 主布局（与目标项目完全一致） ===== -->
    <div class="main-layout">
      <!-- ===== 内容区域（与目标项目完全一致） ===== -->
      <div class="content-wrapper">
        <div class="main-content">
          <div class="card">
            <div class="card-header">用户管理</div>
            <div class="search-bar">
              <input v-model="searchQuery" type="text">
              <span class="result-count">共 {{ filteredUsers.length }} 位用户</span>
            </div>
            <div class="filter-tags">
              <span
                v-for="(state, key) in filterStates"
                :key="key"
                :class="getFilterTagClass(key as keyof FilterStates)"
                @click="toggleFilterTag(key as keyof FilterStates)"
              >
                {{ getFilterLabel(key as keyof FilterStates) }}
              </span>
            </div>
            <div class="table-wrap">
              <!-- 加载中 -->
              <div v-if="loading" class="loading-text">
                加载中...
              </div>

              <!-- 空状态 -->
              <div v-else-if="filteredUsers.length === 0" class="loading-text">
                没有找到匹配的用户
              </div>

              <!-- 用户表格 -->
              <table v-else>
                <thead>
                  <tr>
                    <th class="check-col"><input type="checkbox" title="全选" @change="toggleSelectAll"></th>
                    <th>注册时间</th>
                    <th>用户编号</th>
                    <th>头像</th>
                    <th>用户名</th>
                    <th>标签</th>
                    <th>OI</th>
                    <th>XCPC</th>
                    <th>备注名</th>
                    <th>用户类型</th>
                    <th>权限</th>
                    <th v-if="isSuperAdmin">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="user in filteredUsers" :key="user.user_number">
                    <!-- 选择框（在线绿/离线红） -->
                    <td class="check-col">
                      <input
                        type="checkbox"
                        class="row-checkbox"
                        :class="isUserOnline(user) ? 'online' : 'offline'"
                        :disabled="!canModifyPermissions(user)"
                        :checked="selectedUsers.has(user.user_number)"
                        @change="toggleUserSelection(user.user_number)"
                      >
                    </td>

                    <!-- 注册时间 -->
                    <td>{{ formatTime(user.created_at) }}</td>

                    <!-- 用户编号 -->
                    <td>
                      <router-link
                        :to="`/user/${user.user_number}`"
                        style="color:#2c3e50;text-decoration:none;"
                      >
                        {{ user.user_number }}
                      </router-link>
                    </td>

                    <!-- 头像（双击上传） -->
                    <td>
                      <img
                        class="avatar-image"
                        :src="user.avatar_url || letterAvatar(user.username)"
                        :alt="user.username"
                        style="width:32px;height:32px;border-radius:50%;object-fit:cover;background:#f0f2f5;display:block;cursor:pointer;"
                        @error="(e) => (e.target as HTMLImageElement).src = letterAvatar(user.username)"
                        @dblclick="canModifyUser(user) && uploadAvatar(user)"
                      >
                    </td>

                    <!-- 用户名（双击编辑） -->
                    <td>
                      <input
                        v-if="editing && editing.field === 'username' && editing.userNumber === user.user_number"
                        v-model="editingValue"
                        class="editable-field-input"
                        @blur="saveEdit(user)"
                        @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
                        @keydown.esc.prevent="cancelEdit"
                      >
                      <span
                        v-else
                        class="username-display"
                        :style="{ color: getUserDisplayColor(user) }"
                        @dblclick="startEdit('username', user)"
                      >{{ user.username || '未命名' }}</span>
                    </td>

                    <!-- 标签（双击编辑） -->
                    <td>
                      <input
                        v-if="editing && editing.field === 'user_tag' && editing.userNumber === user.user_number"
                        v-model="editingValue"
                        class="editable-field-input"
                        @blur="saveEdit(user)"
                        @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
                        @keydown.esc.prevent="cancelEdit"
                      >
                      <span
                        v-else
                        @dblclick="startEdit('user_tag', user)"
                      >
                        <span
                          v-if="(user.is_admin ? (user.user_tag || '管理员') : (user.is_cheater ? '作弊者' : (user.user_tag || '')))"
                          class="user-tag-display"
                          :style="{ backgroundColor: getUserDisplayColor(user) }"
                        >{{ user.is_cheater ? '作弊者' : (user.is_admin ? (user.user_tag || '管理员') : user.user_tag) }}</span>
                        <span v-else class="editable-field">-</span>
                      </span>
                    </td>

                    <!-- OI等级 -->
                    <td>
                      <span v-if="user.ccf_level && user.ccf_level >= 1" class="level-badge-svg">{{ user.ccf_level }} 级 <span v-html="getCcfBadgeHtml(user.ccf_level, user)"></span></span>
                      <span v-else>-</span>
                    </td>

                    <!-- XCPC等级 -->
                    <td>
                      <span v-if="user.xcpc_level && user.xcpc_level >= 1" class="level-badge-svg">{{ user.xcpc_level }} 级 <span v-html="getXcpcBalloonHtml(user.xcpc_level, user)"></span></span>
                      <span v-else>-</span>
                    </td>

                    <!-- 备注名（双击编辑） -->
                    <td>
                      <input
                        v-if="editing && editing.field === 'remark' && editing.userNumber === user.user_number"
                        v-model="editingValue"
                        class="editable-field-input"
                        @blur="saveEdit(user)"
                        @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
                        @keydown.esc.prevent="cancelEdit"
                      >
                      <span
                        v-else
                        class="editable-field"
                        @dblclick="startEdit('remark', user)"
                      >{{ user.remark || '-' }}</span>
                    </td>

                    <!-- 用户类型（纯文本，与目标项目一致） -->
                    <td>{{ user.is_admin ? '管理员' : '普通用户' }}</td>

                    <!-- 权限（本地待确认 + 确认修改） -->
                    <td>
                      <div class="perm-group-line">
                        <span class="perm-cat">普通权限</span>
                        <!-- 进入主站（is_banned 反逻辑：绿色=可进入） -->
                        <span
                          v-if="canModifyPermissions(user)"
                          class="action-link"
                          :class="[(pendingChanges[user.user_number]?.is_banned !== undefined ? (pendingChanges[user.user_number].is_banned ? 'red' : 'green') : (user.is_banned ? 'red' : 'green')), (pendingChanges[user.user_number]?.is_banned !== undefined ? 'pending' : '')]"
                          style="cursor:pointer;"
                          @click="toggleLocalPermission(user.user_number, 'is_banned', user.is_banned || false)"
                        >进入主站</span>
                        <span v-else class="action-link" :class="user.is_banned ? 'red' : 'green'" style="cursor:default;">进入主站</span>
                        |
                        <!-- 学术不端（绿色=已标记） -->
                        <span
                          v-if="canModifyPermissions(user)"
                          class="action-link"
                          :class="[(pendingChanges[user.user_number]?.is_cheater !== undefined ? (pendingChanges[user.user_number].is_cheater ? 'green' : 'red') : (user.is_cheater ? 'green' : 'red')), (pendingChanges[user.user_number]?.is_cheater !== undefined ? 'pending' : '')]"
                          style="cursor:pointer;"
                          @click="toggleLocalPermission(user.user_number, 'is_cheater', user.is_cheater || false)"
                        >学术不端</span>
                        <span v-else class="action-link" :class="user.is_cheater ? 'green' : 'red'" style="cursor:default;">学术不端</span>
                        |
                        <!-- 自由发言 -->
                        <span
                          v-if="canModifyPermissions(user)"
                          class="action-link"
                          :class="[(pendingChanges[user.user_number]?.can_speak !== undefined ? (pendingChanges[user.user_number].can_speak ? 'green' : 'red') : (user.can_speak !== false ? 'green' : 'red')), (pendingChanges[user.user_number]?.can_speak !== undefined ? 'pending' : '')]"
                          style="cursor:pointer;"
                          @click="toggleLocalPermission(user.user_number, 'can_speak', user.can_speak !== false)"
                        >自由发言</span>
                        <span v-else class="action-link" :class="user.can_speak !== false ? 'green' : 'red'" style="cursor:default;">自由发言</span>
                      </div>
                      <div class="perm-group-line">
                        <span class="perm-cat">管理权限</span>
                        <template v-for="(perm, idx) in [
                          ...(isSuperAdmin ? [{ name: '超级管理', field: 'is_super_admin', on: !!user.is_super_admin }] : []),
                          { name: '进入后台', field: 'is_admin', on: !!user.is_admin },
                          { name: '用户管理', field: 'can_manage_users', on: !!user.can_manage_users },
                          { name: '秩序管理', field: 'can_manage_posts', on: !!user.can_manage_posts }
                        ]" :key="perm.field">
                          <span v-if="idx > 0"> | </span>
                          <span
                            v-if="canModifyPermissions(user) && canToggleField(perm.field)"
                            class="action-link"
                            :class="[(pendingChanges[user.user_number]?.[perm.field] !== undefined ? (pendingChanges[user.user_number][perm.field] ? 'green' : 'red') : (perm.on ? 'green' : 'red')), (pendingChanges[user.user_number]?.[perm.field] !== undefined ? 'pending' : '')]"
                            style="cursor:pointer;"
                            @click="toggleLocalPermission(user.user_number, perm.field, perm.on)"
                          >{{ perm.name }}</span>
                          <span v-else class="action-link" :class="perm.on ? 'green' : 'red'" style="cursor:default;">{{ perm.name }}</span>
                        </template>
                      </div>
                      <div class="perm-group-line" style="margin-top:4px;">
                        <button
                          class="btn-sm confirm"
                          :disabled="!(pendingChanges[user.user_number] && Object.keys(pendingChanges[user.user_number]).length > 0)"
                          @click="applyUserChanges(user.user_number)"
                        >确认修改</button>
                      </div>
                    </td>

                    <!-- 操作（仅 UID=1 / UID=2 可见） -->
                    <td v-if="authStore.currentUser && [1, 2, 11].includes(authStore.currentUser.user_number)">
                      <button class="btn-reset-password" @click="resetPassword(user.id, user.username)">重置密码</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- ===== 批量操作栏（与目标项目完全一致） ===== -->
            <div class="batch-bar" :class="{ show: selectedUsers.size > 0 }">
              <span class="info">已选 {{ selectedUsers.size }} 位用户</span>
              <button class="btn-sm grant" @click="batchAction('批量授予进入主站权限', { is_banned: false })">授予进入主站权限</button>
              <button class="btn-sm revoke" @click="batchAction('批量撤销进入主站权限', { is_banned: true })">撤销进入主站权限</button>
              <button class="btn-sm grant" @click="batchAction('批量授予自由发言权限', { can_speak: true })">授予自由发言权限</button>
              <button class="btn-sm revoke" @click="batchAction('批量撤销自由发言权限', { can_speak: false })">撤销自由发言权限</button>
              <button v-if="isSuper" class="btn-sm grant" @click="batchAction('批量授予进入后台权限', { is_admin: true })">授予进入后台权限</button>
              <button v-if="isSuper" class="btn-sm revoke" @click="batchAction('批量撤销进入后台权限', { is_admin: false })">撤销进入后台权限</button>
              <button v-if="isSuper" class="btn-sm grant" @click="batchAction('批量授予用户管理权限', { can_manage_users: true })">授予用户管理权限</button>
              <button v-if="isSuper" class="btn-sm revoke" @click="batchAction('批量撤销用户管理权限', { can_manage_users: false })">撤销用户管理权限</button>
              <button v-if="isSuper" class="btn-sm grant" @click="batchAction('批量授予秩序管理权限', { can_manage_posts: true })">授予秩序管理权限</button>
              <button v-if="isSuper" class="btn-sm revoke" @click="batchAction('批量撤销秩序管理权限', { can_manage_posts: false })">撤销秩序管理权限</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ========== 基础样式（与目标项目完全一致） ========== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.admin-page {
  background: #f5f7fa;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  line-height: 1.5;
}

/* ========== 主布局（与目标项目完全一致） ========== */
.main-layout {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px 20px 20px;
  position: relative;
  min-height: 100vh;
}

/* ========== 卡片样式（与目标项目完全一致） ========== */
.card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 20px 24px;
  margin-bottom: 24px;
}

.card-header {
  font-size: 1.25rem;
  font-weight: 600;
  border-left: 4px solid #e74c3c;
  padding-left: 12px;
  margin-bottom: 20px;
}

/* ========== 搜索栏（与目标项目完全一致） ========== */
.search-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.search-bar input {
  flex: 1;
  min-width: 200px;
  padding: 8px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border .2s;
}

.search-bar input:focus {
  border-color: #e74c3c;
}

.search-bar .result-count {
  font-size: 13px;
  color: #999;
  white-space: nowrap;
}

/* ========== 筛选标签（与目标项目完全一致） ========== */
.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0 12px 0;
}

.filter-tag {
  padding: 4px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  transition: background .2s, color .2s, border-color .2s, transform .1s;
  border: 2px solid transparent;
  background: #f0f2f5;
  color: #8a9aa8;
  white-space: nowrap;
}

.filter-tag:hover {
  background: #e0e0e0;
  transform: scale(1.02);
}

.filter-tag.active-green {
  background: #eafaf1;
  color: #52C41A;
  border-color: #52C41A;
}

.filter-tag.active-red {
  background: #fdedec;
  color: #E74C3C;
  border-color: #E74C3C;
}

.filter-tag.active-online {
  background: #eafaf1;
  color: #2ecc71;
  border-color: #2ecc71;
}

.filter-tag.active-offline {
  background: #fdedec;
  color: #e74c3c;
  border-color: #e74c3c;
}

/* ========== 表格样式（与目标项目完全一致） ========== */
.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

th,
td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #edf2f7;
  vertical-align: middle;
}

th {
  background: #f8f9fc;
  font-weight: 600;
  color: #2c3e50;
  white-space: nowrap;
  position: sticky;
  top: 0;
  z-index: 2;
}

th:first-child,
td:first-child {
  padding-left: 8px;
}

th.check-col,
td.check-col {
  width: 40px;
  text-align: center;
}

th.check-col input,
td.check-col input {
  cursor: pointer;
  width: 16px;
  height: 16px;
}

/* ========== 自定义行复选框（在线绿/离线红，与目标项目完全一致） ========== */
.row-checkbox {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border: 2px solid #ccc;
  border-radius: 4px;
  outline: none;
  cursor: pointer;
  background: white;
  position: relative;
  flex-shrink: 0;
}

.row-checkbox:checked {
  background: #3498db;
  border-color: #3498db;
}

.row-checkbox:checked::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'/%3E%3C/svg%3E") no-repeat center;
  background-size: contain;
}

.row-checkbox.online {
  border-color: #2ecc71;
  background: #2ecc71;
}

.row-checkbox.offline {
  border-color: #e74c3c;
  background: #e74c3c;
}

.row-checkbox.online:checked {
  background: #2ecc71;
  border-color: #2ecc71;
}

.row-checkbox.offline:checked {
  background: #e74c3c;
  border-color: #e74c3c;
}

.row-checkbox:disabled {
  opacity: 0.5;
  cursor: default;
}

/* ========== 权限链接（与目标项目完全一致） ========== */
.perm-group-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-bottom: 3px;
}

.perm-group-line:last-child {
  margin-bottom: 0;
}

.perm-cat {
  font-size: 11px;
  color: #888;
  margin-right: 2px;
}

.action-link {
  text-decoration: none;
  font-size: 13px;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
}

.action-link.green {
  color: #52C41A;
  font-weight: 500;
}

.action-link.red {
  color: #E74C3C;
  font-weight: 500;
}

.action-link.green:hover {
  background: #eafaf1;
}

.action-link.red:hover {
  background: #fdedec;
}

.action-link.pending {
  border: 2px solid #f39c12;
  background: #fef9e7;
}

/* ========== 行内编辑（与目标项目完全一致） ========== */
.editable-field {
  cursor: default;
  padding: 2px 4px;
  border-radius: 3px;
}

.editable-field:hover {
  background: #f0f2f5;
}

.editable-field-input {
  border: 1px solid #e74c3c;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 14px;
  width: 100%;
  min-width: 80px;
  outline: none;
}

.username-display {
  font-weight: bold;
  cursor: pointer;
  transition: background .15s;
}

.username-display:hover {
  background: #f0f2f5;
}

.user-tag-display {
  display: inline-block;
  border-radius: 2px;
  padding: 2px 9px;
  color: #fff;
  font-size: 11.5px;
  font-weight: 600;
  margin: 0 0 0 8px;
  cursor: default;
  transition: filter .15s;
  background-color: #9C3DCF;
}

.user-tag-display:hover {
  filter: brightness(0.9);
}

/* ========== 按钮样式（与目标项目完全一致） ========== */
.btn-sm {
  padding: 4px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  margin: 2px;
}

.btn-sm.grant {
  background: #52C41A;
  color: #fff;
}

.btn-sm.revoke {
  background: #E74C3C;
  color: #fff;
}

.btn-sm:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.btn-sm.confirm {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 4px 10px;
  border-radius: 40px;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
  width: auto;
  font-family: inherit;
  font-weight: 500;
}

.btn-sm.confirm:hover {
  background: #c0392b;
}

.btn-sm.confirm:disabled {
  opacity: 0.5;
  cursor: default;
}

.btn-sm.confirm:disabled:hover {
  background: #e74c3c;
}

.btn-reset-password {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  padding: 5px 12px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  text-decoration: none;
  transition: filter 0.2s, transform 0.1s;
  white-space: nowrap;
  font-family: inherit;
  line-height: 1.4;
  color: #fff;
  background: #E74C3C;
}

.btn-reset-password:hover {
  filter: brightness(1.1);
}

.btn-reset-password:active {
  transform: scale(0.96);
}

/* ========== 批量操作栏（与目标项目完全一致） ========== */
.batch-bar {
  display: none;
  margin-top: 16px;
  padding: 12px 16px;
  background: #f8f9fc;
  border-radius: 8px;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.batch-bar.show {
  display: flex;
}

.batch-bar .info {
  font-size: 14px;
  color: #2c3e50;
  margin-right: 8px;
}

.batch-bar .btn-sm {
  font-size: 12px;
  padding: 4px 10px;
}

/* ========== OI/XCPC 徽章（与目标项目完全一致） ========== */
@keyframes rainbow-fill {
  0% { fill: #e74c3c; }
  14.28% { fill: #e67e22; }
  28.57% { fill: #f1c40f; }
  42.85% { fill: #2ecc71; }
  57.14% { fill: #3498db; }
  71.42% { fill: #9b59b6; }
  85.71% { fill: #8e44ad; }
  100% { fill: #e74c3c; }
}

.rainbow-badge path,
.rainbow-badge .fa-secondary {
  animation: rainbow-fill 5s linear infinite;
}

.level-badge-svg {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-weight: 500;
  color: #2c3e50;
  white-space: nowrap;
}

.level-badge-svg svg {
  width: 16px;
  height: 16px;
  vertical-align: middle;
  margin-left: 2px;
}

/* ========== 加载和空状态（与目标项目完全一致） ========== */
.loading-text {
  color: #999;
  text-align: center;
  padding: 40px;
}

/* ========== 响应式（与目标项目完全一致） ========== */
@media (max-width: 800px) {

  table,
  thead,
  tbody,
  th,
  td,
  tr {
    display: block;
  }

  thead tr {
    display: none;
  }

  tr {
    border: 1px solid #eee;
    margin-bottom: 10px;
    padding: 10px;
  }

  td {
    border: none;
    padding: 6px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  td::before {
    content: attr(data-label);
    font-weight: 600;
    color: #333;
    margin-right: 10px;
    flex-shrink: 0;
  }

  td.check-col {
    display: flex;
    justify-content: flex-start;
  }

  td.check-col::before {
    content: '';
    display: none;
  }

  .batch-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .editable-field-input {
    width: auto;
  }
}

@media (max-width: 600px) {
  .card {
    padding: 16px 18px;
  }

  .batch-bar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
