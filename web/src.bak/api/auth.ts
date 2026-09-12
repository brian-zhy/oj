import apiClient from './client'
import type { LoginCredentials, RegisterData, TokenResponse, User } from '@/types'

export const authApi = {
  // 注册
  async register(data: RegisterData): Promise<any> {
    return apiClient.post('/auth/register', data)
  },

  // 发送邮箱验证码
  async sendEmailVerification(email: string): Promise<any> {
    return apiClient.post('/auth/send-verification', { email })
  },

  // 测试邮箱配置
  async testEmailConfig(): Promise<any> {
    return apiClient.get('/auth/email-config-test')
  },

  // 登录（使用用户名/UID/手机/邮箱）
  async loginWithIdentifier(credentials: {
    identifier: string
    password: string
    captcha_id: string
    captcha: string
  }): Promise<TokenResponse> {
    return apiClient.post('/auth/login', credentials)
  },

  // 登录
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)

    return apiClient.post('/tokens', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })
  },

  // 刷新 token
  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    return apiClient.post('/tokens/refresh', { refresh_token: refreshToken })
  },

  // 获取当前用户信息
  async getCurrentUser(): Promise<User> {
    // 加时间戳避免浏览器/中间层缓存旧资料（如刚上传的头像在刷新后仍显示旧图）
    return apiClient.get(`/auth/me?_t=${Date.now()}`)
  },

  // 请求密码重置
  async requestPasswordReset(email: string): Promise<any> {
    return apiClient.post('/auth/password-reset/request', { email })
  },

  // 确认密码重置
  async confirmPasswordReset(token: string, new_password: string): Promise<any> {
    return apiClient.post('/auth/password-reset/confirm', { token, new_password })
  }
}
