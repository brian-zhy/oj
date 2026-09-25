<script setup lang="ts">
import JudgementLogTable from '@/components/JudgementLogTable.vue'
</script>

<template>
  <div class="admin-logs-page">
    <div class="card">
      <div class="card-header">管理日志</div>
      <JudgementLogTable show-admin />
    </div>
  </div>
</template>

<style scoped>
.admin-logs-page {
  max-width: 1400px;
  margin: 0 auto;
}

.card {
  background: var(--surface);
  backdrop-filter: blur(var(--surface-blur)) saturate(1.5);
  -webkit-backdrop-filter: blur(var(--surface-blur)) saturate(1.5);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: 20px 24px;
  margin-bottom: 24px;
}

.card-header {
  font-size: 1.25rem;
  font-weight: 600;
  border-left: 4px solid var(--primary);
  padding-left: 12px;
  margin-bottom: 20px;
}

/* ===== 手机端：原本无任何媒体查询 ===== */
@media (max-width: 600px) {
  .card {
    padding: 16px 14px;
  }
}
</style>
