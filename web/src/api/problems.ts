import apiClient from './client'
import type { Problem, ProblemListItem, CreateSubmissionData, Submission } from '@/types'

export const problemsApi = {
  // 获取题目列表
  async getProblemList(): Promise<ProblemListItem[]> {
    return apiClient.get('/problems')
  },

  // 获取题目详情
  async getProblemById(id: number): Promise<Problem> {
    return apiClient.get(`/problems/${id}`)
  },

  // 提交代码
  async submitCode(data: CreateSubmissionData): Promise<Submission> {
    return apiClient.post('/submissions', data)
  },

  // 获取提交记录
  async getSubmissions(problemId?: number): Promise<Submission[]> {
    const params = problemId ? { problem_id: problemId } : {}
    return apiClient.get('/submissions', { params })
  },

  // 获取提交详情
  async getSubmissionById(id: number): Promise<Submission> {
    return apiClient.get(`/submissions/${id}`)
  }
}
