<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const packages = ref([])
const orders = ref([])

const userInfoText = computed(() => {
  const u = auth.user
  if (!u) return ''
  const count = u.is_admin ? '无限' : u.remain_count
  return `${u.username} · 剩余 ${count} 次`
})

onMounted(async () => {
  await loadPackages()
  await loadOrders()
})

async function loadPackages() {
  const r = await api.getPackages()
  packages.value = r.packages || []
}

async function loadOrders() {
  const r = await api.getOrders()
  orders.value = r.orders || []
}

async function buyPkg(id) {
  if (!confirm('确认购买该套餐？（演示环境将自动完成支付）')) return
  try {
    const r = await api.createOrder({ package_id: id })
    alert(r.message || '购买成功')
    if (r.user) auth.updateUser(r.user)
    await loadOrders()
  } catch (e) {
    alert(e.error || '购买失败')
  }
}
</script>

<template>
  <header class="header">
    <div class="logo">
      <span class="logo-icon">图</span>
      <RouterLink to="/" style="color:inherit;text-decoration:none">图表在线生成器</RouterLink>
    </div>
    <div class="nav-right">
      <span style="font-size:13px">{{ userInfoText }}</span>
      <RouterLink to="/">返回首页</RouterLink>
    </div>
  </header>

  <div class="pay-page">
    <h2>选择会员套餐</h2>
    <div class="packages">
      <div
        v-for="p in packages"
        :key="p.id"
        class="pkg-card"
        :class="{ recommended: p.type === 'month' }"
      >
        <div v-if="p.type === 'month'" class="badge">推荐</div>
        <div class="name">{{ p.package_name }}</div>
        <div class="price">¥{{ p.price }}<span> / {{ p.valid_days }}天</span></div>
        <div class="info">生成次数: {{ p.total_count }} 次<br>有效期: {{ p.valid_days }} 天</div>
        <button class="btn-buy" @click="buyPkg(p.id)">立即购买</button>
      </div>
    </div>

    <div class="history">
      <h3>充值记录</h3>
      <table class="pay-table">
        <thead>
          <tr><th>订单号</th><th>套餐</th><th>金额</th><th>状态</th><th>时间</th></tr>
        </thead>
        <tbody>
          <tr v-if="!orders.length">
            <td colspan="5" style="text-align:center;color:#999">暂无记录</td>
          </tr>
          <tr v-for="o in orders" :key="o.order_id">
            <td>{{ o.order_id }}</td>
            <td>{{ o.package_name || '-' }}</td>
            <td>¥{{ o.pay_amount }}</td>
            <td>
              <span class="tag" :class="'tag-' + o.pay_status">
                {{ o.pay_status === 'paid' ? '已支付' : '待支付' }}
              </span>
            </td>
            <td>{{ o.create_time }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
body { overflow: auto; height: auto; }
.pay-page { max-width: 900px; margin: 40px auto; padding: 0 20px 40px; }
.pay-page h2 { text-align: center; margin-bottom: 30px; font-size: 22px; color: #333; }
.packages { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
.pkg-card { background: #fff; border-radius: 12px; padding: 24px; text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,.06); border: 2px solid transparent; transition: .2s; }
.pkg-card:hover { border-color: #1890ff; transform: translateY(-2px); }
.pkg-card.recommended { border-color: #faad14; }
.pkg-card .badge { display: inline-block; background: #faad14; color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 10px; margin-bottom: 8px; }
.pkg-card .name { font-size: 18px; font-weight: 700; color: #333; margin-bottom: 8px; }
.pkg-card .price { font-size: 32px; font-weight: 700; color: #1890ff; margin-bottom: 4px; }
.pkg-card .price span { font-size: 14px; color: #999; }
.pkg-card .info { font-size: 13px; color: #666; line-height: 1.8; }
.pkg-card .btn-buy { margin-top: 16px; padding: 10px 24px; border: none; border-radius: 6px; background: #1890ff; color: #fff; font-size: 14px; cursor: pointer; width: 100%; }
.pkg-card .btn-buy:hover { background: #40a9ff; }
.history { margin-top: 40px; background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,.06); }
.history h3 { font-size: 16px; margin-bottom: 12px; }
.pay-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.pay-table th, .pay-table td { padding: 10px; text-align: left; border-bottom: 1px solid #f0f0f0; }
.pay-table th { background: #fafafa; font-weight: 600; }
.tag { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.tag-paid { background: #f6ffed; color: #52c41a; }
.tag-pending { background: #fff7e6; color: #faad14; }
</style>
