/**
 * 统一的登录态存储——令牌的唯一来源（single source of truth）。
 *
 * 为什么需要这个模块（「每隔两三分钟就被退出登录」的根因之一）：
 *
 * 1. 令牌此前有两处写入者：axios 拦截器直接写 localStorage，Pinia store 又通过
 *    `watch()` 把自己那份写回去。store 的副本落后于轮换，会把刚换到的新令牌覆盖成
 *    旧的；下一次刷新拿已作废的令牌去换 → 401 → 整个会话被清空。
 * 2. 刷新一旦失败就调用 `clearAuthAndRedirect()` 清掉全部登录态。多个标签页（或一批
 *    并发请求）同时提交同一个已轮换的 refresh 令牌时，输掉的那一方会把所有人踢下线。
 *
 * 现在所有令牌读写都必须经过本模块，其它地方不得再直接碰这几个 key。
 */

export const ACCESS_KEY = 'accessToken'
export const REFRESH_KEY = 'refreshToken'
export const USER_KEY = 'user'
/** 本地会话起算时间，配合 store 的 30 天滑动 TTL 使用 */
export const PERSISTED_AT_KEY = 'authPersistedAt'
/** access 令牌的失效时刻（Unix ms），仅用于决定「要不要提前刷新」 */
const ACCESS_EXP_KEY = 'gr3yph4ntom.accessExp'

/** 同一时刻只允许一个标签页执行刷新的锁名 */
export const REFRESH_LOCK = 'gr3yph4ntom:refresh'

/** 同页内广播「会话已被清空」，store 借此同步内存状态 */
export const LOGOUT_EVENT = 'gr3yph4ntom:logout'

export interface StoredUser {
  id?: number
  username?: string
  handle?: string
  email?: string | null
  avatar_url?: string | null
  is_admin?: boolean
  is_super_admin?: boolean
  can_manage_users?: boolean
  [key: string]: unknown
}

function storage(): Storage | null {
  try {
    return typeof window !== 'undefined' && window.localStorage ? window.localStorage : null
  } catch {
    // 隐私模式下访问 localStorage 会抛异常
    return null
  }
}

export function getAccessToken(): string {
  return storage()?.getItem(ACCESS_KEY) ?? ''
}

export function getRefreshToken(): string {
  return storage()?.getItem(REFRESH_KEY) ?? ''
}

/**
 * 原子地替换整对令牌。
 *
 * 同时把 access 的 exp 解出来存一份：只用来判断「是否该提前刷新」，
 * 绝不参与「会话是否彻底作废」的决策——那是服务端说了算。
 */
export function setTokens(accessToken: string, refreshToken: string): void {
  const store = storage()
  if (!store) return
  store.setItem(ACCESS_KEY, accessToken)
  store.setItem(REFRESH_KEY, refreshToken)
  store.setItem(PERSISTED_AT_KEY, String(Date.now()))
  const exp = readJwtExpiry(accessToken)
  if (exp) store.setItem(ACCESS_EXP_KEY, String(exp))
  else store.removeItem(ACCESS_EXP_KEY)
}

/** 清空登录态；`notify` 用于同页内其它订阅者（Pinia store）同步内存状态 */
export function clearSession(notify = true): void {
  const store = storage()
  if (!store) return
  store.removeItem(ACCESS_KEY)
  store.removeItem(REFRESH_KEY)
  store.removeItem(ACCESS_EXP_KEY)
  store.removeItem(PERSISTED_AT_KEY)
  store.removeItem(USER_KEY)
  try {
    window.sessionStorage.removeItem(USER_KEY)
  } catch {
    /* 忽略：sessionStorage 可能被禁用 */
  }
  if (notify) {
    try {
      window.dispatchEvent(new Event(LOGOUT_EVENT))
    } catch {
      /* 非浏览器环境 */
    }
  }
}

/** access 令牌是否已知过期（未知一律返回 false，交给拦截器按 401 处理） */
export function accessTokenExpired(): boolean {
  const raw = storage()?.getItem(ACCESS_EXP_KEY)
  const exp = raw ? Number(raw) : 0
  return exp > 0 && Date.now() >= exp * 1000
}

/** 本地是否还留有可用的登录凭据 */
export function hasSession(): boolean {
  return Boolean(getRefreshToken() || getAccessToken())
}

/** 本地会话的起算时间（Unix ms），0 表示从未登录过 */
export function getPersistedAt(): number {
  const raw = storage()?.getItem(PERSISTED_AT_KEY)
  const value = raw ? Number(raw) : 0
  return Number.isFinite(value) ? value : 0
}

export function getUser(): StoredUser | null {
  const raw = storage()?.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as StoredUser
  } catch {
    return null
  }
}

export function setUser(user: StoredUser | null): void {
  const store = storage()
  if (!store) return
  if (user) store.setItem(USER_KEY, JSON.stringify(user))
  else store.removeItem(USER_KEY)
  try {
    if (user) window.sessionStorage.setItem(USER_KEY, JSON.stringify(user))
    else window.sessionStorage.removeItem(USER_KEY)
  } catch {
    /* 隐私模式 */
  }
}

/**
 * 订阅登录态变化。
 *
 * `storage` 事件只在**其它**标签页写入时触发，同页写入要靠手动事件补齐；
 * store 通过它保持内存副本与存储一致，而不必自己承担写回的职责。
 */
export function onSessionChange(handler: () => void): () => void {
  if (typeof window === 'undefined') return () => {}
  const onStorage = (event: StorageEvent) => {
    if (
      event.key === null ||
      event.key === ACCESS_KEY ||
      event.key === REFRESH_KEY ||
      event.key === USER_KEY ||
      event.key === PERSISTED_AT_KEY
    ) {
      handler()
    }
  }
  window.addEventListener('storage', onStorage)
  window.addEventListener(LOGOUT_EVENT, handler)
  return () => {
    window.removeEventListener('storage', onStorage)
    window.removeEventListener(LOGOUT_EVENT, handler)
  }
}

/**
 * 在本源所有标签页之间串行执行 `task`。
 *
 * `navigator.locks` 是唯一能跨标签页、且扛得住整页刷新的同源原语，用它保证
 * 不会有两个标签页同时拿同一个 refresh 令牌去轮换。浏览器不支持时退化为
 * 直接执行——那种情况由服务端的轮换宽限期兜底。
 */
export async function withCrossTabLock<T>(
  name: string,
  task: () => Promise<T>,
  onBusy?: () => Promise<T>,
): Promise<T> {
  const locks = typeof navigator !== 'undefined' ? navigator.locks : undefined
  if (!locks) return task()
  if (onBusy) {
    return locks.request(
      name,
      { mode: 'exclusive', ifAvailable: true } as LockOptions,
      async (lock) => (lock ? task() : onBusy()),
    )
  }
  return locks.request(name, { mode: 'exclusive' } as LockOptions, () => task())
}

/** 解 JWT 的 exp（不验签，只读本地已有的令牌内容） */
function readJwtExpiry(token: string): number {
  try {
    const payload = token.split('.')[1]
    if (!payload) return 0
    const json = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
    return typeof json?.exp === 'number' ? json.exp : 0
  } catch {
    return 0
  }
}
