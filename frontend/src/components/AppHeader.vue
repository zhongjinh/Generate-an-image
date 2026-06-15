<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const emit = defineEmits(['open-login', 'open-register'])

const avatarLetter = computed(() => {
  const name = auth.user?.username || 'U'
  return name.charAt(0).toUpperCase()
})

const remainText = computed(() => {
  if (!auth.user) return ''
  if (auth.user.is_admin) return '管理员'
  return `剩余 ${auth.user.remain_count || 0} 次`
})
</script>

<template>
  <header class="header">
    <div class="logo">
      <span class="logo-icon">图</span>
      <RouterLink to="/" style="color:inherit;text-decoration:none">图表在线生成器</RouterLink>
    </div>
    <div class="nav-right">
      <span v-if="auth.isLoggedIn" class="user-info">
        <span class="user-avatar">{{ avatarLetter }}</span>
        <span>{{ auth.user?.username }}</span>
        <span class="remain-count">{{ remainText }}</span>
        <RouterLink to="/pay">购买会员</RouterLink>
        <RouterLink v-if="auth.isAdmin" to="/admin">管理后台</RouterLink>
        <button class="btn-sm" @click="auth.logout()">退出</button>
      </span>
      <span v-else class="login-area">
        <button class="btn-sm" @click="emit('open-login')">登录</button>
        <button class="btn-sm btn-primary" @click="emit('open-register')">注册</button>
      </span>
      <RouterLink to="/pay" class="btn-vip">开通会员</RouterLink>
    </div>
  </header>
</template>

<style scoped>
.login-area {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
