<script setup lang="ts">
import { computed } from 'vue'
import { renderRichText } from '@/utils/markdown'

const props = defineProps<{
  modelValue: string
  placeholder?: string
  height?: string
}>()

const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const previewHtml = computed(() => renderRichText(props.modelValue || ''))

const onInput = (e: Event) => {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
}
</script>

<template>
  <div class="md-split" :style="{ height: height || '320px' }">
    <div class="md-pane">
      <div class="pane-head">编写（Markdown）</div>
      <textarea
        class="md-input"
        :value="modelValue"
        :placeholder="placeholder"
        @input="onInput"
      />
    </div>
    <div class="md-pane">
      <div class="pane-head">实时预览</div>
      <div class="md-preview prose" v-html="previewHtml" />
    </div>
  </div>
</template>

<style scoped>
.md-split {
  display: flex;
  gap: 10px;
  width: 100%;
  box-sizing: border-box;
}

.md-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid #dce0e6;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.pane-head {
  flex-shrink: 0;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #8e9aaf;
  background: #fafbfc;
  border-bottom: 1px solid #eef1f5;
}

.md-input {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.6;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  color: #2d3748;
}

.md-preview {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.7;
  color: #2d3748;
  word-break: break-word;
}

@media (max-width: 760px) {
  .md-split { flex-direction: column; height: auto !important; }
  .md-pane { min-height: 180px; }
}
</style>
