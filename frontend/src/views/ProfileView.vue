<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api } from '../api'

const auth = useAuthStore()
const router = useRouter()

const orders = ref([])
const files = ref([])
const activeTab = ref('info')

// 会员状态
const vipStatus = computed(() => {
  if (!auth.user) return { text: '未登录', class: 'status-expired' }
  if (auth.user.is_admin) return { text: '管理员', class: 'status-admin' }

  if (auth.user.vip_active) {
    const remaining = auth.user.vip_remaining || 0
    if (remaining > 86400) {
      return { text: `有效 - 剩余 ${Math.floor(remaining / 86400)} 天`, class: 'status-active' }
    } else if (remaining > 3600) {
      return { text: `有效 - 剩余 ${Math.floor(remaining / 3600)} 小时`, class: 'status-active' }
    } else if (remaining > 60) {
      return { text: `有效 - 剩余 ${Math.floor(remaining / 60)} 分钟`, class: 'status-active' }
    } else if (remaining > 0) {
      return { text: `有效 - 剩余 ${remaining} 秒`, class: 'status-active' }
    }
    return { text: '有效', class: 'status-active' }
  }

  return { text: '已过期', class: 'status-expired' }
})

// 格式化时间
function formatTime(seconds) {
  if (!seconds || seconds <= 0) return '已过期'
  if (seconds > 86400) return `${Math.floor(seconds / 86400)} 天`
  if (seconds > 3600) return `${Math.floor(seconds / 3600)} 小时 ${Math.floor((seconds % 3600) / 60)} 分钟`
  if (seconds > 60) return `${Math.floor(seconds / 60)} 分钟 ${seconds % 60} 秒`
  return `${seconds} 秒`
}

onMounted(async () => {
  await loadData()
})

async function loadData() {
  try {
    const [ordersRes, filesRes] = await Promise.all([
      api.getOrders(),
      api.getFiles()
    ])
    orders.value = ordersRes.orders || []
    files.value = filesRes.files || []
  } catch {
    /* ignore */
  }
}

function goToPay() {
  router.push('/pay')
}
</script>

<template>
  <header class="header">
    <div class="logo">
      <span class="logo-icon">图</span>
      <RouterLink to="/" style="color:inherit;text-decoration:none">图表在线生成器</RouterLink>
    </div>
    <div class="nav-right">
      <RouterLink to="/">返回首页</RouterLink>
    </div>
  </header>

  <div class="profile-page">
    <!-- 用户信息卡片 -->
    <div class="user-card">
      <div class="user-avatar">
        {{ auth.user?.username?.charAt(0)?.toUpperCase() || 'U' }}
      </div>
      <div class="user-info">
        <div class="username">{{ auth.user?.username }}</div>
        <div class="email">{{ auth.user?.email || '未绑定邮箱' }}</div>
        <div class="vip-badge" :class="vipStatus.class">
          {{ vipStatus.text }}
        </div>
      </div>
      <button class="btn-recharge" @click="goToPay">
        立即充值
      </button>
    </div>

    <!-- 会员剩余时间卡片 -->
    <div class="time-card" v-if="auth.user?.vip_active">
      <div class="time-icon">⏰</div>
      <div class="time-info">
        <div class="time-label">会员剩余时间</div>
        <div class="time-value">{{ formatTime(auth.user?.vip_remaining) }}</div>
      </div>
      <div class="time-expire">
        到期时间：{{ auth.user?.vip_expire_time || '永久' }}
      </div>
    </div>

    <!-- 标签页 -->
    <div class="tabs">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'info' }"
        @click="activeTab = 'info'"
      >使用记录</button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'orders' }"
        @click="activeTab = 'orders'"
      >订单记录</button>
    </div>

    <!-- 使用记录 -->
    <div v-if="activeTab === 'info'" class="tab-content">
      <div class="empty-state" v-if="!files.length">
        <div class="empty-icon">📊</div>
        <div class="empty-text">暂无使用记录</div>
        <RouterLink to="/" class="btn-go">去生成图表</RouterLink>
      </div>
      <div v-else class="file-list">
        <div v-for="file in files" :key="file.id" class="file-item">
          <div class="file-icon">📄</div>
          <div class="file-info">
            <div class="file-title">{{ file.title || '未命名图表' }}</div>
            <div class="file-meta">
              <span class="file-type">{{ file.chart_type }}</span>
              <span class="file-time">{{ file.create_time }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 订单记录 -->
    <div v-if="activeTab === 'orders'" class="tab-content">
      <div class="empty-state" v-if="!orders.length">
        <div class="empty-icon">🛒</div>
        <div class="empty-text">暂无订单记录</div>
        <button class="btn-go" @click="goToPay">去购买</button>
      </div>
      <div v-else class="order-list">
        <div v-for="order in orders" :key="order.order_id" class="order-item">
          <div class="order-icon" :class="'status-' + order.pay_status">
            {{ order.pay_status === 'paid' ? '✓' : '○' }}
          </div>
          <div class="order-info">
            <div class="order-name">{{ order.package_name || '套餐' }}</div>
            <div class="order-meta">
              <span class="order-id">{{ order.order_id }}</span>
              <span class="order-time">{{ order.create_time }}</span>
            </div>
          </div>
          <div class="order-amount">¥{{ order.pay_amount }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 800px;
  margin: 30px auto;
  padding: 0 20px 40px;
}

/* 用户卡片 */
.user-card {
  display: flex;
  align-items: center;
  gap: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 30px;
  color: #fff;
  margin-bottom: 20px;
}

.user-avatar {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
}

.user-info {
  flex: 1;
}

.username {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}

.email {
  font-size: 14px;
  opacity: 0.8;
  margin-bottom: 8px;
}

.vip-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.status-active {
  background: rgba(82, 196, 26, 0.3);
  color: #b7eb8f;
}

.status-expired {
  background: rgba(255, 77, 79, 0.3);
  color: #ffa39e;
}

.status-admin {
  background: rgba(255, 215, 0, 0.3);
  color: #ffd700;
}

.btn-recharge {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  border: 2px solid rgba(255, 255, 255, 0.5);
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-recharge:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: #fff;
}

/* 时间卡片 */
.time-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.time-icon {
  font-size: 32px;
}

.time-info {
  flex: 1;
}

.time-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.time-value {
  font-size: 24px;
  font-weight: 700;
  color: #52c41a;
}

.time-expire {
  font-size: 12px;
  color: #999;
}

/* 标签页 */
.tabs {
  display: flex;
  gap: 4px;
  background: #f5f5f5;
  border-radius: 8px;
  padding: 4px;
  margin-bottom: 20px;
}

.tab-btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: all 0.2s;
}

.tab-btn.active {
  background: #fff;
  color: #333;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.tab-content {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 16px;
  color: #999;
  margin-bottom: 20px;
}

.btn-go {
  display: inline-block;
  background: #1890ff;
  color: #fff;
  padding: 10px 24px;
  border-radius: 6px;
  text-decoration: none;
  font-size: 14px;
  border: none;
  cursor: pointer;
}

.btn-go:hover {
  background: #40a9ff;
}

/* 文件列表 */
.file-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.file-icon {
  font-size: 24px;
}

.file-info {
  flex: 1;
}

.file-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.file-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #999;
}

.file-type {
  background: #e6f7ff;
  color: #1890ff;
  padding: 2px 6px;
  border-radius: 4px;
}

/* 订单列表 */
.order-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.order-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
}

.order-icon.status-paid {
  background: #f6ffed;
  color: #52c41a;
}

.order-icon.status-pending {
  background: #fff7e6;
  color: #faad14;
}

.order-info {
  flex: 1;
}

.order-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
}

.order-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #999;
}

.order-amount {
  font-size: 18px;
  font-weight: 700;
  color: #ff4d4f;
}
</style>
