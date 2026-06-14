# 图表在线生成器

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?logo=javascript&logoColor=black)
![draw.io](https://img.shields.io/badge/draw.io-Renderer-F08705?logo=diagrams.net&logoColor=white)

通过编写 JSON 配置，在线生成专业图表，支持导出 SVG / PNG / JPG。

## 支持的图表类型

| 类型 | 标识 | 说明 |
|------|------|------|
| 功能模块图 | `module` | 系统功能模块划分 |
| 用例图 | `usecase` | UML 用例图 |
| E-R 图 | `er` | 实体关系图 |
| 活动图 | `activity` | UML 活动图 |
| 架构图 | `architecture` | 系统架构图 |
| 类图 | `class` | UML 类图 |
| 流程图 | `flowchart` | 通用流程图 |
| 属性图 | `attribute` | 数据属性图 |
| 序列图 | `sequence` | UML 时序图 |

## 快速开始

```bash
# 启动服务
python run.py

# 访问
# http://127.0.0.1:8765
```

首次启动自动创建数据库，管理员账号密码见控制台输出。

## 环境配置

复制模板并填写：

```bash
cp .env.example .env
```

| 配置项 | 说明 | 开发默认值 |
|--------|------|-----------|
| `APP_ENV` | 环境 (`development` / `production`) | `development` |
| `HOST` | 监听地址 | `127.0.0.1` |
| `PORT` | 监听端口 | `8765` |
| `JWT_SECRET` | JWT 签名密钥 | 自动生成 |
| `ADMIN_PASSWORD` | 管理员密码 | `admin123` |
| `CONVERT_API_KEY` | 转换服务密钥 | 自动生成 |

生产环境必须设置 `JWT_SECRET` 和 `CONVERT_API_KEY`，否则启动报错。

## 项目结构

```
├── frontend/              # 前端代码
│   ├── index.html         # 主页面（JSON 编辑器 + 图表预览）
│   ├── admin.html         # 管理后台
│   ├── pay.html           # 会员购买页
│   ├── css/
│   └── js/
├── backend/               # 后端代码
│   ├── server.py          # HTTP 服务 & API 路由
│   ├── auth.py            # JWT 认证
│   ├── config.py          # 配置管理
│   ├── db.py              # 数据库操作
│   └── python_convert/    # JSON → draw.io XML 转换引擎
│       ├── json2xml.py    # 转换入口
│       ├── adapters.py    # 输入归一化
│       ├── builders/      # 各图表类型构建器
│       └── schema/        # JSON Schema & 示例
├── data/                  # 运行时数据（SQLite，已忽略）
├── third-party-licenses/  # 第三方库许可证
├── run.py                 # 启动入口
├── .env                   # 本地配置（已忽略）
├── .env.example           # 配置模板
└── requirements.txt       # Python 依赖
```


## 第三方许可

本项目使用以下第三方库，其许可证文件见 `third-party-licenses/` 目录：

- [draw.io](https://github.com/jgraph/drawio) — Apache 2.0 License（图表渲染器 `viewer-static.min.js`）
- [DOMPurify](https://github.com/cure53/DOMPurify) — Apache 2.0 / MPL 2.0（HTML 净化）
- [pako](https://github.com/nodeca/pako) — MIT / Zlib（压缩解压）

## 技术栈

- **前端**：原生 HTML / CSS / JavaScript + draw.io 静态渲染器
- **后端**：Python 标准库（`http.server` + `sqlite3`）
- **图表引擎**：JSON → draw.io XML → SVG 渲染
