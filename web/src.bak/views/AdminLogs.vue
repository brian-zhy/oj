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
</style>
