<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { teamsApi, type TeamItem } from '@/api/teams'
import { userNameColor } from '@/utils/userColor'

const router = useRouter()
const authStore = useAuthStore()
const isLoggedIn = computed(() => authStore.isAuthenticated)

const teams = ref<TeamItem[]>([])
const total = ref(0)
const page = ref(0)
const loading = ref(false)
const error = ref('')

const hasMore = computed(() => teams.value.length < total.value)

const load = async (append = false) => {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await teamsApi.list(page.value)
    teams.value = append ? [...teams.value, ...data.items] : data.items
    total.value = data.total
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const loadMore = () => {
  page.value++
  load(true)
}

// ===== 新建团队 =====
const showCreate = ref(false)
const form = ref({ name: '', description: '' })
const creating = ref(false)
const createError = ref('')

const openCreate = () => {
  form.value = { name: '', description: '' }
  createError.value = ''
  showCreate.value = true
}

const doCreate = async () => {
  if (!form.value.name.trim()) {
    createError.value = '请输入团队名称'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    const team = await teamsApi.create({
      name: form.value.name.trim(),
      description: form.value.description.trim() || undefined,
    })
    showCreate.value = false
    router.push(`/teams/${team.id}`)
  } catch (err: any) {
    createError.value = err.response?.data?.detail || '创建失败'
  } finally {
    creating.value = false
  }
}

const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

const fmtDate = (iso: string | null) => (iso ? iso.slice(0, 10) : '—')

onMounted(() => load())
</script>

<template>
  <div class="teams-page">
    <div class="teams-container">
      <div class="page-head">
        <h2 class="page-title">团队</h2>
        <button v-if="isLoggedIn" class="btn-primary" @click="openCreate"><i class="fa-solid fa-plus"></i> 新建团队</button>
      </div>

      <div v-if="loading && teams.length === 0" class="empty">加载中...</div>
      <div v-else-if="error && teams.length === 0" class="empty">{{ error }}</div>
      <div v-else-if="teams.length === 0" class="empty">
        还没有团队，点击右上角「新建团队」创建第一个
      </div>

      <div v-else class="team-grid">
        <div
          v-for="t in teams"
          :key="t.id"
          class="team-card"
          @click="router.push(`/teams/${t.id}`)"
        >
          <div class="team-card-head">
            <span class="team-name">{{ t.name }}</span>
            <span class="team-count">{{ t.member_count }} 人</span>
          </div>
          <div v-if="t.description" class="team-desc">{{ t.description }}</div>
          <div class="team-card-foot">
            <img class="owner-avatar" :src="t.owner.avatar_url || letterAvatar(t.owner.username)" alt="" />
            <span class="owner-name" :style="{ color: userNameColor(t.owner) }">{{ t.owner.username }}</span>
            <span class="team-date">{{ fmtDate(t.created_at) }}</span>
          </div>
        </div>
      </div>

      <div v-if="hasMore" class="load-more">
        <button class="btn-secondary" :disabled="loading" @click="loadMore">
          {{ loading ? '加载中...' : '加载更多' }}
        </button>
      </div>

      <!-- 新建团队弹窗 -->
      <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
        <div class="modal-box">
          <div class="modal-header">
            <h3>新建团队</h3>
            <button class="modal-close" @click="showCreate = false"><i class="fa-solid fa-xmark"></i></button>
          </div>
          <div class="modal-body">
            <label class="form-item">
              <span class="form-label">团队名称 *</span>
              <input v-model="form.name" class="form-input" maxlength="50" placeholder="例如：NLNOJ 出题组" />
            </label>
            <label class="form-item">
              <span class="form-label">团队简介（可选）</span>
              <textarea v-model="form.description" class="form-input" rows="3" maxlength="500" placeholder="介绍一下这个团队" />
            </label>
            <div v-if="createError" class="form-error">{{ createError }}</div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="showCreate = false">取消</button>
            <button class="btn-primary" :disabled="creating" @click="doCreate">
              {{ creating ? '创建中...' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.teams-page { background: #f5f7fa; min-height: calc(100vh - 60px); }
.teams-container { max-width: 1000px; margin: 0 auto; padding: 24px 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.page-title { color: var(--primary); font-size: 22px; margin: 0; }

.team-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.team-card { background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 16px 18px; cursor: pointer; transition: transform .12s, box-shadow .12s; display: flex; flex-direction: column; gap: 8px; }
.team-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,.09); }
.team-card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.team-name { font-size: 16px; font-weight: 700; color: #2c3e50; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.team-count { flex-shrink: 0; font-size: 12px; color: var(--primary); background: #fef0ef; border-radius: 20px; padding: 2px 10px; font-weight: 600; }
.team-desc { font-size: 13px; color: #8e9aaf; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.team-card-foot { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.owner-avatar { width: 20px; height: 20px; border-radius: 50%; object-fit: cover; }
.owner-name { font-weight: 600; }
.team-date { margin-left: auto; color: #b2bac6; font-size: 12px; }

.load-more { text-align: center; margin-top: 18px; }
.empty { text-align: center; color: #999; padding: 48px 0; }

.btn-primary { background: var(--primary); color: #fff; border: none; border-radius: 8px; padding: 8px 20px; font-weight: 600; cursor: pointer; font-size: 14px; }
.btn-primary:hover { background: var(--primary-hover); }
.btn-primary:disabled { opacity: .6; cursor: not-allowed; }
.btn-secondary { background: #eee; color: #333; border: none; border-radius: 8px; padding: 8px 20px; font-weight: 600; cursor: pointer; font-size: 14px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 999; display: flex; justify-content: center; align-items: center; }
.modal-box { background: #fff; border-radius: 14px; width: 90%; max-width: 440px; padding: 24px 28px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.modal-header h3 { margin: 0; font-size: 18px; color: #262626; }
.modal-close { background: none; border: none; font-size: 20px; color: #8e9aaf; cursor: pointer; }
.form-item { display: block; margin-bottom: 14px; }
.form-label { display: block; font-size: 13px; font-weight: 600; color: #4b4b4b; margin-bottom: 6px; }
.form-input { width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid #dce0e6; border-radius: 8px; font-size: 14px; outline: none; font-family: inherit; resize: vertical; }
.form-input:focus { border-color: var(--primary); }
.form-error { color: var(--primary); font-size: 13px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 12px; margin-top: 8px; }

/* ===== 手机端：容器横向内边距归零（避免与 App.vue 页边距叠加）===== */
@media (max-width: 600px) {
  .teams-container {
    padding: 16px 0;
  }

  .team-card {
    padding: 14px;
  }
}
</style>
