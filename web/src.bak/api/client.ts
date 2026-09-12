import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

// In development, use empty string to leverage Vite proxy
// In production, use the environment variable or default to relative path
const BASE_URL = import.meta.env.MODE === 'development' ? '' : (import.meta.env.VITE_API_BASE_URL || '')

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取 token
    const token = localStorage.getItem('accessToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
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

// 进行中的刷新请求（单飞）：后端 refresh token 是轮换机制（刷新即作废旧令牌），
// access 过期时页面并发请求会各自收到 401，必须共享同一次刷新，
// 否则后到的刷新带着已作废的 refresh token 会 401，把人踢回登录页
let refreshingPromise: Promise<string> | null = null

// 刷新失败，清除 token 并跳转到登录页
const clearAuthAndRedirect = () => {
  localStorage.removeItem('accessToken')
  localStorage.removeItem('refreshToken')
  localStorage.removeItem('user')

  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

const refreshTokens = async (): Promise<string> => {
  const refreshToken = localStorage.getItem('refreshToken')
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }

  // 调用刷新 token 接口（用裸 axios，避免带上过期 access token 的循环拦截）
  const response = await axios.post(
    '/tokens/refresh',
    { refresh_token: refreshToken }
  )

  const { access_token, refresh_token: newRefreshToken } = response.data

  // 保存新 token
  localStorage.setItem('accessToken', access_token)
  localStorage.setItem('refreshToken', newRefreshToken)
  return access_token
}

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  async (error) => {
    const originalRequest = error.config

    // Token 过期，尝试刷新（并发 401 复用同一个进行中的刷新）
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        if (!refreshingPromise) {
          refreshingPromise = refreshTokens().finally(() => {
            refreshingPromise = null
          })
        }
        const accessToken = await refreshingPromise

        // 用新 token 重试原请求
        originalRequest.headers.Authorization = `Bearer ${accessToken}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        clearAuthAndRedirect()
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
