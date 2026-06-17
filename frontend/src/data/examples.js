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
    title: '论坛发帖功能活动图',
    nodes: [
      { match_text: '用户', text: '用户' },
      { match_text: '系统', text: '后台系统' },
      { match_text: '数据库', text: '数据库' },
      { match_text: '登录后台系统', text: '登录系统' },
      { match_text: '进入商家入驻审核模块', text: '进入交流论坛' },
      { match_text: '校验资料完整性', text: '敏感词与内容校验' },
      { match_text: '查看待审核资料', text: '填写帖子标题与内容' },
      { match_text: '资料是否完整？', text: '内容是否包含敏感词？' },
      { match_text: '更新商家状态', text: '保存帖子数据\n增加用户积分' },
      { match_text: '标注驳回原因', text: '显示违规内容提示' },
      { match_text: '同步结果至前端', text: '返回发布结果' }
    ],
    links: [
      { match_text: '是', text: '是' },
      { match_text: '否', text: '否' }
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
    plantuml: [
      '@startuml',
      '!pragma theme plain',
      'skinparam backgroundColor white',
      'skinparam actorBackgroundColor white',
      'skinparam participantBackgroundColor white',
      'skinparam databaseBackgroundColor white',
      'skinparam sequenceMessageAlign center',
      'skinparam maxMessageSize 1200',
      'skinparam ArrowColor black',
      'skinparam LifeLineBackgroundColor white',
      '',
      'actor "用户" as User #white',
      'participant "前端" as Frontend #white',
      'participant "登录接口" as LoginAPI #white',
      'participant "认证服务" as AuthService #white',
      'database "数据库" as DB #white',
      '',
      'activate User #white',
      '',
      'User -> Frontend: 1. 输入账号学号与密码',
      'activate Frontend #white',
      '',
      'Frontend -> LoginAPI: 2. POST /api/login\\n账号与密码',
      'activate LoginAPI #white',
      '',
      'LoginAPI -> AuthService: 3. 校验账号密码',
      'activate AuthService #white',
      '',
      'AuthService -> DB: 4. 查询用户信息',
      'activate DB #white',
      'DB --> AuthService: 5. 返回用户信息含角色',
      'deactivate DB',
      '',
      'AuthService -> AuthService: 6. 生成会话或令牌',
      'activate AuthService #white',
      'deactivate AuthService',
      '',
      'AuthService --> LoginAPI: 7. 校验成功返回用户信息与令牌',
      'deactivate AuthService',
      '',
      'LoginAPI --> Frontend: 8. 200 OK 含 token role menus',
      'deactivate LoginAPI',
      '',
      'Frontend -> Frontend: 9. 保存认证信息',
      'activate Frontend #white',
      'deactivate Frontend',
      '',
      'Frontend -> Frontend: 10. 按角色加载可访问菜单',
      'activate Frontend #white',
      'deactivate Frontend',
      '',
      'Frontend --> User: 11. 跳转首页',
      'deactivate Frontend',
      '',
      'deactivate User',
      '@enduml'
    ].join('\n')
  }
};