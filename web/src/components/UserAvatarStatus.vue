<script setup lang="ts">
import { computed } from 'vue'
import { isUserOnline } from '@/utils/presence'

const props = withDefaults(
  defineProps<{
    user?: { last_seen?: string | Date | null } | null
    size?: number
  }>(),
  {
    size: 10,
  },
)

const isOnline = computed(() => isUserOnline(props.user))
</script>

<template>
  <span class="avatar-status-wrap" :style="{ '--status-size': `${size}px` }">
    <slot />
    <span
      class="avatar-status-dot"
      :class="isOnline ? 'online' : 'offline'"
      :title="isOnline ? '在线' : '离线'"
      aria-label="user online status"
    />
  </span>
</template>

<style scoped>
.avatar-status-wrap {
  position: relative;
  display: inline-block;
  line-height: 0;
}

.avatar-status-dot {
  position: absolute;
  right: 0;
  bottom: 0;
  width: var(--status-size);
  height: var(--status-size);
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.18);
  z-index: 1;
}

.avatar-status-dot.online {
  background: #22c55e;
}

.avatar-status-dot.offline {
  background: #ef4444;
}
</style>
