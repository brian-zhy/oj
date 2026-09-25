import { defineStore } from 'pinia'
import { ref, computed, watch, onScopeDispose } from 'vue'
import { authApi } from '@/api/auth'
import type { LoginCredentials, RegisterData, User } from '@/types'
import { startPresenceHeartbeat, stopPresenceHeartbeat } from '@/utils/presence'
import * as session from '@/utils/session'

const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000

export const useAuthStore = defineStore('auth', () => {
  // State（内存副本，真实来源始终是 utils/session）
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const currentUser = computed(() => user.value)

  /**
   * 把存储里的登录态同步进内存。
   *
   * 令牌只有 utils/session 一个写入者，store 只读不回写；否则 store 的滞后副本
   * 会把刚轮换出来的新令牌覆盖成旧的，下一次刷新就会 401 并踢掉全部标签页。
   */
  function applySession() {
    accessToken.value = session.getAccessToken() || null
    refreshToken.value = session.getRefreshToken() || null
    user.value = (session.getUser() as User | null) ?? null
    if (accessToken.value && user.value) startPresenceHeartbeat()
  }

  // Actions
  async function login(credentials: LoginCredentials) {
    try {
      const response = await authApi.login(credentials)
      session.setTokens(response.access_token, response.refresh_token)
      applySession()

      const userInfo = await fetchCurrentUser()
      if (userInfo) startPresenceHeartbeat()

      return true
    } catch (error) {
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
      const response = await authApi.loginWithIdentifier(credentials)
      session.setTokens(response.access_token, response.refresh_token)
      applySession()

      const userInfo = await fetchCurrentUser()
      if (userInfo) startPresenceHeartbeat()

      return true
    } catch (error) {
      console.error('AuthStore: 登录失败', error)
      throw error
    }
  }

  async function register(data: RegisterData) {
    try {
      const response = await authApi.register(data)

      session.setTokens(response.tokens.access_token, response.tokens.refresh_token)
      session.setUser(response.user)
      applySession()

      startPresenceHeartbeat()

      return true
    } catch (error) {
      console.error('Registration failed:', error)
      throw error
    }
  }

  async function logout() {
    try {
      session.clearSession()
      accessToken.value = null
      refreshToken.value = null
      user.value = null
      stopPresenceHeartbeat()
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  /**
   * 拉取当前用户。
   *
   * 失败时**不再**清除登录态：access 过期由 axios 拦截器负责刷新并重试，
   * 刷新真失败时拦截器已经清过会话；这里再清一次只会把网络抖动、502
   * 之类的临时故障放大成「被退出登录」。
   */
  async function fetchCurrentUser() {
    if (!accessToken.value) {
      return null
    }

    try {
      const userData = await authApi.getCurrentUser()
      user.value = userData
      if (user.value) startPresenceHeartbeat()
      return userData
    } catch (error) {
      console.error('AuthStore: 获取当前用户失败', error)
      return null
    }
  }

  // 静默同步用户信息：管理员可能已修改本用户权限。
  // 与 fetchCurrentUser 的区别：失败时保留本地登录态（不因网络抖动把人登出）。
  async function syncCurrentUser() {
    if (!accessToken.value) return null
    try {
      user.value = await authApi.getCurrentUser()
      if (user.value) startPresenceHeartbeat()
      return user.value
    } catch {
      // 静默失败：保留现有本地信息
      return null
    }
  }

  /**
   * 初始化：从存储恢复状态。
   *
   * 本地 30 天 TTL 只是「太久没打开就别装登录」的兜底；令牌本身是否有效
   * 由服务端判定（过期时拦截器会自动刷新）。
   */
  function restoreState() {
    if (!session.hasSession()) {
      accessToken.value = null
      refreshToken.value = null
      user.value = null
      return
    }

    const persistedAt = session.getPersistedAt()
    if (persistedAt > 0 && Date.now() - persistedAt > SESSION_TTL_MS) {
      session.clearSession()
      accessToken.value = null
      refreshToken.value = null
      user.value = null
      stopPresenceHeartbeat()
      return
    }

    applySession()
  }

  // 用户资料允许就地修改（如换头像），因此只把「用户」这一项写回存储；
  // 令牌不参与这个 watch，避免覆盖拦截器刚换到的新令牌。
  watch(user, (value) => {
    session.setUser(value as session.StoredUser | null)
  })

  // 跨标签页保持一致：别的标签页刷新了令牌或登出了，本页内存状态跟着更新
  const unsubscribe = session.onSessionChange(applySession)
  onScopeDispose(unsubscribe)

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
    syncCurrentUser,
    restoreState
  }
})
