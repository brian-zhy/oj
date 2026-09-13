import apiClient from './client'
import type { HostedImage, ImageListResponse, ImageQuota, WatermarkMode } from '@/types'

export interface ImageListParams {
  page?: number
  page_size?: number
  premium?: boolean
  locked?: boolean
  q?: string
}

export const imagesApi = {
  // 上传图片（multipart）；大图 + 加水印较慢，单独放宽超时
  async upload(file: File, watermark: WatermarkMode = 'none'): Promise<HostedImage> {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('watermark', watermark)
    return apiClient.post('/api/images/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },

  async list(params: ImageListParams = {}): Promise<ImageListResponse> {
    return apiClient.get('/api/images', { params })
  },

  async quota(): Promise<ImageQuota> {
    return apiClient.get('/api/images/quota')
  },

  // 切换锁定（锁定后不可删除）
  async toggleLock(id: number): Promise<HostedImage> {
    return apiClient.patch(`/api/images/${id}/lock`)
  },

  async remove(id: number): Promise<{ success: boolean }> {
    return apiClient.delete(`/api/images/${id}`)
  },
}
