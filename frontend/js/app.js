/**
 * 图表在线生成器 - 主逻辑
 */
var currentXml = '';
var currentScale = 1;
var currentChartType = 'module';

var CHART_TYPES = [
  { id: 'module', name: '功能模块图', icon: '▣' },
  { id: 'usecase', name: '用例图', icon: '◎' },
  { id: 'er', name: 'E-R图', icon: '⬡' },
  { id: 'activity', name: '活动图', icon: '▶' },
  { id: 'architecture', name: '架构图', icon: '▤' },
  { id: 'class', name: '类图', icon: '▦' },
  { id: 'flowchart', name: '流程图', icon: '◇' },
  { id: 'attribute', name: '属性图', icon: '◉' },
  { id: 'sequence', name: '序列图', icon: '⇄' }
];

var EXAMPLES = {
  module: {
    type: 'module',
     "title": "社区电商平台",
  "roles": [
    {
      "name": "用户端",
      "modules": [
        "首页展示",
        "商品搜索",
        "商品分类",
        "商品详情",
        "购物车管理",
        "订单确认",
        "支付结算",
        "订单中心",
        "个人资料",
        "收货地址",
        "优惠券中心",
        "积分商城",
        "商品收藏",
        "商品评价",
        "客服咨询",
        "消息通知"
      ]
    },
    {
      "name": "管理端",
      "modules": [
        "数据看板",
        "商品上架",
        "商品下架",
        "商品分类管理",
        "库存管理",
        "订单处理",
        "订单发货",
        "售后管理",
        "用户列表",
        "用户权限",
        "优惠券发放",
        "满减活动",
        "秒杀活动",
        "轮播图管理",
        "公告管理",
        "系统设置"
      ]
    }
  ]
  },
  usecase: {
    "actor": "车主",
  "use_cases": [
    {
      "name": "故障报修",
      "includes": [
        "提交故障报修",
        "查询报修进度",
        "取消报修"
      ]
    },
    {
      "name": "保养预约",
      "includes": [
        "预约车辆保养",
        "查询预约记录",
        "取消预约"
      ]
    },
    {
      "name": "维修查询",
      "includes": [
        "查询维修订单",
        "查询维修信息"
      ]
    },
    {
      "name": "留言反馈",
      "includes": [
        "留言交流",
        "提交意见反馈"
      ]
    },
    {
      "name": "公告服务",
      "includes": [
        "浏览公告",
        "查看聊天记录"
      ]
    },
    {
      "name": "个人中心",
      "includes": [
        "收藏服务",
        "修改个人信息"
      ]
    }
  ]
  },
  er: {
    type: 'er',
    title: '文创产品 E-R 图',
    center_entity: '文创产品',
    entities: [
      { name: '用户' },
      { name: '文创产品类型' },
      { name: '文创产品' },
      { name: '商家' },
      { name: '订单' },
      { name: '收藏' },
      { name: '评价' },
      { name: '购物车' },
      { name: '地址' }
    ],
    relationships: [
      { from: '文创产品类型', to: '文创产品', name: '包含', cardinality: '1:N' },
      { from: '商家', to: '文创产品', name: '供应', cardinality: '1:N' },
      { from: '用户', to: '订单', name: '创建', cardinality: '1:N' },
      { from: '地址', to: '订单', name: '关联', cardinality: '1:N' },
      { from: '用户', to: '收藏', name: '添加', cardinality: '1:N' },
      { from: '文创产品', to: '收藏', name: '被收藏', cardinality: '1:N' },
      { from: '用户', to: '评价', name: '发表', cardinality: '1:N' },
      { from: '订单', to: '评价', name: '获得', cardinality: '1:N' },
      { from: '文创产品', to: '评价', name: '被评价', cardinality: '1:N' },
      { from: '用户', to: '购物车', name: '拥有', cardinality: '1:N' },
      { from: '文创产品', to: '购物车', name: '加入', cardinality: '1:N' },
      { from: '用户', to: '地址', name: '拥有', cardinality: '1:N' }
    ]
  },
  activity: {
    type: 'activity',
    title: '用户登录活动图',
    nodes: [
      { name: '开始', type: 'start' },
      { name: '输入信息', type: 'action' },
      { name: '验证', type: 'action' },
      { name: '通过？', type: 'decision' },
      { name: '进入系统', type: 'action' },
      { name: '结束', type: 'end' }
    ],
    flows: [
      { from: '开始', to: '输入信息' },
      { from: '输入信息', to: '验证' },
      { from: '验证', to: '通过？' },
      { from: '通过？', to: '进入系统', label: '是' },
      { from: '通过？', to: '输入信息', label: '否', dashed: true },
      { from: '进入系统', to: '结束' }
    ]
  },
  architecture: {
    type: 'architecture',
    title: '戏曲文化传播平台系统架构图',
    links: ['HTTP/HTTPS', 'JDBC/SQL'],
    layers: [
      {
        name: '前端交互层',
        groups: [
          { name: '用户端', nodes: ['注册登录', '戏曲浏览与视频观看', '问答交流与评论', '公告查看与反馈'] },
          { name: '管理员端', nodes: ['用户管理', '戏曲分类/内容/视频管理', '问答评论审核', '公告与反馈管理'] }
        ]
      },
      {
        name: '后端业务层',
        groups: [
          { name: '业务接口', nodes: ['用户鉴权', '角色拦截'] },
          { name: '业务逻辑', nodes: ['内容审核与发布', '视频资源管理'] },
          { name: '本地缓存', nodes: ['会话存储', '热点戏曲数据'] }
        ]
      },
      {
        name: '数据持久层',
        groups: [
          { name: 'MySQL', nodes: ['用户与管理员数据', '戏曲分类/内容/视频数据', '问答/回答/评论数据', '公告与反馈数据'] },
          { name: 'Redis', nodes: ['会话存储', '热点戏曲数据'] }
        ]
      }
    ]
  },
  class: {
    type: 'class',
    title: '面向对象设计类图',
    classes: [
      {
        name: 'Animal',
        attributes: ['- name: String', '- age: int'],
        methods: ['+ eat(): void', '+ sleep(): void']
      },
      {
        name: 'Dog',
        attributes: ['- breed: String'],
        methods: ['+ bark(): void']
      }
    ],
    relationships: [
      { from: 'Dog', to: 'Animal', type: 'inheritance' }
    ]
  },
  flowchart: {
    type: 'flowchart',
    title: '用户登录流程',
    steps: [
      { id: 1, type: '开始', text: '开始' },
      { id: 2, type: '输入', text: '输入账号密码' },
      { id: 3, type: '处理', text: '验证账号' },
      { id: 4, type: '判断', text: '验证通过？', branches: { '否': 2 } },
      { id: 5, type: '处理', text: '加载用户信息' },
      { id: 6, type: '输出', text: '跳转首页' },
      { id: 7, type: '结束', text: '结束' }
    ]
  },
  attribute: {
    type: 'attribute',
    title: '用户实体属性图',
    tables: [
      {
        name: 'user',
        comment: '用户',
        columns: [
          { name: 'user_id', pk: true, comment: '用户ID' },
          { name: 'username', comment: '用户名' },
          { name: 'password', comment: '密码' },
          { name: 'nickname', comment: '昵称' },
          { name: 'real_name', comment: '真实姓名' },
          { name: 'gender', comment: '性别' },
          { name: 'phone', comment: '手机号' },
          { name: 'email', comment: '邮箱' },
          { name: 'avatar', comment: '头像' },
          { name: 'birthday', comment: '生日' },
          { name: 'role', comment: '角色' },
          { name: 'balance', comment: '账户余额' },
          { name: 'last_login', comment: '最后登录时间' }
        ]
      }
    ]
  },
  sequence: {
    type: 'sequence',
    title: '用户登录序列图',
    participants: [
      { id: 'user', name: '用户' },
      { id: 'frontend', name: '前端' },
      { id: 'api', name: '登录接口' },
      { id: 'auth', name: '认证服务' },
      { id: 'db', name: '数据库' }
    ],
    messages: [
      { from: 'user', to: 'frontend', label: '输入账号密码' },
      { from: 'frontend', to: 'api', label: 'POST /api/login' },
      { from: 'api', to: 'auth', label: '校验账号密码' },
      { from: 'auth', to: 'db', label: '查询用户信息' },
      { from: 'db', to: 'auth', label: '返回用户信息', type: 'return' },
      { from: 'auth', to: 'api', label: '校验成功', type: 'return' },
      { from: 'api', to: 'frontend', label: '200 OK', type: 'return' },
      { from: 'frontend', to: 'user', label: '跳转首页', type: 'return' }
    ]
  }
};

document.addEventListener('DOMContentLoaded', function () {
  initChartNav();
  loadExample();
});

function initChartNav() {
  var list = document.getElementById('chartNavList');
  if (!list) return;
  list.innerHTML = '';
  CHART_TYPES.forEach(function (item) {
    var li = document.createElement('li');
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'chart-nav-item' + (item.id === currentChartType ? ' active' : '');
    btn.setAttribute('data-type', item.id);
    btn.innerHTML = '<span class="chart-nav-icon">' + item.icon + '</span><span>' + item.name + '</span>';
    btn.onclick = function () { selectChartType(item.id); };
    li.appendChild(btn);
    list.appendChild(li);
  });
}

function selectChartType(type) {
  currentChartType = type;
  document.querySelectorAll('.chart-nav-item').forEach(function (el) {
    el.classList.toggle('active', el.getAttribute('data-type') === type);
  });
  var chart = null;
  for (var i = 0; i < CHART_TYPES.length; i++) {
    if (CHART_TYPES[i].id === type) { chart = CHART_TYPES[i]; break; }
  }
  var badge = document.getElementById('currentChartName');
  if (badge && chart) badge.textContent = chart.name;
  loadExample();
  currentXml = '';
}

function switchChartType() {
  selectChartType(currentChartType);
}

function loadExample() {
  var type = currentChartType;
  var example = EXAMPLES[type];
  if (!example) return;
  document.getElementById('jsonEditor').textContent = JSON.stringify(example, null, 2);
  hideError();
}

function formatJson() {
  var editor = document.getElementById('jsonEditor');
  var text = editor.textContent.trim();
  if (!text) return;
  try {
    editor.textContent = JSON.stringify(JSON.parse(text), null, 2);
    hideError();
  } catch (e) {
    showError('JSON 解析错误: ' + e.message);
  }
}

function uploadJson() {
  document.getElementById('fileInput').click();
}

function handleFile(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function (e) {
    document.getElementById('jsonEditor').textContent = e.target.result;
    hideError();
  };
  reader.readAsText(file);
  event.target.value = '';
}

function doConvert() {
  if (!Auth.isLoggedIn()) {
    showError('请先登录后再生成图表');
    showLogin();
    return;
  }

  var editor = document.getElementById('jsonEditor');
  var jsonStr = editor.textContent.trim();
  if (!jsonStr) {
    showError('请输入 JSON 配置');
    return;
  }

  try {
    JSON.parse(jsonStr);
  } catch (e) {
    showError('JSON 解析错误: ' + e.message);
    return;
  }

  hideError();

  convertJsonToXml(jsonStr).then(function (xml) {
    currentXml = xml;
    currentScale = 1;
    Xml2Chart.render(currentXml, document.getElementById('renderArea'));
  }).catch(function (e) {
    var msg = e.error || e.message || String(e);
    showError(msg);
    if (msg.indexOf('登录') !== -1 || msg.indexOf('次数') !== -1) {
      Auth.refreshUser();
    }
  });
}

function convertJsonToXml(jsonStr) {
  return Api.convertJson({ json_content: jsonStr }).then(function (data) {
    if (data.remain_count !== undefined) {
      var u = Auth.getUser();
      if (u && !u.is_admin) {
        u.remain_count = data.remain_count;
        localStorage.setItem('user', JSON.stringify(u));
        Auth.updateUI();
      }
    }
    return data.xml;
  });
}

function exportAs(format) {
  if (!currentXml) {
    alert('请先渲染图表');
    return;
  }
  switch (format) {
    case 'svg': ExportImg.svg(); break;
    case 'png': ExportImg.png(); break;
    case 'jpg': ExportImg.jpg(); break;
  }
}

function zoomIn() {
  currentScale = Math.min(currentScale + 0.2, 3);
  applyScale();
}

function zoomOut() {
  currentScale = Math.max(currentScale - 0.2, 0.3);
  applyScale();
}

function resetView() {
  currentScale = 1;
  applyScale();
}

function applyScale() {
  var container = document.getElementById('renderArea');
  var mxgraph = container.querySelector('.mxgraph');
  if (mxgraph) {
    mxgraph.style.transform = 'scale(' + currentScale + ')';
    mxgraph.style.transformOrigin = 'top center';
  }
}

function showError(msg) {
  var el = document.getElementById('jsonError');
  el.textContent = msg;
  el.style.display = 'block';
}

function hideError() {
  document.getElementById('jsonError').style.display = 'none';
}

function showLogin() {
  openAuthModal('login');
}

function showRegister() {
  openAuthModal('register');
}

function openAuthModal(tab) {
  clearAuthMessages();
  document.getElementById('authModal').style.display = 'flex';
  switchAuthTab(tab || 'login');
}

function closeAuthModal() {
  document.getElementById('authModal').style.display = 'none';
  clearAuthMessages();
  document.getElementById('loginPass').value = '';
  document.getElementById('regPass').value = '';
}

function onAuthOverlayClick(e) {
  if (e.target.id === 'authModal') closeAuthModal();
}

function switchAuthTab(tab) {
  var isLogin = tab === 'login';
  document.getElementById('tabLogin').classList.toggle('active', isLogin);
  document.getElementById('tabRegister').classList.toggle('active', !isLogin);
  document.getElementById('loginForm').style.display = isLogin ? 'block' : 'none';
  document.getElementById('registerForm').style.display = isLogin ? 'none' : 'block';
  document.getElementById('authModalTitle').textContent = isLogin ? '欢迎回来' : '创建账号';
  document.getElementById('authModalSubtitle').textContent = isLogin
    ? '登录后即可生成专业图表'
    : '注册即赠送 1 次免费生成次数';
  clearAuthMessages();
}

function clearAuthMessages() {
  var err = document.getElementById('authFormError');
  var ok = document.getElementById('authFormSuccess');
  err.textContent = '';
  err.classList.remove('show');
  ok.textContent = '';
  ok.classList.remove('show');
  document.querySelectorAll('.form-group input').forEach(function (inp) {
    inp.classList.remove('error');
  });
}

function showAuthError(msg) {
  var el = document.getElementById('authFormError');
  el.textContent = msg;
  el.classList.add('show');
  document.getElementById('authFormSuccess').classList.remove('show');
}

function showAuthSuccess(msg) {
  var el = document.getElementById('authFormSuccess');
  el.textContent = msg;
  el.classList.add('show');
  document.getElementById('authFormError').classList.remove('show');
}

function setAuthLoading(btnId, loading) {
  var btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  if (loading) {
    btn.dataset.originalText = btn.textContent;
    btn.textContent = '处理中...';
  } else if (btn.dataset.originalText) {
    btn.textContent = btn.dataset.originalText;
  }
}

async function doLogin(e) {
  if (e) e.preventDefault();
  clearAuthMessages();

  var u = document.getElementById('loginUser').value.trim();
  var p = document.getElementById('loginPass').value;

  if (!u) {
    showAuthError('请输入用户名');
    document.getElementById('loginUser').classList.add('error');
    return;
  }
  if (!p) {
    showAuthError('请输入密码');
    document.getElementById('loginPass').classList.add('error');
    return;
  }

  setAuthLoading('loginBtn', true);
  var res = await Auth.login(u, p);
  setAuthLoading('loginBtn', false);

  if (res.success) {
    document.getElementById('loginPass').value = '';
    closeAuthModal();
  } else {
    var msg = res.error || '登录失败';
    if (msg.indexOf('密码') !== -1 || msg.indexOf('用户名') !== -1) {
      showAuthError(msg);
      document.getElementById('loginPass').classList.add('error');
    } else {
      showAuthError(msg);
    }
  }
}

async function doRegister(e) {
  if (e) e.preventDefault();
  clearAuthMessages();

  var u = document.getElementById('regUser').value.trim();
  var p = document.getElementById('regPass').value;
  var phone = document.getElementById('regPhone').value.trim();

  if (!u) {
    showAuthError('请输入用户名');
    document.getElementById('regUser').classList.add('error');
    return;
  }
  if (u.length < 3 || u.length > 20) {
    showAuthError('用户名长度须为 3-20 位');
    document.getElementById('regUser').classList.add('error');
    return;
  }
  if (!p) {
    showAuthError('请输入密码');
    document.getElementById('regPass').classList.add('error');
    return;
  }
  if (p.length < 6) {
    showAuthError('密码至少 6 位');
    document.getElementById('regPass').classList.add('error');
    return;
  }

  setAuthLoading('registerBtn', true);
  var res = await Auth.register(u, p, phone);
  setAuthLoading('registerBtn', false);

  if (res.success) {
    showAuthSuccess('注册成功！已赠送 1 次免费生成次数');
    setTimeout(function () { closeAuthModal(); }, 1200);
  } else {
    showAuthError(res.error || '注册失败');
    if ((res.error || '').indexOf('用户名') !== -1) {
      document.getElementById('regUser').classList.add('error');
    }
  }
}
