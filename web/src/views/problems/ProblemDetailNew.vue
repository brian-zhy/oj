<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const problemId = ref(parseInt(route.params.id as string))
const loading = ref(true)
const error = ref('')
const problem = ref<any>(null)

const loadProblem = () => {
  console.log('加载题目，ID:', problemId.value)

  // 模拟数据
  setTimeout(() => {
    problem.value = {
      id: problemId.value,
      title: '两数之和',
      description: '给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值 target 的那两个整数。',
      difficulty: 'easy',
      time_limit: 1000,
      memory_limit: 256
    }
    loading.value = false
    console.log('题目加载完成:', problem.value)
  }, 500)
}

const submitCode = () => {
  console.log('提交代码')
  router.push(`/submit?problem_id=${problemId.value}`)
}

onMounted(() => {
  console.log('页面挂载，题目ID:', problemId.value)
  loadProblem()
})
</script>

<template>
  <div class="p-8 bg-gray-50">
    <!-- 调试面板 -->
    <div class="mb-6 p-4 bg-yellow-100 border-2 border-yellow-300 rounded">
      <h3 class="font-bold text-lg mb-2">🔍 调试面板</h3>
      <div class="space-y-1 text-sm">
        <p>📍 路由参数ID: <strong>{{ $route.params.id }}</strong></p>
        <p>🔢 计算属性ID: <strong>{{ problemId }}</strong></p>
        <p>⏳ 加载状态: <strong>{{ loading }}</strong></p>
        <p>📦 题目数据: <strong>{{ problem ? '✅ 已加载' : '❌ 未加载' }}</strong></p>
        <p>🐛 错误信息: <strong>{{ error || '无' }}</strong></p>
        <p v-if="problem">📝 题目标题: <strong>{{ problem.title }}</strong></p>
      </div>
    </div>

    <h1 class="text-2xl font-bold mb-4">题目详情页面</h1>

    <div v-if="loading" class="text-center py-12">
      <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      <p class="mt-4 text-gray-600">加载中...</p>
    </div>

    <div v-else-if="error" class="text-center py-12">
      <div class="p-4 bg-red-100 border border-red-300 rounded">
        <h3 class="font-bold text-red-700">加载失败</h3>
        <p class="text-red-600">{{ error }}</p>
      </div>
    </div>

    <div v-else>
      <div v-if="problem" class="space-y-6">
        <!-- 题目信息 -->
        <div class="bg-white p-6 rounded-lg shadow">
          <h2 class="text-xl font-bold mb-2">
            {{ problem.id }}. {{ problem.title }}
          </h2>
          <div class="mt-2 text-sm text-gray-600">
            <span class="px-2 py-1 bg-green-100 rounded">难度: {{ problem.difficulty }}</span>
            <span class="ml-4">⏱️ 时间限制: {{ problem.time_limit }}ms</span>
            <span class="ml-4">💾 内存限制: {{ problem.memory_limit }}MB</span>
          </div>
          <button
            @click="submitCode"
            class="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          >
            提交代码
          </button>
        </div>

        <!-- 题目描述 -->
        <div class="bg-white p-6 rounded-lg shadow">
          <h3 class="text-lg font-bold mb-2">📄 题目描述</h3>
          <p class="text-gray-700">{{ problem.description }}</p>
        </div>
      </div>

      <div v-else class="text-center py-12">
        <div class="p-4 bg-orange-100 border border-orange-300 rounded">
          <h3 class="font-bold text-orange-700">题目数据为空</h3>
          <p class="text-orange-600 mt-2">请检查控制台日志获取更多信息</p>
        </div>
      </div>
    </div>
  </div>
</template>
