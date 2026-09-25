import axios from 'axios'
import type { AxiosError, AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { pingUserPresence } from '@/utils/presence'
import * as session from '@/utils/session'

// In development, use empty string to leverage Vite proxy
// In production, use the environment variable or default to relative path
const BASE_URL = import.meta.env.MODE === 'development' ? '' : (import.meta.env.VITE_API_BASE_URL || '')

interface RetriableRequest extends InternalAxiosRequestConfig {
  _retry?: boolean
  /** 发出该请求时使用的 refresh 令牌，用于判断「401 之后令牌是否已被别人换掉」 */
  _refreshTokenUsed?: string
}

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000
})

// 这些端点的 401 是「凭据本身不对」，不能触发刷新，否则登录失败会被误判成会话失效
const NO_REFRESH_PATHS = ['/tokens', '/tokens/refresh', '/auth/login', '/auth/register']

function shouldAttemptRefresh(url: string | undefined): boolean {
  if (!url) return true
  const path = url.split('?')[0]
  return !NO_REFRESH_PATHS.includes(path)
}

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    const token = session.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      const requestUrl = (config.url || '').toLowerCase()
      if (!requestUrl.includes('/users/me/seen')) {
        void pingUserPresence()
      }
    }
    // 记录此刻的 refresh 令牌，供 401 时判断是否已被其它请求/标签页轮换
    ;(config as RetriableRequest)._refreshTokenUsed = session.getRefreshToken()
    // GET 请求统一加时间戳参数：绕开浏览器缓存的 301 跳转劫持
    //（按 URL 匹配，URL 不同即不命中缓存的错误重定向）
    if ((config.method || 'get').toLowerCase() === 'get') {
      config.params = { ...config.params, _t: Date.now() }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 真正执行一次刷新（在跨标签页锁内运行）。
 *
 * 返回新的 access 令牌；会话确实失效时返回 null；
 * 刷新接口因网络或服务端异常失败时抛错——这三种结果必须区分开，
 * 否则一次 502 就会把用户踢下线（这正是原来误登出的第二个根因）。
 */
async function doRefresh(staleRefreshToken: string | null): Promise<string | null> {
  const current = session.getRefreshToken()

  // 已经有别人（本页其它请求或别的标签页）刷新成功：直接采用，绝不重复提交
  if (current && staleRefreshToken && current !== staleRefreshToken) {
    return session.getAccessToken()
  }
  if (!current) return null

  try {
    // 用裸 axios，避免带上过期 access token 触发拦截器递归
    const response = await axios.post(`${BASE_URL}/tokens/refresh`, { refresh_token: current })
    const { access_token, refresh_token } = response.data as {
      access_token: string
      refresh_token: string
    }
    session.setTokens(access_token, refresh_token)
    return access_token
  } catch (error) {
    // 请求失败期间别人可能已经刷新成功，再确认一次
    const after = session.getRefreshToken()
    if (after && after !== current) return session.getAccessToken()

    const status = (error as AxiosError).response?.status
    // 没有响应（断网/超时）或 5xx / 429：会话没有失效证据，保留登录态交给调用方处理
    if (!status || status >= 500 || status === 429) {
      throw error
    }
    // 401/403：refresh 令牌确实失效，才允许清空会话
    session.clearSession()
    return null
  }
}

// 本页内的刷新单飞：并发 401 共享同一次刷新（后端令牌是轮换制，重复提交必失败）
let refreshingPromise: Promise<string | null> | null = null

function refreshSession(staleRefreshToken: string | null): Promise<string | null> {
  if (!refreshingPromise) {
    const run = () => doRefresh(staleRefreshToken)
    // 抢不到锁说明别的标签页正在刷新：排队等它完成，进去后大概率直接采用其结果
    refreshingPromise = session
      .withCrossTabLock(session.REFRESH_LOCK, run, run)
      .finally(() => {
        refreshingPromise = null
      })
  }
  return refreshingPromise
}

function redirectToLogin() {
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  async (error) => {
    const originalRequest = error.config as RetriableRequest | undefined
    const status = error.response?.status

    // Token 过期，尝试刷新（并发 401 复用同一个进行中的刷新）
    if (
      status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      shouldAttemptRefresh(originalRequest.url)
    ) {
      originalRequest._retry = true

      let accessToken: string | null = null
      try {
        accessToken = await refreshSession(originalRequest._refreshTokenUsed ?? null)
      } catch {
        // 刷新接口本身不可用（断网/502）：保持登录态，把原始错误抛给业务层
        return Promise.reject(error)
      }

      if (accessToken) {
        originalRequest.headers.Authorization = `Bearer ${accessToken}`
        return apiClient(originalRequest)
      }

      redirectToLogin()
      return Promise.reject(error)
    }

    return Promise.reject(error)
  }
)

export default apiClient
