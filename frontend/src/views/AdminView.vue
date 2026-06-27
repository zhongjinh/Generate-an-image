<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'

const section = ref('stats')
const stats = ref({})
const users = ref([])
const orders = ref([])
const packages = ref([])

// 兑换码相关
const codes = ref([])
const codeFilter = ref('all')
const genPackageId = ref('')
const genCount = ref(10)
const generating = ref(false)
const generatedCodes = ref([])
const showCodesModal = ref(false)

onMounted(() => loadStats())

function showSection(name) {
  section.value = name
  if (name === 'stats') loadStats()
  if (name === 'users') loadUsers()
  if (name === 'orders') loadOrders()
  if (name === 'packages') loadPackages()
  if (name === 'codes') loadCodes()
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

async function savePackage(pkg) {
  try {
    await api.adminUpdatePackage(pkg.id, {
      package_name: pkg.package_name,
      price: pkg.price,
      total_count: pkg.total_count,
      valid_days: pkg.valid_days,
      buy_link: pkg.buy_link || '',
      is_enable: !!pkg.is_enable,
    })
    alert('保存成功')
  } catch (e) {
    alert(e.error || '保存失败')
  }
}

function formatPkgDays(days) {
  if (!days) return ''
  days = parseFloat(days)
  if (days < 1) return `${Math.round(days * 24)}小时`
  if (days === 1) return '1天'
  if (days < 30) return `${days}天`
  if (days < 365) return `${Math.round(days / 30)}个月`
  return `${Math.round(days / 365)}年`
}

// 兑换码功能
async function loadCodes() {
  await loadPackages()
  const params = {}
  if (codeFilter.value !== 'all') params.status = codeFilter.value
  const r = await api.adminListCodes(params)
  codes.value = r.codes || []
}

async function generateCodes() {
  if (!genPackageId.value) { alert('请选择套餐'); return }
  if (genCount.value < 1 || genCount.value > 500) { alert('数量范围 1-500'); return }

  generating.value = true
  try {
    const r = await api.adminGenerateCodes({ package_id: parseInt(genPackageId.value), count: genCount.value })
    generatedCodes.value = r.codes || []
    showCodesModal.value = true
    await loadCodes()
  } catch (e) {
    alert(e.error || '生成失败')
  } finally {
    generating.value = false
  }
}

async function deleteCode(id) {
  if (!confirm('确定删除该兑换码？')) return
  try {
    await api.adminDeleteCode(id)
    await loadCodes()
  } catch (e) {
    alert(e.error || '删除失败')
  }
}

function copyCodes() {
  const text = generatedCodes.value.join('\n')
  navigator.clipboard.writeText(text).then(() => alert('已复制到剪贴板'))
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
      <a :class="{ active: section === 'codes' }" @click="showSection('codes')">🎫 兑换码</a>
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
        <p class="section-tip">💡 设置「购买链接」后，用户点击购买会跳转到外部发卡平台</p>
        <div class="table-wrap">
          <table class="admin-table">
            <thead>
              <tr><th>ID</th><th>名称</th><th>价格</th><th>时长</th><th>购买链接（留空则本地购买）</th><th>状态</th><th>操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="p in packages" :key="p.id">
                <td>{{ p.id }}</td>
                <td>{{ p.package_name }}</td>
                <td>¥{{ p.price }}</td>
                <td>{{ formatPkgDays(p.valid_days) }}</td>
                <td>
                  <input
                    v-model="p.buy_link"
                    type="text"
                    class="link-input"
                    placeholder="https://发卡平台.com/buy/xxx"
                  />
                </td>
                <td>{{ p.is_enable ? '启用' : '禁用' }}</td>
                <td>
                  <button class="btn-action" @click="savePackage(p)">保存</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 兑换码管理 -->
      <div v-show="section === 'codes'" class="section">
        <div class="admin-header"><h2>兑换码管理</h2></div>

        <!-- 生成兑换码 -->
        <div class="gen-form">
          <div class="gen-row">
            <label>选择套餐：</label>
            <select v-model="genPackageId" class="gen-select">
              <option value="">请选择</option>
              <option v-for="p in packages" :key="p.id" :value="p.id">
                {{ p.package_name }} ({{ formatDuration(p.valid_days) }})
              </option>
            </select>
            <label>数量：</label>
            <input v-model.number="genCount" type="number" min="1" max="500" class="gen-input" />
            <button class="btn-gen" @click="generateCodes" :disabled="generating">
              {{ generating ? '生成中...' : '批量生成' }}
            </button>
          </div>
        </div>

        <!-- 筛选 -->
        <div class="filter-row">
          <button :class="{ active: codeFilter === 'all' }" @click="codeFilter = 'all'; loadCodes()">全部</button>
          <button :class="{ active: codeFilter === 'unused' }" @click="codeFilter = 'unused'; loadCodes()">未使用</button>
          <button :class="{ active: codeFilter === 'used' }" @click="codeFilter = 'used'; loadCodes()">已使用</button>
        </div>

        <!-- 兑换码列表 -->
        <div class="table-wrap">
          <table class="admin-table">
            <thead>
              <tr><th>ID</th><th>兑换码</th><th>套餐</th><th>时长</th><th>状态</th><th>使用者</th><th>使用时间</th><th>操作</th></tr>
            </thead>
            <tbody>
              <tr v-if="!codes.length">
                <td colspan="8" style="text-align:center;color:#999">暂无兑换码</td>
              </tr>
              <tr v-for="c in codes" :key="c.id">
                <td>{{ c.id }}</td>
                <td class="code-cell">{{ c.code }}</td>
                <td>{{ c.package_name || '-' }}</td>
                <td>{{ formatDuration(c.valid_days) }}</td>
                <td>
                  <span v-if="c.is_used" class="tag tag-used">已使用</span>
                  <span v-else class="tag tag-unused">未使用</span>
                </td>
                <td>{{ c.used_by_name || '-' }}</td>
                <td>{{ c.used_at || '-' }}</td>
                <td>
                  <button v-if="!c.is_used" class="btn-action btn-danger" @click="deleteCode(c.id)">删除</button>
                  <span v-else style="color:#999">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <!-- 生成结果弹窗 -->
  <div v-if="showCodesModal" class="modal-overlay" @click.self="showCodesModal = false">
    <div class="modal">
      <div class="modal-header">
        <h3>✅ 生成成功</h3>
        <button class="btn-close" @click="showCodesModal = false">&times;</button>
      </div>
      <div class="modal-body">
        <p>共生成 <strong>{{ generatedCodes.length }}</strong> 个兑换码：</p>
        <textarea class="codes-textarea" readonly :value="generatedCodes.join('\n')"></textarea>
        <button class="btn-copy" @click="copyCodes">📋 复制全部</button>
        <p class="tip">请将兑换码导入独角数卡等发卡平台进行售卖</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-layout { display: flex; min-height: calc(100vh - 52px); }
.sidebar { width: 200px; background: #001529; color: #fff; padding: 20px 0; position: sticky; top: 0; height: calc(100vh - 52px); overflow-y: auto; }
.sidebar h3 { padding: 0 20px; font-size: 16px; margin-bottom: 20px; color: #fff; }
.sidebar a { display: block; padding: 10px 20px; color: #ffffffa0; text-decoration: none; font-size: 14px; cursor: pointer; }
.sidebar a:hover, .sidebar a.active { background: #1890ff; color: #fff; }
.admin-main { flex: 1; padding: 20px; background: #f0f2f5; }
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
.section-tip { font-size: 13px; color: #666; margin: -10px 0 16px; background: #fffbe6; padding: 8px 12px; border-radius: 6px; border: 1px solid #ffe58f; }
.link-input {
  width: 100%;
  min-width: 200px;
  padding: 6px 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 12px;
  outline: none;
}
.link-input:focus { border-color: #1890ff; }

/* 兑换码管理 */
.gen-form {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.gen-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.gen-row label { font-size: 13px; color: #666; }
.gen-select {
  padding: 6px 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 13px;
  min-width: 160px;
}
.gen-input {
  width: 70px;
  padding: 6px 10px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 13px;
}
.btn-gen {
  padding: 6px 20px;
  background: #1890ff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-gen:hover { background: #40a9ff; }
.btn-gen:disabled { background: #ccc; cursor: not-allowed; }

.filter-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.filter-row button {
  padding: 6px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.filter-row button.active {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}

.code-cell {
  font-family: monospace;
  letter-spacing: 1px;
  color: #1890ff;
  font-weight: 600;
}
.tag-used { background: #f0f0f0; color: #999; }
.tag-unused { background: #f6ffed; color: #52c41a; }

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: #fff;
  border-radius: 12px;
  width: 500px;
  max-width: 90%;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}
.modal-header h3 { margin: 0; font-size: 18px; }
.btn-close { background: none; border: none; font-size: 24px; color: #999; cursor: pointer; }
.modal-body { padding: 20px; }
.modal-body p { font-size: 14px; color: #666; margin: 0 0 12px; }
.codes-textarea {
  width: 100%;
  height: 200px;
  padding: 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-family: monospace;
  font-size: 14px;
  letter-spacing: 1px;
  resize: none;
  margin-bottom: 12px;
}
.btn-copy {
  padding: 8px 20px;
  background: #52c41a;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.btn-copy:hover { background: #73d13d; }
.tip { color: #faad14; font-size: 12px; margin-top: 12px !important; }
</style>
