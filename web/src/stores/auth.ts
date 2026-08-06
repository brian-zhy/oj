import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { LoginCredentials, RegisterData, User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const currentUser = computed(() => user.value)

  // Actions
  async function login(credentials: LoginCredentials) {
    try {
      console.log('AuthStore: 开始登录请求', credentials.username)
      const response = await authApi.login(credentials)
      console.log('AuthStore: 登录响应', response)

      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token

      console.log('AuthStore: 获取当前用户...')
      const user = await fetchCurrentUser()
      console.log('AuthStore: 当前用户信息', user)

      return true
    } catch (error: any) {
      console.error('AuthStore: 登录失败', error)
      // 抛出错误以便上层处理
      throw error
    }
  }

  async function loginWithIdentifier(credentials: {
    identifier: string
    password: string
    captcha_id: string
    captcha: string
  }) {
    try {
      console.log('AuthStore: 开始登录请求', credentials.identifier)
      const response = await authApi.loginWithIdentifier(credentials)
      console.log('AuthStore: 登录响应', response)

      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token

      console.log('AuthStore: 获取当前用户...')
      const user = await fetchCurrentUser()
      console.log('AuthStore: 当前用户信息', user)

      return true
    } catch (error: any) {
      console.error('AuthStore: 登录失败', error)
      throw error
    }
  }

  async function register(data: RegisterData) {
    try {
      console.log('AuthStore: 开始注册请求', data)
      const response = await authApi.register(data)
      console.log('AuthStore: 注册响应', response)

      // 设置令牌
      accessToken.value = response.tokens.access_token
      refreshToken.value = response.tokens.refresh_token

      // 设置用户信息
      user.value = response.user

      // 持久化状态
      persistState()

      return true
    } catch (error: any) {
      console.error('Registration failed:', error)
      throw error
    }
  }

  async function logout() {
    try {
      // 可以选择调用后端登出接口（如果有）
      accessToken.value = null
      refreshToken.value = null
      user.value = null
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  async function fetchCurrentUser() {
    if (!accessToken.value) {
      console.log('AuthStore: 没有访问令牌，跳过获取用户')
      return null
    }

    try {
      console.log('AuthStore: 正在获取当前用户...')
      const userData = await authApi.getCurrentUser()
      console.log('AuthStore: 获取到用户数据', userData)
      user.value = userData
      return userData
    } catch (error) {
      console.error('AuthStore: 获取当前用户失败', error)
      // Token 可能已过期，清除认证状态
      accessToken.value = null
      refreshToken.value = null
      user.value = null
      return null
    }
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) return false

    try {
      const response = await authApi.refreshToken(refreshToken.value)
      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token
      return true
    } catch (error) {
      console.error('Token refresh failed:', error)
      await logout()
      return false
    }
  }

  // 初始化：从 localStorage 恢复状态
  function restoreState() {
    const storedAccessToken = localStorage.getItem('accessToken')
    const storedRefreshToken = localStorage.getItem('refreshToken')
    const storedUser = localStorage.getItem('user')

    if (storedAccessToken) {
      accessToken.value = storedAccessToken
    }
    if (storedRefreshToken) {
      refreshToken.value = storedRefreshToken
    }
    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser)
      } catch (error) {
        console.error('Failed to parse stored user:', error)
      }
    }
  }

  // 持久化状态到 localStorage
  function persistState() {
    if (accessToken.value) {
      localStorage.setItem('accessToken', accessToken.value)
    } else {
      localStorage.removeItem('accessToken')
    }

    if (refreshToken.value) {
      localStorage.setItem('refreshToken', refreshToken.value)
    } else {
      localStorage.removeItem('refreshToken')
    }

    if (user.value) {
      localStorage.setItem('user', JSON.stringify(user.value))
    } else {
      localStorage.removeItem('user')
    }
  }

  // 监听状态变化并持久化
  watch([accessToken, refreshToken, user], () => {
    persistState()
  })

  return {
    // State
    user,
    accessToken,
    refreshToken,
    // Getters
    isAuthenticated,
    currentUser,
    // Actions
    login,
    loginWithIdentifier,
    register,
    logout,
    fetchCurrentUser,
    refreshAccessToken,
    restoreState
  }
})

// 导入 watch 函数
import { watch } from 'vue'
