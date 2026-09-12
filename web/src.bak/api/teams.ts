import apiClient from './client'

export interface TeamUserBrief {
  user_id: number | null
  username: string
  user_tag: string
  is_admin: boolean
  is_super_admin: boolean
  is_banned: boolean
  is_cheater: boolean
  can_manage_users: boolean
  can_manage_posts: boolean
  can_manage_problems: boolean
  user_number: number | null
  avatar_url: string
}

export interface TeamMemberItem {
  user_id: number
  role: 'owner' | 'admin' | 'member'
  note: string
  joined_at: string | null
  user: TeamUserBrief
}

export interface TeamItem {
  id: number
  name: string
  description: string
  owner: TeamUserBrief
  owner_id: number
  member_count: number
  created_at: string | null
  is_owner: boolean
  is_member: boolean
  is_team_admin: boolean
}

export interface TeamDetailItem extends TeamItem {
  members: TeamMemberItem[]
}

export const teamsApi = {
  async list(page = 0, pageSize = 20): Promise<{ items: TeamItem[]; total: number }> {
    return apiClient.get('/api/teams', { params: { page, page_size: pageSize } })
  },

  async get(id: number): Promise<TeamDetailItem> {
    return apiClient.get(`/api/teams/${id}`)
  },

  async create(data: { name: string; description?: string }): Promise<TeamItem> {
    return apiClient.post('/api/teams', data)
  },

  async join(id: number): Promise<{ success: boolean }> {
    return apiClient.post(`/api/teams/${id}/join`)
  },

  async leave(id: number): Promise<{ success: boolean }> {
    return apiClient.post(`/api/teams/${id}/leave`)
  },

  async dissolve(id: number): Promise<{ success: boolean }> {
    return apiClient.delete(`/api/teams/${id}`)
  },

  async updateMember(
    teamId: number,
    userId: number,
    data: { role?: 'member' | 'admin'; note?: string }
  ): Promise<TeamMemberItem> {
    return apiClient.put(`/api/teams/${teamId}/members/${userId}`, data)
  },

  async removeMember(teamId: number, userId: number): Promise<{ success: boolean }> {
    return apiClient.delete(`/api/teams/${teamId}/members/${userId}`)
  },
}
