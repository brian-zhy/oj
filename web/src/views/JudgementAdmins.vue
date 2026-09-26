<script setup lang="ts">
import { ref, onMounted } from 'vue'
import apiClient from '@/api/client'
import { userNameColor } from '@/utils/userColor'

// 参考站 /judgement/admins：公示所有管理权限持有者
interface AdminUser {
  id: number
  username: string
  avatar_url: string
  user_tag: string
  user_number: number
  is_super_admin: boolean
  is_admin: boolean
  can_manage_users: boolean
  can_manage_posts: boolean
  can_manage_problems: boolean
  can_manage_tags: boolean
  can_assign_admin: boolean
}

const admins = ref<AdminUser[]>([])
const loading = ref(true)
const error = ref('')

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const data: any = await apiClient.get('/api/judgement/admins')
    admins.value = data.admins || []
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// 与全站一致的字母头像
const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}
const avatarOf = (u: AdminUser) => u.avatar_url || letterAvatar(u.username)

const tagOf = (u: AdminUser) => {
  if (u.user_tag) return u.user_tag
  if (u.is_super_admin) return '超级管理员'
  if (u.is_admin) return '管理员'
  return '成员'
}

// 该用户持有的管理权限徽章（不设限的全部列出）
const permsOf = (u: AdminUser) => {
  const list: string[] = []
  if (u.is_super_admin) list.push('超级管理员')
  if (u.is_admin) list.push('管理员')
  if (u.can_manage_users) list.push('用户管理')
  if (u.can_manage_posts) list.push('秩序管理')
  if (u.can_manage_problems) list.push('题目管理')
  if (u.can_manage_tags) list.push('Tag 管理')
  if (u.can_assign_admin) list.push('授予管理员')
  return list
}

onMounted(load)
</script>

<template>
  <div class="admins-page">
    <div class="admins-container">
      <div class="card head-card">
        <h2 class="page-title">管理名单</h2>
        <p class="page-sub">此处列出拥有管理权限的成员及其权限明细。</p>
      </div>

      <div v-if="loading" class="loading-state">
        <span class="loading-spinner"></span>
        <span>名单加载中…</span>
      </div>
      <div v-else-if="error" class="card empty">{{ error }}</div>
      <div v-else-if="admins.length === 0" class="card empty">暂无管理员</div>

      <div v-else class="card list-card">
        <div v-for="u in admins" :key="u.id" class="entry">
          <img class="avatar" :src="avatarOf(u)" :alt="u.username">
          <div class="entry-main">
            <div class="name-row">
              <router-link
                :to="`/user/${u.user_number}`"
                class="name"
                :style="{ color: userNameColor(u) }"
              >{{ u.username }}</router-link>
              <span class="user-tag-display" :style="{ backgroundColor: userNameColor(u) }">{{ tagOf(u) }}</span>
            </div>
            <div class="perm-row">
              <span v-for="p in permsOf(u)" :key="p" class="perm-badge">{{ p }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admins-page { min-height: calc(100vh - 60px - 80px); }
.admins-container { max-width: 860px; margin: 0 auto; padding: 4px 0 24px; display: flex; flex-direction: column; gap: 16px; }

.head-card { padding: 20px 26px; }
.page-title { color: var(--primary); font-size: 22px; margin: 0; }
.page-sub { color: var(--text-sub); font-size: 13px; margin: 6px 0 0; }

.empty { text-align: center; color: #999; padding: 48px 0; }

.list-card { padding: 10px 20px; }

.entry { display: flex; align-items: center; gap: 14px; padding: 12px 6px; }
.entry + .entry { border-top: var(--border-width) solid var(--border-color); }
.avatar { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
.entry-main { min-width: 0; }

.name-row { display: flex; align-items: center; gap: 2px; }
.name { font-weight: 700; font-size: 14px; text-decoration: none; }
.name:hover { text-decoration: underline; }

/* 与主站一致：用户名后方的方框称号 */
.user-tag-display {
  display: inline-block;
  border-radius: 2px;
  padding: 2px 9px;
  color: #fff;
  font-size: 11.5px;
  font-weight: 600;
  margin: 0 0 0 4px;
  cursor: default;
  transition: filter 0.15s;
  vertical-align: middle;
}
.user-tag-display:hover { filter: brightness(0.9); }

.perm-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 5px; }
.perm-badge {
  font-size: 11px;
  color: #5a6b85;
  background: rgba(148, 163, 184, 0.16);
  border: var(--border-width) solid var(--border-color);
  border-radius: 4px;
  padding: 1px 7px;
}
</style>
