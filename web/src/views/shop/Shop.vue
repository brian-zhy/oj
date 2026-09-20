<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'
import { userNameColor } from '@/utils/userColor'

const authStore = useAuthStore()
const me = computed(() => authStore.currentUser)

interface ShopItem {
  id: number
  name: string
  price: number
  desc: string
  prev: string | null
  owned: boolean
  prev_owned: boolean
  can_redeem: boolean
  locked_by: string | null
  enough_exp: boolean
}

const experience = ref(0)
const items = ref<ShopItem[]>([])
const loading = ref(true)
const error = ref('')
const actingId = ref<number | null>(null)
const actionMsg = ref('')

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const data: any = await apiClient.get('/api/shop/items')
    experience.value = data.experience
    items.value = data.items
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const redeem = async (item: ShopItem) => {
  if (!item.can_redeem) return
  if (!confirm(`确定花费 ${item.price} 经验兑换「${item.name}」吗？兑换后自动佩戴。`)) return
  actingId.value = item.id
  actionMsg.value = ''
  try {
    const res: any = await apiClient.post('/api/shop/redeem', { item_id: item.id })
    actionMsg.value = `兑换成功！「${res.name}」已加入你的 Tag 卡并自动佩戴`
    await load()
    // 同步 authStore（经验余额与佩戴中的 tag 全站生效）
    await authStore.syncCurrentUser()
  } catch (err: any) {
    actionMsg.value = err.response?.data?.detail || '兑换失败'
  } finally {
    actingId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="shop-page">
    <div class="shop-container">
      <div class="shop-head card">
        <div>
          <h2 class="page-title">经验商店</h2>
          <p class="page-sub">用刷题攒下的经验兑换专属称号——每件商品都需要持有前一件才能兑换</p>
        </div>
        <div class="exp-box">
          <div class="exp-label">我的经验</div>
          <div class="exp-value">{{ experience }}</div>
        </div>
      </div>

      <div v-if="actionMsg" class="action-msg">{{ actionMsg }}</div>

      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="error" class="empty">{{ error }}</div>

      <div v-else class="item-list">
        <div
          v-for="(item, i) in items"
          :key="item.id"
          class="item-card"
          :class="{ owned: item.owned, locked: !item.prev_owned }"
        >
          <div class="chain-line" v-if="i > 0" />
          <div class="item-main">
            <div class="item-title-row">
              <span class="item-name" :class="{ owned: item.owned }">{{ item.name }}</span>
              <span class="item-price" :class="{ ok: item.enough_exp }">✦ {{ item.price }} 经验</span>
            </div>
            <div class="item-desc">{{ item.desc }}</div>
            <div class="item-state">
              <span v-if="item.owned" class="state-tag owned">已拥有</span>
              <span v-else-if="item.locked_by" class="state-tag locked">需要前置：{{ item.locked_by }}</span>
              <span v-else-if="!item.enough_exp" class="state-tag lack">
                经验不足（还差 {{ item.price - experience }}）
              </span>
              <span v-else class="state-tag ready">可以兑换</span>
            </div>
          </div>
          <div class="item-action">
            <span v-if="item.owned" class="owned-badge"><i class="fa-solid fa-circle-check"></i> 已拥有</span>
            <button
              v-else
              class="btn-redeem"
              :disabled="!item.can_redeem || actingId === item.id"
              @click="redeem(item)"
            >
              {{ actingId === item.id ? '兑换中...' : '兑换' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.shop-page { background: #f5f7fa; min-height: calc(100vh - 60px); }
.shop-container { max-width: 860px; margin: 0 auto; padding: 24px 20px; }

.shop-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px; background: #fff; border-radius: 14px; border: 1px solid var(--primary); padding: 20px 26px; margin-bottom: 16px; }
.page-title { color: var(--primary); font-size: 22px; margin: 0; }
.page-sub { color: #8e9aaf; font-size: 13px; margin: 6px 0 0; }
.exp-box { text-align: center; background: #fff7e6; border: 1px solid #ffe7ba; border-radius: 12px; padding: 10px 26px; }
.exp-label { font-size: 12px; color: #ad6800; }
.exp-value { font-size: 26px; font-weight: 800; color: #d48806; }

.action-msg { background: #eafaf1; color: #27ae60; padding: 10px 16px; border-radius: 8px; margin-bottom: 14px; font-size: 14px; }

.item-list { display: flex; flex-direction: column; gap: 12px; }
.item-card { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 14px; background: #fff; border-radius: 12px; border: 1px solid var(--primary); padding: 16px 20px; }
.item-card.owned { background: #fafff5; }
.item-card.locked { opacity: .68; }
.chain-line { position: absolute; left: 34px; top: -13px; width: 2px; height: 13px; background: #d9e2ec; }

.item-main { flex: 1; min-width: 0; }
.item-title-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.item-name { font-size: 16px; font-weight: 800; color: #2c3e50; }
.item-name.owned { color: #52c41a; }
.item-price { font-size: 13px; font-weight: 700; color: #d48806; background: #fff7e6; border-radius: 14px; padding: 2px 12px; }
.item-price:not(.ok) { color: #c2c9d4; background: #f2f4f7; }
.item-desc { margin-top: 6px; color: #8e9aaf; font-size: 13px; }
.item-state { margin-top: 8px; }
.state-tag { font-size: 12px; padding: 2px 10px; border-radius: 14px; }
.state-tag.owned { color: #52c41a; background: #f6ffed; }
.state-tag.locked { color: #8e9aaf; background: #f2f4f7; }
.state-tag.lack { color: #ad6800; background: #fff7e6; }
.state-tag.ready { color: #52c41a; background: #f6ffed; }

.item-action { flex-shrink: 0; }
.btn-redeem { background: var(--primary); color: #fff; border: none; border-radius: 20px; padding: 9px 26px; font-weight: 700; cursor: pointer; font-size: 14px; }
.btn-redeem:hover:not(:disabled) { background: var(--primary-hover); }
.btn-redeem:disabled { opacity: .45; cursor: not-allowed; }
.owned-badge { color: #52c41a; font-weight: 700; font-size: 14px; }

.empty { text-align: center; color: #999; padding: 48px 0; background: #fff; border-radius: 12px; }
</style>
