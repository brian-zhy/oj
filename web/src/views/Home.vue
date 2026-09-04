<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const authStore = useAuthStore()

const isLoggedIn = computed(() => authStore.isAuthenticated)
const currentUser = computed(() => authStore.currentUser)

// ==================== 通用工具 ====================

const COLOR_RED = '#e74c3c'
const COLOR_PURPLE = '#9C3DCF'
const COLOR_BROWN = '#AD8B00'

// 获取用户显示颜色
const getUserDisplayColor = (user: any) => {
  if (user?.is_cheater) return COLOR_BROWN
  if (user?.is_admin) return COLOR_PURPLE
  return COLOR_RED
}

// 获取用户标签显示
const getUserTagDisplay = (user: any) => {
  if (!user) return ''
  if (user.is_cheater) {
    return user.is_admin ? (user.user_tag || '管理员') : '作弊者'
  }
  return user.user_tag || ''
}

// 生成字母头像
const letterAvatar = (name: string) => {
  const ch = (name || 'U').trim().charAt(0).toUpperCase() || 'U'
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(ch)}%3C/text%3E%3C/svg%3E`
}

const getUserAvatar = (item: any) => {
  return item.avatar_url || letterAvatar(item.username)
}

// 富文本渲染（Markdown + LaTeX 公式）
import { renderRichText as renderMarkdown } from '@/utils/markdown'

// ==================== 打卡（纯前端，localStorage 存储） ====================

const PUNCH_KEY = 'oj_punch_records'

// 读取本地打卡记录
const readPunchRecords = (): Record<string, boolean> => {
  try {
    return JSON.parse(localStorage.getItem(PUNCH_KEY) || '{}')
  } catch {
    return {}
  }
}

// 随机种子（splitmix32）
function splitmix32(seed: number) {
  seed = seed >>> 0
  return function () {
    seed = (seed + 0x9E3779B9) >>> 0
    let z = seed
    z = ((z ^ (z >>> 16)) * 0x85EBCA6B) >>> 0
    z = ((z ^ (z >>> 13)) * 0xC2B2AE35) >>> 0
    z = (z ^ (z >>> 16)) >>> 0
    return (z >>> 0) / 4294967296
  }
}

function getDailySeed(userId: string) {
  const today = getTodayDateStr()
  const base = String(userId || 'anonymous')
  const salt = '✨NLNOJ🏮'
  const combined = base + today + salt
  let hash = 5381
  for (let i = 0; i < combined.length; i++) {
    hash = ((hash << 5) + hash) + combined.charCodeAt(i)
    hash |= 0
  }
  const dateNum = parseInt(today.replace(/-/g, ''))
  hash = ((hash >>> 0) ^ dateNum * 2654435761) >>> 0
  return Math.abs(hash) >>> 0
}

function getDeviceId() {
  let id = localStorage.getItem('device_id')
  if (!id) {
    id = 'dev_' + Math.random().toString(36).slice(2, 10)
    localStorage.setItem('device_id', id)
  }
  return id
}

// 日期工具（时区为东八区）
function getTodayDateStr() {
  const now = new Date()
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(now)
}

const getChineseWeekday = (date: Date) => {
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  return weekdays[date.getDay()]
}

const getMonthSize = (date: Date) => {
  const year = date.getFullYear()
  const month = date.getMonth()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  return daysInMonth >= 30 ? '大' : '小'
}

const getMonthChinese = (date: Date) => {
  const months = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']
  return months[date.getMonth()] + '月'
}

const daysUntil = (targetDate: Date) => {
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const target = new Date(targetDate)
  target.setHours(0, 0, 0, 0)
  const diff = target.getTime() - now.getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

// 当前时间（每分钟刷新一次，保证跨天正确）
const now = ref(new Date())
let clockTimer: number | null = null

const dayStr = computed(() => String(now.value.getDate()).padStart(2, '0'))
const weekday = computed(() => getChineseWeekday(now.value))
const monthChineseFull = computed(() => getMonthChinese(now.value) + getMonthSize(now.value))
const cspDays1 = computed(() => daysUntil(new Date(2026, 8, 18)))
const cspDays2 = computed(() => daysUntil(new Date(2026, 9, 30)))

// 打卡记录写入localStorage（非响应式），用它触发依赖打卡数据的computed重新求值
const punchVersion = ref(0)

// 今日是否已打卡
const checkedInToday = computed(() => {
  void punchVersion.value
  return !!readPunchRecords()[getTodayDateStr()]
})

// 连续打卡天数
const streakDays = computed(() => {
  void punchVersion.value
  const punchDates = new Set(Object.keys(readPunchRecords()))
  let streak = 0
  const checkDate = new Date(getTodayDateStr() + 'T00:00:00+08:00')
  while (true) {
    const year = checkDate.getFullYear()
    const month = String(checkDate.getMonth() + 1).padStart(2, '0')
    const day = String(checkDate.getDate()).padStart(2, '0')
    const dateStr = `${year}-${month}-${day}`
    if (punchDates.has(dateStr)) {
      streak++
      checkDate.setDate(checkDate.getDate() - 1)
    } else {
      break
    }
  }
  return streak
})

// ===== 运势 =====
const ACTIVITIES = [
  { name: '写作文', good: '非常有文采', bad: '不知所云，离题千里' },
  { name: '写洛谷日报', good: '文思泉涌，下笔如有神', bad: '发现还差得远' },
  { name: '放假', good: '自由自在的一个假期', bad: '就放一天，全是作业' },
  { name: '玩网游', good: '犹如神助', bad: '匹配到一群猪队友' },
  { name: '考试', good: '学的全会，蒙的全对', bad: '作弊会被抓' },
  { name: '背诵课文', good: '看一遍就背下来了', bad: '记忆力只有 50 Byte' },
  { name: '交友', good: '友谊地久天长', bad: '交友不慎' },
  { name: '骗分', good: '"不可以，总司令"然后拿一半分', bad: '一分不得' },
  { name: '抽卡', good: '一发入魂', bad: '只有保底' },
  { name: '贴贴', good: '说不定擦出火花', bad: '一定会被拒绝' },
  { name: '出公开赛', good: 'rated，评价很高', bad: '出了原题裸题错题不可做题' },
  { name: '开电脑', good: '电脑的状态也很好', bad: '意外的死机故障不可避' },
  { name: '祭祀', good: '获得祖宗的庇护', bad: '未能得到祖宗保佑' },
  { name: '体育锻炼', good: '身体棒棒哒', bad: '消耗的能量全吃回来了' },
  { name: '网购', good: '买到历史最低价', bad: '正好错过促销' },
  { name: '摸鱼', good: '放松身心', bad: '被教练制裁' },
  { name: '请教问题', good: '获得大佬的解答', bad: '被当作 xxs' },
  { name: '抢最优解', good: '一发就是最优解', bad: '越卡常越慢' },
  { name: '洗澡', good: '洗香香', bad: '小心着凉' },
  { name: '唱歌', good: '成为歌神', bad: '别人唱歌要钱，你要命' },
  { name: '玩我的世界', good: '下界挖到远古遗骸', bad: '转角遇到苦力怕' },
  { name: '熬夜', good: '事情终究可以完成的', bad: '爆肝，通宵干不完' },
  { name: '写暴戾语言', good: '成功发泄', bad: '禁赛一年' },
  { name: '卷题', good: '水平显著提升', bad: '我咋啥都不会' },
  { name: '上洛谷', good: '全方位提升', bad: '你谷日爆' },
  { name: '出行', good: '一路顺风', bad: '路途也许坎坷' },
  { name: '点外卖', good: '及时送到', bad: '一直没有送到还不给退款' },
  { name: '写题解', good: '一遍通过审核', bad: '连续提交不符合要求' },
  { name: '学新算法', good: '看一遍就懂了', bad: '怎么也学不会' },
  { name: '重构代码', good: '代码质量明显提高', bad: '越改越乱' },
  { name: '继续完成 WA 的题', good: '下一次就 AC', bad: '然而变成了 TLE' },
  { name: '打线上公开赛', good: '涨很多 rating', bad: '掉大分' },
  { name: '参加模拟赛', good: '可以 AK 虐全场', bad: '注意爆零' },
  { name: '水讨论区', good: '看到有趣的事情', bad: '和其他人激情对线' },
  { name: '写作业', good: '都会写，写的全对', bad: '上课讲了这些了吗' },
  { name: '装弱', good: '谦虚最好了', bad: '被看穿' },
  { name: '看视频网站', good: '愉悦身心', bad: '会被教练看见' },
  { name: '刷题', good: '成为虐题狂魔', bad: '容易 WA' },
  { name: '装逼', good: '获得众人敬仰', bad: '被识破' },
  { name: '睡觉', good: '养足精力，明日再战', bad: '翻来覆去睡不着' },
  { name: '切水题', good: '通过数猛涨', bad: '被抓抄题解' },
  { name: '膜拜大神', good: '接受神犇光环照耀', bad: '被大神鄙视' },
  { name: '吃饭', good: '人是铁饭是钢', bad: '小心变胖啊' },
  { name: '上厕所', good: '想出了题目的解法', bad: '被机房惨案' },
  { name: '打东方', good: 'All clear！', bad: '满身疮痍' },
  { name: '造数据', good: '严谨数据，经久耐用', bad: '数据出锅，当众谢罪' },
  { name: '纳财', good: '要到好多 Money', bad: '然而今天并没有财运' },
  { name: '去食堂', good: '给了双倍的量', bad: '爱吃的菜刚被打完' },
  { name: '上课', good: '100% 消化', bad: '反正你听不懂' },
  { name: '发朋友圈', good: '分享是种美德', bad: '会被当做卖面膜的' },
  { name: '扶老奶奶过马路', good: '增加 RP', bad: '会被讹' },
  { name: '水工单', good: '与他人友好交流', bad: '这工单是人吗' },
  { name: '发工单', good: '被成功采纳', bad: '喜提禁言' },
  { name: '举报', good: '被举报的人遭受正义制裁', bad: '被管理驳回' },
  { name: '看电视', good: '有你最喜欢的节目', bad: '电视瘫痪' },
  { name: '猜猜犇', good: '都认识', bad: '都不认识' },
  { name: '打牌', good: '一手好牌，大获全胜', bad: '一手烂牌，一败涂地' },
  { name: '看医生', good: '医生治好了你的病', bad: '医生也看不出来你哪里有病' }
]

const FORTUNE_LEVELS = [
  { label: '大吉', cls: 'good' },
  { label: '中吉', cls: 'good' },
  { label: '小吉', cls: 'good' },
  { label: '中平', cls: 'bad' },
  { label: '凶', cls: 'terrible' },
  { label: '大凶', cls: 'terrible' }
]

// 计算今日运势（纯前端种子算法）
const dailyFortune = computed(() => {
  if (!checkedInToday.value) return null
  const userIdSeed = isLoggedIn.value ? String(currentUser.value?.user_number || '') : getDeviceId()
  const rand = splitmix32(getDailySeed(userIdSeed))
  const fortuneIdx = Math.floor(rand() * FORTUNE_LEVELS.length)
  const fortune = FORTUNE_LEVELS[fortuneIdx]
  const shuffled = [...ACTIVITIES]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  const picked = shuffled.slice(0, 4)
  const goodItems = picked.slice(0, 2).map(a => ({ name: a.name, desc: a.good }))
  const badItems = picked.slice(2, 4).map(a => ({ name: a.name, desc: a.bad }))
  return { label: fortune.label, cls: fortune.cls, goodItems, badItems }
})

const fortuneLabel = computed(() => dailyFortune.value?.label || '')
const fortuneClass = computed(() => {
  const cls = dailyFortune.value?.cls
  if (cls === 'good') return 'lg-fg-red'
  if (cls === 'bad') return 'lg-fg-green'
  if (cls === 'terrible') return 'lg-fg-black'
  return 'lg-fg-green'
})
const fortuneColor = computed(() => {
  const cls = dailyFortune.value?.cls
  if (cls === 'good') return '#E74C3C'
  if (cls === 'bad') return '#5EB95E'
  if (cls === 'terrible') return '#000000'
  return '#5EB95E'
})
const fortuneGoodItems = computed(() =>
  dailyFortune.value?.label === '大凶' ? [] : (dailyFortune.value?.goodItems || [])
)
const fortuneBadItems = computed(() =>
  dailyFortune.value?.label === '大吉' ? [] : (dailyFortune.value?.badItems || [])
)

// 点击打卡
const doPunch = () => {
  if (!isLoggedIn.value) {
    router.push('/login')
    return
  }
  const today = getTodayDateStr()
  const records = readPunchRecords()
  if (records[today]) return
  records[today] = true
  localStorage.setItem(PUNCH_KEY, JSON.stringify(records))
  punchVersion.value++
}

// 当前用户的展示信息
const meColor = computed(() => getUserDisplayColor(currentUser.value))
const meTag = computed(() => getUserTagDisplay(currentUser.value))

// ==================== 近期讨论 ====================
const recentPosts = ref<any[]>([])
const recentLoading = ref(false)

const relTime = (iso: string) => {
  if (!iso) return ''
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 172800000) return `${Math.floor(diff / 86400)} 天前`
  return new Date(iso).toLocaleDateString('zh-CN')
}

const loadRecentPosts = async () => {
  recentLoading.value = true
  try {
    const data: any = await apiClient.get('/api/forum/recent?limit=10')
    recentPosts.value = Array.isArray(data) ? data : []
  } catch {
    recentPosts.value = []
  } finally {
    recentLoading.value = false
  }
}

// ==================== 犇犇模块 ====================

const MAX_LENGTH = 227 // 普通用户最大字数限制

const benbenContent = ref('')
const benbenList = ref<any[]>([])
const feedMode = ref<'all' | 'my'>('all')
const isLoading = ref(false)
const hasMore = ref(true)
const lastId = ref<number | null>(null)
const currentReplyingId = ref<number | null>(null)
const currentReplyUsername = ref<string | null>(null)

// 加载状态文案（对应原站 loadingSentinel）
const sentinelText = ref('')
const sentinelVisible = ref(true)

const benbenTextareaRef = ref<HTMLTextAreaElement | null>(null)
const loadingSentinelRef = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

// 是否被禁言
const cannotSpeak = computed(() => currentUser.value?.can_speak === false)

// 更新加载指示文案
const updateSentinel = () => {
  // 列表为空时：空状态由 benben-empty 呈现，sentinel 仅在出错时显示错误信息
  if (benbenList.value.length === 0) {
    sentinelVisible.value = sentinelText.value === '加载出错，请刷新'
    return
  }
  if (!hasMore.value) {
    sentinelText.value = '没有更多动态了'
    sentinelVisible.value = true
  } else if (isLoading.value) {
    sentinelText.value = '加载中...'
    sentinelVisible.value = true
  } else {
    sentinelText.value = '滚动加载更多...'
    sentinelVisible.value = true
  }
}

// 时间格式化（与原站一致的完整时间）
const formatTime = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 切换犇犇标签页
const switchTab = (mode: 'all' | 'my') => {
  feedMode.value = mode
  currentReplyingId.value = null
  currentReplyUsername.value = null
  loadBenbenList(true)
}

// 发布犇犇
const postBenben = async () => {
  const content = benbenContent.value.trim()
  if (!content) {
    alert('内容不能为空')
    return
  }

  if (!currentUser.value) {
    router.push('/login')
    return
  }

  if (cannotSpeak.value) {
    alert('你已被禁言，无法发布犇犇')
    return
  }

  // 校验回复前缀，决定 reply_to
  let finalReplyToId: number | null = null
  if (currentReplyingId.value && currentReplyUsername.value) {
    const trimmed = content.trimStart()
    const prefix = `|| @${currentReplyUsername.value} :`
    if (trimmed.startsWith(prefix)) {
      finalReplyToId = currentReplyingId.value
    } else {
      currentReplyingId.value = null
      currentReplyUsername.value = null
    }
  }

  const finalContent = currentUser.value.is_admin ? content : content.substring(0, MAX_LENGTH)

  try {
    await apiClient.post('/benben', {
      content: finalContent,
      ...(finalReplyToId ? { reply_to: finalReplyToId } : {})
    })

    benbenContent.value = ''
    currentReplyingId.value = null
    currentReplyUsername.value = null
    await loadBenbenList(true)
  } catch (error: any) {
    console.error('发布失败:', error)
    const errorMessage = error.response?.data?.detail || error.message || '未知错误'
    alert('发布失败：' + errorMessage)
  }
}

// 删除犇犇
const deleteBenben = async (id: number) => {
  try {
    await apiClient.delete(`/benben/${id}`)
    await loadBenbenList(true)
  } catch (error: any) {
    console.error(error)
    alert('删除失败：' + (error.response?.data?.detail || error.message || '未知错误'))
  }
}

// 回复犇犇
const replyToBenben = (item: any) => {
  currentReplyingId.value = item.id
  currentReplyUsername.value = item.username
  const replyText = ` || @${item.username} : ${item.content}`
  benbenContent.value = replyText

  nextTick(() => {
    const textarea = benbenTextareaRef.value
    if (textarea) {
      textarea.focus()
      // 将光标移动到文本开头
      textarea.setSelectionRange(0, 0)
      textarea.scrollTop = 0
    }
  })
}

// 举报（占位，与原站一致）
const reportBenben = () => {
  alert('举报功能暂未开放，请联系管理员。')
}

// 加载犇犇列表
const loadBenbenList = async (reset = true) => {
  if (isLoading.value) return

  // 未登录用户不加载动态列表
  if (!isLoggedIn.value) {
    isLoading.value = false
    hasMore.value = false
    updateSentinel()
    return
  }

  if (reset) {
    hasMore.value = true
    lastId.value = null
    benbenList.value = []
    sentinelText.value = '加载中...'
    sentinelVisible.value = true
  }

  if (!hasMore.value) {
    updateSentinel()
    return
  }

  isLoading.value = true
  sentinelText.value = '加载中...'
  sentinelVisible.value = true

  try {
    let url = `/benben?limit=20`
    if (lastId.value) url += `&before_id=${lastId.value}`
    if (feedMode.value === 'my') url += '&mode=my'

    // 响应拦截器已解包 response.data
    const data = (await apiClient.get(url)) as any[]

    if (data && data.length > 0) {
      benbenList.value = reset ? data : [...benbenList.value, ...data]
      lastId.value = data[data.length - 1].id

      if (data.length < 20) {
        hasMore.value = false
        sentinelText.value = '没有更多动态了'
      } else {
        hasMore.value = true
        sentinelText.value = '滚动加载更多...'
      }
    } else {
      hasMore.value = false
      if (reset) benbenList.value = []
      sentinelText.value = '没有更多动态了'
    }
  } catch (error) {
    console.error(error)
    sentinelText.value = '加载出错，请刷新'
  } finally {
    isLoading.value = false
    updateSentinel()
  }
}

// 回到顶部
const showBackTop = ref(false)
const handleScroll = () => {
  showBackTop.value = window.pageYOffset > 300
}
const backToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// 生命周期
onMounted(async () => {
  window.addEventListener('scroll', handleScroll, { passive: true })
  clockTimer = window.setInterval(() => {
    now.value = new Date()
  }, 60000)
  loadRecentPosts()

  if (isLoggedIn.value) {
    await loadBenbenList(true)

    // 无限滚动监听
    observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !isLoading.value && hasMore.value && isLoggedIn.value) {
        loadBenbenList(false)
      }
    }, { threshold: 0.1 })
    if (loadingSentinelRef.value) observer.observe(loadingSentinelRef.value)
  } else {
    updateSentinel()
  }
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
  if (clockTimer) clearInterval(clockTimer)
  if (observer) observer.disconnect()
})
</script>

<template>
  <div class="home-page">
    <div class="home-container">
      <!-- ===== 打卡卡片 ===== -->
      <div class="card punch-card">
        <div class="lg-punch">
          <!-- 广告轮播位（暂无广告数据） -->
          <div class="ad-col">
            <div class="ad-placeholder">
              <span>没有更多广告了</span>
            </div>
          </div>

          <!-- 打卡/运势面板 -->
          <div class="fortune-col">
            <template v-if="!checkedInToday">
              <p v-if="isLoggedIn" class="welcome-line">
                欢迎回来，<router-link
                  :to="`/user/${currentUser?.user_number}`"
                  class="benben-username"
                  :style="{ color: meColor }"
                >{{ currentUser?.username }}</router-link><span
                  v-if="meTag"
                  class="user-tag-display"
                  :style="{ backgroundColor: meColor }"
                >{{ meTag }}</span>
              </p>

              <div class="lg-index-calendar">
                <div class="lg-punch-left">
                  <span v-for="(ch, i) in monthChineseFull.split('')" :key="'m' + i">{{ ch }}</span>
                </div>
                <span class="lg-punch-big">{{ dayStr }}</span>
                <div class="lg-punch-right">
                  <span v-for="(ch, i) in weekday.split('')" :key="'w' + i">{{ ch }}</span>
                </div>
              </div>

              <div class="lg-small">
                距 <strong>CSP-J/S 2026 第一轮</strong> 还剩 <strong>{{ cspDays1 }} 天</strong><br>
                距 <strong>CSP-J/S 2026 第二轮</strong> 还剩 <strong>{{ cspDays2 }} 天</strong><br>
                <button v-if="isLoggedIn" class="am-btn am-btn-warning" @click.stop="doPunch">点击打卡</button>
              </div>
            </template>

            <template v-else>
              <h2 class="fortune-title">
                <router-link
                  :to="`/user/${currentUser?.user_number}`"
                  class="benben-username"
                  :style="{ color: meColor }"
                >{{ currentUser?.username }}</router-link><span
                  v-if="meTag"
                  class="user-tag-display"
                  :style="{ backgroundColor: meColor }"
                >{{ meTag }}</span> <span class="fortune-title-suffix">的运势</span>
              </h2>

              <div class="fortune-result-wrap">
                <span class="lg-punch-result" :class="fortuneClass" :style="{ color: fortuneColor }">§ {{ fortuneLabel }} §</span>
              </div>

              <!-- 大吉：万事皆宜 -->
              <div v-if="fortuneLabel === '大吉'" class="fortune-grid">
                <div class="fortune-col-item">
                  <div v-for="item in fortuneGoodItems" :key="item.name" class="fortune-entry">
                    <span class="lg-bold fortune-good-label">宜：{{ item.name }}</span><br>
                    <span class="lg-small fortune-desc">{{ item.desc }}</span>
                  </div>
                </div>
                <div class="fortune-col-item">
                  <span class="lg-bold fortune-nothing">万事皆宜</span>
                </div>
              </div>

              <!-- 大凶：诸事不宜 -->
              <div v-else-if="fortuneLabel === '大凶'" class="fortune-grid">
                <div class="fortune-col-item">
                  <span class="lg-bold fortune-nothing-red">诸事不宜</span>
                </div>
                <div class="fortune-col-item">
                  <div v-for="item in fortuneBadItems" :key="item.name" class="fortune-entry">
                    <span class="lg-bold fortune-bad-strong">忌：</span>
                    <span class="fortune-bad-name">{{ item.name }}</span><br>
                    <span class="lg-small fortune-desc">{{ item.desc }}</span>
                  </div>
                </div>
              </div>

              <!-- 其他：宜忌并排 -->
              <div v-else class="fortune-grid">
                <div class="fortune-col-item">
                  <div v-for="item in fortuneGoodItems" :key="item.name" class="fortune-entry">
                    <span class="lg-bold fortune-good-label">宜：{{ item.name }}</span><br>
                    <span class="lg-small fortune-desc">{{ item.desc }}</span>
                  </div>
                </div>
                <div class="fortune-col-item">
                  <div v-for="item in fortuneBadItems" :key="item.name" class="fortune-entry">
                    <span class="lg-bold fortune-bad-name">忌：{{ item.name }}</span><br>
                    <span class="lg-small fortune-desc">{{ item.desc }}</span>
                  </div>
                </div>
              </div>

              <div class="lg-small fortune-days">
                你已经在 <span class="brand-highlight">✨ NLNOJ</span> 连续打卡了 <strong>{{ streakDays }}</strong> 天
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- ===== 近期讨论 ===== -->
      <div class="card recent-posts-card">
        <div class="card-header">近期讨论</div>
        <div class="recent-posts-list">
          <div v-if="recentLoading" class="empty-state">加载中...</div>
          <div v-else-if="recentPosts.length === 0" class="empty-state">没有更多讨论了</div>
          <section
            v-for="p in recentPosts"
            v-else
            :key="p.id"
            class="post-card"
            @click="$router.push(`/discuss/${p.id}`)"
          >
            <div class="post-card-body">
              <div class="post-avatar">
                <img :src="getUserAvatar(p.author)" :alt="p.author?.username"
                  @error="($event.target as HTMLImageElement).src = letterAvatar(p.author?.username)">
              </div>
              <div class="post-info">
                <span class="post-title-link">{{ p.title }}</span>
                <div class="post-meta-line">
                  <div class="post-meta-row1">
                    <span class="post-author-forum">
                      <router-link
                        :to="p.author?.user_number ? `/user/${p.author.user_number}` : '#'"
                        class="benben-username"
                        :style="{ color: getUserDisplayColor(p.author) }"
                        @click.stop
                      >{{ p.author?.username }}</router-link>
                      <span
                        v-if="getUserTagDisplay(p.author)"
                        class="user-tag-display"
                        :style="{ backgroundColor: getUserDisplayColor(p.author) }"
                      >{{ getUserTagDisplay(p.author) }}</span>
                      In <span class="post-forum-name">{{ p.forum_name }}</span>
                    </span>
                  </div>
                  <div class="post-meta-row2">
                    <span class="post-time-reply">{{ relTime(p.created_at) }} {{ p.reply_count }}回复</span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>

      <!-- ===== 犇犇模块 ===== -->
      <div v-if="isLoggedIn" class="card benben-module">
        <div class="benben-header">有什么新鲜事告诉大家</div>

        <div class="benben-editor">
          <textarea
            ref="benbenTextareaRef"
            v-model="benbenContent"
            rows="3"
            :disabled="cannotSpeak"
          ></textarea>
          <div class="benben-submit-btn">
            <button
              class="auth-btn"
              :disabled="cannotSpeak"
              @click="postBenben"
            >
              发射犇犇！
            </button>
          </div>
        </div>

        <div class="benben-nav">
          <div class="benben-tab" :class="{ active: feedMode === 'all' }" @click="switchTab('all')">全部</div>
          <div class="benben-tab" :class="{ active: feedMode === 'my' }" @click="switchTab('my')">我的</div>
        </div>

        <div class="benben-list">
          <div v-if="benbenList.length === 0 && !isLoading" class="benben-empty">
            {{ sentinelText === '加载出错，请刷新' ? sentinelText : '没有更多动态了' }}
          </div>

          <div v-for="item in benbenList" :key="item.id" class="benben-item" :data-id="item.id">
            <div class="benben-avatar">
              <router-link :to="`/user/${item.user_number}`">
                <img
                  :src="getUserAvatar(item)"
                  :alt="item.username"
                  @error="($event.target as HTMLImageElement).src = letterAvatar(item.username)"
                >
              </router-link>
            </div>

            <div class="benben-content">
              <div class="benben-item-header">
                <div class="post-author">
                  <span class="benben-user">
                    <router-link
                      :to="`/user/${item.user_number}`"
                      class="benben-username"
                      :style="{ color: getUserDisplayColor(item) }"
                    >{{ item.username }}</router-link><span
                      v-if="getUserTagDisplay(item)"
                      class="user-tag-display"
                      :style="{ backgroundColor: getUserDisplayColor(item) }"
                    >{{ getUserTagDisplay(item) }}</span>
                  </span>
                  <span class="benben-time">{{ formatTime(item.created_at) }}</span>
                </div>

                <div class="benben-actions">
                  <button class="benben-report-btn" @click="reportBenben()">举报</button>
                  <button class="benben-reply-btn" @click="replyToBenben(item)">回复</button>
                  <button
                    v-if="currentUser?.user_number === item.user_number"
                    class="benben-delete"
                    @click="deleteBenben(item.id)"
                  >删除</button>
                </div>
              </div>

              <div class="benben-text" v-html="renderMarkdown(item.content)"></div>

              <div v-if="item.reply_to_username" class="benben-reply-hint">
                ↩️ 回复了 @{{ item.reply_to_username }}
              </div>
            </div>
          </div>

          <div
            v-show="sentinelVisible"
            ref="loadingSentinelRef"
            class="loading-sentinel"
          >{{ sentinelText }}</div>
        </div>
      </div>
    </div>

    <!-- 回到顶部 -->
    <button v-show="showBackTop" class="back-to-top" title="回到顶部" @click="backToTop">↑</button>
  </div>
</template>

<style scoped>
/* ========== 页面容器 ========== */
.home-page {
  min-height: 100vh;
  line-height: 1.5;
}

.home-container {
  max-width: 1400px;
  margin: 0 auto;
}

/* ========== 卡片 ========== */
.card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  padding: 20px 24px;
  margin-bottom: 24px;
}

.card-header {
  font-size: 1.25rem;
  font-weight: 600;
  border-left: 4px solid #e74c3c;
  padding-left: 12px;
  margin-bottom: 20px;
}

/* ========== 打卡卡片 ========== */
.punch-card {
  padding: 18px 24px 20px;
}

.punch-card .lg-punch {
  text-align: center;
  display: flex;
  gap: 20px;
  align-items: stretch;
}

.punch-card .ad-col {
  flex: 2;
  min-width: 0;
  display: flex;
  align-items: stretch;
}

.punch-card .fortune-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.ad-placeholder {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: #999;
  font-size: 14px;
  min-height: 100px;
  border-radius: 12px;
}

.welcome-line {
  font-weight: 700;
  font-size: 1.2rem;
  margin-bottom: 8px;
}

.lg-index-calendar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 8px 0 12px;
  color: #396A42;
}

.lg-index-calendar .lg-punch-left,
.lg-index-calendar .lg-punch-right {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  font-size: 0.95rem;
  font-weight: 400;
  color: #396A42;
  line-height: 1.3;
}

.lg-index-calendar .lg-punch-big {
  font-size: 5rem;
  font-weight: 700;
  color: #396A42;
  line-height: 1.1;
  letter-spacing: 2px;
}

.lg-small {
  font-size: 0.95rem;
  color: #555;
  line-height: 1.8;
}

.lg-small strong {
  color: #2c3e50;
  font-weight: 700;
}

.am-btn {
  display: inline-block;
  padding: 8px 16px;
  margin-top: 10px;
  font-size: 15px;
  font-weight: normal;
  border: none;
  border-radius: 40px;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
  text-decoration: none;
  color: #fff;
}

.am-btn-warning {
  background: #F37B1D;
}

.am-btn-warning:hover {
  background: #E0690C;
}

.fortune-title {
  margin-bottom: 0;
  font-size: 1.3rem;
  font-weight: 500;
  color: #333;
  text-align: center;
}

.fortune-title-suffix {
  font-weight: bold;
}

.lg-bold {
  font-weight: bold;
}

.fortune-result-wrap {
  text-align: center;
}

.lg-punch-result {
  font-size: 4rem;
  font-weight: bold;
  letter-spacing: 4px;
  padding: 8px 32px;
  border-radius: 30px;
  display: inline-block;
  margin-bottom: 12px;
  line-height: 1.2;
}

.lg-fg-red {
  color: #E74C3C;
}

.lg-fg-green {
  color: #5EB95E;
}

.lg-fg-black {
  color: #000000;
}

.fortune-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 32px;
  margin: 6px 0 10px;
}

.fortune-grid .fortune-col-item {
  flex: 1 1 200px;
  min-width: 140px;
}

.fortune-entry {
  margin-bottom: 10px;
  line-height: 1.5;
}

.fortune-good-label {
  color: #E74C3C;
}

.fortune-desc {
  display: block;
  margin-top: 1px;
  padding-left: 2px;
}

.fortune-nothing {
  color: #000;
  font-size: 1rem;
  line-height: 1.5;
}

.fortune-nothing-red {
  color: #E74C3C;
  font-size: 1rem;
  line-height: 1.5;
}

.fortune-bad-strong {
  color: #000000;
}

.fortune-bad-name {
  color: #000000;
}

.fortune-days {
  text-align: center;
  padding-top: 8px;
  margin-top: 4px;
}

.brand-highlight {
  color: #e74c3c;
  font-weight: 700;
}

/* ========== 近期讨论 ========== */
.recent-posts-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #999;
  font-size: 14px;
  grid-column: 1 / -1;
}

.recent-posts-card .post-card {
  background: #fff;
  border: 1px solid #e8ecf1;
  border-radius: 8px;
  transition: border-color 0.2s, box-shadow 0.2s;
  height: 100%;
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.recent-posts-card .post-card:hover {
  border-color: #f0a08a;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
}

.post-card-body {
  display: flex;
  gap: 14px;
  padding: 14px 16px;
  align-items: center;
}

.post-avatar img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  display: block;
  background: #f0f2f5;
}

.post-avatar {
  flex-shrink: 0;
}

.post-title-link {
  color: #e74c3c;
  font-weight: 600;
  font-size: 14px;
}

.post-card:hover .post-title-link {
  text-decoration: underline;
}

.post-meta-line {
  margin-top: 4px;
  font-size: 13px;
  color: #8a9aa8;
  display: flex;
  flex-direction: column;
  gap: 2px 0;
}

.post-forum-name {
  color: #e74c3c;
}

.post-time-reply strong {
  color: #2c3e50;
}

/* ========== 犇犇模块 ========== */
.benben-header {
  font-size: 1.25rem;
  font-weight: 600;
  border-left: 4px solid #e74c3c;
  padding-left: 12px;
  margin-bottom: 20px;
}

.benben-editor {
  margin-bottom: 20px;
}

.benben-editor textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  font-family: inherit;
}

.benben-editor textarea:focus {
  outline: none;
  border-color: #e74c3c;
}

.benben-submit-btn {
  margin-top: 10px;
}

.auth-btn {
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 30px;
  padding: 6px 20px;
  font-size: 14px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
}

.auth-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.benben-nav {
  display: flex;
  margin: 20px 0 0 0;
  padding: 0;
  list-style: none;
  background: #f8f9fc;
  border-radius: 12px;
  overflow: hidden;
}

.benben-tab {
  flex: 1;
  text-align: center;
  cursor: pointer;
  padding: 12px 16px;
  font-size: 16px;
  font-weight: 500;
  color: #6c7a8e;
  transition: all 0.2s;
  background: #f8f9fc;
  border-bottom: 2px solid transparent;
}

.benben-tab:hover {
  color: #e74c3c;
  background: #f0f2f5;
}

.benben-tab.active {
  color: #e74c3c;
  background: white;
  border-bottom-color: #e74c3c;
}

.benben-list {
  margin-top: 20px;
}

.benben-item {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  position: relative;
}

.benben-avatar {
  flex-shrink: 0;
  width: 40px;
  margin-top: 8px;
}

.benben-avatar a {
  display: block;
}

.benben-avatar img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  background: #f0f2f5;
}

.benben-content {
  flex: 1;
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 16px;
  padding: 8px 16px;
  position: relative;
}

.benben-content::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 16px;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 8px 8px 8px 0;
  border-color: transparent #f0f2f5 transparent transparent;
  z-index: 1;
}

.benben-content::after {
  content: '';
  position: absolute;
  left: -9px;
  top: 16px;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 8px 8px 8px 0;
  border-color: transparent #e9ecef transparent transparent;
  z-index: 0;
}

.benben-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  background: #f0f2f5;
  padding: 6px 12px;
  margin: -12px -16px 12px -16px;
  border-radius: 16px 16px 0 0;
}

.post-author {
  display: flex;
  align-items: center;
  gap: 4px 8px;
  flex-wrap: wrap;
}

.benben-user {
  display: inline-flex;
  align-items: center;
  vertical-align: middle;
}

.benben-username {
  font-weight: bold;
  color: #333;
  text-decoration: none;
  font-size: 14px;
  vertical-align: middle;
}

.benben-username:hover {
  color: #e74c3c;
}

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

.user-tag-display:hover {
  filter: brightness(0.9);
}

.benben-time {
  font-size: 12px;
  color: #999;
}

.benben-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.benben-report-btn,
.benben-reply-btn,
.benben-delete {
  background: none;
  border: none;
  color: #999;
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}

.benben-report-btn:hover,
.benben-reply-btn:hover,
.benben-delete:hover {
  color: #e74c3c;
}

.benben-text {
  word-break: break-word;
}

.benben-text :deep(pre) {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 12px;
  overflow-x: auto;
  margin: 8px 0;
}

.benben-text :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.benben-text :deep(a) {
  color: #e74c3c;
  text-decoration: none;
}

.benben-text :deep(a:hover) {
  text-decoration: underline;
}

.benben-reply-hint {
  margin-top: 12px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 12px;
  color: #6b7280;
}

.benben-empty,
.no-more-message {
  text-align: center;
  padding: 40px;
  color: #999;
  font-size: 14px;
}

.loading-sentinel {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 13px;
}

/* ========== 回到顶部 ========== */
.back-to-top {
  position: fixed;
  bottom: 30px;
  right: 30px;
  background: #e74c3c;
  color: #fff;
  border: none;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  font-size: 24px;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  z-index: 999;
  transition: opacity 0.3s, transform 0.3s;
}

.back-to-top:hover {
  background: #e74c3c;
  transform: scale(1.1);
}

/* ========== 响应式 ========== */
@media (max-width: 700px) {
  .punch-card .lg-punch {
    flex-direction: column;
  }

  .punch-card .ad-col {
    border-bottom: 1px solid #eee;
    padding-bottom: 12px;
    margin-bottom: 12px;
  }

  .punch-card .ad-col,
  .punch-card .fortune-col {
    flex: 1 1 auto;
    min-width: 0;
  }

  .punch-card .lg-punch-result {
    font-size: 2.8rem;
  }
}

@media (max-width: 600px) {
  .recent-posts-list {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .card {
    padding: 16px 18px;
  }

  .benben-item {
    gap: 10px;
  }

  .benben-avatar {
    width: 32px;
    margin-top: 6px;
  }

  .benben-avatar img {
    width: 32px;
    height: 32px;
  }

  .benben-content {
    padding: 6px 12px;
  }

  .benben-item-header {
    padding: 4px 10px;
    margin: -10px -12px 10px -12px;
    flex-direction: column;
    align-items: flex-start;
  }

  .post-author {
    gap: 6px;
  }

  .benben-actions {
    gap: 8px;
  }

  .benben-text {
    font-size: 14px;
  }

  .lg-index-calendar .lg-punch-big {
    font-size: 2rem;
  }

  .lg-small {
    font-size: 0.88rem;
  }

  .am-btn {
    padding: 6px 20px;
    font-size: 14px;
  }

  .back-to-top {
    bottom: 20px;
    right: 20px;
    width: 40px;
    height: 40px;
    font-size: 20px;
  }
}
</style>
