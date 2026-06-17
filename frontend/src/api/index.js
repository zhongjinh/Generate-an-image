const BASE_URL = '/api'
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
  saveFile: (d) => request('POST', '/files', d),
  getFiles: () => request('GET', '/files'),

  getPackages: () => request('GET', '/vip/packages'),
  createOrder: (d) => request('POST', '/orders', d),
  getOrders: () => request('GET', '/orders'),

  adminUsers: () => request('GET', '/admin/users'),
  adminOrders: () => request('GET', '/admin/orders'),
  adminStats: () => request('GET', '/admin/stats'),
  adminResetCount: (id, count) => request('PUT', `/admin/users/${id}/count`, { count }),
  adminDisableUser: (id) => request('PUT', `/admin/users/${id}/disable`, {}),
  adminUpdatePackage: (id, data) => request('PUT', `/admin/packages/${id}`, data)
}
