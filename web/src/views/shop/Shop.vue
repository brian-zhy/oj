<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

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

// 双商店：经验（刷题）/ 贡献（出题），同一套 Tag 卡链式解锁玩法。
// tab 即路由（/shop 与 /shop/contribution），刷新/分享链接不丢状态
type Tab = 'exp' | 'contribution'
const tab = computed<Tab>(() =>
  route.path.endsWith('/contribution') ? 'contribution' : 'exp')
const switchTab = (t: Tab) => {
  if (t === tab.value) return
  actionMsg.value = ''
  router.push(t === 'contribution' ? '/shop/contribution' : '/shop')
}
const experience = ref(0)
const contribution = ref(0)
const expItems = ref<ShopItem[]>([])
const contribItems = ref<ShopItem[]>([])
const loading = ref(true)
const error = ref('')
const actingId = ref<number | null>(null)
const actionMsg = ref('')

const currencyLabel = computed(() => (tab.value === 'exp' ? '经验' : '贡献'))
const balance = computed(() => (tab.value === 'exp' ? experience.value : contribution.value))
const currentItems = computed(() => (tab.value === 'exp' ? expItems.value : contribItems.value))

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    // 响应拦截器已解包一层：返回值就是 data 本身（类型标注沿用 any）
    const [exp, contrib] = (await Promise.all([
      apiClient.get('/api/shop/items'),
      apiClient.get('/api/shop/contribution/items'),
    ])) as any[]
    experience.value = exp.experience
    expItems.value = exp.items
    contribution.value = contrib.contribution
    contribItems.value = contrib.items
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const redeemEndpoint = () => (tab.value === 'exp' ? '/api/shop/redeem' : '/api/shop/contribution/redeem')

const redeem = async (item: ShopItem) => {
  if (!item.can_redeem) return
  if (!confirm(`确定花费 ${item.price} ${currencyLabel.value}兑换「${item.name}」吗？兑换后自动佩戴。`)) return
  actingId.value = item.id
  actionMsg.value = ''
  try {
    const res: any = await apiClient.post(redeemEndpoint(), { item_id: item.id })
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
  <div class="shop-page" :class="{ contrib: tab === 'contribution' }">
    <div class="shop-container">
      <div class="shop-head card">
        <div>
          <h2 class="page-title">{{ tab === 'exp' ? '经验商店' : '贡献商店' }}</h2>
          <p class="page-sub">
            {{ tab === 'exp'
              ? '用刷题攒下的经验兑换专属称号——每件商品都需要持有前一件才能兑换'
              : '用出题攒下的贡献兑换专属称号——题目难度越高，出题人获得的贡献越多' }}
          </p>
          <div class="shop-tabs">
            <button class="shop-tab" :class="{ active: tab === 'exp' }" @click="switchTab('exp')">经验商店</button>
            <button class="shop-tab" :class="{ active: tab === 'contribution' }" @click="switchTab('contribution')">贡献商店</button>
          </div>
        </div>
        <div class="exp-box">
          <div class="exp-label">我的{{ currencyLabel }}</div>
          <div class="exp-value">{{ balance }}</div>
        </div>
      </div>

      <div v-if="actionMsg" class="action-msg">{{ actionMsg }}</div>

      <div v-if="loading" class="empty">加载中...</div>
      <div v-else-if="error" class="empty">{{ error }}</div>

      <div v-else class="item-list">
        <div
          v-for="(item, i) in currentItems"
          :key="item.id"
          class="item-card"
          :class="{ owned: item.owned, locked: !item.prev_owned }"
        >
          <div class="chain-line" v-if="i > 0" />
          <div class="item-main">
            <div class="item-title-row">
              <span class="item-name" :class="{ owned: item.owned }">{{ item.name }}</span>
              <span class="item-price" :class="{ ok: item.enough_exp }">✦ {{ item.price }} {{ currencyLabel }}</span>
            </div>
            <div class="item-desc">{{ item.desc }}</div>
            <div class="item-state">
              <span v-if="item.owned" class="state-tag owned">已拥有</span>
              <span v-else-if="item.locked_by" class="state-tag locked">需要前置：{{ item.locked_by }}</span>
              <span v-else-if="!item.enough_exp" class="state-tag lack">
                {{ currencyLabel }}不足（还差 {{ item.price - balance }}）
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

.shop-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px; background: #fff; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 20px 26px; margin-bottom: 16px; }
.page-title { color: var(--primary); font-size: 22px; margin: 0; }
.contrib .page-title { color: #27ae60; }
.page-sub { color: #8e9aaf; font-size: 13px; margin: 6px 0 0; }
.exp-box { text-align: center; background: #fff7e6; border: 1px solid #ffe7ba; border-radius: 12px; padding: 10px 26px; }
.exp-label { font-size: 12px; color: #ad6800; }
.exp-value { font-size: 26px; font-weight: 800; color: #d48806; }
.contrib .exp-box { background: #f0faf4; border-color: #cdebd6; }
.contrib .exp-label { color: #1d7a46; }
.contrib .exp-value { color: #27ae60; }

.shop-tabs { display: flex; gap: 8px; margin-top: 14px; }
.shop-tab { border: 1px solid #e2e6ee; background: #fff; color: #66708c; border-radius: 20px; padding: 7px 22px; font-size: 14px; font-weight: 700; cursor: pointer; }
.shop-tab.active { background: var(--primary); border-color: var(--primary); color: #fff; }
.contrib .shop-tab.active { background: #27ae60; border-color: #27ae60; }

.action-msg { background: #eafaf1; color: #27ae60; padding: 10px 16px; border-radius: 8px; margin-bottom: 14px; font-size: 14px; }

.item-list { display: flex; flex-direction: column; gap: 12px; }
.item-card { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 14px; background: #fff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.05); padding: 16px 20px; }
.item-card.owned { background: #fafff5; }
.item-card.locked { opacity: .68; }
.chain-line { position: absolute; left: 34px; top: -13px; width: 2px; height: 13px; background: #d9e2ec; }

.item-main { flex: 1; min-width: 0; }
.item-title-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.item-name { font-size: 16px; font-weight: 800; color: #2c3e50; }
.item-name.owned { color: #52c41a; }
.item-price { font-size: 13px; font-weight: 700; color: #d48806; background: #fff7e6; border-radius: 14px; padding: 2px 12px; }
.item-price:not(.ok) { color: #c2c9d4; background: #f2f4f7; }
.contrib .item-price { color: #27ae60; background: #f0faf4; }
.contrib .item-price:not(.ok) { color: #c2c9d4; background: #f2f4f7; }
.item-desc { margin-top: 6px; color: #8e9aaf; font-size: 13px; }
.item-state { margin-top: 8px; }
.state-tag { font-size: 12px; padding: 2px 10px; border-radius: 14px; }
.state-tag.owned { color: #52c41a; background: #f6ffed; }
.state-tag.locked { color: #8e9aaf; background: #f2f4f7; }
.state-tag.lack { color: #ad6800; background: #fff7e6; }
.state-tag.ready { color: #52c41a; background: #f6ffed; }

.item-action { flex-shrink: 0; }
.btn-redeem { background: var(--primary); color: #fff; border: none; border-radius: 20px; padding: 9px 26px; font-weight: 700; cursor: pointer; font-size: 14px; }
.contrib .btn-redeem { background: #27ae60; }
.btn-redeem:hover:not(:disabled) { background: var(--primary-hover); }
.contrib .btn-redeem:hover:not(:disabled) { background: #219a52; }
.btn-redeem:disabled { opacity: .45; cursor: not-allowed; }
.owned-badge { color: #52c41a; font-weight: 700; font-size: 14px; }

.empty { text-align: center; color: #999; padding: 48px 0; background: #fff; border-radius: 12px; }
</style>
