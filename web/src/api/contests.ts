import apiClient from './client'

export interface ContestProblemItem {
  alias: string
  problem_id: number
  sort_order: number
  title: string
  difficulty: string
  problem_number: string
}

export interface ContestItem {
  id: number
  title: string
  description: string
  visibility: 'public' | 'private' | 'team' | 'team_private'
  type_label: string
  team_id: number | null
  team_name: string | null
  invite_code?: string | null
  start_time: string | null
  end_time: string | null
  status: 'pending' | 'running' | 'ended'
  owner: { user_id: number; username: string }
  participant_count: number
  problem_count: number
  is_owner: boolean
  can_manage: boolean
  is_participant: boolean
  can_view_problems?: boolean
  problems?: ContestProblemItem[]
}

export interface RankDetail {
  tries: number
  solved: boolean
  minutes?: number
  penalty?: number
}

export interface RankRow {
  rank: number
  user: Record<string, any>
  solved: number
  penalty: number
  detail: Record<string, RankDetail>
}

export const contestsApi = {
  async list(page = 0): Promise<{ items: ContestItem[]; total: number }> {
    return apiClient.get('/api/contests', { params: { page, page_size: 50 } })
  },

  async get(id: number): Promise<ContestItem> {
    return apiClient.get(`/api/contests/${id}`)
  },

  async create(data: {
    title: string
    description?: string
    start_time: string
    end_time: string
    problem_codes: string[]
    team_id?: number
    visibility?: 'public' | 'private' | 'team' | 'team_private'
    invite_code?: string
  }): Promise<ContestItem> {
    return apiClient.post('/api/contests', data)
  },

  async remove(id: number): Promise<{ success: boolean }> {
    return apiClient.delete(`/api/contests/${id}`)
  },

  async register(id: number, inviteCode?: string): Promise<{ success: boolean }> {
    return apiClient.post(`/api/contests/${id}/register`,
      inviteCode ? { invite_code: inviteCode } : undefined)
  },

  async rank(id: number): Promise<{ aliases: string[]; rows: RankRow[] }> {
    return apiClient.get(`/api/contests/${id}/rank`)
  },
}
