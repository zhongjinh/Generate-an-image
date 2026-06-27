<script setup>
import { computed, ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api } from '../api'

const auth = useAuthStore()
const emit = defineEmits(['open-login', 'open-register'])

const showInviteModal = ref(false)
const inviteCode = ref('')
const inviteInput = ref('')
const inviteMessage = ref('')
const inviteError = ref('')

const avatarLetter = computed(() => {
  const name = auth.user?.username || 'U'
  return name.charAt(0).toUpperCase()
})

// 会员状态显示
const vipStatusText = computed(() => {
  if (!auth.user) return ''
  if (auth.user.is_admin) return '管理员'

  if (auth.user.vip_active) {
    const remaining = auth.user.vip_remaining || 0
    if (remaining > 86400) {
      return `会员剩余 ${Math.floor(remaining / 86400)} 天`
    } else if (remaining > 3600) {
      return `会员剩余 ${Math.floor(remaining / 3600)} 小时`
    } else if (remaining > 0) {
      return `会员剩余 ${Math.floor(remaining / 60)} 分钟`
    }
    return '会员有效'
  }

  return '未开通会员'
})

const vipStatusClass = computed(() => {
  if (!auth.user) return ''
  if (auth.user.is_admin || auth.user.vip_active) return 'vip-active'
  return 'vip-expired'
})

async function openInviteModal() {
  showInviteModal.value = true
  inviteMessage.value = ''
  inviteError.value = ''
  inviteInput.value = ''

  // 获取自己的邀请码
  try {
    const r = await api.getInviteCode()
    inviteCode.value = r.invite_code || ''
  } catch {
    inviteCode.value = ''
  }
}

async function acceptInvite() {
  if (!inviteInput.value.trim()) {
    inviteError.value = '请输入邀请码'
    return
  }

  inviteError.value = ''
  inviteMessage.value = ''

  try {
    const r = await api.acceptInvite({ code: inviteInput.value.trim() })
    inviteMessage.value = r.message
    inviteInput.value = ''
    // 刷新用户信息
    auth.refreshUser()
  } catch (e) {
    inviteError.value = e.error || '邀请码无效'
  }
}

function copyInviteCode() {
  if (inviteCode.value) {
    navigator.clipboard.writeText(inviteCode.value).then(() => {
      inviteMessage.value = '邀请码已复制到剪贴板'
      setTimeout(() => { inviteMessage.value = '' }, 2000)
    })
  }
}
</script>

<template>
  <header class="header">
    <div class="logo">
      <span class="logo-icon">
        <svg width="28" height="28" viewBox="0 0 128 128" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="4" y="4" width="120" height="120" rx="24" fill="url(#logoBg)"/>
          <rect x="22" y="78" width="14" height="28" rx="3" fill="#67d4d4" opacity="0.9"/>
          <rect x="42" y="58" width="14" height="48" rx="3" fill="#66a6ff" opacity="0.9"/>
          <rect x="62" y="42" width="14" height="64" rx="3" fill="#fff" opacity="0.85"/>
          <rect x="82" y="26" width="14" height="80" rx="3" fill="#ffd700"/>
          <path d="M29 74C40 68 49 54 56 50C63 46 69 38 76 34C83 30 89 24 96 20" stroke="#ffd700" stroke-width="3.5" stroke-linecap="round"/>
          <circle cx="29" cy="74" r="3.5" fill="#ffd700"/>
          <circle cx="49" cy="54" r="3.5" fill="#ffd700"/>
          <circle cx="69" cy="38" r="3.5" fill="#ffd700"/>
          <circle cx="89" cy="24" r="3.5" fill="#ffd700"/>
          <polygon points="93,16 100,18 95,24" fill="#ffd700"/>
          <defs>
            <linearGradient id="logoBg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#667eea"/>
              <stop offset="100%" stop-color="#764ba2"/>
            </linearGradient>
          </defs>
        </svg>
      </span>
      <RouterLink to="/" style="color:inherit;text-decoration:none">图表在线生成器</RouterLink>
    </div>
    <div class="nav-right">
      <span v-if="auth.isLoggedIn" class="user-info">
        <span class="user-avatar">{{ avatarLetter }}</span>
        <span>{{ auth.user?.username }}</span>
        <span class="vip-status" :class="vipStatusClass">{{ vipStatusText }}</span>
        <button class="btn-sm btn-invite" @click="openInviteModal">邀请</button>
        <RouterLink to="/profile" class="btn-profile">个人中心</RouterLink>
        <RouterLink to="/pay" class="btn-vip">开通会员</RouterLink>
        <button class="btn-sm" @click="auth.logout()">退出</button>
      </span>
      <span v-else class="login-area">
        <button class="btn-sm" @click="emit('open-login')">登录</button>
        <button class="btn-sm btn-primary" @click="emit('open-register')">注册</button>
      </span>
    </div>
  </header>

  <!-- 邀请弹窗 -->
  <div v-if="showInviteModal" class="modal-overlay" @click.self="showInviteModal = false">
    <div class="modal">
      <div class="modal-header">
        <h3>邀请好友</h3>
        <button class="btn-close" @click="showInviteModal = false">&times;</button>
      </div>
      <div class="modal-body">
        <!-- 我的邀请码 -->
        <div class="invite-section">
          <div class="section-title">我的邀请码</div>
          <div class="invite-code-box">
            <span class="code-text">{{ inviteCode || '加载中...' }}</span>
            <button class="btn-copy" @click="copyInviteCode">复制</button>
          </div>
          <div class="section-hint">分享给好友，好友输入后双方都能获得 30 分钟无限使用</div>
        </div>

        <!-- 输入邀请码 -->
        <div class="invite-section">
          <div class="section-title">输入好友邀请码</div>
          <div class="invite-input-box">
            <input
              v-model="inviteInput"
              type="text"
              placeholder="请输入邀请码"
              maxlength="32"
              @keyup.enter="acceptInvite"
            />
            <button class="btn-accept" @click="acceptInvite">确认</button>
          </div>
        </div>

        <!-- 消息提示 -->
        <div v-if="inviteMessage" class="msg-success">{{ inviteMessage }}</div>
        <div v-if="inviteError" class="msg-error">{{ inviteError }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.vip-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}

.vip-active {
  background: #f6ffed;
  color: #52c41a;
}

.vip-expired {
  background: #fff7e6;
  color: #faad14;
}

.btn-invite {
  background: #722ed1;
  color: #fff;
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-invite:hover {
  background: #9254de;
}

.btn-profile {
  background: #f0f0f0;
  color: #333;
  padding: 4px 12px;
  border-radius: 4px;
  text-decoration: none;
  font-size: 13px;
}
.btn-profile:hover {
  background: #e0e0e0;
}

.btn-vip {
  background: linear-gradient(135deg, #faad14, #ff6b00);
  color: #fff;
  padding: 4px 12px;
  border-radius: 4px;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #fff;
  border-radius: 12px;
  width: 420px;
  max-width: 90%;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
}

.invite-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.section-hint {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.invite-code-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f5f5f5;
  border-radius: 6px;
  padding: 10px 12px;
}

.code-text {
  flex: 1;
  font-family: monospace;
  font-size: 16px;
  color: #333;
  letter-spacing: 1px;
}

.btn-copy {
  background: #1890ff;
  color: #fff;
  border: none;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-copy:hover {
  background: #40a9ff;
}

.invite-input-box {
  display: flex;
  gap: 8px;
}

.invite-input-box input {
  flex: 1;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
  outline: none;
}
.invite-input-box input:focus {
  border-color: #1890ff;
}

.btn-accept {
  background: #722ed1;
  color: #fff;
  border: none;
  padding: 8px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.btn-accept:hover {
  background: #9254de;
}

.msg-success {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  color: #52c41a;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  margin-top: 12px;
}

.msg-error {
  background: #fff2f0;
  border: 1px solid #ffccc7;
  color: #ff4d4f;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  margin-top: 12px;
}
</style>
