<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const from = computed(() => (route.query.from as string) || '')
</script>

<template>
  <div class="no-access-page">
    <div class="no-access-card">
      <div class="no-access-icon">⛔</div>
      <h2 class="no-access-title">你无权访问此页面</h2>
      <p class="no-access-sub">
        {{ from ? `该页面的功能需要相应的管理权限` : '该页面需要相应的管理权限' }}
      </p>
      <p v-if="from" class="no-access-path">目标路径：{{ from }}</p>
      <div class="no-access-actions">
        <button class="btn-home" @click="router.push('/')">返回主页</button>
        <button class="btn-back" @click="router.back()">返回上一页</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.no-access-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1.6;
}

.no-access-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  padding: 48px 60px;
  text-align: center;
  max-width: 460px;
  width: 90%;
}

.no-access-icon {
  font-size: 52px;
  margin-bottom: 14px;
}

.no-access-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 8px;
}

.no-access-sub {
  color: #8a9aa8;
  font-size: 14px;
  margin: 0 0 6px;
}

.no-access-path {
  color: #c0c8d0;
  font-size: 12px;
  margin: 0 0 22px;
  word-break: break-all;
}

.no-access-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-home {
  padding: 9px 26px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 22px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-home:hover {
  background: var(--primary-hover);
}

.btn-back {
  padding: 9px 26px;
  background: #f3f4f6;
  color: #4a5568;
  border: none;
  border-radius: 22px;
  font-size: 14px;
  cursor: pointer;
}

.btn-back:hover {
  background: #e5e7eb;
}
</style>
