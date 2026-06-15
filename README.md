# 图表在线生成器

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)

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

### 1. 配置环境变量

```bash
cp .env.example .env
```

**所有配置项均为必填**，`.env` 不存在或任一项为空/无效时，服务无法启动。请编辑 `.env` 填写全部值（尤其是 `JWT_SECRET`、`ADMIN_PASSWORD`、`CONVERT_API_KEY`）。

### 2. 安装依赖

```bash
# 后端
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 3. 开发模式（两个终端）

```bash
# 终端 1：启动 FastAPI 后端
python run.py

# 终端 2：启动 Vue 开发服务器（自动代理 /api）
cd frontend
npm run dev
```

访问 http://127.0.0.1:5173

### 4. 生产模式

```bash
cd frontend && npm run build
python run.py
```

访问 http://127.0.0.1:8765（后端同时托管前端打包产物）

首次启动自动创建数据库，管理员账号为 `admin`，密码为 `.env` 中的 `ADMIN_PASSWORD`。

## 环境配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `APP_ENV` | 环境，仅 `development` 或 `production` | `development` |
| `HOST` | 监听地址 | `127.0.0.1` |
| `PORT` | 监听端口（1-65535） | `8765` |
| `JWT_SECRET` | JWT 签名密钥 | 32 位以上随机字符串 |
| `ADMIN_PASSWORD` | 管理员 `admin` 的密码 | 自行设置 |
| `REGISTER_FREE_COUNT` | 新用户注册赠送次数 | `1` |
| `CONVERT_API_KEY` | 转换服务 API 密钥 | 自行设置 |
| `CONVERT_PORT` | 独立转换服务端口 | `5000` |
| `PUBLIC_CONVERT` | 转换接口是否公开，`1` 或 `0` | `1` |

## 项目结构

```
├── frontend/              # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── views/         # 页面（首页 / 会员 / 管理后台）
│   │   ├── components/    # 公共组件
│   │   ├── stores/        # Pinia 状态
│   │   ├── api/           # API 请求
│   │   └── utils/         # 图表渲染、导出
│   └── public/            # draw.io 静态渲染器
├── backend/               # FastAPI 后端
│   ├── main.py            # 应用入口
│   ├── routers/           # API 路由
│   ├── auth.py            # JWT 认证
│   ├── config.py          # 配置管理
│   ├── db.py              # 数据库操作
│   └── python_convert/    # JSON → draw.io XML 转换引擎
├── data/                  # 运行时数据（SQLite，已忽略）
├── run.py                 # 启动入口
├── requirements.txt       # Python 依赖
├── .env                   # 本地配置（必填，已忽略）
└── .env.example           # 配置模板
```

## API 文档

开发环境启动后访问：http://127.0.0.1:8765/api/docs

## 技术栈

- **前端**：Vue 3 + Vite + Vue Router + Pinia + draw.io 静态渲染器
- **后端**：FastAPI + SQLite
- **图表引擎**：JSON → draw.io XML → SVG 渲染

## 第三方许可

本项目使用以下第三方库，其许可证文件见 `third-party-licenses/` 目录：

- [draw.io](https://github.com/jgraph/drawio) — Apache 2.0 License（图表渲染器 `viewer-static.min.js`）
- [DOMPurify](https://github.com/cure53/DOMPurify) — Apache 2.0 / MPL 2.0（HTML 净化）
- [pako](https://github.com/nodeca/pako) — MIT / Zlib（压缩解压）
