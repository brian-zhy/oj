<template>
  <div class="admin-test-page">
    <h1>管理后台测试页面</h1>
    <div class="user-info">
      <h2>当前用户信息：</h2>
      <pre>{{ userInfo }}</pre>
    </div>
    <div class="permissions">
      <h2>权限检查：</h2>
      <ul>
        <li>is_super_admin: {{ user?.is_super_admin }}</li>
        <li>is_admin: {{ user?.is_admin }}</li>
        <li>can_manage_users: {{ user?.can_manage_users }}</li>
      </ul>
    </div>
    <div class="routes">
      <h2>可用路由：</h2>
      <ul>
        <li><router-link to="/admin">用户管理</router-link></li>
        <li><router-link to="/admin">新集成管理后台</router-link></li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const user = computed(() => authStore.currentUser)
const userInfo = computed(() => {
  if (!user.value) return '未登录'
  return JSON.stringify(user.value, null, 2)
})
</script>

<style scoped>
.admin-test-page {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.user-info, .permissions, .routes {
  margin-top: 20px;
  padding: 15px;
  background: #f9f9f9;
  border-radius: 8px;
}

pre {
  background: #f0f0f0;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}

ul {
  list-style: none;
  padding: 0;
}

li {
  padding: 5px 0;
}

a {
  color: #e74c3c;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
</style>