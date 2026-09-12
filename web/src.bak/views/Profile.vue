<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { userProfileApi, type UserProfileUpdate } from '@/api/userProfile'

const router = useRouter()
const authStore = useAuthStore()

// 用户资料表单
const profileForm = ref<UserProfileUpdate>({
  username: '',
  bio: '',
  avatar_url: '',
  user_tag: '',
  username_color: ''
})

// 密码修改表单
const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

// UI状态
const loading = ref(false)
const saving = ref(false)
const passwordSaving = ref(false)
const activeTab = ref('profile')
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const showPasswordForm = ref(false)

// 头像预览
const avatarPreview = computed(() => {
  return profileForm.value.avatar_url || generateAvatar(profileForm.value.username || 'U')
})

// 生成简单头像
const generateAvatar = (name: string) => {
  const initial = name.charAt(0).toUpperCase()
  return `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' fill='%23e74c3c'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='white' font-size='16' font-family='Arial'%3E${encodeURIComponent(initial)}%3C/text%3E%3C/svg%3E`
}

// 格式化日期
const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

// 加载用户资料
const loadProfile = async () => {
  loading.value = true
  try {
    const user = await userProfileApi.getCurrentUser()
    profileForm.value = {
      username: user.username,
      bio: user.bio || '',
      avatar_url: user.avatar_url || '',
      user_tag: user.user_tag || '',
      username_color: user.username_color || ''
    }
  } catch (error: any) {
    showMessage('加载用户资料失败', 'error')
    console.error('Load profile error:', error)
  } finally {
    loading.value = false
  }
}

// 保存用户资料
const saveProfile = async () => {
  if (saving.value) return

  saving.value = true
  message.value = ''

  try {
    const updatedUser = await userProfileApi.updateProfile(profileForm.value)
    // 更新本地用户状态
    if (authStore.currentUser) {
      Object.assign(authStore.currentUser, updatedUser)
    }
    showMessage('资料更新成功', 'success')
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || '更新失败，请稍后重试'
    showMessage(errorMsg, 'error')
  } finally {
    saving.value = false
  }
}

// 修改密码
const updatePassword = async () => {
  if (passwordSaving.value) return

  // 验证密码
  if (passwordForm.value.new_password.length < 8) {
    showMessage('新密码至少需要8个字符', 'error')
    return
  }

  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    showMessage('两次输入的密码不一致', 'error')
    return
  }

  passwordSaving.value = true
  message.value = ''

  try {
    await userProfileApi.updatePassword({
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password
    })

    showMessage('密码修改成功', 'success')
    // 清空密码表单
    passwordForm.value = {
      old_password: '',
      new_password: '',
      confirm_password: ''
    }
    showPasswordForm.value = false
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || '密码修改失败'
    showMessage(errorMsg, 'error')
  } finally {
    passwordSaving.value = false
  }
}

// 显示消息
const showMessage = (msg: string, type: 'success' | 'error') => {
  message.value = msg
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 5000)
}

// 切换标签
const setActiveTab = (tab: string) => {
  activeTab.value = tab
}

// 退出登录
const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

// 组件挂载时加载用户资料
onMounted(() => {
  if (authStore.currentUser) {
    profileForm.value = {
      username: authStore.currentUser.username,
      bio: authStore.currentUser.bio || '',
      avatar_url: authStore.currentUser.avatar_url || '',
      user_tag: authStore.currentUser.user_tag || '',
      username_color: authStore.currentUser.username_color || ''
    }
  } else {
    loadProfile()
  }
})
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold text-gray-900 mb-6">个人中心</h1>

    <div class="bg-white shadow-md rounded-lg overflow-hidden">
      <!-- 头部 -->
      <div class="bg-gradient-to-r from-red-500 to-red-600 px-6 py-8">
        <div class="flex items-center space-x-6">
          <div class="relative">
            <img
              :src="avatarPreview"
              :alt="profileForm.username"
              class="w-24 h-24 rounded-full border-4 border-white shadow-lg"
              onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 40 40%22%3E%3Crect width=%2240%22 height=%2240%22 fill=%22%23e74c3c%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 fill=%22white%22 font-size=%2216%22 font-family=%22Arial%22%3EU%3C/text%3E%3C/svg%3E'"
            />
          </div>
          <div class="text-white">
            <h1 class="text-2xl font-bold">{{ profileForm.username }}</h1>
            <p class="text-red-100 mt-1">
              UID: {{ authStore.currentUser?.user_number }}
            </p>
            <p v-if="profileForm.user_tag" class="text-red-100 mt-1">
              {{ profileForm.user_tag }}
            </p>
          </div>
        </div>
      </div>

      <!-- 消息提示 -->
      <div v-if="message" :class="`p-4 mx-6 mt-6 rounded-lg ${messageType === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`">
        {{ message }}
      </div>

      <!-- 标签导航 -->
      <div class="border-b border-gray-200">
        <nav class="flex -mb-px">
          <button
            @click="setActiveTab('profile')"
            :class="`px-6 py-4 text-sm font-medium ${activeTab === 'profile' ? 'text-red-600 border-b-2 border-red-600' : 'text-gray-500 hover:text-gray-700'}`"
          >
            基本资料
          </button>
          <button
            @click="setActiveTab('security')"
            :class="`px-6 py-4 text-sm font-medium ${activeTab === 'security' ? 'text-red-600 border-b-2 border-red-600' : 'text-gray-500 hover:text-gray-700'}`"
          >
            安全设置
          </button>
          <button
            @click="setActiveTab('stats')"
            :class="`px-6 py-4 text-sm font-medium ${activeTab === 'stats' ? 'text-red-600 border-b-2 border-red-600' : 'text-gray-500 hover:text-gray-700'}`"
          >
            统计信息
          </button>
        </nav>
      </div>

      <!-- 内容区域 -->
      <div class="p-6">
        <!-- 基本资料 -->
        <div v-show="activeTab === 'profile'">
          <div class="space-y-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">用户名</label>
              <input
                v-model="profileForm.username"
                type="text"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="请输入用户名"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">个人简介</label>
              <textarea
                v-model="profileForm.bio"
                rows="4"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="介绍一下自己..."
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">头像URL</label>
              <input
                v-model="profileForm.avatar_url"
                type="url"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="https://example.com/avatar.jpg"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">用户标签</label>
              <input
                v-model="profileForm.user_tag"
                type="text"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="比如：算法爱好者、Python开发者..."
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">用户名颜色</label>
              <input
                v-model="profileForm.username_color"
                type="text"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="#e74c3c"
              />
            </div>

            <div class="pt-4">
              <button
                @click="saveProfile"
                :disabled="saving"
                class="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ saving ? '保存中...' : '保存资料' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 安全设置 -->
        <div v-show="activeTab === 'security'">
          <div class="space-y-6">
            <div v-if="!showPasswordForm" class="text-center py-8">
              <p class="text-gray-500 mb-4">为了账户安全，建议定期修改密码</p>
              <button
                @click="showPasswordForm = true"
                class="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                修改密码
              </button>
            </div>

            <div v-else class="space-y-6">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">当前密码</label>
                <input
                  v-model="passwordForm.old_password"
                  type="password"
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="请输入当前密码"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">新密码</label>
                <input
                  v-model="passwordForm.new_password"
                  type="password"
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="请输入新密码（至少8个字符）"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">确认新密码</label>
                <input
                  v-model="passwordForm.confirm_password"
                  type="password"
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="请再次输入新密码"
                />
              </div>

              <div class="flex space-x-4">
                <button
                  @click="updatePassword"
                  :disabled="passwordSaving"
                  class="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {{ passwordSaving ? '修改中...' : '确认修改' }}
                </button>
                <button
                  @click="showPasswordForm = false; passwordForm = { old_password: '', new_password: '', confirm_password: '' }"
                  class="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                >
                  取消
                </button>
              </div>
            </div>

            <!-- 危险操作 -->
            <div class="pt-6 border-t border-gray-200">
              <h3 class="text-lg font-semibold text-gray-900 mb-4">危险操作</h3>
              <button
                @click="handleLogout"
                class="w-full px-4 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
              >
                退出登录
              </button>
            </div>
          </div>
        </div>

        <!-- 统计信息 -->
        <div v-show="activeTab === 'stats'">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-gray-50 rounded-lg p-6 text-center">
              <div class="text-3xl font-bold text-red-600 mb-2">0</div>
              <div class="text-gray-600">已解决题目</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-6 text-center">
              <div class="text-3xl font-bold text-green-600 mb-2">0</div>
              <div class="text-gray-600">提交次数</div>
            </div>
            <div class="bg-gray-50 rounded-lg p-6 text-center">
              <div class="text-3xl font-bold text-blue-600 mb-2">0%</div>
              <div class="text-gray-600">通过率</div>
            </div>
          </div>

          <div class="mt-6 p-4 bg-gray-50 rounded-lg">
            <h3 class="text-sm font-medium text-gray-700 mb-2">账户信息</h3>
            <div class="text-sm text-gray-600 space-y-1">
              <p>邮箱: {{ authStore.currentUser?.email }}</p>
              <p>注册时间: {{ formatDate(authStore.currentUser?.created_at || '') }}</p>
              <p>账户状态:
                <span v-if="authStore.currentUser?.is_active" class="text-green-600">已激活</span>
                <span v-else class="text-red-600">未激活</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
