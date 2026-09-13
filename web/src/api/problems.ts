import apiClient from './client'
import type {
  Problem,
  ProblemListItem,
  ProblemListResponse,
} from '@/types'

export interface ProblemFilterParams {
  page?: number
  page_size?: number
  difficulty?: string
  source?: string
  tag?: string
  keyword?: string
  all?: boolean
}

export const problemsApi = {
  // 题目列表（支持难度 / 来源 / 标签 / 关键词筛选）
  async list(
    params: ProblemFilterParams = {}
  ): Promise<ProblemListResponse> {
    return apiClient.get('/api/problems', { params })
  },

  // 题目详情（含题面）
  async get(id: number): Promise<Problem> {
    return apiClient.get(`/api/problems/${id}`)
  },

  // 按统一题号访问（P1001 / T10）
  async getByCode(code: string): Promise<Problem> {
    return apiClient.get(`/api/problems/by-code/${encodeURIComponent(code)}`)
  },

  // 去重后的来源列表（筛选下拉用）
  async sources(): Promise<string[]> {
    return apiClient.get('/api/problems/sources')
  },

  // 以下需题目管理权限
  async create(data: Partial<Problem>): Promise<Problem> {
    return apiClient.post('/api/problems', data)
  },

  async update(
    id: number,
    data: Partial<Problem> & { author?: string }
  ): Promise<Problem> {
    return apiClient.put(`/api/problems/${id}`, data)
  },
}

export type { Problem, ProblemListItem }
