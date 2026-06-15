const BASE_URL = '/api'

function getToken() {
  return localStorage.getItem('token') || ''
}

async function request(method, path, data) {
  const res = await fetch(BASE_URL + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {})
    },
    body: data ? JSON.stringify(data) : undefined
  })

  let body
  try {
    body = await res.json()
  } catch {
    throw { error: '响应解析失败' }
  }

  if (res.ok) return body
  throw body
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, data) => request('POST', path, data),
  put: (path, data) => request('PUT', path, data),

  login: (d) => request('POST', '/auth/login', d),
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
