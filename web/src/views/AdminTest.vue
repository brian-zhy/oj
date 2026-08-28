<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const authStore = useAuthStore()

// 检查权限
const canAccessAdmin = computed(() => {
  const user = authStore.currentUser
  console.log('AdminTest - 权限检查:', {
    user: user,
    is_super_admin: user?.is_super_admin,
    is_admin: user?.is_admin,
    can_manage_users: user?.can_manage_users
  })
  return user && (user.is_super_admin || user.is_admin || user.can_manage_users)
})

// 显示权限信息
const permissionInfo = computed(() => {
  const user = authStore.currentUser
  if (!user) return null

  return {
    username: user.username,
    user_number: user.user_number,
    is_admin: user.is_admin,
    is_super_admin: user.is_super_admin,
    can_manage_users: user.can_manage_users,
    can_manage_posts: user.can_manage_posts,
    can_access_admin: canAccessAdmin.value
  }
})

// 测试API调用
const testAdminApi = async () => {
  try {
    console.log('测试管理后台API调用...')
    const response = await apiClient.get('/admin/users')
    console.log('API调用成功:', response)
    return response
  } catch (error) {
    console.error('API调用失败:', error)
    throw error
  }
}
</script>

<template>
  <div class="admin-test">
    <h1>管理后台权限测试页面</h1>

    <div v-if="!permissionInfo" class="error">
      <h2>❌ 未登录</h2>
      <p>请先登录后访问此页面</p>
    </div>

    <div v-else class="info">
      <h2>✅ 已登录</h2>
      <h3>用户信息</h3>
      <pre>{{ permissionInfo }}</pre>

      <h3>权限检查结果</h3>
      <p v-if="canAccessAdmin" class="success">✅ 有管理后台访问权限</p>
      <p v-else class="error">❌ 无管理后台访问权限</p>

      <div class="test-section">
        <h3>API测试</h3>
        <button @click="testAdminApi" class="test-btn">测试管理后台API</button>
      </div>

      <div class="debug">
        <h3>调试信息</h3>
        <p>AccessToken: {{ authStore.accessToken ? '存在' : '不存在' }}</p>
        <p>CurrentUser: {{ authStore.currentUser ? '存在' : '不存在' }}</p>
        <p>IsAuthenticated: {{ authStore.isAuthenticated }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-test {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  font-family: Arial, sans-serif;
}

h1 {
  color: #333;
  border-bottom: 2px solid #e74c3c;
  padding-bottom: 10px;
}

h2 {
  color: #2ecc71;
}

h3 {
  color: #34495e;
  margin-top: 20px;
}

.info, .error {
  background: white;
  padding: 15px;
  border-radius: 8px;
  margin: 10px 0;
}

.error {
  background: #fee;
  border: 1px solid #f88;
}

.success {
  color: #27ae60;
  font-weight: bold;
}

pre {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
}

.test-section {
  margin: 20px 0;
}

.test-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.test-btn:hover {
  background: #2980b9;
}

.debug {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  margin: 20px 0;
}

.debug p {
  margin: 5px 0;
  font-family: monospace;
}
</style>
