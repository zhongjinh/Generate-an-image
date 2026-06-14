/**
 * 登录与鉴权
 */
var Auth = (function () {
  var user = null;

  function saveToken(token) { localStorage.setItem('token', token); }
  function clearToken() { localStorage.removeItem('token'); localStorage.removeItem('user'); }
  function getToken() { return localStorage.getItem('token'); }
  function isLoggedIn() { return !!getToken(); }

  function saveUser(u) {
    user = u;
    localStorage.setItem('user', JSON.stringify(u));
  }

  function getUser() {
    if (user) return user;
    try { user = JSON.parse(localStorage.getItem('user')); } catch (e) { user = null; }
    return user;
  }

  function isAdmin() {
    var u = getUser();
    return u && u.is_admin;
  }

  async function login(username, password) {
    try {
      var res = await Api.login({ username: username, password: password });
      if (res.token) {
        saveToken(res.token);
        saveUser(res.user);
        updateUI();
        return { success: true };
      }
      return { success: false, error: res.error || '登录失败' };
    } catch (e) {
      return { success: false, error: e.error || '网络错误，请稍后重试' };
    }
  }

  async function register(username, password, phone) {
    try {
      var res = await Api.register({ username: username, password: password, phone: phone || '' });
      if (res.token) {
        saveToken(res.token);
        saveUser(res.user);
        updateUI();
        return { success: true };
      }
      return { success: false, error: res.error || '注册失败' };
    } catch (e) {
      return { success: false, error: e.error || '网络错误，请稍后重试' };
    }
  }

  function logout() {
    clearToken();
    user = null;
    updateUI();
  }

  async function refreshUser() {
    if (!isLoggedIn()) return;
    try {
      var res = await Api.getUserInfo();
      if (res.user) saveUser(res.user);
      updateUI();
    } catch (e) { /* ignore */ }
  }

  function updateUI() {
    var userInfo = document.getElementById('userInfo');
    var loginArea = document.getElementById('loginArea');
    var userName = document.getElementById('userName');
    var remainCount = document.getElementById('remainCount');
    var adminLink = document.getElementById('adminLink');
    if (!userInfo || !loginArea) return;

    if (isLoggedIn()) {
      var u = getUser();
      userInfo.style.display = 'flex';
      loginArea.style.display = 'none';
      if (userName) userName.textContent = u ? u.username : '';
      var avatar = document.getElementById('userAvatar');
      if (avatar && u) avatar.textContent = (u.username || 'U').charAt(0).toUpperCase();
      if (remainCount) {
        if (u && u.is_admin) {
          remainCount.textContent = '管理员';
        } else {
          remainCount.textContent = '剩余 ' + (u ? u.remain_count || 0 : 0) + ' 次';
        }
      }
      if (adminLink) adminLink.style.display = isAdmin() ? 'inline' : 'none';
    } else {
      userInfo.style.display = 'none';
      loginArea.style.display = 'flex';
      if (adminLink) adminLink.style.display = 'none';
    }
  }

  updateUI();
  if (isLoggedIn()) refreshUser();

  return {
    login: login,
    register: register,
    logout: logout,
    isLoggedIn: isLoggedIn,
    isAdmin: isAdmin,
    getUser: getUser,
    updateUI: updateUI,
    refreshUser: refreshUser
  };
})();
