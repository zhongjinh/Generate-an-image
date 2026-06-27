<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

// 套餐列表
const packages = ref([])

// 兑换相关
const redeemCode = ref('')
const redeeming = ref(false)
const redeemMessage = ref('')
const redeemError = ref('')

// 支付相关
const paying = ref(false)
const showPayModal = ref(false)
const payForm = ref('')
const currentOrderId = ref('')
const payCheckTimer = ref(null)

// 兑换记录
const records = ref([])

const userInfoText = computed(() => {
  const u = auth.user
  if (!u) return ''
  if (u.is_admin) return `${u.username} · 管理员`
  if (u.vip_active) {
    const remaining = u.vip_remaining || 0
    if (remaining > 86400) return `${u.username} · 会员剩余 ${Math.floor(remaining / 86400)} 天`
    if (remaining > 3600) return `${u.username} · 会员剩余 ${Math.floor(remaining / 3600)} 小时`
    if (remaining > 60) return `${u.username} · 会员剩余 ${Math.floor(remaining / 60)} 分钟`
    return `${u.username} · 会员有效`
  }
  return `${u.username} · 未开通会员`
})

onMounted(async () => {
  await loadPackages()
  await loadHistory()
})

onUnmounted(() => {
  stopPayCheck()
})

async function loadPackages() {
  const r = await api.getPackages()
  packages.value = r.packages || []
}

async function loadHistory() {
  try {
    const r = await api.redeemHistory()
    records.value = r.records || []
  } catch {
    records.value = []
  }
}

// 购买套餐
async function buyPkg(pkg) {
  // 如果有外部链接，直接跳转
  if (pkg.buy_link) {
    window.open(pkg.buy_link, '_blank')
    return
  }

  // 否则走支付宝支付流程
  paying.value = true
  try {
    const r = await api.createPayment({ package_id: pkg.id })
    if (r.success && r.pay_form) {
      currentOrderId.value = r.order_id
      payForm.value = r.pay_form
      showPayModal.value = true
      startPayCheck()
    } else {
      alert(r.error || '创建支付失败')
    }
  } catch (e) {
    alert(e.error || '创建支付失败')
  } finally {
    paying.value = false
  }
}

// 开始轮询支付状态
function startPayCheck() {
  stopPayCheck()
  payCheckTimer.value = setInterval(async () => {
    if (!currentOrderId.value) return
    try {
      const r = await api.checkPayment(currentOrderId.value)
      if (r.paid) {
        stopPayCheck()
        showPayModal.value = false
        if (r.user) auth.updateUser(r.user)
        alert('支付成功！VIP 已激活')
        await loadHistory()
      }
    } catch (e) {
      console.error('查询支付状态失败:', e)
    }
  }, 3000)
}

function stopPayCheck() {
  if (payCheckTimer.value) {
    clearInterval(payCheckTimer.value)
    payCheckTimer.value = null
  }
}

function openPayWindow() {
  // 创建一个新窗口并提交表单
  const payWindow = window.open('', '_blank')
  if (payWindow) {
    payWindow.document.write(payForm.value)
    payWindow.document.close()
  }
}

function closePayModal() {
  showPayModal.value = false
  stopPayCheck()
  loadHistory()
}

// 兑换
async function doRedeem() {
  const code = redeemCode.value.trim()
  if (!code) {
    redeemError.value = '请输入兑换码'
    return
  }

  redeeming.value = true
  redeemError.value = ''
  redeemMessage.value = ''

  try {
    const r = await api.redeemCode({ code })
    redeemMessage.value = r.message || '兑换成功！'
    redeemCode.value = ''
    if (r.user) auth.updateUser(r.user)
    await loadHistory()
  } catch (e) {
    redeemError.value = e.error || '兑换失败'
  } finally {
    redeeming.value = false
  }
}

function formatDuration(days) {
  if (!days) return ''
  days = parseFloat(days)
  if (days < 1) {
    const hours = Math.round(days * 24)
    if (hours < 1) return '30分钟'
    return `${hours}小时`
  }
  if (days === 1) return '1天'
  if (days < 30) return `${days}天`
  if (days < 365) return `${Math.round(days / 30)}个月`
  return `${Math.round(days / 365)}年`
}

function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
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
      <span style="font-size:13px">{{ userInfoText }}</span>
      <RouterLink to="/">返回首页</RouterLink>
    </div>
  </header>

  <div class="pay-page">
    <!-- VIP 状态卡片 -->
    <div class="status-card">
      <div class="status-icon">{{ auth.user?.vip_active ? '👑' : '🎁' }}</div>
      <div class="status-info">
        <div class="status-title">
          {{ auth.user?.is_admin ? '管理员' : auth.user?.vip_active ? '会员用户' : '普通用户' }}
        </div>
        <div class="status-detail">
          <template v-if="auth.user?.is_admin">
            管理员拥有无限使用权限
          </template>
          <template v-else-if="auth.user?.vip_active">
            会员有效，{{ userInfoText.split('·')[1]?.trim() || '' }}
          </template>
          <template v-else>
            购买会员套餐，解锁无限使用权限
          </template>
        </div>
      </div>
    </div>

    <!-- 套餐列表 -->
    <div class="section">
      <h2>💎 选择会员套餐</h2>
      <p class="section-hint">支持支付宝支付</p>

      <div class="packages">
        <div
          v-for="p in packages"
          :key="p.id"
          class="pkg-card"
          :class="{ recommended: p.type === 'month' }"
        >
          <div v-if="p.type === 'month'" class="badge badge-hot">推荐</div>
          <div v-else-if="p.type === 'year'" class="badge badge-vip">超值</div>
          <div class="pkg-name">{{ p.package_name }}</div>
          <div class="pkg-price">¥<span>{{ p.price }}</span></div>
          <div class="pkg-duration">{{ formatDuration(p.valid_days) }}</div>
          <div class="pkg-desc">会员期间无限使用</div>
          <button class="btn-buy" @click="buyPkg(p)" :disabled="paying">
            {{ p.buy_link ? '去购买 →' : (paying ? '处理中...' : '立即购买') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 兑换码输入 -->
    <div class="section redeem-section">
      <h2>🎫 兑换会员卡码</h2>
      <p class="section-hint">已有兑换码？输入即可激活会员</p>

      <div class="redeem-form">
        <input
          v-model="redeemCode"
          type="text"
          placeholder="请输入兑换码（如 A3K9B2F7）"
          maxlength="32"
          class="redeem-input"
          @keyup.enter="doRedeem"
        />
        <button class="btn-redeem" @click="doRedeem" :disabled="redeeming">
          {{ redeeming ? '兑换中...' : '立即兑换' }}
        </button>
      </div>

      <div v-if="redeemMessage" class="msg success">{{ redeemMessage }}</div>
      <div v-if="redeemError" class="msg error">{{ redeemError }}</div>
    </div>

    <!-- 兑换记录 -->
    <div class="section">
      <h3>📋 兑换记录</h3>
      <table class="history-table">
        <thead>
          <tr>
            <th>兑换码</th>
            <th>套餐</th>
            <th>时长</th>
            <th>兑换时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!records.length">
            <td colspan="4" style="text-align:center;color:#999">暂无兑换记录</td>
          </tr>
          <tr v-for="r in records" :key="r.code">
            <td class="code-cell">{{ r.code }}</td>
            <td>{{ r.package_name || '-' }}</td>
            <td>{{ formatDuration(r.valid_days) }}</td>
            <td>{{ formatTime(r.used_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- 支付弹窗 -->
  <div v-if="showPayModal" class="modal-overlay" @click.self="closePayModal">
    <div class="modal">
      <div class="modal-header">
        <h3>支付宝支付</h3>
        <button class="btn-close" @click="closePayModal">&times;</button>
      </div>
      <div class="modal-body">
        <p class="tip">请在新打开的支付页面完成付款</p>
        <button class="btn-pay" @click="openPayWindow">
          💙 打开支付宝支付
        </button>
        <p class="hint">支付完成后，系统会自动确认，请勿关闭此页面</p>
        <div class="pay-status">
          <span class="loading-dot"></span>
          等待支付确认...
        </div>
      </div>
      <div class="modal-footer">
        <p>订单号：{{ currentOrderId }}</p>
        <button class="btn-close-modal" @click="closePayModal">取消支付</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pay-page {
  max-width: 900px;
  margin: 30px auto;
  padding: 0 20px 40px;
}

/* VIP 状态卡片 */
.status-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 28px;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}
.status-icon { font-size: 48px; }
.status-info { flex: 1; }
.status-title { font-size: 20px; font-weight: 700; margin-bottom: 6px; }
.status-detail { font-size: 14px; opacity: 0.9; }

/* 通用 section */
.section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 20px;
}
.section h2 { margin: 0 0 6px; font-size: 20px; color: #333; }
.section h3 { margin: 0 0 16px; font-size: 16px; color: #333; }
.section-hint { color: #999; font-size: 13px; margin: 0 0 16px; }


.pay-method input { display: none; }
.method-icon { font-size: 18px; }

/* 套餐卡片 */
.packages {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.pkg-card {
  background: #fafafa;
  border: 2px solid #f0f0f0;
  border-radius: 12px;
  padding: 20px 16px;
  text-align: center;
  transition: all 0.2s;
  position: relative;
}
.pkg-card:hover { border-color: #1890ff; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(24,144,255,0.15); }
.pkg-card.recommended { border-color: #faad14; background: #fffbe6; }
.badge {
  position: absolute;
  top: -8px;
  right: -8px;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 11px;
  color: #fff;
}
.badge-hot { background: #ff7a45; }
.badge-vip { background: #722ed1; }
.pkg-name { font-size: 16px; font-weight: 700; color: #333; margin-bottom: 8px; }
.pkg-price { font-size: 32px; font-weight: 700; color: #1890ff; margin-bottom: 4px; }
.pkg-price span { font-size: inherit; }
.pkg-duration { font-size: 13px; color: #666; margin-bottom: 8px; }
.pkg-desc { font-size: 12px; color: #999; margin-bottom: 14px; }
.btn-buy {
  width: 100%;
  padding: 10px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-buy:hover { background: #40a9ff; }
.btn-buy:disabled { background: #ccc; cursor: not-allowed; }
.pkg-card.recommended .btn-buy { background: #faad14; }
.pkg-card.recommended .btn-buy:hover { background: #ffc53d; }

/* 兑换区域 */
.redeem-section { background: #f9f9ff; }
.redeem-form { display: flex; gap: 10px; }
.redeem-input {
  flex: 1;
  padding: 12px 16px;
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  font-size: 16px;
  letter-spacing: 2px;
  outline: none;
  font-family: monospace;
  transition: border-color 0.2s;
}
.redeem-input:focus { border-color: #1890ff; }
.btn-redeem {
  padding: 12px 28px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.btn-redeem:hover { opacity: 0.9; }
.btn-redeem:disabled { opacity: 0.6; cursor: not-allowed; }
.msg { margin-top: 14px; padding: 10px 14px; border-radius: 6px; font-size: 14px; }
.msg.success { background: #f6ffed; border: 1px solid #b7eb8f; color: #52c41a; }
.msg.error { background: #fff2f0; border: 1px solid #ffccc7; color: #ff4d4f; }

/* 记录表格 */
.history-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.history-table th, .history-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f0f0; }
.history-table th { background: #fafafa; font-weight: 600; color: #666; }
.code-cell { font-family: monospace; letter-spacing: 1px; color: #1890ff; font-weight: 600; }

/* 支付弹窗 */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal {
  background: #fff;
  border-radius: 12px;
  width: 420px;
  max-width: 90%;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}
.modal-header h3 { margin: 0; font-size: 18px; }
.btn-close { background: none; border: none; font-size: 24px; color: #999; cursor: pointer; }
.modal-body { padding: 24px 20px; text-align: center; }
.tip { margin: 0 0 20px; color: #666; font-size: 14px; }
.btn-pay {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 36px;
  background: #1677ff;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-pay:hover { background: #4096ff; }
.hint { margin: 16px 0 0; color: #999; font-size: 12px; }
.pay-status {
  margin-top: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #1890ff;
  font-size: 14px;
}
.loading-dot {
  width: 8px;
  height: 8px;
  background: #1890ff;
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid #f0f0f0;
  text-align: center;
}
.modal-footer p { margin: 0 0 12px; font-size: 12px; color: #999; }
.btn-close-modal {
  padding: 8px 20px;
  background: #f5f5f5;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.btn-close-modal:hover { background: #e8e8e8; }
</style>
