/**
 * API 请求封装
 */
var Api = (function () {
  var BASE_URL = '/api';

  function getToken() {
    return localStorage.getItem('token') || '';
  }

  function request(method, path, data) {
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open(method, BASE_URL + path, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      var token = getToken();
      if (token) xhr.setRequestHeader('Authorization', 'Bearer ' + token);
      xhr.onload = function () {
        try {
          var res = JSON.parse(xhr.responseText);
          if (xhr.status >= 200 && xhr.status < 300) resolve(res);
          else reject(res);
        } catch (e) {
          reject({ error: '响应解析失败' });
        }
      };
      xhr.onerror = function () { reject({ error: '网络错误' }); };
      xhr.send(data ? JSON.stringify(data) : null);
    });
  }

  return {
    get: function (path) { return request('GET', path); },
    post: function (path, data) { return request('POST', path, data); },
    put: function (path, data) { return request('PUT', path, data); },

    login: function (d) { return this.post('/auth/login', d); },
    register: function (d) { return this.post('/auth/register', d); },
    getUserInfo: function () { return this.get('/user/info'); },

    convertJson: function (d) { return this.post('/convert', d); },
    saveFile: function (d) { return this.post('/files', d); },
    getFiles: function () { return this.get('/files'); },

    getPackages: function () { return this.get('/vip/packages'); },
    createOrder: function (d) { return this.post('/orders', d); },
    getOrders: function () { return this.get('/orders'); },

    adminUsers: function () { return this.get('/admin/users'); },
    adminOrders: function () { return this.get('/admin/orders'); },
    adminStats: function () { return this.get('/admin/stats'); },
    adminResetCount: function (id, count) { return this.put('/admin/users/' + id + '/count', { count: count }); },
    adminDisableUser: function (id) { return this.put('/admin/users/' + id + '/disable', {}); },
    adminUpdatePackage: function (id, data) { return this.put('/admin/packages/' + id, data); }
  };
})();
