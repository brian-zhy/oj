<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { problemsApi } from '@/api/problems'
import { marked } from 'marked'
import type { Problem } from '@/types'

const route = useRoute()
const router = useRouter()

const problem = ref<Problem | null>(null)
const loading = ref(true)
const error = ref('')

const problemId = computed(() => parseInt(route.params.id as string))

const loadProblem = async () => {
  try {
    loading.value = true
    console.log('开始加载题目，ID:', problemId.value)

    // 临时模拟数据，后续替换为真实 API
    problem.value = {
      id: problemId.value,
      title: '两数之和',
      description: `
## 题目描述

给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值 target 的那两个整数，并返回它们的数组下标。

你可以假设每种输入只会对应一个答案。但是，数组中同一个元素在答案里不能重复出现。

你可以按任意顺序返回答案。

## 示例

**示例 1：**
\`\`\`
输入：nums = [2,7,11,15], target = 9
输出：[0,1]
解释：因为 nums[0] + nums[1] == 9 ，返回 [0, 1] 。
\`\`\`

**示例 2：**
\`\`\`
输入：nums = [3,2,4], target = 6
输出：[1,2]
\`\`\`

**示例 3：**
\`\`\`
输入：nums = [3,3], target = 6
输出：[0,1]
\`\`\`

## 提示

- 2 <= nums.length <= 10^4
- -10^9 <= nums[i] <= 10^9
- -10^9 <= target <= 10^9
- 只会存在一个有效答案
      `,
      difficulty: 'easy',
      time_limit: 1000,
      memory_limit: 256,
      examples: [
        {
          input: 'nums = [2,7,11,15], target = 9',
          output: '[0,1]',
          explanation: '因为 nums[0] + nums[1] == 9'
        }
      ],
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    }

    console.log('题目数据加载完成:', problem.value)
  } catch (err: any) {
    error.value = '加载题目详情失败'
    console.error('加载题目失败:', err)
  } finally {
    loading.value = false
    console.log('加载状态完成，loading:', loading.value, 'problem:', problem.value)
  }
}

const submitCode = () => {
  router.push(`/submit?problem_id=${problemId.value}`)
}

// 配置marked选项
marked.setOptions({
  breaks: true, // 启用换行符转换
  gfm: true,   // 启用GitHub风格markdown
})

// 解析markdown内容
const renderedDescription = computed(() => {
  if (!problem.value) return ''
  try {
    return marked(problem.value.description)
  } catch (error) {
    console.error('Markdown解析错误:', error)
    return problem.value.description
  }
})

onMounted(() => {
  console.log('题目详情页面挂载')
  console.log('路由参数:', route.params)
  console.log('题目ID:', problemId.value)
  console.log('开始加载题目数据...')
  loadProblem()
})
</script>

<template>
  <div>
    <!-- 调试信息 -->
    <div class="mb-4 p-4 bg-yellow-50 rounded border border-yellow-200">
      <h3 class="font-bold">调试信息</h3>
      <p>题目ID: {{ problemId }}</p>
      <p>加载状态: {{ loading }}</p>
      <p>错误信息: {{ error }}</p>
      <p>题目数据: {{ problem ? '已加载' : '未加载' }}</p>
    </div>

    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      <p class="mt-4 text-gray-600">加载中...</p>
    </div>

    <div v-else-if="error" class="text-center py-12">
      <p class="text-red-600">{{ error }}</p>
    </div>

    <div v-else-if="problem" class="space-y-6">
      <!-- 题目头部 -->
      <div class="bg-white shadow-md rounded-lg p-6">
        <div class="flex justify-between items-start">
          <div>
            <h1 class="text-2xl font-bold text-gray-900 mb-2">
              {{ problem.id }}. {{ problem.title }}
            </h1>
            <div class="flex items-center space-x-4 text-sm text-gray-600">
              <span>时间限制: {{ problem.time_limit }}ms</span>
              <span>内存限制: {{ problem.memory_limit }}MB</span>
            </div>
          </div>
          <button
            @click="submitCode"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            提交代码
          </button>
        </div>
      </div>

      <!-- 题目描述 -->
      <div class="bg-white shadow-md rounded-lg p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">题目描述</h2>
        <div class="prose prose-sm max-w-none text-gray-700" v-html="renderedDescription"></div>
      </div>

      <!-- 示例 -->
      <div v-if="problem.examples && problem.examples.length > 0" class="bg-white shadow-md rounded-lg p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">示例</h2>
        <div class="space-y-4">
          <div
            v-for="(example, index) in problem.examples"
            :key="index"
            class="border rounded-lg p-4 bg-gray-50"
          >
            <div class="mb-2">
              <span class="font-medium text-gray-700">输入:</span>
              <pre class="mt-1 text-sm text-gray-900">{{ example.input }}</pre>
            </div>
            <div class="mb-2">
              <span class="font-medium text-gray-700">输出:</span>
              <pre class="mt-1 text-sm text-gray-900">{{ example.output }}</pre>
            </div>
            <div v-if="example.explanation">
              <span class="font-medium text-gray-700">说明:</span>
              <p class="mt-1 text-sm text-gray-600">{{ example.explanation }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
