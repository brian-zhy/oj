<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { contestsApi } from '@/api/contests'
import { problemsApi } from '@/api/problems'
import { userNameColor } from '@/utils/userColor'

const router = useRouter()
const authStore = useAuthStore()
const me = computed(() => authStore.currentUser)

// 未开放选择：当前仅支持公开赛 / 邀请赛，赛制固定 ACM
const visibility = ref<'public' | 'private'>('public')
const inviteCode = ref('')

const form = ref({ title: '', description: '', start_date: '', start_time: '', end_date: '', end_time: '' })
const createError = ref('')
const creating = ref(false)

// 题目池（主题库公开题，勾选顺序即比赛内 A/B/C/D）
const pool = ref<{ id: number; title: string; problem_number: string }[]>([])
const picked = ref<number[]>([])
const poolLoading = ref(false)

const canSubmit = computed(() =>
  form.value.title.trim() && form.value.start_date && form.value.start_time
  && form.value.end_date && form.value.end_time && picked.value.length > 0
)

const togglePick = (id: number) => {
  const i = picked.value.indexOf(id)
  if (i === -1) picked.value.push(id)
  else picked.value.splice(i, 1)
}

// 默认时间：今天 19:00 ~ 明天 21:00（东八区语义按浏览器本地时间）
const pad = (n: number) => String(n).padStart(2, '0')
const now = new Date()
form.value.start_date = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
form.value.start_time = '19:00'
const tomorrow = new Date(now.getTime() + 86400000)
form.value.end_date = `${tomorrow.getFullYear()}-${pad(tomorrow.getMonth() + 1)}-${pad(tomorrow.getDate())}`
form.value.end_time = '21:00'

const doCreate = async () => {
  if (!form.value.title.trim()) { createError.value = '请输入比赛名称'; return }
  if (!form.value.start_date || !form.value.start_time || !form.value.end_date || !form.value.end_time) {
    createError.value = '请选择完整的起止时间'
    return
  }
  if (visibility.value === 'private' && inviteCode.value.trim().length < 3) {
    createError.value = '邀请赛需设置 3-32 位邀请码'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    const created = await contestsApi.create({
      title: form.value.title.trim(),
      description: form.value.description.trim() || undefined,
      start_time: new Date(`${form.value.start_date}T${form.value.start_time}`).toISOString(),
      end_time: new Date(`${form.value.end_date}T${form.value.end_time}`).toISOString(),
      problem_ids: picked.value,
      visibility: visibility.value,
      invite_code: visibility.value === 'private' ? inviteCode.value.trim() : undefined,
    })
    router.push(`/contests/${created.id}`)
  } catch (err: any) {
    createError.value = err.response?.data?.detail || '创建失败'
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  poolLoading.value = true
  try {
    const data: any = await problemsApi.list({ page: 0, page_size: 100 })
    pool.value = data.items
  } finally {
    poolLoading.value = false
  }
})
</script>

<template>
  <div class="contest-create-page">
    <div class="contest-create-container">
      <div class="back-link">
        <a @click.prevent="router.push('/contests')" href="#">← 返回比赛列表</a>
      </div>

      <div class="card form-card">
        <div class="form-row">
          <span class="row-label">比赛名称</span>
          <div class="row-value">
            <input v-model="form.title" class="form-input w-title" maxlength="100" placeholder="例如：NLNOJ 月赛 #1" />
          </div>
        </div>

        <div class="form-row">
          <span class="row-label">举办者</span>
          <div class="row-value">
            <span class="owner-name" :style="{ color: userNameColor(me) }">{{ me?.username }}</span>
            <span class="owner-check">✔</span>
          </div>
        </div>

        <div class="form-row">
          <span class="row-label">公开程度</span>
          <div class="row-value">
            <select v-model="visibility" class="form-input w-select">
              <option value="public">公开赛（自由报名）</option>
              <option value="private">邀请赛（报名需邀请码）</option>
            </select>
          </div>
        </div>

        <div v-if="visibility === 'private'" class="form-row">
          <span class="row-label">邀请码</span>
          <div class="row-value">
            <input v-model="inviteCode" class="form-input w-title" maxlength="32" placeholder="3-32 位，报名时需填写" />
          </div>
        </div>

        <div class="form-row">
          <span class="row-label">比赛赛制</span>
          <div class="row-value">
            <select class="form-input w-select" disabled>
              <option>ACM 赛制（通过数优先，罚时其次）</option>
            </select>
            <span class="hint">IOI / OI 赛制暂未开放</span>
          </div>
        </div>

        <div class="form-row">
          <span class="row-label">开始时间</span>
          <div class="row-value time-pair">
            <input v-model="form.start_date" type="date" class="form-input" />
            <input v-model="form.start_time" type="time" class="form-input" />
          </div>
        </div>

        <div class="form-row">
          <span class="row-label">结束时间</span>
          <div class="row-value time-pair">
            <input v-model="form.end_date" type="date" class="form-input" />
            <input v-model="form.end_time" type="time" class="form-input" />
          </div>
        </div>

        <div class="form-row top">
          <span class="row-label">比赛说明</span>
          <div class="row-value">
            <textarea v-model="form.description" class="form-input" rows="6" placeholder="邀请码、来源、描述、难度、赛时答疑与赛后题解……（支持 Markdown）" />
          </div>
        </div>

        <div class="form-row top">
          <span class="row-label">比赛题目</span>
          <div class="row-value">
            <div class="hint mb">按勾选顺序作为比赛内的 A / B / C / D…（{{ picked.length }} 道已选）</div>
            <div v-if="poolLoading" class="hint">题目加载中...</div>
            <div v-else class="pool">
              <label v-for="p in pool" :key="p.id" class="pool-item">
                <input type="checkbox" :checked="picked.includes(p.id)" @change="togglePick(p.id)" />
                <span class="pool-no">{{ p.problem_number }}</span> {{ p.title }}
              </label>
            </div>
          </div>
        </div>

        <div v-if="createError" class="form-error">{{ createError }}</div>

        <div class="submit-row">
          <button class="btn-secondary" @click="router.push('/contests')">取消</button>
          <button class="btn-primary" :disabled="creating || !canSubmit" @click="doCreate">
            {{ creating ? '创建中...' : '创建比赛' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.contest-create-page { background: #f5f7fa; min-height: calc(100vh - 60px); }
.contest-create-container { max-width: 920px; margin: 0 auto; padding: 20px; }
.back-link { margin-bottom: 12px; }
.back-link a { color: var(--primary); font-size: 14px; cursor: pointer; text-decoration: none; }
.back-link a:hover { text-decoration: underline; }

.card.form-card { background: #fff; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 26px 30px; }
.form-row { display: flex; align-items: center; gap: 18px; padding: 12px 0; border-bottom: 1px solid #f7f8fa; }
.form-row.top { align-items: flex-start; }
.row-label { width: 90px; flex-shrink: 0; font-size: 14px; font-weight: 600; color: #4b4b4b; text-align: right; }
.row-value { flex: 1; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.form-input { padding: 8px 12px; border: 1px solid #dce0e6; border-radius: 8px; font-size: 14px; outline: none; font-family: inherit; }
.form-input:focus { border-color: var(--primary); }
.form-input:disabled { background: #f5f6f8; color: #66708a; }
.w-title { width: min(360px, 100%); }
.w-select { width: min(360px, 100%); background: #fff; }
.time-pair .form-input { width: auto; }
textarea.form-input { width: 100%; box-sizing: border-box; resize: vertical; }
.owner-name { font-weight: 700; font-size: 15px; }
.owner-check { color: #52c41a; }
.hint { font-size: 12px; color: #8e9aaf; }
.hint.mb { margin-bottom: 8px; }

.pool { max-height: 240px; overflow-y: auto; border: 1px solid #eef1f5; border-radius: 8px; padding: 10px 14px; display: flex; flex-direction: column; gap: 5px; width: 100%; box-sizing: border-box; }
.pool-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #1f2a3a; cursor: pointer; }
.pool-item input { accent-color: var(--primary); }
.pool-no { color: var(--primary); font-weight: 600; }

.form-error { color: #e74c3c; font-size: 13px; margin-top: 12px; }
.submit-row { display: flex; justify-content: flex-end; gap: 12px; margin-top: 18px; }
.btn-primary { background: var(--primary); color: #fff; border: none; border-radius: 8px; padding: 9px 26px; font-weight: 600; cursor: pointer; font-size: 14px; }
.btn-primary:hover:not(:disabled) { background: var(--primary-hover); }
.btn-primary:disabled { opacity: .55; cursor: not-allowed; }
.btn-secondary { background: #eee; color: #333; border: none; border-radius: 8px; padding: 9px 26px; font-weight: 600; cursor: pointer; font-size: 14px; }

@media (max-width: 640px) {
  .form-row { flex-direction: column; align-items: stretch; gap: 6px; }
  .row-label { width: auto; text-align: left; }
}
</style>
