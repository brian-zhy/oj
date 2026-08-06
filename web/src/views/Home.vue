<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 数据状态
const loading = ref(true)
const announcements = ref([])
const recentProblems = ref([])
const recentDiscussions = ref([])
const recentArticles = ref([])
const topUsers = ref([])

// 跳转到题目
const goToProblem = (problemId: number) => {
  router.push(`/problems/${problemId}`)
}

// 跳转到讨论
const goToDiscussion = (discussionId: number) => {
  router.push(`/discuss/${discussionId}`)
}

// 跳转到文章
const goToArticle = (articleId: number) => {
  router.push(`/articles/${articleId}`)
}

// 获取难度颜色
const getDifficultyColor = (difficulty: string) => {
  switch (difficulty) {
    case '简单': return 'text-green-600 bg-green-50'
    case '中等': return 'text-yellow-600 bg-yellow-50'
    case '困难': return 'text-red-600 bg-red-50'
    default: return 'text-gray-600 bg-gray-50'
  }
}

// 获取排名颜色
const getRankColor = (rank: number) => {
  switch (rank) {
    case 1: return 'text-yellow-600'
    case 2: return 'text-gray-600'
    case 3: return 'text-orange-600'
    default: return 'text-gray-500'
  }
}

// 加载首页数据
const loadHomeData = async () => {
  loading.value = true
  try {
    // TODO: 从后端API获取真实数据
    // const [announcementsData, problemsData, discussionsData, articlesData, usersData] = await Promise.all([
    //   fetch('http://localhost:8000/api/announcements').then(res => res.json()),
    //   fetch('http://localhost:8000/api/problems/recent').then(res => res.json()),
    //   fetch('http://localhost:8000/api/discussions/recent').then(res => res.json()),
    //   fetch('http://localhost:8000/api/articles/recent').then(res => res.json()),
    //   fetch('http://localhost:8000/api/users/top').then(res => res.json())
    // ])

    // announcements.value = announcementsData
    // recentProblems.value = problemsData
    // recentDiscussions.value = discussionsData
    // recentArticles.value = articlesData
    // topUsers.value = usersData

    // 暂时设置为空数组
    announcements.value = []
    recentProblems.value = []
    recentDiscussions.value = []
    recentArticles.value = []
    topUsers.value = []
  } catch (error) {
    console.error('加载首页数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 组件挂载时获取数据
onMounted(() => {
  loadHomeData()
})
</script>

<template>
  <div class="home-page">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div class="banner-content">
        <h1 class="banner-title">欢迎来到 Online Judge</h1>
        <p class="banner-subtitle">提升你的编程能力，挑战算法难题</p>
        <div class="banner-buttons">
          <button
            v-if="!authStore.isAuthenticated"
            @click="router.push('/register')"
            class="banner-btn primary"
          >
            开始学习
          </button>
          <button
            @click="router.push('/problems')"
            class="banner-btn secondary"
          >
            浏览题目
          </button>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <p class="loading-text">加载中...</p>
    </div>

    <!-- 主要内容区域 -->
    <div v-else class="main-content">
      <!-- 左侧内容 -->
      <div class="left-content">
        <!-- 公告区域 -->
        <div class="section-card" v-if="announcements.length > 0">
          <div class="section-header">
            <h2 class="section-title">📢 系统公告</h2>
          </div>
          <div class="section-body">
            <div
              v-for="announcement in announcements"
              :key="announcement.id"
              class="announcement-item"
            >
              <h3 class="announcement-title">{{ announcement.title }}</h3>
              <p class="announcement-content">{{ announcement.content }}</p>
              <div class="announcement-meta">
                <span class="meta-text">{{ announcement.author }}</span>
                <span class="meta-text">{{ announcement.date }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 最新题目 -->
        <div class="section-card">
          <div class="section-header">
            <h2 class="section-title">📝 最新题目</h2>
            <router-link to="/problems" class="section-link">查看更多 →</router-link>
          </div>
          <div class="section-body">
            <div v-if="recentProblems.length > 0" class="problem-list">
              <div
                v-for="problem in recentProblems"
                :key="problem.id"
                class="problem-item"
                @click="goToProblem(problem.id)"
              >
                <div class="problem-info">
                  <span class="problem-id">{{ problem.id }}</span>
                  <span class="problem-title">{{ problem.title }}</span>
                </div>
                <div class="problem-meta">
                  <span :class="['difficulty-badge', getDifficultyColor(problem.difficulty)]">
                    {{ problem.difficulty }}
                  </span>
                  <span class="acceptance-rate">{{ problem.acceptance }}%</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              <p class="empty-text">暂无题目数据</p>
              <router-link to="/problems" class="empty-link">前往题目列表</router-link>
            </div>
          </div>
        </div>

        <!-- 最新讨论 -->
        <div class="section-card" v-if="authStore.isAuthenticated">
          <div class="section-header">
            <h2 class="section-title">💬 热门讨论</h2>
            <router-link to="/discuss" class="section-link">查看更多 →</router-link>
          </div>
          <div class="section-body">
            <div v-if="recentDiscussions.length > 0" class="discussion-list">
              <div
                v-for="discussion in recentDiscussions"
                :key="discussion.id"
                class="discussion-item"
                @click="goToDiscussion(discussion.id)"
              >
                <div class="discussion-title">{{ discussion.title }}</div>
                <div class="discussion-meta">
                  <span class="meta-text">{{ discussion.author }}</span>
                  <span class="meta-text">💬 {{ discussion.replies }}</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              <p class="empty-text">暂无讨论数据</p>
              <router-link to="/discuss" class="empty-link">发起讨论</router-link>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧边栏 -->
      <div class="right-sidebar">
        <!-- 排行榜 -->
        <div class="sidebar-card">
          <div class="sidebar-header">
            <h3 class="sidebar-title">🏆 用户排行</h3>
          </div>
          <div class="sidebar-body">
            <div v-if="topUsers.length > 0" class="ranking-list">
              <div
                v-for="user in topUsers"
                :key="user.rank"
                class="ranking-item"
              >
                <span :class="['rank-number', getRankColor(user.rank)]">{{ user.rank }}</span>
                <div class="user-info">
                  <span class="username">{{ user.username }}</span>
                  <div class="user-stats">
                    <span class="stat">解决: {{ user.solved }}</span>
                    <span class="stat">评分: {{ user.rating }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              <p class="empty-text">暂无排行数据</p>
            </div>
          </div>
        </div>

        <!-- 最新文章 -->
        <div class="sidebar-card" v-if="authStore.isAuthenticated">
          <div class="sidebar-header">
            <h3 class="sidebar-title">📚 最新文章</h3>
          </div>
          <div class="sidebar-body">
            <div v-if="recentArticles.length > 0" class="article-list">
              <div
                v-for="article in recentArticles"
                :key="article.id"
                class="article-item"
                @click="goToArticle(article.id)"
              >
                <div class="article-title">{{ article.title }}</div>
                <div class="article-meta">
                  <span class="meta-text">{{ article.author }}</span>
                  <span class="meta-text">👁️ {{ article.views }}</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              <p class="empty-text">暂无文章数据</p>
              <router-link to="/articles" class="empty-link">阅读文章</router-link>
            </div>
          </div>
        </div>

        <!-- 快速链接 -->
        <div class="sidebar-card">
          <div class="sidebar-header">
            <h3 class="sidebar-title">🔗 快速链接</h3>
          </div>
          <div class="sidebar-body">
            <div class="quick-links">
              <router-link to="/help" class="quick-link">帮助中心</router-link>
              <router-link to="/rules" class="quick-link">社区规则</router-link>
              <router-link to="/contact" class="quick-link">联系我们</router-link>
              <router-link to="/about" class="quick-link">关于我们</router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 页面容器 */
.home-page {
  min-height: 100vh;
  background: #f5f7fa;
}

/* 欢迎横幅 */
.welcome-banner {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  padding: 60px 20px;
  text-align: center;
}

.banner-content {
  max-width: 800px;
  margin: 0 auto;
}

.banner-title {
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 16px;
  color: white;
}

.banner-subtitle {
  font-size: 20px;
  margin-bottom: 32px;
  opacity: 0.9;
}

.banner-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.banner-btn {
  padding: 14px 32px;
  border-radius: 30px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.banner-btn.primary {
  background: white;
  color: #e74c3c;
  border: 2px solid white;
}

.banner-btn.primary:hover {
  background: #f9fafb;
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

.banner-btn.secondary {
  background: transparent;
  color: white;
  border: 2px solid white;
}

.banner-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-2px);
}

/* 加载状态 */
.loading-container {
  max-width: 1200px;
  margin: 60px auto;
  text-align: center;
  padding: 40px 20px;
}

.loading-spinner {
  border: 4px solid #f3f4f6;
  border-top: 4px solid #e74c3c;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  color: #6b7280;
  font-size: 16px;
}

/* 主要内容区域 */
.main-content {
  max-width: 1200px;
  margin: 32px auto 0;
  padding: 0 20px;
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

/* 左侧内容 */
.left-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 右侧边栏 */
.right-sidebar {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 卡片通用样式 */
.section-card, .sidebar-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.section-header, .sidebar-header {
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title, .sidebar-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.section-link {
  color: #e74c3c;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}

.section-link:hover {
  color: #c0392b;
}

.section-body, .sidebar-body {
  padding: 20px;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 32px 20px;
}

.empty-text {
  color: #9ca3af;
  font-size: 14px;
  margin-bottom: 16px;
}

.empty-link {
  color: #e74c3c;
  text-decoration: none;
  font-size: 14px;
  padding: 8px 16px;
  border: 1px solid #e74c3c;
  border-radius: 6px;
  transition: all 0.2s;
}

.empty-link:hover {
  background: #e74c3c;
  color: white;
}

/* 公告样式 */
.announcement-item {
  padding: 16px;
  border-radius: 8px;
  background: #fef3c7;
  border-left: 4px solid #f59e0b;
}

.announcement-title {
  font-weight: 600;
  color: #92400e;
  margin-bottom: 8px;
}

.announcement-content {
  color: #78350f;
  margin-bottom: 12px;
  line-height: 1.6;
}

.announcement-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
}

.meta-text {
  color: #92400e;
}

/* 题目列表 */
.problem-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.problem-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-radius: 8px;
  background: #f9fafb;
  cursor: pointer;
  transition: all 0.2s;
}

.problem-item:hover {
  background: #f3f4f6;
  transform: translateX(4px);
}

.problem-info {
  display: flex;
  gap: 12px;
  align-items: center;
}

.problem-id {
  font-weight: 600;
  color: #6b7280;
}

.problem-title {
  color: #1f2937;
}

.problem-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.difficulty-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
}

.acceptance-rate {
  color: #6b7280;
  font-size: 14px;
}

/* 讨论列表 */
.discussion-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.discussion-item {
  padding: 16px;
  border-radius: 8px;
  background: #f9fafb;
  cursor: pointer;
  transition: all 0.2s;
}

.discussion-item:hover {
  background: #f3f4f6;
}

.discussion-title {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 8px;
}

.discussion-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
}

/* 排行榜 */
.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ranking-item {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  background: #f9fafb;
}

.rank-number {
  font-weight: 700;
  font-size: 16px;
  min-width: 24px;
  text-align: center;
}

.user-info {
  flex: 1;
}

.username {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 4px;
}

.user-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
}

.stat {
  color: #6b7280;
}

/* 文章列表 */
.article-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.article-item {
  padding: 12px;
  border-radius: 8px;
  background: #f9fafb;
  cursor: pointer;
  transition: all 0.2s;
}

.article-item:hover {
  background: #f3f4f6;
}

.article-title {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 8px;
}

.article-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
}

/* 快速链接 */
.quick-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-link {
  padding: 12px;
  border-radius: 8px;
  background: #f9fafb;
  color: #374151;
  text-decoration: none;
  text-align: center;
  transition: all 0.2s;
}

.quick-link:hover {
  background: #f3f4f6;
  color: #e74c3c;
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .main-content {
    grid-template-columns: 1fr;
  }

  .right-sidebar {
    order: -1;
  }
}

@media (max-width: 600px) {
  .banner-title {
    font-size: 32px;
  }

  .banner-subtitle {
    font-size: 16px;
  }

  .banner-buttons {
    flex-direction: column;
  }

  .banner-btn {
    width: 100%;
  }

  .main-content {
    padding: 0 16px;
    margin-top: 24px;
  }

  .section-body, .sidebar-body {
    padding: 16px;
  }
}
</style>
