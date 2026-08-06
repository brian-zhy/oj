<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import apiClient from '@/api/client'

const router = useRouter()
const route = useRoute()

// 用户信息
const userProfile = ref({
  id: 0,
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
  phone: ''
})

// 加载状态
const loading = ref(false)
const error = ref('')

// 统计信息
const stats = ref({
  solved_count: 0,
  submission_count: 0,
  accept_rate: 0
})

// 计算头像显示
const avatarDisplay = computed(() => {
  if (userProfile.value.avatar_url) {
    return userProfile.value.avatar_url
  }
  return '/images/default-avatar.png'
})

// 计算显示名称
const displayName = computed(() => {
  return userProfile.value.username || '用户'
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

// 加载用户信息
const loadUserProfile = async () => {
  const userId = route.params.id
  loading.value = true
  error.value = ''

  try {
    const response = await apiClient.get(`/users/${userId}`)
    userProfile.value = response

    // 加载统计信息（如果后端提供）
    try {
      const statsResponse = await apiClient.get(`/users/${userId}/stats`)
      stats.value = statsResponse
    } catch (statsError) {
      console.log('统计信息不可用')
    }
  } catch (err: any) {
    error.value = '用户不存在或无权访问'
    console.error('加载用户信息失败:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadUserProfile()
})
</script>

<template>
  <div class="user-detail-page">
    <div class="user-detail-container">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error-state">
        <div class="error-icon">⚠️</div>
        <p>{{ error }}</p>
        <button @click="router.push('/')" class="back-btn">返回首页</button>
      </div>

      <!-- 用户信息 -->
      <div v-else class="user-info-card">
        <!-- 头部信息 -->
        <div class="user-header">
          <div class="avatar-section">
            <img
              :src="avatarDisplay"
              :alt="displayName"
              class="user-avatar"
              onerror="this.onerror=null;this.src='/images/default-avatar.png'"
            />
          </div>

          <div class="basic-info">
            <h1 class="user-name">{{ displayName }}</h1>

            <div class="user-meta">
              <span class="user-id">用户ID: {{ userProfile.id }}</span>
              <span class="user-number">用户编号: {{ userProfile.user_number }}</span>
            </div>

            <div class="user-badges">
              <span v-if="userProfile.is_admin" class="badge admin-badge">管理员</span>
              <span v-if="!userProfile.can_speak" class="badge muted-badge">禁言</span>
              <span v-if="userProfile.user_tag" class="badge tag-badge">{{ userProfile.user_tag }}</span>
            </div>
          </div>
        </div>

        <!-- 个人简介 -->
        <div v-if="userProfile.bio" class="user-bio">
          <h3>个人简介</h3>
          <p>{{ userProfile.bio }}</p>
        </div>

        <!-- 统计信息 -->
        <div class="user-stats">
          <h3>解题统计</h3>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-value">{{ stats.solved_count }}</div>
              <div class="stat-label">已解决</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ stats.submission_count }}</div>
              <div class="stat-label">提交数</div>
            </div>
            <div class="stat-item">
              <div class="stat-value">{{ stats.accept_rate }}%</div>
              <div class="stat-label">通过率</div>
            </div>
          </div>
        </div>

        <!-- 账户信息 -->
        <div class="account-info">
          <h3>账户信息</h3>
          <div class="info-row">
            <span class="info-label">注册时间:</span>
            <span class="info-value">{{ formatDate(userProfile.created_at) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">账户状态:</span>
            <span class="info-value">
              <span :class="userProfile.is_active ? 'status-active' : 'status-inactive'">
                {{ userProfile.is_active ? '正常' : '未激活' }}
              </span>
            </span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <button @click="router.push('/problems')" class="action-btn primary-btn">
            🎯 去刷题
          </button>
          <button @click="router.push('/submissions')" class="action-btn secondary-btn">
            📝 查看提交
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-detail-page {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 20px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
}

.user-detail-container {
  max-width: 800px;
  margin: 0 auto;
}

.loading-state,
.error-state {
  background: white;
  border-radius: 16px;
  padding: 60px 20px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 20px;
  border: 4px solid #f3f4f6;
  border-top-color: #e74c3c;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.back-btn {
  margin-top: 20px;
  padding: 12px 24px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
}

.user-info-card {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.user-header {
  display: flex;
  gap: 24px;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #e5e7eb;
}

.avatar-section {
  flex-shrink: 0;
}

.user-avatar {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  object-fit: cover;
  border: 4px solid #e74c3c;
}

.basic-info {
  flex: 1;
}

.user-name {
  font-size: 28px;
  color: #1f2937;
  margin-bottom: 12px;
  font-weight: 600;
}

.user-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  color: #6b7280;
  font-size: 14px;
}

.user-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.admin-badge {
  background: #fef3c7;
  color: #92400e;
}

.muted-badge {
  background: #fee2e2;
  color: #991b1b;
}

.tag-badge {
  background: #dbeafe;
  color: #1e40af;
}

.user-bio,
.user-stats,
.account-info {
  margin-bottom: 32px;
}

.user-bio h3,
.user-stats h3,
.account-info h3 {
  font-size: 18px;
  color: #1f2937;
  margin-bottom: 16px;
  font-weight: 600;
}

.user-bio p {
  color: #4b5563;
  line-height: 1.6;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-item {
  text-align: center;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #e74c3c;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #6b7280;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
}

.info-label {
  color: #6b7280;
  font-size: 14px;
}

.info-value {
  color: #1f2937;
  font-size: 14px;
}

.status-active {
  color: #10b981;
  font-weight: 500;
}

.status-inactive {
  color: #ef4444;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.action-btn {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.primary-btn {
  background: #e74c3c;
  color: white;
}

.primary-btn:hover {
  background: #c0392b;
}

.secondary-btn {
  background: #f3f4f6;
  color: #1f2937;
}

.secondary-btn:hover {
  background: #e5e7eb;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .user-header {
    flex-direction: column;
    text-align: center;
  }

  .user-avatar {
    margin: 0 auto;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>