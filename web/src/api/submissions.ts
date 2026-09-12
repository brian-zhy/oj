import apiClient from './client'
import type {
  Submission,
  SubmissionListResponse,
  TestCaseItem,
} from '@/types'

export interface SubmissionListParams {
  page?: number
  page_size?: number
  problem_id?: number
}

export const submissionsApi = {
  // 提交代码（后台评测，返回的 status 短暂为 pending/judging）
  async create(
    problemId: number,
    data: { code: string; language: string }
  ): Promise<Submission> {
    return apiClient.post(`/api/problems/${problemId}/submissions`, data)
  },

  // 某题的提交记录（全站可见）
  async listByProblem(
    problemId: number,
    params: { page?: number; page_size?: number } = {}
  ): Promise<SubmissionListResponse> {
    return apiClient.get(`/api/problems/${problemId}/submissions`, { params })
  },

  // 我的提交记录（可按题目过滤）
  async listMine(
    params: SubmissionListParams = {}
  ): Promise<SubmissionListResponse> {
    return apiClient.get('/api/submissions/mine', { params })
  },

  // 我在该题的最后一次提交（含代码，用于提交页回填）；从未提交返回 null
  async getMyLast(problemId: number): Promise<Submission | null> {
    return apiClient.get(`/api/problems/${problemId}/my-last-submission`)
  },

  // 提交详情
  async get(id: number): Promise<Submission> {
    return apiClient.get(`/api/submissions/${id}`)
  },
}

// 测试点管理（题目管理权限）
export const testCasesApi = {
  async list(problemId: number): Promise<TestCaseItem[]> {
    return apiClient.get(`/api/problems/${problemId}/test-cases`)
  },

  async create(
    problemId: number,
    data: { input_data: string; expected_output: string }
  ): Promise<TestCaseItem> {
    return apiClient.post(`/api/problems/${problemId}/test-cases`, data)
  },

  async remove(problemId: number, caseId: number): Promise<{ success: boolean }> {
    return apiClient.delete(`/api/problems/${problemId}/test-cases/${caseId}`)
  },
}
