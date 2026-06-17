import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'

function loadUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(loadUser())

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => !!user.value?.is_admin)

  function saveSession(newToken, u) {
    token.value = newToken
    user.value = u
    localStorage.setItem('token', newToken)
    localStorage.setItem('user', JSON.stringify(u))
  }

  function clearSession() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  async function login(email, password) {
    try {
      const account = email.trim()
      const payload = account.includes('@')
        ? { email: account, password }
        : { username: account, password }
      const res = await api.login(payload)
      if (res.token) {
        saveSession(res.token, res.user)
        return { success: true }
      }
      return { success: false, error: res.error || '登录失败' }
    } catch (e) {
      return { success: false, error: e.error || '网络错误，请稍后重试' }
    }
  }

  async function sendCode(email) {
    try {
      const res = await api.sendCode({ email: email.trim() })
      return { success: true, message: res.message }
    } catch (e) {
      return { success: false, error: e.error || '发送失败' }
    }
  }

  async function register(email, password, code) {
    try {
      const res = await api.register({ email: email.trim(), password, code })
      if (res.token) {
        saveSession(res.token, res.user)
        return { success: true }
      }
      return { success: false, error: res.error || '注册失败' }
    } catch (e) {
      return { success: false, error: e.error || '网络错误，请稍后重试' }
    }
  }

  function logout() {
    clearSession()
  }

  async function refreshUser() {
    if (!token.value) return
    try {
      const res = await api.getUserInfo()
      if (res.user) {
        user.value = res.user
        localStorage.setItem('user', JSON.stringify(res.user))
      }
    } catch {
      /* ignore */
    }
  }

  function updateUser(u) {
    user.value = u
    localStorage.setItem('user', JSON.stringify(u))
  }

  if (token.value) {
    refreshUser()
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    login,
    sendCode,
    register,
    logout,
    refreshUser,
    updateUser
  }
})
