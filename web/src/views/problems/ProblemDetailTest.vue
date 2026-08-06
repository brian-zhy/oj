<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

console.log('题目详情测试页面')
console.log('题目ID:', route.params.id)
console.log('认证状态:', authStore.isAuthenticated)
console.log('用户信息:', authStore.currentUser)
console.log('Access Token:', authStore.accessToken)
</script>

<template>
  <div class="p-8 bg-white">
    <h1 class="text-2xl font-bold mb-4">题目详情测试页面</h1>

    <div class="space-y-4">
      <div class="p-4 bg-blue-50 rounded">
        <h2 class="font-bold">题目ID: {{ route.params.id }}</h2>
      </div>

      <div class="p-4 bg-green-50 rounded">
        <h2 class="font-bold">认证状态: {{ authStore.isAuthenticated ? '已登录' : '未登录' }}</h2>
      </div>

      <div v-if="authStore.currentUser" class="p-4 bg-yellow-50 rounded">
        <h2 class="font-bold">当前用户: {{ authStore.currentUser.username }}</h2>
        <p>邮箱: {{ authStore.currentUser.email }}</p>
      </div>

      <div class="p-4 bg-gray-50 rounded">
        <h2 class="font-bold">调试信息</h2>
        <p>Access Token: {{ authStore.accessToken ? '存在' : '不存在' }}</p>
        <p>Refresh Token: {{ authStore.refreshToken ? '存在' : '不存在' }}</p>
      </div>
    </div>
  </div>
</template>
