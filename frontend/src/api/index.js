const BASE_URL = import.meta.env.VITE_API_BASE || '/api'
const CLIENT_TOKEN = import.meta.env.VITE_APP_CLIENT_TOKEN || ''
const DEFAULT_TIMEOUT_MS = 20000

function getToken() {
  return localStorage.getItem('token') || ''
}

async function request(method, path, data, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(BASE_URL + path, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(CLIENT_TOKEN ? { 'X-Client-Token': CLIENT_TOKEN } : {}),
        ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {})
      },
      body: data ? JSON.stringify(data) : undefined,
      signal: controller.signal
    })

    let body
    try {
      body = await res.json()
    } catch {
      throw { error: '响应解析失败' }
    }

    if (res.ok) return body
    throw body
  } catch (e) {
    if (e?.name === 'AbortError') {
      throw { error: '请求超时，请检查网络或稍后重试' }
    }
    throw e
  } finally {
    clearTimeout(timer)
  }
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, data) => request('POST', path, data),
  put: (path, data) => request('PUT', path, data),

  login: (d) => request('POST', '/auth/login', d),
  sendCode: (d) => request('POST', '/auth/send-code', d),
  register: (d) => request('POST', '/auth/register', d),
  getUserInfo: () => request('GET', '/user/info'),

  convertJson: (d) => request('POST', '/convert', d),
  convertExample: (d) => request('POST', '/convert-example', d),
  convertText: (d) => request('POST', '/convert-text', d),
  convertTextExample: () => request('POST', '/convert-text-example'),
  convertAi: (d, timeoutMs = 120000) => request('POST', '/convert-ai', d, timeoutMs),
  convertAiExample: () => request('POST', '/convert-ai-example'),
  saveFile: (d) => request('POST', '/files', d),
  getFiles: () => request('GET', '/files'),

  getInviteCode: () => request('GET', '/invite/code'),
  acceptInvite: (d) => request('POST', '/invite/accept', d),
  getInviteStatus: () => request('GET', '/invite/status'),

  getPackages: () => request('GET', '/vip/packages'),
  createOrder: (d) => request('POST', '/orders', d),
  getOrders: () => request('GET', '/orders'),

  redeemCode: (d) => request('POST', '/redeem', d),
  redeemHistory: () => request('GET', '/redeem/history'),
  shopBuy: (d) => request('POST', '/shop/buy', d),

  createPayment: (d) => request('POST', '/payment/create', d),
  checkPayment: (orderId) => request('GET', `/payment/check/${orderId}`),

  adminUsers: () => request('GET', '/admin/users'),
  adminOrders: () => request('GET', '/admin/orders'),
  adminStats: () => request('GET', '/admin/stats'),
  adminResetCount: (id, count) => request('PUT', `/admin/users/${id}/count`, { count }),
  adminDisableUser: (id) => request('PUT', `/admin/users/${id}/disable`, {}),
  adminUpdatePackage: (id, data) => request('PUT', `/admin/packages/${id}`, data),
  adminGenerateCodes: (d) => request('POST', '/redeem/admin/generate', d),
  adminListCodes: (params) => {
    const qs = new URLSearchParams(params).toString()
    return request('GET', '/redeem/admin/list' + (qs ? '?' + qs : ''))
  },
  adminDeleteCode: (id) => request('DELETE', `/redeem/admin/${id}`)
}
