<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import apiClient from '@/api/client'
import { userNameColor } from '@/utils/userColor'

// 参考站 /judgement/admins：公示「用户管理」与「秩序管理」持有者
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
}

const admins = ref<AdminUser[]>([])
const loading = ref(true)
const error = ref('')

const userMgmt = computed(() => admins.value.filter(u => u.can_manage_users))
const postMgmt = computed(() => admins.value.filter(u => u.can_manage_posts))

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

onMounted(load)
</script>

<template>
  <div class="admins-page">
    <div class="admins-container">
      <div class="card head-card">
        <h2 class="page-title">管理名单</h2>
        <p class="page-sub">此处列出拥有「用户管理」或「秩序管理」权限的管理员。</p>
      </div>

      <div v-if="loading" class="loading-state">
        <span class="loading-spinner"></span>
        <span>名单加载中…</span>
      </div>
      <div v-else-if="error" class="card empty">{{ error }}</div>
      <div v-else-if="admins.length === 0" class="card empty">暂无管理员</div>

      <div v-else class="two-col">
        <div class="card col">
          <div class="col-header">👤 用户管理 <span class="count">({{ userMgmt.length }})</span></div>
          <div v-if="userMgmt.length === 0" class="col-empty">暂无</div>
          <div v-for="u in userMgmt" :key="'u' + u.id" class="entry">
            <img class="avatar" :src="avatarOf(u)" :alt="u.username">
            <div class="entry-main">
              <router-link
                :to="`/user/${u.user_number}`"
                class="name"
                :style="{ color: userNameColor(u) }"
              >{{ u.username }}</router-link>
              <div class="entry-sub">
                <span class="tag" :style="{ backgroundColor: userNameColor(u) }">{{ tagOf(u) }}</span>
                <span class="uid">UID {{ u.user_number }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="card col">
          <div class="col-header">⚖️ 秩序管理 <span class="count">({{ postMgmt.length }})</span></div>
          <div v-if="postMgmt.length === 0" class="col-empty">暂无</div>
          <div v-for="u in postMgmt" :key="'p' + u.id" class="entry">
            <img class="avatar" :src="avatarOf(u)" :alt="u.username">
            <div class="entry-main">
              <router-link
                :to="`/user/${u.user_number}`"
                class="name"
                :style="{ color: userNameColor(u) }"
              >{{ u.username }}</router-link>
              <div class="entry-sub">
                <span class="tag" :style="{ backgroundColor: userNameColor(u) }">{{ tagOf(u) }}</span>
                <span class="uid">UID {{ u.user_number }}</span>
              </div>
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

.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.col { padding: 18px 20px; }
.col-header { font-weight: 800; color: var(--text-main); font-size: 15px; margin-bottom: 12px; }
.col-header .count { color: var(--text-sub); font-weight: 700; }
.col-empty { color: #999; font-size: 13px; padding: 8px 4px; }

.entry { display: flex; align-items: center; gap: 12px; padding: 10px 6px; border-radius: var(--radius-sm); transition: background 0.15s; }
.entry:hover { background: rgba(148, 163, 184, 0.12); }
.avatar { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
.entry-main { min-width: 0; }
.name { font-weight: 700; font-size: 14px; text-decoration: none; }
.name:hover { text-decoration: underline; }
.entry-sub { display: flex; align-items: center; gap: 8px; margin-top: 3px; }
.tag { color: #fff; font-size: 11px; padding: 1px 8px; border-radius: 9px; }
.uid { color: var(--text-sub); font-size: 12px; }

@media (max-width: 640px) {
  .two-col { grid-template-columns: 1fr; }
}
</style>
