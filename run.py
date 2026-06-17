#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图表在线生成器 - 启动入口"""

import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.config import ADMIN_PASSWORD, ENV, HOST, PORT, ROOT
from backend.converter import HAS_CONVERTER
from backend.db import init_db


def main():
    init_db()
    print("=" * 50)
    print(f"  图表在线生成器 [{ENV}]  ·  FastAPI")
    print("=" * 50)
    print(f"目录: {ROOT}")
    print(f"数据库: {ROOT / 'data' / 'app.db'}")
    print(f"管理员: admin / {ADMIN_PASSWORD}")
    print(f"转换模块: {'可用' if HAS_CONVERTER else '不可用'}")
    print(f"API: http://{HOST}:{PORT}/api/health")
    print(f"文档: http://{HOST}:{PORT}/api/docs")
    print("前端开发: cd frontend && npm run dev")
    print("新用户注册赠送 1 次生成次数")
    print("按 Ctrl+C 停止")
    print("=" * 50)
    # Windows 下 reload 易产生僵尸进程，多实例抢端口会导致邮件等功能异常
    use_reload = ENV == "development" and sys.platform != "win32"
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=use_reload)


if __name__ == "__main__":
    main()
