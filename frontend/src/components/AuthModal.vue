<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const showModal = ref(false)
const tab = ref('login')

const loginUser = ref('')
const loginPass = ref('')
const regUser = ref('')
const regPass = ref('')
const regPhone = ref('')
const formError = ref('')
const formSuccess = ref('')
const loading = ref(false)

function clearMessages() {
  formError.value = ''
  formSuccess.value = ''
}

function open(tabName = 'login') {
  tab.value = tabName
  clearMessages()
  loginPass.value = ''
  regPass.value = ''
  showModal.value = true
}

function close() {
  showModal.value = false
  clearMessages()
  loginPass.value = ''
  regPass.value = ''
}

function onOverlayClick(e) {
  if (e.target.classList.contains('modal-overlay')) close()
}

async function doLogin(e) {
  e.preventDefault()
  clearMessages()
  if (!loginUser.value.trim()) {
    formError.value = '请输入用户名'
    return
  }
  if (!loginPass.value) {
    formError.value = '请输入密码'
    return
  }
  loading.value = true
  const res = await auth.login(loginUser.value.trim(), loginPass.value)
  loading.value = false
  if (res.success) {
    loginPass.value = ''
    close()
  } else {
    formError.value = res.error || '登录失败'
  }
}

async function doRegister(e) {
  e.preventDefault()
  clearMessages()
  const u = regUser.value.trim()
  if (!u) {
    formError.value = '请输入用户名'
    return
  }
  if (u.length < 3 || u.length > 20) {
    formError.value = '用户名长度须为 3-20 位'
    return
  }
  if (!regPass.value) {
    formError.value = '请输入密码'
    return
  }
  if (regPass.value.length < 6) {
    formError.value = '密码至少 6 位'
    return
  }
  loading.value = true
  const res = await auth.register(u, regPass.value, regPhone.value.trim())
  loading.value = false
  if (res.success) {
    formSuccess.value = '注册成功！已赠送 1 次免费生成次数'
    setTimeout(close, 1200)
  } else {
    formError.value = res.error || '注册失败'
  }
}

defineExpose({ open })
</script>

<template>
  <div v-if="showModal" class="modal-overlay" @click="onOverlayClick">
    <div class="auth-modal-wrap">
      <div class="auth-modal">
        <button type="button" class="modal-close" aria-label="关闭" @click="close">&times;</button>
        <div class="auth-modal-header">
          <h2>{{ tab === 'login' ? '欢迎回来' : '创建账号' }}</h2>
          <p>{{ tab === 'login' ? '登录后即可生成专业图表' : '注册即赠送 1 次免费生成次数' }}</p>
        </div>
        <div class="auth-tabs">
          <button
            type="button"
            class="auth-tab"
            :class="{ active: tab === 'login' }"
            @click="tab = 'login'; clearMessages()"
          >登录</button>
          <button
            type="button"
            class="auth-tab"
            :class="{ active: tab === 'register' }"
            @click="tab = 'register'; clearMessages()"
          >注册</button>
        </div>
        <div class="auth-form">
          <div v-if="formError" class="form-error show">{{ formError }}</div>
          <div v-if="formSuccess" class="form-success show">{{ formSuccess }}</div>

          <form v-show="tab === 'login'" @submit="doLogin">
            <div class="form-group">
              <label>用户名</label>
              <input v-model="loginUser" type="text" placeholder="请输入用户名" autocomplete="username" />
            </div>
            <div class="form-group">
              <label>密码</label>
              <input v-model="loginPass" type="password" placeholder="请输入密码" autocomplete="current-password" />
            </div>
            <button type="submit" class="btn-auth" :disabled="loading">{{ loading ? '处理中...' : '登录' }}</button>
          </form>

          <form v-show="tab === 'register'" @submit="doRegister">
            <div class="form-group">
              <label>用户名</label>
              <input v-model="regUser" type="text" placeholder="3-20 位字符" autocomplete="username" />
            </div>
            <div class="form-group">
              <label>密码</label>
              <input v-model="regPass" type="password" placeholder="至少 6 位" autocomplete="new-password" />
            </div>
            <div class="form-group">
              <label>手机号 <span style="color:#94a3b8;font-weight:400">（可选）</span></label>
              <input v-model="regPhone" type="text" placeholder="手机号" autocomplete="tel" />
            </div>
            <button type="submit" class="btn-auth" :disabled="loading">{{ loading ? '处理中...' : '注册并领取免费次数' }}</button>
            <p class="auth-tip">注册即赠送 <strong>1 次</strong> 免费图表生成</p>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>
