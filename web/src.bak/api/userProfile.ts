import apiClient from './client'
import type { User } from '@/types'

export interface UserProfileUpdate {
  username?: string
  bio?: string
  avatar_url?: string
  user_tag?: string
  username_color?: string
}

export interface PasswordUpdate {
  old_password: string
  new_password: string
}

export const userProfileApi = {
  // 获取当前用户信息
  async getCurrentUser(): Promise<User> {
    return apiClient.get('/users/me')
  },

  // 更新用户资料
  async updateProfile(data: UserProfileUpdate): Promise<User> {
    return apiClient.put('/users/me/profile', data)
  },

  // 更新密码
  async updatePassword(data: PasswordUpdate): Promise<{ message: string }> {
    return apiClient.put('/users/me/password', data)
  },

  // 上传头像
  async uploadAvatar(file: File): Promise<{ message: string }> {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/users/me/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 根据ID获取用户信息
  async getUserById(userId: number): Promise<User> {
    return apiClient.get(`/users/${userId}`)
  },

  // 根据用户编号获取用户信息
  async getUserByNumber(userNumber: number): Promise<User> {
    return apiClient.get(`/users/number/${userNumber}`)
  }
}
