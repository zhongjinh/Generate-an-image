#!/bin/bash
# 在服务器项目根目录执行: bash deploy/baota/deploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "==> 项目目录: $ROOT"

if [ ! -f .env ]; then
  echo "错误: 请先创建 .env（可参考 deploy/baota/env.production.example）"
  exit 1
fi

# Python 虚拟环境
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt

# 前端构建（需提前 export VITE_* 环境变量）
if [ -z "${VITE_APP_CLIENT_TOKEN:-}" ]; then
  echo "警告: 未设置 VITE_APP_CLIENT_TOKEN，请先 export 再构建"
  echo "  export VITE_APP_CLIENT_TOKEN=与.env中APP_CLIENT_TOKEN相同"
  exit 1
fi

cd frontend
npm install
npm run build
cd "$ROOT"

echo "==> 前端已构建到 frontend/dist"

# 试启动健康检查
source venv/bin/activate
python -c "from backend.main import app; print('后端加载 OK:', app.title)"

echo ""
echo "部署准备完成。请在宝塔 Supervisor 中启动/重启 diagram-api，并重载 Nginx。"
