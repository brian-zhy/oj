export const USER_ONLINE_THRESHOLD_MS = 60_000

let lastPresencePingAt = 0
let heartbeatTimer: number | undefined
let visibilityHandler: (() => void) | undefined

export function isUserOnline(
  user?: { last_seen?: string | Date | null } | null,
  thresholdMs = USER_ONLINE_THRESHOLD_MS,
): boolean {
  if (!user?.last_seen) return false

  const timestamp = new Date(user.last_seen).getTime()
  if (Number.isNaN(timestamp)) return false

  return Date.now() - timestamp <= thresholdMs
}

export async function pingUserPresence(): Promise<boolean> {
  const accessToken = localStorage.getItem('accessToken')
  if (!accessToken) return false

  const now = Date.now()
  if (now - lastPresencePingAt < 30_000) return true
  lastPresencePingAt = now

  try {
    await fetch('/users/me/seen', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    })
    return true
  } catch {
    return false
  }
}

export function startPresenceHeartbeat(): void {
  if (heartbeatTimer) return

  void pingUserPresence()
  heartbeatTimer = window.setInterval(() => {
    if (document.visibilityState === 'visible') {
      void pingUserPresence()
    }
  }, 30_000)

  visibilityHandler = () => {
    if (!document.hidden) void pingUserPresence()
  }
  document.addEventListener('visibilitychange', visibilityHandler)
}

export function stopPresenceHeartbeat(): void {
  if (heartbeatTimer) {
    window.clearInterval(heartbeatTimer)
    heartbeatTimer = undefined
  }
  if (visibilityHandler) {
    document.removeEventListener('visibilitychange', visibilityHandler)
    visibilityHandler = undefined
  }
}
