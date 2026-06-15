export const EXAMPLES = {
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