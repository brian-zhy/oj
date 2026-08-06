<template>
  <div class="p-8 bg-white">
    <h1 class="text-2xl font-bold mb-4">简单题目详情页面</h1>
    <p>题目ID: {{ $route.params.id }}</p>
    <p>如果你能看到这个页面，说明路由是正常的。</p>
    <button class="mt-4 px-4 py-2 bg-blue-600 text-white rounded">
      测试按钮
    </button>
  </div>
</template>

<script setup lang="ts">
console.log('简单题目详情页面加载了')
</script>
