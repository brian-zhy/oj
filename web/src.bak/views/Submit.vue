<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { problemsApi } from '@/api/problems'

const route = useRoute()

const problemId = ref<number>(parseInt(route.query.problem_id as string))
const code = ref('')
const language = ref('python')
const loading = ref(false)
const error = ref('')

const languages = [
  { value: 'python', label: 'Python 3' },
  { value: 'java', label: 'Java' },
  { value: 'cpp', label: 'C++' },
  { value: 'c', label: 'C' },
  { value: 'javascript', label: 'JavaScript' }
]

const handleSubmit = async () => {
  if (!code.value.trim()) {
    error.value = '请输入代码'
    return
  }

  loading.value = true
  error.value = ''

  try {
    // 临时模拟提交，后续替换为真实 API
    await new Promise(resolve => setTimeout(resolve, 1000))
    alert('提交成功！')
    code.value = ''
  } catch (err: any) {
    error.value = err.response?.data?.detail || '提交失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">提交代码</h1>

    <div class="bg-white shadow-md rounded-lg p-6">
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          选择编程语言
        </label>
        <select
          v-model="language"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option v-for="lang in languages" :key="lang.value" :value="lang.value">
            {{ lang.label }}
          </option>
        </select>
      </div>

      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          代码
        </label>
        <textarea
          v-model="code"
          rows="20"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
          placeholder="请输入你的代码..."
        ></textarea>
      </div>

      <div v-if="error" class="mb-4 text-red-600 text-sm">
        {{ error }}
      </div>

      <div class="flex justify-end space-x-4">
        <button
          type="button"
          @click="code = ''"
          class="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          清空
        </button>
        <button
          type="submit"
          @click="handleSubmit"
          :disabled="loading"
          class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ loading ? '提交中...' : '提交' }}
        </button>
      </div>
    </div>

    <!-- 代码提示 -->
    <div class="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
      <h3 class="font-medium text-blue-900 mb-2">💡 提示</h3>
      <ul class="text-sm text-blue-800 space-y-1">
        <li>• 请确保代码能够编译通过</li>
        <li>• 注意代码的输入输出格式</li>
        <li>• 提交后会自动进行评测，请耐心等待结果</li>
      </ul>
    </div>
  </div>
</template>
