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
    path: '/problems',
    name: 'ProblemList',
    component: () => import('@/views/problems/ProblemList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/problems/:id',
    name: 'ProblemDetail',
    component: () => import('@/views/problems/ProblemDetailNew.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/problems/:id/test',
    name: 'ProblemDetailTest',
    component: () => import('@/views/problems/ProblemDetailTest.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/problems/:id/simple',
    name: 'SimpleDetail',
    component: () => import('@/views/problems/SimpleDetail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/submit',
    name: 'Submit',
    component: () => import('@/views/Submit.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/submissions',
    name: 'SubmissionList',
    component: () => import('@/views/SubmissionList.vue'),
    meta: { requiresAuth: true }
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
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 路由守卫
router.beforeEach((to) => {
  const authStore = useAuthStore()

  // 确保认证状态已恢复
  if (!authStore.accessToken && localStorage.getItem('accessToken')) {
    authStore.restoreState()
  }

  const requiresAuth = to.meta.requiresAuth
  console.log('路由守卫:', to.path, '需要认证:', requiresAuth, '已认证:', authStore.isAuthenticated)

  if (requiresAuth && !authStore.isAuthenticated) {
    // 需要认证但未登录，重定向到登录页
    console.log('未登录，重定向到登录页')
    return { name: 'Login', query: { redirect: to.fullPath } }
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    // 已登录用户访问登录页，重定向到首页
    console.log('已登录，重定向到首页')
    return { name: 'Home' }
  } else {
    console.log('路由检查通过，继续导航')
    return true
  }
})

export default router
