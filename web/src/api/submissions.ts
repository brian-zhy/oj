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
    data: { code: string; language: string; contest_id?: number }
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
  // 上传 zip 压缩包批量导入测试点（.in/.out 成对，包≤50M 解压≤100M）
  async uploadZip(
    problemId: number,
    file: File
  ): Promise<{ success: boolean; imported: number }> {
    const fd = new FormData()
    fd.append('file', file)
    // 不能手动设置 multipart/form-data；浏览器需要自动附带 boundary
    // 否则 FastAPI 不能正确解析 FormData，上传会出现 422 / 导入失败
    return apiClient.post(`/api/problems/${problemId}/test-cases/upload-zip`, fd)
  },

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
