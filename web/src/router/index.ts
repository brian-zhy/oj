import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/test',
    name: 'Test',
    component: () => import('@/views/Test.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/auth/ForgotPassword.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('@/views/auth/ResetPassword.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/UserProfile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/user/:id',
    name: 'UserDetail',
    component: () => import('@/views/UserDetail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/judgement',
    name: 'Judgement',
    component: () => import('@/views/Judgement.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/discuss',
    name: 'Discuss',
    component: () => import('@/views/discuss/Discuss.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/discuss/new',
    name: 'DiscussNew',
    component: () => import('@/views/discuss/DiscussNew.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/discuss/:id',
    name: 'DiscussPost',
    component: () => import('@/views/discuss/DiscussPost.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/tickets',
    name: 'Tickets',
    component: () => import('@/views/tickets/Tickets.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tickets/new',
    name: 'TicketCreate',
    component: () => import('@/views/tickets/TicketCreate.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tickets/:id',
    name: 'TicketDetail',
    component: () => import('@/views/tickets/TicketDetail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/Admin.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/logs',
    name: 'AdminLogs',
    component: () => import('@/views/AdminLogs.vue'),
    meta: { requiresAuth: true, requiresUserManage: true }
  },
  {
    path: '/test-admin',
    name: 'TestAdmin',
    component: () => import('@/views/admin/Test.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin-test',
    name: 'AdminTest',
    component: () => import('@/views/AdminTest.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

// ===== 未开放页面：统一指向「本功能暂未开放」 =====
import ComingSoon from '@/views/ComingSoon.vue'

const comingSoonPaths = [
  '/problems',      // 题库
  '/courses',       // 网校
  '/training',      // 训练题单
  '/contests',      // 比赛
  '/submissions',   // 评测记录
  '/articles',      // 文章广场
  '/ranking',       // 排行榜
  '/image',         // 图片上传
  '/clipboard',     // 云剪贴板
  '/themes',        // 主题商店
  '/help',          // 帮助中心
  '/contact',       // 联系我们
  '/rules',         // 社区规则
  '/user/notification', // 消息通知
]

comingSoonPaths.forEach((p) => {
  routes.push({
    path: p,
    name: 'ComingSoon_' + p.replace(/\//g, '_'),
    component: ComingSoon,
    meta: { requiresAuth: false }
  })
})

// 兜底：未知路径同样显示「本功能暂未开放」
routes.push({
  path: '/:pathMatch(.*)*',
  name: 'ComingSoon_CatchAll',
  component: ComingSoon,
  meta: { requiresAuth: false }
})

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫
router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  // 恢复认证状态
  if (!authStore.accessToken && localStorage.getItem('accessToken')) {
    authStore.restoreState()
  }

  const requiresAuth = to.meta.requiresAuth || false
  const requiresAdmin = to.meta.requiresAdmin || false

  console.log('路由守卫:', to.path, '需要认证:', requiresAuth, '需要管理员:', requiresAdmin)
  console.log('accessToken:', !!authStore.accessToken)
  console.log('当前用户:', authStore.currentUser)
  console.log('已登录:', authStore.isAuthenticated)

  // 检查是否需要认证
  if (requiresAuth && !authStore.isAuthenticated) {
    console.log('用户未登录，重定向到登录页')
    return { name: 'Login', query: { redirect: to.fullPath } }
  }

  // 如果已登录但没有用户信息，尝试获取
  if (authStore.isAuthenticated && !authStore.currentUser) {
    console.log('有token但没有用户信息，尝试获取...')
    try {
      await authStore.fetchCurrentUser()
      console.log('获取用户信息成功:', authStore.currentUser)
    } catch (error) {
      console.error('获取用户信息失败:', error)
      // 获取用户信息失败，清除无效token
      authStore.logout()
      return { name: 'Login', query: { redirect: to.fullPath } }
    }
  }

  // 检查是否需要管理员权限
  if (requiresAdmin) {
    const user = authStore.currentUser
    console.log('管理员权限检查:', {
      user: user?.username,
      is_super_admin: user?.is_super_admin,
      is_admin: user?.is_admin,
      can_manage_users: user?.can_manage_users
    })

    if (!user || (!user.is_super_admin && !user.is_admin && !user.can_manage_users)) {
      console.log('用户没有管理员权限，重定向到主页')
      return { name: 'Home' }
    }
  }

  // 检查是否需要用户管理权限（如管理日志页）
  if (to.meta.requiresUserManage) {
    const user = authStore.currentUser
    if (!user || !user.can_manage_users) {
      console.log('用户没有用户管理权限，重定向到主页')
      return { name: 'Home' }
    }
  }

  console.log('路由检查通过，继续导航')
  return true
})

export default router
