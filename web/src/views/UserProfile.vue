<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const authStore = useAuthStore()

// 用户资料
const userProfile = ref({
  username: '',
  email: '',
  user_number: '',
  bio: '',
  avatar_url: '',
  user_tag: '',
  username_color: '',
  created_at: '',
  is_active: false,
  is_admin: false,
  can_speak: false,
  can_manage_users: false,
  can_manage_posts: false,
  phone: ''
} as any)

// 编辑模式
const isEditing = ref(false)
const editForm = ref({
  bio: '',
  user_tag: ''
})

// ===== 头像上传 =====
const avatarUploading = ref(false)
const avatarInputRef = ref<HTMLInputElement | null>(null)

const pickAvatar = () => {
  if (avatarUploading.value) return
  avatarInputRef.value?.click()
}

const onAvatarChange = async (e: Event) => {
  const files = (e.target as HTMLInputElement).files
  if (!files || !files.length) return
  const file = files[0]

  if (!file.type.startsWith('image/')) {
    showMessage('请选择图片文件', 'error')
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    showMessage('图片不能超过 5MB', 'error')
    return
  }

  avatarUploading.value = true
  const previousAvatar = userProfile.value.avatar_url || ''
  let failMsg = ''

  try {
    const fd = new FormData()
    fd.append('file', file)
    const res: any = await apiClient.post('/users/me/avatar', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    userProfile.value.avatar_url = res.avatar_url
  } catch (error: any) {
    failMsg = error.response?.data?.detail || ''
    // 请求报错时向服务端核实真实结果——请求可能被代理/插件改写，但实际已成功
    try {
      const me: any = await apiClient.get('/auth/me')
      if (me?.avatar_url && me.avatar_url !== previousAvatar) {
        userProfile.value.avatar_url = me.avatar_url
        failMsg = ''
      }
    } catch {
      /* 核实也失败则维持失败判定 */
    }
  }

  avatarUploading.value = false
  if (failMsg) {
    showMessage(failMsg || '头像上传失败，请稍后重试', 'error')
  } else {
    // 同步顶栏等处的本地缓存
    if (authStore.currentUser) {
      authStore.currentUser.avatar_url = userProfile.value.avatar_url
    }
    showMessage('头像更新成功', 'success')
  }
  if (avatarInputRef.value) avatarInputRef.value.value = ''
}

// 加载状态
const loading = ref(false)
const saving = ref(false)

// 统计信息
const stats = ref({
  solved_count: 0,
  submission_count: 0,
  accept_rate: 0
})

// 成功/失败消息
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

// 计算头像显示
const avatarDisplay = computed(() => {
  if (userProfile.value.avatar_url) {
    return userProfile.value.avatar_url
  }
  // 生成默认头像
  const initial = userProfile.value.username?.charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(initial)}%3C/text%3E%3C/svg%3E`
})

// 格式化日期
const formatDate = (dateString: string) => {
  if (!dateString) return '未知'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// 加载用户资料
const loadProfile = async () => {
  loading.value = true
  try {
    // 响应拦截器已解包 response.data
    const response: any = await apiClient.get('/auth/me')
    userProfile.value = response
    editForm.value = {
      bio: response.bio || '',
      user_tag: response.user_tag || ''
    }

    // 加载统计信息（如果有相关API）
    // await loadStats()
  } catch (error: any) {
    console.error('加载用户资料失败:', error)
    showMessage('加载用户资料失败', 'error')
  } finally {
    loading.value = false
  }
}

// 开始编辑
const startEdit = () => {
  isEditing.value = true
  editForm.value = {
    bio: userProfile.value.bio || '',
    user_tag: userProfile.value.user_tag || ''
  }
}

// 取消编辑
const cancelEdit = () => {
  isEditing.value = false
  editForm.value = {
    bio: userProfile.value.bio || '',
    user_tag: userProfile.value.user_tag || ''
  }
}

// 保存资料
const saveProfile = async () => {
  if (saving.value) return

  saving.value = true
  try {
    const response: any = await apiClient.put('/users/me/profile', {
      bio: editForm.value.bio,
      user_tag: editForm.value.user_tag
    })

    // 更新本地用户信息
    userProfile.value = {
      ...userProfile.value,
      ...response
    }

    isEditing.value = false
    showMessage('资料更新成功', 'success')
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || '更新失败，请稍后重试'
    showMessage(errorMsg, 'error')
  } finally {
    saving.value = false
  }
}

// 显示消息
const showMessage = (msg: string, type: 'success' | 'error') => {
  message.value = msg
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 3000)
}

// ===== 安全设置（修改自己的密码） =====
const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})
const changingPassword = ref(false)
const showPasswordForm = ref(false)

const changePassword = async () => {
  const { old_password, new_password, confirm_password } = passwordForm.value

  if (!old_password || !new_password || !confirm_password) {
    showMessage('请填写完整', 'error')
    return
  }
  if (new_password.length < 8) {
    showMessage('新密码至少需要 8 位', 'error')
    return
  }
  if (new_password === old_password) {
    showMessage('新密码不能与旧密码相同', 'error')
    return
  }
  if (new_password !== confirm_password) {
    showMessage('两次输入的新密码不一致', 'error')
    return
  }

  changingPassword.value = true
  try {
    await apiClient.put('/users/me/password', { old_password, new_password })
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
    showPasswordForm.value = false
    showMessage('密码修改成功', 'success')
  } catch (error: any) {
    showMessage(error.response?.data?.detail || '修改失败，请稍后重试', 'error')
  } finally {
    changingPassword.value = false
  }
}

// 退出登录
const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

// 组件挂载时加载资料
onMounted(() => {
  loadProfile()
})
</script>

<template>
  <div class="profile-page">
    <div class="profile-container">
      <!-- 头部 -->
      <div class="profile-header">
        <div class="avatar-section">
          <div class="avatar-wrapper avatar-clickable" title="点击更换头像" @click="pickAvatar">
            <img
              :src="avatarDisplay"
              :alt="userProfile.username"
              class="avatar"
              onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 40 40%22%3E%3Crect width=%2240%22 height=%2240%22 fill=%22%23e74c3c%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22white%22 font-size=%2216%22 font-family=%22Arial%22%3EU%3C/text%3E%3C/svg%3E'"
            />
            <div v-if="avatarUploading" class="avatar-overlay">上传中…</div>
            <div v-else class="avatar-overlay avatar-overlay-hover">📷 更换</div>
            <div v-if="userProfile.is_admin" class="admin-badge">管理员</div>
          </div>
          <input
            ref="avatarInputRef"
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            style="display: none"
            @change="onAvatarChange"
          >
        </div>

        <div class="user-info">
          <h1 class="username" :style="{ color: userProfile.username_color || '#1a202c' }">
            {{ userProfile.username }}
          </h1>
          <div class="user-meta">
            <span class="uid">UID: {{ userProfile.user_number }}</span>
            <span v-if="userProfile.user_tag" class="user-tag">{{ userProfile.user_tag }}</span>
          </div>
          <p v-if="userProfile.bio" class="bio">{{ userProfile.bio }}</p>
          <p v-else class="bio empty">这个人很懒，还没有填写个人简介</p>
        </div>

        <div class="actions">
          <button v-if="!isEditing" @click="startEdit" class="btn-edit">
            编辑资料
          </button>
          <div v-else class="edit-actions">
            <button @click="saveProfile" :disabled="saving" class="btn-save">
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button @click="cancelEdit" :disabled="saving" class="btn-cancel">
              取消
            </button>
          </div>
          <button @click="handleLogout" class="btn-logout">
            退出登录
          </button>
        </div>
      </div>

      <!-- 消息提示 -->
      <div v-if="message" :class="['message', messageType]">
        {{ message }}
      </div>

      <!-- 编辑表单 -->
      <div v-if="isEditing" class="edit-form">
        <div class="form-group">
          <label>个人简介</label>
          <textarea
            v-model="editForm.bio"
            rows="3"
            class="form-textarea"
            placeholder="介绍一下自己..."
            maxlength="200"
          />
          <span class="char-count">{{ editForm.bio.length }}/200</span>
        </div>

        <div class="form-group">
          <label>用户标签</label>
          <input
            v-model="editForm.user_tag"
            type="text"
            class="form-input"
            placeholder="比如：算法爱好者、Python开发者..."
            maxlength="50"
          />
        </div>

        <div class="form-group">
          <label>头像</label>
          <p class="avatar-hint">直接点击左上角头像即可上传新头像（支持 jpg/png/gif/webp，5MB 以内）</p>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="stats-section">
        <h2 class="section-title">解题统计</h2>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">{{ stats.solved_count }}</div>
            <div class="stat-label">已解决</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ stats.submission_count }}</div>
            <div class="stat-label">提交次数</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ stats.accept_rate }}%</div>
            <div class="stat-label">通过率</div>
          </div>
        </div>
      </div>

      <!-- 账户信息 -->
      <div class="account-section">
        <h2 class="section-title">账户信息</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">邮箱</span>
            <span class="info-value">{{ userProfile.email }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">手机号</span>
            <span class="info-value">{{ userProfile.phone || '未绑定' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">注册时间</span>
            <span class="info-value">{{ formatDate(userProfile.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">账户状态</span>
            <span class="info-value" :class="userProfile.is_active ? 'status-active' : 'status-inactive'">
              {{ userProfile.is_active ? '已激活' : '未激活' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">发言权限</span>
            <span class="info-value" :class="userProfile.can_speak ? 'status-active' : 'status-inactive'">
              {{ userProfile.can_speak ? '已启用' : '已禁用' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 安全设置 -->
      <div class="account-section security-section">
        <h2 class="section-title">安全设置</h2>
        <p class="security-hint">为了账号安全，请定期更换密码。密码需至少 8 位。</p>

        <button v-if="!showPasswordForm" class="btn-change-password" @click="showPasswordForm = true">
          修改密码
        </button>

        <form v-else class="password-form" @submit.prevent="changePassword">
          <div class="form-group">
            <label>当前密码</label>
            <input
              v-model="passwordForm.old_password"
              type="password"
              class="form-input"
              placeholder="请输入当前密码"
              autocomplete="current-password"
              required
            />
          </div>
          <div class="form-group">
            <label>新密码</label>
            <input
              v-model="passwordForm.new_password"
              type="password"
              class="form-input"
              placeholder="至少 8 位"
              maxlength="72"
              autocomplete="new-password"
              required
            />
          </div>
          <div class="form-group">
            <label>确认新密码</label>
            <input
              v-model="passwordForm.confirm_password"
              type="password"
              class="form-input"
              placeholder="再次输入新密码"
              maxlength="72"
              autocomplete="new-password"
              required
            />
          </div>
          <div class="password-actions">
            <button type="submit" :disabled="changingPassword" class="btn-save">
              {{ changingPassword ? '提交中...' : '确认修改' }}
            </button>
            <button type="button" :disabled="changingPassword" class="btn-cancel" @click="showPasswordForm = false">
              取消
            </button>
          </div>
        </form>
      </div>

      <!-- 权限信息 -->
      <div v-if="userProfile.is_admin" class="permissions-section">
        <h2 class="section-title">管理权限</h2>
        <div class="permissions-grid">
          <div class="permission-item">
            <span class="permission-label">用户管理</span>
            <span class="permission-value">{{ userProfile.can_manage_users ? '✓' : '✗' }}</span>
          </div>
          <div class="permission-item">
            <span class="permission-label">帖子管理</span>
            <span class="permission-value">{{ userProfile.can_manage_posts ? '✓' : '✗' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 页面容器 */
.profile-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
}

.profile-container {
  max-width: 900px;
  margin: 0 auto;
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

/* 头部 */
.profile-header {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  padding: 32px;
  color: white;
  display: flex;
  gap: 24px;
  align-items: center;
}

.avatar-section {
  flex-shrink: 0;
}

.avatar-wrapper {
  position: relative;
  display: inline-block;
}

.avatar-clickable {
  cursor: pointer;
}

.avatar-overlay {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 2px 0;
  text-align: center;
  font-size: 11px;
  color: #fff;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 0 0 80px 80px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s;
}

.avatar-clickable:hover .avatar-overlay-hover,
.avatar-overlay:not(.avatar-overlay-hover) {
  opacity: 1;
}

.avatar-hint {
  color: #9ca3af;
  font-size: 13px;
}

.avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: 4px solid white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  object-fit: cover;
}

.admin-badge {
  position: absolute;
  bottom: -4px;
  right: -8px;
  background: #f59e0b;
  color: white;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 12px;
  border: 2px solid white;
  font-weight: 600;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.username {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px 0;
  color: white;
}

.user-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.uid {
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
}

.user-tag {
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
}

.bio {
  font-size: 14px;
  line-height: 1.5;
  opacity: 0.9;
  margin: 0;
  max-width: 500px;
}

.bio.empty {
  opacity: 0.6;
  font-style: italic;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.btn-edit {
  padding: 8px 16px;
  background: white;
  color: #e74c3c;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-edit:hover {
  background: #f9fafb;
  transform: translateY(-1px);
}

.edit-actions {
  display: flex;
  gap: 8px;
  flex-direction: column;
}

.btn-save {
  padding: 8px 16px;
  background: white;
  color: #e74c3c;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-save:hover:not(:disabled) {
  background: #f9fafb;
  transform: translateY(-1px);
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.3);
}

.btn-logout {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-logout:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 消息提示 */
.message {
  margin: 20px 32px;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  text-align: center;
  animation: slideDown 0.3s ease-out;
}

.message.success {
  background: #d1fae5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.message.error {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 编辑表单 */
.edit-form {
  padding: 32px;
  border-bottom: 1px solid #f3f4f6;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  transition: all 0.2s;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #e74c3c;
  box-shadow: 0 0 0 3px rgba(231, 76, 60, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.char-count {
  display: block;
  text-align: right;
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

/* 统计信息 */
.stats-section {
  padding: 32px;
  border-bottom: 1px solid #f3f4f6;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 20px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.stat-card {
  background: #f9fafb;
  padding: 20px;
  border-radius: 12px;
  text-align: center;
  transition: all 0.2s;
}

.stat-card:hover {
  background: #f3f4f6;
  transform: translateY(-2px);
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #e74c3c;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

/* 账户信息 */
.account-section {
  padding: 32px;
  border-bottom: 1px solid #f3f4f6;
}

/* 安全设置 */
.security-hint {
  color: #9ca3af;
  font-size: 13px;
  margin: -8px 0 16px;
}

.btn-change-password {
  padding: 8px 20px;
  background: white;
  color: #e74c3c;
  border: 1px solid #e74c3c;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-change-password:hover {
  background: #fef2f2;
}

.password-form {
  max-width: 420px;
}

.password-actions {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}

.password-actions .btn-cancel {
  background: #f3f4f6;
  color: #374151;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 8px;
}

.info-label {
  font-size: 13px;
  color: #6b7280;
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  color: #1a202c;
  font-weight: 500;
}

.status-active {
  color: #10b981;
  font-weight: 600;
}

.status-inactive {
  color: #ef4444;
  font-weight: 600;
}

/* 权限信息 */
.permissions-section {
  padding: 32px;
}

.permissions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.permission-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fef3c7;
  border-radius: 8px;
  border: 1px solid #fde68a;
}

.permission-label {
  font-size: 14px;
  color: #92400e;
  font-weight: 500;
}

.permission-value {
  font-size: 18px;
  color: #92400e;
  font-weight: 700;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .profile-page {
    padding: 16px;
  }

  .profile-header {
    flex-direction: column;
    text-align: center;
    padding: 24px;
  }

  .actions {
    flex-direction: row;
    width: 100%;
  }

  .edit-actions {
    flex-direction: row;
    width: 100%;
  }

  .username {
    font-size: 20px;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .info-item {
    flex-direction: column;
    gap: 4px;
    text-align: center;
  }
}
</style>
