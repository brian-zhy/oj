<template>
  <div class="admin-page-wrapper">
    <!-- 直接使用原HTML的div结构 -->
    <div ref="adminContainer" class="admin-container" v-html="originalHTML"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const adminContainer = ref<HTMLElement>()
const originalHTML = ref('')

onMounted(async () => {
  // 检查管理员权限
  const user = authStore.currentUser
  if (!user || !user.can_manage_users) {
    alert('您没有访问管理后台的权限')
    window.location.href = '/'
    return
  }

  try {
    // 动态导入原HTML文件内容
    const htmlModule = await import('./UserManagement.html?raw')
    originalHTML.value = htmlModule.default

    // 等待DOM更新后注入脚本
    setTimeout(() => {
      injectScripts()
      setupEventListeners()
    }, 100)
  } catch (error) {
    console.error('加载管理后台失败:', error)
  }
})

function injectScripts() {
  if (!adminContainer.value) return

  // 注入认证信息到全局
  window.__AUTH_INFO__ = {
    accessToken: localStorage.getItem('accessToken') || '',
    refreshToken: localStorage.getItem('refreshToken') || '',
    apiUrl: import.meta.env.VITE_API_BASE_URL || '',
    currentUser: authStore.currentUser
  }

  // 注入适配器脚本
  const adapterScript = document.createElement('script')
  adapterScript.type = 'module'
  adapterScript.textContent = `
    // Supabase适配器代码
    ${getSupabaseAdapterCode()}
  `
  document.head.appendChild(adapterScript)

  // 初始化原页面中的脚本
  const scripts = adminContainer.value.querySelectorAll('script')
  scripts.forEach(script => {
    const newScript = document.createElement('script')
    Array.from(script.attributes).forEach(attr => {
      newScript.setAttribute(attr.name, attr.value)
    })
    newScript.textContent = script.textContent
    script.parentNode?.replaceChild(newScript, script)
  })
}

function setupEventListeners() {
  // 设置与原页面的通信
  window.addEventListener('message', handleFrameMessage)
}

function handleFrameMessage(event: MessageEvent) {
  // 处理来自适配器的消息
  if (event.data.type === 'API_CALL') {
    handleApiCall(event.data)
  }
}

async function handleApiCall(message: any) {
  const { endpoint, method, data, callbackId } = message

  try {
    const response = await fetch(endpoint, {
      method: method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
      },
      body: data ? JSON.stringify(data) : undefined
    })

    const result = await response.json()

    // 发送结果回适配器
    window.postMessage({
      type: 'API_RESPONSE',
      callbackId,
      result
    }, '*')
  } catch (error) {
    window.postMessage({
      type: 'API_RESPONSE',
      callbackId,
      error: error.message
    }, '*')
  }
}

function getSupabaseAdapterCode() {
  return `
    // Supabase适配器
    class SupabaseAdapter {
      constructor() {
        this.auth = new AuthAdapter()
      }

      from(table) {
        return new QueryBuilder(table)
      }

      channel(channelName) {
        return new ChannelAdapter(channelName)
      }
    }

    class QueryBuilder {
      constructor(table) {
        this.table = table
        this.filters = []
      }

      select(columns) {
        this.columns = columns
        return this
      }

      eq(field, value) {
        this.filters.push({ field, value })
        return this
      }

      async single() {
        try {
          const response = await fetch('/auth/me', {
            headers: {
              'Authorization': 'Bearer ' + window.__AUTH_INFO__.accessToken,
              'Content-Type': 'application/json'
            }
          })

          if (!response.ok) throw new Error('获取用户信息失败')

          const data = await response.json()
          return { data, error: null }
        } catch (error) {
          return { data: null, error }
        }
      }

      async execute() {
        try {
          const params = new URLSearchParams()
          this.filters.forEach(filter => {
            params.append('search', filter.value)
          })

          const response = await fetch('/admin/users?' + params, {
            headers: {
              'Authorization': 'Bearer ' + window.__AUTH_INFO__.accessToken,
              'Content-Type': 'application/json'
            }
          })

          if (!response.ok) throw new Error('获取用户列表失败')

          const data = await response.json()
          return { data: data.data || data, error: null }
        } catch (error) {
          return { data: [], error }
        }
      }
    }

    class AuthAdapter {
      async getSession() {
        try {
          if (!window.__AUTH_INFO__.accessToken) {
            return { data: { session: null }, error: null }
          }

          const response = await fetch('/auth/me', {
            headers: {
              'Authorization': 'Bearer ' + window.__AUTH_INFO__.accessToken,
              'Content-Type': 'application/json'
            }
          })

          if (response.ok) {
            const userData = await response.json()
            return {
              data: {
                session: {
                  user: {
                    id: userData.id.toString(),
                    email: userData.email,
                    aud: 'authenticated'
                  },
                  expires_at: Date.now() + 30 * 60 * 1000
                }
              },
              error: null
            }
          }

          return { data: { session: null }, error: null }
        } catch (error) {
          return { data: { session: null }, error }
        }
      }

      async signOut() {
        window.__AUTH_INFO__.accessToken = ''
        window.__AUTH_INFO__.refreshToken = ''
        localStorage.removeItem('accessToken')
        localStorage.removeItem('refreshToken')
        localStorage.removeItem('user')
        window.location.href = '/login'
        return { error: null }
      }
    }

    class ChannelAdapter {
      constructor(channelName) {
        this.channelName = channelName
        this.subscribeInterval = null
      }

      on(event, callback) {
        if (event === 'postgres_changes') {
          this.subscribeInterval = setInterval(async () => {
            try {
              const response = await fetch('/admin/users/online', {
                headers: { 'Authorization': 'Bearer ' + window.__AUTH_INFO__.accessToken }
              })

              if (response.ok) {
                const result = await response.json()
                callback({ payload: { onlineUsers: result.online_users } })
              }
            } catch (error) {
              console.error('轮询在线用户失败:', error)
            }
          }, 30000)
        }
        return this
      }

      subscribe() {
        return { unsubscribe: () => {
          if (this.subscribeInterval) {
            clearInterval(this.subscribeInterval)
          }
        }}
      }
    }

    // 创建全局supabase对象
    window.supabase = {
      createClient: () => new SupabaseAdapter()
    }
  `
}

onUnmounted(() => {
  window.removeEventListener('message', handleFrameMessage)
})
</script>

<style scoped>
.admin-page-wrapper {
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.admin-container {
  width: 100%;
  height: 100%;
  overflow: auto;
}

/* 保持原HTML的所有样式 */
.admin-container :deep(*) {
  all: revert;
}
</style>