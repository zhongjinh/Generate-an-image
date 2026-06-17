<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'

const section = ref('stats')
const stats = ref({})
const users = ref([])
const orders = ref([])
const packages = ref([])

onMounted(() => loadStats())

function showSection(name) {
  section.value = name
  if (name === 'stats') loadStats()
  if (name === 'users') loadUsers()
  if (name === 'orders') loadOrders()
  if (name === 'packages') loadPackages()
}

async function loadStats() {
  stats.value = await api.adminStats()
}

async function loadUsers() {
  const r = await api.adminUsers()
  users.value = r.users || []
}

async function loadOrders() {
  const r = await api.adminOrders()
  orders.value = r.orders || []
}

async function loadPackages() {
  const r = await api.getPackages()
  packages.value = r.packages || []
}

async function resetCount(id) {
  const count = prompt('输入新的生成次数:')
  if (count === null) return
  await api.adminResetCount(id, parseInt(count, 10))
  await loadUsers()
}

async function toggleDisable(id) {
  await api.adminDisableUser(id)
  await loadUsers()
}
</script>

<template>
  <header class="header">
    <div class="logo">
      <span class="logo-icon">图</span>
      管理后台
    </div>
    <div class="nav-right"><RouterLink to="/">返回前台</RouterLink></div>
  </header>

  <div class="admin-layout">
    <div class="sidebar">
      <h3>管理菜单</h3>
      <a :class="{ active: section === 'stats' }" @click="showSection('stats')">数据统计</a>
      <a :class="{ active: section === 'users' }" @click="showSection('users')">用户管理</a>
      <a :class="{ active: section === 'orders' }" @click="showSection('orders')">订单管理</a>
      <a :class="{ active: section === 'packages' }" @click="showSection('packages')">套餐配置</a>
    </div>

    <div class="admin-main">
      <div v-show="section === 'stats'" class="section">
        <div class="admin-header"><h2>数据统计</h2></div>
        <div class="stat-cards">
          <div class="stat-card"><div class="label">总用户数</div><div class="value">{{ stats.total_users ?? '-' }}</div></div>
          <div class="stat-card"><div class="label">今日新增</div><div class="value">{{ stats.today_users ?? '-' }}</div></div>
          <div class="stat-card"><div class="label">付费订单</div><div class="value">{{ stats.total_orders ?? '-' }}</div></div>
          <div class="stat-card"><div class="label">总营收(元)</div><div class="value">¥{{ stats.total_revenue?.toFixed?.(2) ?? '-' }}</div></div>
          <div class="stat-card"><div class="label">今日生成</div><div class="value">{{ stats.today_charts ?? '-' }}</div></div>
        </div>
      </div>

      <div v-show="section === 'users'" class="section">
        <div class="admin-header"><h2>用户管理</h2></div>
        <div class="table-wrap">
          <table class="admin-table">
            <thead>
              <tr><th>ID</th><th>用户名</th><th>邮箱</th><th>手机号</th><th>剩余次数</th><th>会员</th><th>状态</th><th>注册时间</th><th>操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="u in users" :key="u.id">
                <td>{{ u.id }}</td>
                <td>{{ u.username }}</td>
                <td>{{ u.email || '-' }}</td>
                <td>{{ u.phone || '-' }}</td>
                <td>{{ u.remain_count }}</td>
                <td>{{ u.vip_type || '普通' }}</td>
                <td>
                  <span v-if="u.is_disabled" class="tag tag-disabled">已禁用</span>
                  <span v-else>正常</span>
                </td>
                <td>{{ u.create_time }}</td>
                <td>
                  <button class="btn-action" @click="resetCount(u.id)">重置次数</button>
                  <button class="btn-action btn-danger" @click="toggleDisable(u.id)">
                    {{ u.is_disabled ? '启用' : '禁用' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-show="section === 'orders'" class="section">
        <div class="admin-header"><h2>订单管理</h2></div>
        <div class="table-wrap">
          <table class="admin-table">
            <thead>
              <tr><th>订单号</th><th>用户</th><th>套餐</th><th>金额</th><th>状态</th><th>创建时间</th></tr>
            </thead>
            <tbody>
              <tr v-for="o in orders" :key="o.order_id">
                <td>{{ o.order_id }}</td>
                <td>{{ o.username }}</td>
                <td>{{ o.package_name || '-' }}</td>
                <td>¥{{ o.pay_amount }}</td>
                <td><span class="tag" :class="'tag-' + o.pay_status">{{ o.pay_status }}</span></td>
                <td>{{ o.create_time }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-show="section === 'packages'" class="section">
        <div class="admin-header"><h2>套餐配置</h2></div>
        <div class="table-wrap">
          <table class="admin-table">
            <thead>
              <tr><th>ID</th><th>名称</th><th>类型</th><th>价格</th><th>次数</th><th>天数</th><th>状态</th></tr>
            </thead>
            <tbody>
              <tr v-for="p in packages" :key="p.id">
                <td>{{ p.id }}</td>
                <td>{{ p.package_name }}</td>
                <td>{{ p.type }}</td>
                <td>¥{{ p.price }}</td>
                <td>{{ p.total_count }}</td>
                <td>{{ p.valid_days }}天</td>
                <td>{{ p.is_enable ? '启用' : '禁用' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
body { overflow: hidden; height: 100vh; }
.admin-layout { display: flex; height: calc(100vh - 52px); }
.sidebar { width: 200px; background: #001529; color: #fff; padding: 20px 0; }
.sidebar h3 { padding: 0 20px; font-size: 16px; margin-bottom: 20px; color: #fff; }
.sidebar a { display: block; padding: 10px 20px; color: #ffffffa0; text-decoration: none; font-size: 14px; cursor: pointer; }
.sidebar a:hover, .sidebar a.active { background: #1890ff; color: #fff; }
.admin-main { flex: 1; padding: 20px; overflow: auto; background: #f0f2f5; }
.admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.admin-header h2 { font-size: 18px; }
.stat-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 20px; }
.stat-card { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.stat-card .label { font-size: 13px; color: #999; }
.stat-card .value { font-size: 28px; font-weight: 700; color: #333; margin-top: 4px; }
.table-wrap { background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.admin-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.admin-table th, .admin-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f0f0; }
.admin-table th { background: #fafafa; font-weight: 600; color: #333; }
.tag { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.tag-paid { background: #f6ffed; color: #52c41a; }
.tag-pending { background: #fff7e6; color: #faad14; }
.tag-disabled { background: #fff2f0; color: #ff4d4f; }
.btn-action { padding: 4px 10px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; font-size: 12px; cursor: pointer; margin-right: 4px; }
.btn-action:hover { border-color: #1890ff; color: #1890ff; }
.btn-danger { border-color: #ff4d4f !important; color: #ff4d4f !important; }
</style>
