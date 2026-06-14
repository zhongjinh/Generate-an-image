#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置模块 - 支持开发/生产环境
优先级：环境变量 > .env 文件 > 默认值
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------- 目录 ----------
FRONTEND_DIR = ROOT / "frontend"

# ---------- 加载 .env 文件 ----------
# 优先级：系统环境变量 > .env > 代码默认值


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if not key:
                continue
            if value and key not in os.environ:
                os.environ[key] = value


_load_dotenv(ROOT / ".env")

# ---------- 环境切换 ----------
ENV = os.environ.get("APP_ENV", "development")  # development | production
DEBUG = ENV == "development"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int = 0) -> int:
    val = os.environ.get(name)
    return int(val) if val else default


def _env_float(name: str, default: float = 0.0) -> float:
    val = os.environ.get(name)
    return float(val) if val else default


# ---------- 服务器 ----------
HOST = _env("HOST", "127.0.0.1")
PORT = _env_int("PORT", 8765)

# ---------- 数据库 ----------
DB_PATH = ROOT / "data" / "app.db"

# ---------- 认证 ----------
_jwt_secret = _env("JWT_SECRET")
if not _jwt_secret:
    if ENV == "production":
        raise RuntimeError("生产环境必须通过环境变量 JWT_SECRET 指定密钥")
    _jwt_secret = secrets.token_hex(32)
    print(f"[配置] JWT_SECRET 未设置，已自动生成随机密钥（仅限开发环境）")
JWT_SECRET = _jwt_secret

# ---------- 管理员 ----------
ADMIN_PASSWORD = _env("ADMIN_PASSWORD")
if not ADMIN_PASSWORD and ENV == "development":
    ADMIN_PASSWORD = "admin123"
    print(f"[配置] 管理员默认密码: admin / admin123（仅限开发环境）")
elif not ADMIN_PASSWORD:
    ADMIN_PASSWORD = secrets.token_urlsafe(12)
    print(f"[配置] 管理员密码已随机生成: admin / {ADMIN_PASSWORD}（请妥善保存）")

# ---------- 用户 ----------
REGISTER_FREE_COUNT = _env_int("REGISTER_FREE_COUNT", 1)

# ---------- 转换服务 ----------
CONVERT_API_KEY = _env("CONVERT_API_KEY")
if not CONVERT_API_KEY:
    if ENV == "production":
        raise RuntimeError("生产环境必须通过环境变量 CONVERT_API_KEY 指定密钥")
    CONVERT_API_KEY = secrets.token_urlsafe(24)
    print(f"[配置] CONVERT_API_KEY 未设置，已自动生成随机密钥（仅限开发环境）")

CONVERT_PORT = _env_int("CONVERT_PORT", 5000)
PUBLIC_CONVERT = _env("PUBLIC_CONVERT", "1") != "0"
