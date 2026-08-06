<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { problemsApi } from '@/api/problems'
import type { ProblemListItem } from '@/types'

const router = useRouter()
const problems = ref<ProblemListItem[]>([])
const loading = ref(true)
const error = ref('')

const loadProblems = async () => {
  try {
    loading.value = true
    // 临时模拟数据，后续替换为真实 API
    problems.value = [
      {
        id: 1,
        title: '两数之和',
        difficulty: 'easy',
        acceptance_rate: 45.5,
        solved_count: 1250
      },
      {
        id: 2,
        title: '无重复字符的最长子串',
        difficulty: 'medium',
        acceptance_rate: 32.1,
        solved_count: 890
      },
      {
        id: 3,
        title: '正则表达式匹配',
        difficulty: 'hard',
        acceptance_rate: 25.8,
        solved_count: 450
      }
    ]
  } catch (err: any) {
    error.value = '加载题目列表失败'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const getDifficultyColor = (difficulty: string) => {
  switch (difficulty) {
    case 'easy':
      return 'bg-green-100 text-green-800'
    case 'medium':
      return 'bg-yellow-100 text-yellow-800'
    case 'hard':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const getDifficultyText = (difficulty: string) => {
  switch (difficulty) {
    case 'easy':
      return '简单'
    case 'medium':
      return '中等'
    case 'hard':
      return '困难'
    default:
      return '未知'
  }
}

onMounted(() => {
  loadProblems()
})
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold text-gray-900 mb-8">题目列表</h1>

    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      <p class="mt-4 text-gray-600">加载中...</p>
    </div>

    <div v-else-if="error" class="text-center py-12">
      <p class="text-red-600">{{ error }}</p>
    </div>

    <div v-else class="bg-white shadow-md rounded-lg overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              ID
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              标题
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              难度
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              通过率
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              通过人数
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              操作
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="problem in problems"
            :key="problem.id"
            class="hover:bg-gray-50"
          >
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ problem.id }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              <router-link
                :to="`/problems/${problem.id}`"
                class="text-blue-600 hover:text-blue-800 hover:underline"
              >
                {{ problem.title }}
              </router-link>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span
                class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                :class="getDifficultyColor(problem.difficulty)"
              >
                {{ getDifficultyText(problem.difficulty) }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ problem.acceptance_rate?.toFixed(1) }}%
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ problem.solved_count }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
              <router-link
                :to="`/problems/${problem.id}`"
                class="text-blue-600 hover:text-blue-800 hover:underline"
              >
                查看详情
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="problems.length === 0" class="text-center py-12">
        <p class="text-gray-600">暂无题目</p>
      </div>
    </div>
  </div>
</template>
