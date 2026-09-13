import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import './style.css'
import './assets/markdown.css'
import 'sweetalert2/dist/sweetalert2.min.css'
import App from './App.vue'
import { useAuthStore } from './stores/auth'
import { installCodeCopy } from './utils/codeCopy'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 恢复认证状态
const authStore = useAuthStore()
authStore.restoreState()

// 切回标签页时静默同步最新权限（60 秒节流）：
// 管理员改完权限，用户切回来即生效，无需刷新
let lastPermissionSync = 0
window.addEventListener('focus', () => {
  const now = Date.now()
  if (now - lastPermissionSync < 60_000) return
  lastPermissionSync = now
  if (authStore.isAuthenticated) authStore.syncCurrentUser()
})

// 代码块复制按钮：全局事件委托（v-html 插入的内容无法绑定 Vue 事件）
installCodeCopy()

app.mount('#app')
