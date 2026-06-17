<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const showModal = ref(false)
const tab = ref('login')

const loginEmail = ref('')
const loginPass = ref('')
const regEmail = ref('')
const regCode = ref('')
const regPass = ref('')
const formError = ref('')
const formSuccess = ref('')
const loading = ref(false)
const codeSending = ref(false)
const codeCountdown = ref(0)
let countdownTimer = null

function clearMessages() {
  formError.value = ''
  formSuccess.value = ''
}

function open(tabName = 'login') {
  tab.value = tabName
  clearMessages()
  loginPass.value = ''
  regPass.value = ''
  regCode.value = ''
  showModal.value = true
}

function close() {
  showModal.value = false
  clearMessages()
  loginPass.value = ''
  regPass.value = ''
  regCode.value = ''
}

function onOverlayClick(e) {
  if (e.target.classList.contains('modal-overlay')) close()
}

function startCountdown(seconds = 60) {
  codeCountdown.value = seconds
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    codeCountdown.value -= 1
    if (codeCountdown.value <= 0) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

async function sendCode() {
  clearMessages()
  const email = regEmail.value.trim()
  if (!email) {
    formError.value = '请先填写邮箱'
    return
  }
  if (codeCountdown.value > 0 || codeSending.value) return

  codeSending.value = true
  try {
    const res = await auth.sendCode(email)
    if (res.success) {
      formSuccess.value = res.message || '验证码已发送，请查收邮件'
      startCountdown(60)
    } else {
      formError.value = res.error || '发送失败'
    }
  } finally {
    codeSending.value = false
  }
}

async function doLogin(e) {
  e.preventDefault()
  clearMessages()
  if (!loginEmail.value.trim()) {
    formError.value = '请输入邮箱'
    return
  }
  if (!loginPass.value) {
    formError.value = '请输入密码'
    return
  }
  loading.value = true
  const res = await auth.login(loginEmail.value.trim(), loginPass.value)
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
  const email = regEmail.value.trim()
  if (!email) {
    formError.value = '请输入邮箱'
    return
  }
  if (!regCode.value.trim()) {
    formError.value = '请输入邮箱验证码'
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
  const res = await auth.register(email, regPass.value, regCode.value.trim())
  loading.value = false
  if (res.success) {
    formSuccess.value = '注册成功！已赠送免费生成次数'
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
          <p>{{ tab === 'login' ? '使用邮箱登录后即可生成专业图表' : '验证邮箱后注册，赠送免费生成次数' }}</p>
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
              <label>邮箱</label>
              <input
                v-model="loginEmail"
                type="email"
                placeholder="请输入注册邮箱"
                autocomplete="email"
              />
            </div>
            <div class="form-group">
              <label>密码</label>
              <input
                v-model="loginPass"
                type="password"
                placeholder="请输入密码"
                autocomplete="current-password"
              />
            </div>
            <button type="submit" class="btn-auth" :disabled="loading">
              {{ loading ? '处理中...' : '登录' }}
            </button>
            <p class="auth-tip">管理员仍可使用用户名 <strong>admin</strong> 登录</p>
          </form>

          <form v-show="tab === 'register'" @submit="doRegister">
            <div class="form-group">
              <label>邮箱</label>
              <input
                v-model="regEmail"
                type="email"
                placeholder="用于登录与接收验证码"
                autocomplete="email"
              />
            </div>
            <div class="form-group">
              <label>验证码</label>
              <div class="code-row">
                <input
                  v-model="regCode"
                  type="text"
                  maxlength="6"
                  placeholder="6 位验证码"
                  autocomplete="one-time-code"
                />
                <button
                  type="button"
                  class="btn-send-code"
                  :disabled="codeSending || codeCountdown > 0"
                  @click="sendCode"
                >
                  {{
                    codeSending
                      ? '发送中...'
                      : codeCountdown > 0
                        ? `${codeCountdown}s 后重发`
                        : '获取验证码'
                  }}
                </button>
              </div>
            </div>
            <div class="form-group">
              <label>密码</label>
              <input
                v-model="regPass"
                type="password"
                placeholder="至少 6 位"
                autocomplete="new-password"
              />
            </div>
            <button type="submit" class="btn-auth" :disabled="loading">
              {{ loading ? '处理中...' : '注册并领取免费次数' }}
            </button>
            <p class="auth-tip">注册即赠送 <strong>1 次</strong> 免费图表生成</p>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>
