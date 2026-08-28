// 认证相关类型
export interface User {
  id: number
  username: string
  email: string
  user_number: number
  phone?: string | null
  is_active: boolean
  is_banned: boolean
  is_admin: boolean
  is_super_admin: boolean
  is_cheater: boolean
  can_speak: boolean
  can_manage_users: boolean
  can_manage_posts: boolean
  can_assign_admin: boolean
  avatar_url?: string | null
  user_tag?: string | null
  username_color?: string | null
  bio?: string | null
  created_at: string
  updated_at?: string
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterData {
  username: string
  email?: string
  phone?: string
  password: string
  email_token?: string
  email_code?: string
  phone_token?: string
  phone_code?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// 题目相关类型
export interface Problem {
  id: number
  title: string
  description: string
  difficulty: 'easy' | 'medium' | 'hard'
  time_limit?: number
  memory_limit?: number
  examples?: Array<{
    input: string
    output: string
    explanation?: string
  }>
  created_at: string
  updated_at: string
}

export interface ProblemListItem {
  id: number
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  acceptance_rate?: number
  solved_count?: number
}

// 提交相关类型
export interface Submission {
  id: number
  problem_id: number
  user_id: number
  code: string
  language: string
  status: 'pending' | 'judging' | 'accepted' | 'wrong_answer' | 'time_limit_exceeded' | 'memory_limit_exceeded' | 'runtime_error' | 'compile_error'
  submit_time: string
  judge_time?: string
  runtime?: number
  memory_usage?: number
}

export interface CreateSubmissionData {
  problem_id: number
  code: string
  language: string
}

// 通用 API 响应类型
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface ApiError {
  detail: string
  status_code?: number
}

// 全局类型扩展
declare global {
  interface Window {
    __AUTH_TOKENS__?: {
      accessToken: string
      refreshToken: string
      apiUrl: string
    }
    __AUTH_INFO__?: {
      accessToken: string
      refreshToken: string
      apiUrl: string
      currentUser: User | null
    }
    supabase?: any
  }
}

export {} // 确保这是模块文件
