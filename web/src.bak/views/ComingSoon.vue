<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const path = computed(() => route.path)
</script>

<template>
  <div class="coming-soon-page">
    <div class="soon-card">
      <div class="soon-icon">🚧</div>
      <h2 class="soon-title">本功能暂未开放</h2>
      <p class="soon-sub">该功能正在开发中，敬请期待</p>
      <p class="soon-path">当前路径：{{ path }}</p>
      <div class="soon-actions">
        <button class="btn-home" @click="router.push('/')">返回主页</button>
        <button class="btn-back" @click="router.back()">返回上一页</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.coming-soon-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1.6;
}

.soon-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  padding: 48px 60px;
  text-align: center;
  max-width: 460px;
  width: 90%;
}

.soon-icon {
  font-size: 52px;
  margin-bottom: 14px;
}

.soon-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 8px;
}

.soon-sub {
  color: #8a9aa8;
  font-size: 14px;
  margin: 0 0 6px;
}

.soon-path {
  color: #c0c8d0;
  font-size: 12px;
  margin: 0 0 22px;
  word-break: break-all;
}

.soon-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-home {
  padding: 9px 26px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 22px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-home:hover {
  background: #c0392b;
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
