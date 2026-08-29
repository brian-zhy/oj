<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const CATEGORIES: Record<string, string> = {
  consult: '一般咨询',
  suggestion: '建议反馈',
  bug: 'Bug反馈',
  appeal: '账号申诉',
}

const STATUS: Record<string, { text: string; color: string; bg: string }> = {
  pending: { text: '待处理', color: '#00BCD4', bg: '#E0F7FA' },
  replied: { text: '待补充', color: '#FF9800', bg: '#FFF3E0' },
  processing: { text: '处理中', color: '#D4AC0D', bg: '#FDF6DD' },
  suspended: { text: '挂起', color: '#909399', bg: '#F4F4F5' },
  resolved: { text: '已完成', color: '#52C41A', bg: '#F0FAE5' },
  closed: { text: '已关闭', color: '#E74C3C', bg: '#FDECEC' },
  deleted: { text: '已删除', color: '#909399', bg: '#F4F4F5' },
}

const OPEN_STATUSES = ['pending', 'replied', 'processing', 'suspended']

// 管理员可手动设置的状态（「待补充」仅由回复自动产生，不提供手动设置）
const MANAGEABLE_STATUS = Object.fromEntries(
  Object.entries(STATUS).filter(([key]) => key !== 'replied')
)

const ticket = ref<any>(null)
const loading = ref(true)
const error = ref('')

const replyContent = ref('')
const replySubmitting = ref(false)
const newStatus = ref('')
const statusSubmitting = ref(false)

// 责任人指派
const staffList = ref<any[]>([])
const showAssign = ref(false)
const assigneeId = ref<number | null>(null)
const assigning = ref(false)

const toggleAssign = async () => {
  showAssign.value = !showAssign.value
  if (showAssign.value && staffList.value.length === 0) {
    try {
      const data: any = await apiClient.get('/api/tickets/staff')
      staffList.value = Array.isArray(data) ? data : []
    } catch {
      staffList.value = []
    }
  }
}

const doAssign = async () => {
  assigning.value = true
  try {
    await apiClient.put(`/api/tickets/${route.params.id}/assign`, { assignee_id: assigneeId.value })
    showAssign.value = false
    await loadTicket()
  } catch (err: any) {
    alert(err.response?.data?.detail || '指派失败')
  } finally {
    assigning.value = false
  }
}

// 工单描述编辑
const editingDesc = ref(false)
const descContent = ref('')
const descSaving = ref(false)

const startEditDesc = () => {
  descContent.value = ticket.value.description || ''
  editingDesc.value = true
}

const saveDesc = async () => {
  if (!descContent.value.trim()) return
  descSaving.value = true
  try {
    await apiClient.put(`/api/tickets/${route.params.id}/description`, { content: descContent.value.trim() })
    editingDesc.value = false
    await loadTicket()
  } catch (err: any) {
    alert(err.response?.data?.detail || '保存失败')
  } finally {
    descSaving.value = false
  }
}

const me = computed(() => authStore.currentUser)
const isStaff = computed(() => ticket.value?.can_manage)
const isCreator = computed(() => ticket.value?.is_creator)
const canReply = computed(() => {
  if (!ticket.value) return false
  if (isStaff.value) return true
  return isCreator.value && OPEN_STATUSES.includes(ticket.value.status)
})

const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

const fmtTime = (iso: string) => (iso ? String(iso).replace('T', ' ').slice(0, 16) : '')

// 相对时间（如「25 天前」）
const relTime = (iso: string) => {
  if (!iso) return ''
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 2592000) return `${Math.floor(diff / 86400)} 天前`
  return new Date(iso).toLocaleDateString('zh-CN')
}

// 用户名颜色（管理员紫 / 普通红）
const userColor = (u: any) => (u?.is_admin ? '#9C3DCF' : '#e74c3c')

// 状态中文名 → 配色（时间线记录用）
const statusColorByText = (text: string) => {
  const key = Object.keys(STATUS).find(k => STATUS[k].text === text)
  return key ? STATUS[key].color : '#52C41A'
}

const loadTicket = async () => {
  loading.value = true
  error.value = ''
  try {
    ticket.value = await apiClient.get(`/api/tickets/${route.params.id}`)
    newStatus.value = ticket.value.status
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const submitReply = async () => {
  if (!replyContent.value.trim()) return
  replySubmitting.value = true
  try {
    await apiClient.post(`/api/tickets/${route.params.id}/replies`, { content: replyContent.value.trim() })
    replyContent.value = ''
    await loadTicket()
  } catch (err: any) {
    alert(err.response?.data?.detail || '回复失败')
  } finally {
    replySubmitting.value = false
  }
}

const changeStatus = async () => {
  if (!newStatus.value || newStatus.value === ticket.value.status) return
  statusSubmitting.value = true
  try {
    await apiClient.put(`/api/tickets/${route.params.id}/status`, { status: newStatus.value })
    await loadTicket()
  } catch (err: any) {
    alert(err.response?.data?.detail || '状态更新失败')
  } finally {
    statusSubmitting.value = false
  }
}

const closeOwn = async () => {
  if (!confirm('确定关闭这个工单吗？')) return
  try {
    await apiClient.put(`/api/tickets/${route.params.id}/status`, { status: 'closed' })
    await loadTicket()
  } catch (err: any) {
    alert(err.response?.data?.detail || '关闭失败')
  }
}

onMounted(() => loadTicket())
</script>

<template>
  <div class="ticket-detail-page">
    <div class="detail-container">
      <div v-if="loading" class="state-box">加载中...</div>
      <div v-else-if="error" class="state-box error-text">❌ {{ error }}</div>

      <template v-else-if="ticket">
        <!-- 头部 -->
        <div class="ticket-head card">
          <div class="head-row">
            <span class="ticket-no">{{ ticket.ticket_no }}</span>
            <h2 class="ticket-title">{{ ticket.title }}</h2>
            <span class="status-badge" :style="{ color: STATUS[ticket.status]?.color, backgroundColor: STATUS[ticket.status]?.bg }">
              {{ STATUS[ticket.status]?.text || ticket.status }}
            </span>
          </div>

          <!-- 字段信息网格 -->
          <div class="meta-grid">
            <div class="meta-item">
              <div class="meta-label">发起人</div>
              <div class="meta-value">
                <router-link
                  :to="ticket.creator?.user_number ? `/user/${ticket.creator.user_number}` : '#'"
                  class="creator-link"
                  :style="{ color: ticket.creator?.is_admin ? '#9C3DCF' : '#e74c3c' }"
                >{{ ticket.creator?.username || '未知用户' }}</router-link>
                <span
                  v-if="ticket.creator?.user_tag"
                  class="user-tag-display"
                  :style="{ backgroundColor: ticket.creator?.is_admin ? '#9C3DCF' : '#e74c3c' }"
                >{{ ticket.creator.user_tag }}</span>
              </div>
            </div>
            <div class="meta-item">
              <div class="meta-label">责任人</div>
              <div class="meta-value">
                <template v-if="ticket.assignee">
                  <router-link
                    :to="ticket.assignee.user_number ? `/user/${ticket.assignee.user_number}` : '#'"
                    class="creator-link"
                    :style="{ color: ticket.assignee.is_admin ? '#9C3DCF' : '#e74c3c' }"
                  >{{ ticket.assignee.username }}</router-link>
                  <span
                    v-if="ticket.assignee.user_tag"
                    class="user-tag-display"
                    :style="{ backgroundColor: ticket.assignee.is_admin ? '#9C3DCF' : '#e74c3c' }"
                  >{{ ticket.assignee.user_tag }}</span>
                </template>
                <span v-else class="muted">暂无</span>
                <button v-if="isStaff" class="btn-assign" @click="toggleAssign">
                  {{ ticket.assignee ? '更改' : '指派' }}
                </button>
                <span v-if="showAssign" class="assign-pop">
                  <select v-model="assigneeId" class="status-select">
                    <option :value="null">取消指派</option>
                    <option v-for="u in staffList" :key="u.user_id" :value="u.user_id">
                      {{ u.username }}{{ u.user_tag ? ` (${u.user_tag})` : '' }}
                    </option>
                  </select>
                  <button class="btn-status" :disabled="assigning" @click="doAssign">
                    {{ assigning ? '处理中...' : '确认' }}
                  </button>
                </span>
              </div>
            </div>
            <div class="meta-item">
              <div class="meta-label">工单类型</div>
              <div class="meta-value">{{ CATEGORIES[ticket.category] || ticket.category }}</div>
            </div>
            <div class="meta-item">
              <div class="meta-label">创建时间</div>
              <div class="meta-value">{{ fmtTime(ticket.created_at) }}</div>
            </div>
          </div>

          <div class="head-meta">
            <span v-if="ticket.is_public">🌐 公开工单（登录用户可见）</span>
            <span v-else>🔒 私密工单（仅创建者与管理员可见）</span>
          </div>

        </div>

        <!-- 工单描述 -->
        <div class="desc-card card">
          <div class="desc-head">
            <span class="desc-title">工单描述</span>
            <button
              v-if="isCreator && OPEN_STATUSES.includes(ticket.status) && !editingDesc"
              class="btn-edit-desc"
              @click="startEditDesc"
            >编辑</button>
          </div>
          <template v-if="!editingDesc">
            <div class="desc-content">{{ ticket.description }}</div>
          </template>
          <template v-else>
            <textarea
              v-model="descContent"
              rows="5"
              class="reply-textarea"
              maxlength="5000"
            ></textarea>
            <div class="reply-actions">
              <button class="btn-submit" :disabled="descSaving || !descContent.trim()" @click="saveDesc">
                {{ descSaving ? '保存中...' : '保存' }}
              </button>
              <button class="btn-cancel-2" :disabled="descSaving" @click="editingDesc = false">取消</button>
            </div>
          </template>
        </div>

        <!-- 操作状态条（工单描述之下、回复之上） -->
        <div class="action-bar card">
          <template v-if="isStaff">
            <span class="staff-label">处理操作：</span>
            <select v-model="newStatus" class="status-select">
              <option
                v-for="(s, key) in MANAGEABLE_STATUS"
                :key="key"
                :value="key"
              >{{ s.text }}</option>
            </select>
            <button
              class="btn-status"
              :disabled="statusSubmitting || newStatus === ticket.status"
              @click="changeStatus"
            >{{ statusSubmitting ? '更新中...' : '更新状态' }}</button>
          </template>
          <template v-else-if="isCreator && OPEN_STATUSES.includes(ticket.status)">
            <span class="staff-label">问题已解决？</span>
            <button class="btn-close-own" @click="closeOwn">关闭工单</button>
          </template>
        </div>

        <!-- 回复时间线 -->
        <div v-if="ticket.replies.slice(1).length > 0" class="replies">
          <div v-if="ticket.replies.filter((r: any) => !r.action_text).length > 1" class="replies-title">
            回复（{{ ticket.replies.filter((r: any) => !r.action_text).length - 1 }}）
          </div>
          <template v-for="r in ticket.replies.slice(1)" :key="r.id">
            <!-- 状态变更记录（洛谷样式：头像+彩色名+徽章+状态名，下方相对时间） -->
            <div v-if="r.action_text" class="action-record">
              <div class="action-head">
                <img
                  :src="r.user?.avatar_url || letterAvatar(r.user?.username)"
                  class="reply-avatar"
                  :alt="r.user?.username"
                >
                <span class="reply-user" :style="{ color: userColor(r.user) }">{{ r.user?.username || '未知用户' }}</span>
                <span
                  v-if="r.user?.user_tag || r.user?.is_admin"
                  class="user-tag-display"
                  :style="{ backgroundColor: userColor(r.user) }"
                >{{ r.user?.user_tag || '管理员' }}</span>
                <!-- 指派记录：被指派人以彩色名+标签展示 -->
                <span v-if="r.action_text.startsWith('将责任人') && r.action_target" class="action-text">
                  将责任人指派为
                  <router-link
                    :to="r.action_target.user_number ? `/user/${r.action_target.user_number}` : '#'"
                    class="action-user"
                    :style="{ color: r.action_target.is_admin ? '#9C3DCF' : '#e74c3c' }"
                  >{{ r.action_target.username }}</router-link>
                  <span
                    v-if="r.action_target.user_tag"
                    class="user-tag-display"
                    :style="{ backgroundColor: r.action_target.is_admin ? '#9C3DCF' : '#e74c3c' }"
                  >{{ r.action_target.user_tag }}</span>
                </span>
                <span v-else-if="r.action_text === '取消了责任人'" class="action-text">取消了责任人</span>
                <span v-else class="action-text">将工单状态设置为 <b class="action-status" :style="{ color: statusColorByText(r.action_text) }">{{ r.action_text }}</b></span>
              </div>
              <div class="action-time-line">{{ relTime(r.created_at) }}</div>
            </div>
            <!-- 普通回复 -->
            <div v-else class="reply-item" :class="{ staff: r.is_staff }">
              <div class="reply-head">
                <img
                  :src="r.user?.avatar_url || letterAvatar(r.user?.username)"
                  class="reply-avatar"
                  :alt="r.user?.username"
                >
                <span class="reply-user" :style="{ color: userColor(r.user) }">{{ r.user?.username || '未知用户' }}</span>
                <span
                  v-if="r.user?.user_tag || r.user?.is_admin"
                  class="user-tag-display"
                  :style="{ backgroundColor: userColor(r.user) }"
                >{{ r.user?.user_tag || '管理员' }}</span>
                <span v-if="r.user_id === ticket.creator_id" class="creator-badge">发起人</span>
                <span class="reply-time">{{ fmtTime(r.created_at) }}</span>
              </div>
              <div class="reply-content">{{ r.content }}</div>
            </div>
          </template>
        </div>

        <!-- 回复框 -->
        <div v-if="canReply" class="reply-box card">
          <div class="reply-box-head">
            {{ isStaff ? '以管理员身份回复（仅「待处理」工单会自动变为「待补充」，其他状态保持不变）' : '补充信息 / 追问' }}
          </div>
          <textarea
            v-model="replyContent"
            rows="4"
            class="reply-textarea"
            placeholder="请输入回复内容……"
            maxlength="5000"
          ></textarea>
          <div class="reply-actions">
            <button class="btn-submit" :disabled="replySubmitting || !replyContent.trim()" @click="submitReply">
              {{ replySubmitting ? '发送中...' : '回复' }}
            </button>
          </div>
        </div>
        <div v-else class="state-box closed-tip">该工单已完结，如仍有问题请返回<a href="/tickets" class="link">工单中心</a>新建工单。</div>

        <div class="back-bar">
          <button class="btn-back" @click="router.push('/tickets')">← 返回工单中心</button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.ticket-detail-page {
  min-height: 100vh;
  line-height: 1.6;
}

.detail-container {
  max-width: 860px;
  margin: 0 auto;
}

.card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 18px 22px;
}

.state-box {
  text-align: center;
  padding: 60px 20px;
  color: #999;
  background: #fff;
  border-radius: 12px;
}

.error-text {
  color: #e74c3c;
}

.closed-tip .link {
  color: #e74c3c;
  margin: 0 4px;
}

.ticket-head {
  margin-bottom: 16px;
}

.head-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.ticket-no {
  color: #8a9aa8;
  font-weight: 600;
}

.ticket-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
  flex: 1;
  min-width: 200px;
  word-break: break-word;
}

.status-badge {
  display: inline-block;
  padding: 3px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.head-meta {
  margin-top: 12px;
  color: #8a9aa8;
  font-size: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 14px 20px;
  margin-top: 16px;
  padding: 14px 16px;
  background: #f8f9fc;
  border-radius: 10px;
}

.meta-label {
  font-size: 12px;
  color: #8a9aa8;
  margin-bottom: 4px;
}

.meta-value {
  font-size: 14px;
  color: #2c3e50;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.meta-value.muted {
  color: #b0b8c1;
  font-weight: 400;
}

.creator-link {
  font-weight: 700;
  text-decoration: none;
}

.btn-assign {
  padding: 3px 12px;
  background: #3498db;
  color: #fff;
  border: none;
  border-radius: 14px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-assign:hover {
  background: #2980b9;
}

.assign-pop {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 8px;
}

.assign-pop select {
  flex: 1;
  min-width: 0;
}

.btn-status {
  white-space: nowrap;
}

.creator-link:hover {
  text-decoration: underline;
}

.user-tag-display {
  display: inline-block;
  border-radius: 2px;
  padding: 1px 8px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  cursor: default;
}

.staff-bar {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed #edf2f7;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.staff-label {
  font-size: 13px;
  color: #8a9aa8;
}

.status-select {
  padding: 7px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  color: #4a5568;
}

.btn-status {
  padding: 7px 18px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 18px;
  font-size: 13px;
  cursor: pointer;
}

.btn-status:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-close-own {
  padding: 7px 18px;
  background: #f3f4f6;
  color: #4a5568;
  border: none;
  border-radius: 18px;
  font-size: 13px;
  cursor: pointer;
}

.action-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.desc-card {
  margin-bottom: 16px;
}

.desc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.desc-title {
  font-weight: 700;
  font-size: 15px;
  color: #2c3e50;
}

.btn-edit-desc {
  padding: 4px 16px;
  background: #3498db;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-edit-desc:hover {
  background: #2980b9;
}

.desc-content {
  color: #2d3748;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

.btn-cancel-2 {
  padding: 8px 22px;
  background: #f3f4f6;
  color: #4a5568;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
}

.replies-title {
  font-weight: 700;
  font-size: 14px;
  color: #8a9aa8;
  padding: 0 4px;
}

.action-record {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 12px 18px;
}

.action-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.action-text {
  font-size: 14px;
  color: #2d3748;
}

.action-status {
  font-weight: 700;
}

.action-user {
  font-weight: 700;
  text-decoration: none;
}

.action-user:hover {
  text-decoration: underline;
}

.action-time-line {
  margin-top: 4px;
  padding-left: 34px;
  font-size: 12px;
  color: #a0aec0;
}

.replies {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.reply-item {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 14px 18px;
}

.reply-item.staff {
  border-left: 3px solid #e74c3c;
}

.reply-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.reply-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  object-fit: cover;
  background: #f0f2f5;
}

.reply-user {
  font-weight: 700;
  font-size: 14px;
  color: #2c3e50;
}

.staff-badge {
  background: #e74c3c;
  color: #fff;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.creator-badge {
  background: #3498db;
  color: #fff;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 600;
}

.reply-time {
  color: #a0aec0;
  font-size: 12px;
  margin-left: auto;
}

.reply-content {
  color: #2d3748;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

.reply-box-head {
  font-size: 13px;
  color: #8a9aa8;
  margin-bottom: 10px;
}

.reply-textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}

.reply-textarea:focus {
  border-color: #e74c3c;
}

.reply-actions {
  margin-top: 10px;
  text-align: right;
}

.btn-submit {
  padding: 8px 28px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.back-bar {
  margin-top: 16px;
}

.btn-back {
  padding: 8px 22px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  font-size: 13px;
  color: #4a5568;
  cursor: pointer;
}

.btn-back:hover {
  color: #e74c3c;
  border-color: #e74c3c;
}
</style>
