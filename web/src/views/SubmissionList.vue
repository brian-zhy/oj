<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { problemsApi } from '@/api/problems'
import type { Submission } from '@/types'

const router = useRouter()
const submissions = ref<Submission[]>([])
const loading = ref(true)
const error = ref('')

const loadSubmissions = async () => {
  try {
    loading.value = true
    // 临时模拟数据，后续替换为真实 API
    submissions.value = [
      {
        id: 1,
        problem_id: 1,
        user_id: 1,
        code: 'print("Hello")',
        language: 'python',
        status: 'accepted',
        submit_time: '2024-01-15T10:30:00Z',
        judge_time: '2024-01-15T10:30:02Z',
        runtime: 45,
        memory_usage: 15.2
      },
      {
        id: 2,
        problem_id: 2,
        user_id: 1,
        code: 'def solution():\n    return "wrong"',
        language: 'python',
        status: 'wrong_answer',
        submit_time: '2024-01-15T11:15:00Z',
        judge_time: '2024-01-15T11:15:01Z',
        runtime: 30,
        memory_usage: 12.8
      },
      {
        id: 3,
        problem_id: 3,
        user_id: 1,
        code: 'int main() { return 0; }',
        language: 'cpp',
        status: 'compile_error',
        submit_time: '2024-01-15T12:00:00Z',
        judge_time: '2024-01-15T12:00:01Z'
      }
    ]
  } catch (err: any) {
    error.value = '加载提交记录失败'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'accepted':
      return 'bg-green-100 text-green-800'
    case 'wrong_answer':
      return 'bg-red-100 text-red-800'
    case 'time_limit_exceeded':
      return 'bg-yellow-100 text-yellow-800'
    case 'memory_limit_exceeded':
      return 'bg-orange-100 text-orange-800'
    case 'runtime_error':
      return 'bg-purple-100 text-purple-800'
    case 'compile_error':
      return 'bg-gray-100 text-gray-800'
    default:
      return 'bg-blue-100 text-blue-800'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'accepted':
      return '通过'
    case 'wrong_answer':
      return '答案错误'
    case 'time_limit_exceeded':
      return '超时'
    case 'memory_limit_exceeded':
      return '内存超限'
    case 'runtime_error':
      return '运行错误'
    case 'compile_error':
      return '编译错误'
    case 'pending':
      return '等待中'
    case 'judging':
      return '评测中'
    default:
      return '未知'
  }
}

const formatTime = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const goToSubmissionDetail = (id: number) => {
  // 跳转到提交详情页面
  console.log('查看提交详情:', id)
}

onMounted(() => {
  loadSubmissions()
})
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold text-gray-900 mb-8">提交记录</h1>

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
              提交ID
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              题目ID
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              语言
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              状态
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              运行时间
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              内存使用
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              提交时间
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              操作
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="submission in submissions"
            :key="submission.id"
            class="hover:bg-gray-50"
          >
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              #{{ submission.id }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ submission.problem_id }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ submission.language }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span
                class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                :class="getStatusColor(submission.status)"
              >
                {{ getStatusText(submission.status) }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ submission.runtime ? `${submission.runtime}ms` : '-' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
              {{ submission.memory_usage ? `${submission.memory_usage}MB` : '-' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ formatTime(submission.submit_time) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-blue-600">
              <button
                @click="goToSubmissionDetail(submission.id)"
                class="hover:underline"
              >
                查看详情
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="submissions.length === 0" class="text-center py-12">
        <p class="text-gray-600">暂无提交记录</p>
      </div>
    </div>
  </div>
</template>
