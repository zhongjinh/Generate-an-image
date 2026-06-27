#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置模块
优先级：系统环境变量 > .env 文件
所有配置项均必填，缺失或为空时启动失败。
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
FRONTEND_DIST = ROOT / "frontend" / "dist"


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
            if key not in os.environ:
                os.environ[key] = value


if not ENV_FILE.exists():
    raise RuntimeError(
        "缺少 .env 配置文件。请复制模板并填写全部必填项：\n"
        "  cp .env.example .env"
    )

_load_dotenv(ENV_FILE)


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"配置项 {name} 未设置或为空，请在 .env 中填写")
    return value


def _require_int(name: str) -> int:
    value = _require(name)
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"配置项 {name} 必须是整数，当前值: {value}") from exc


def _require_choice(name: str, choices: set[str]) -> str:
    value = _require(name)
    if value not in choices:
        allowed = ", ".join(sorted(choices))
        raise RuntimeError(f"配置项 {name} 必须是以下之一: {allowed}，当前值: {value}")
    return value


def _optional(name: str, default: str) -> str:
    value = os.environ.get(name, default).strip()
    return value or default


ENV = _require_choice("APP_ENV", {"development", "production"})
DEBUG = ENV == "development"

HOST = _require("HOST")
PORT = _require_int("PORT")
if PORT <= 0 or PORT > 65535:
    raise RuntimeError(f"配置项 PORT 必须在 1-65535 之间，当前值: {PORT}")

MYSQL_HOST = _require("MYSQL_HOST")
MYSQL_PORT = _require_int("MYSQL_PORT")
if MYSQL_PORT <= 0 or MYSQL_PORT > 65535:
    raise RuntimeError(f"配置项 MYSQL_PORT 必须在 1-65535 之间，当前值: {MYSQL_PORT}")
MYSQL_USER = _require("MYSQL_USER")
MYSQL_PASSWORD = _optional("MYSQL_PASSWORD", "")
MYSQL_DATABASE = _require("MYSQL_DATABASE")

JWT_SECRET = _require("JWT_SECRET")
def _optional_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"配置项 {name} 必须是整数，当前值: {raw}") from exc


JWT_EXPIRE_HOURS = _optional_int("JWT_EXPIRE_HOURS", 168)
if JWT_EXPIRE_HOURS <= 0 or JWT_EXPIRE_HOURS > 8760:
    raise RuntimeError("配置项 JWT_EXPIRE_HOURS 必须在 1-8760 之间")

ADMIN_PASSWORD = _require("ADMIN_PASSWORD")
ADMIN_USERNAME = _optional("ADMIN_USERNAME", "admin").strip().lower()
if not ADMIN_USERNAME or len(ADMIN_USERNAME) < 3:
    raise RuntimeError("配置项 ADMIN_USERNAME 至少 3 个字符")

if ENV == "production":
    if len(ADMIN_PASSWORD) < 12:
        raise RuntimeError("生产环境 ADMIN_PASSWORD 至少 12 位")
    if ADMIN_USERNAME in {"admin", "root", "administrator", "test"}:
        raise RuntimeError("生产环境请修改 ADMIN_USERNAME，勿使用 admin/root 等常见用户名")

LOGIN_MAX_FAILURES = _optional_int("LOGIN_MAX_FAILURES", 5)
LOGIN_LOCKOUT_MINUTES = _optional_int("LOGIN_LOCKOUT_MINUTES", 30)
if LOGIN_MAX_FAILURES < 3 or LOGIN_MAX_FAILURES > 20:
    raise RuntimeError("配置项 LOGIN_MAX_FAILURES 必须在 3-20 之间")

# 前端请求必须携带的客户端令牌（与 VITE_APP_CLIENT_TOKEN 一致）
APP_CLIENT_TOKEN = _optional("APP_CLIENT_TOKEN", "")

# 演示发卡接口，生产环境必须为 0
ALLOW_SHOP_DEMO = _optional("ALLOW_SHOP_DEMO", "0" if ENV == "production" else "1") == "1"

if ENV == "production" and ALLOW_SHOP_DEMO:
    raise RuntimeError("生产环境禁止 ALLOW_SHOP_DEMO=1，会绕过支付直接发卡")

if ENV == "production" and not APP_CLIENT_TOKEN:
    raise RuntimeError("生产环境必须设置 APP_CLIENT_TOKEN（随机 32+ 字符）")

# 生产环境 CORS 白名单（逗号分隔，如 https://example.com,https://www.example.com）
_cors_raw = _optional("CORS_ORIGINS", "")
CORS_ORIGINS = [o.strip() for o in _cors_raw.split(",") if o.strip()]

# 生产环境允许的 Host 头（逗号分隔，如 example.com,api.example.com）
_hosts_raw = _optional("TRUSTED_HOSTS", "")
TRUSTED_HOSTS = {h.strip().lower() for h in _hosts_raw.split(",") if h.strip()}

# 是否部署在 Cloudflare 之后（用于日志与文档提示）
BEHIND_CLOUDFLARE = _optional("BEHIND_CLOUDFLARE", "0") == "1"

# 可选：内部 API 密钥（Cloudflare Pages Functions 转发时携带，防止绕过 CDN 直连后端）
INTERNAL_API_SECRET = _optional("INTERNAL_API_SECRET", "")

# 生产环境若未设置 CORS 且未设置内部密钥，给出明确提示
if ENV == "production" and not CORS_ORIGINS and not INTERNAL_API_SECRET:
    raise RuntimeError(
        "生产环境请至少设置 CORS_ORIGINS 或 INTERNAL_API_SECRET 之一，"
        "详见 .env.example 中的 Cloudflare 部署说明"
    )

REGISTER_FREE_COUNT = _require_int("REGISTER_FREE_COUNT")
if REGISTER_FREE_COUNT < 0:
    raise RuntimeError("配置项 REGISTER_FREE_COUNT 不能为负数")

CONVERT_API_KEY = _require("CONVERT_API_KEY")
CONVERT_PORT = _require_int("CONVERT_PORT")
if CONVERT_PORT <= 0 or CONVERT_PORT > 65535:
    raise RuntimeError(f"配置项 CONVERT_PORT 必须在 1-65535 之间，当前值: {CONVERT_PORT}")

PUBLIC_CONVERT = _require_choice("PUBLIC_CONVERT", {"0", "1"}) == "1"

if ENV == "production" and PUBLIC_CONVERT:
    raise RuntimeError("生产环境请设置 PUBLIC_CONVERT=0，防止转换接口被滥用")

SMTP_HOST = _require("SMTP_HOST")
SMTP_PORT = _require_int("SMTP_PORT")
if SMTP_PORT <= 0 or SMTP_PORT > 65535:
    raise RuntimeError(f"配置项 SMTP_PORT 必须在 1-65535 之间，当前值: {SMTP_PORT}")
SMTP_USER = _require("SMTP_USER")
SMTP_PASSWORD = _require("SMTP_PASSWORD")
SMTP_FROM = _require("SMTP_FROM")
SMTP_FROM_NAME = _optional("SMTP_FROM_NAME", "图表在线生成器")
SMTP_USE_TLS = _require_choice("SMTP_USE_TLS", {"0", "1"}) == "1"

# 支付宝配置
ALIPAY_APP_ID = _optional("ALIPAY_APP_ID", "")
ALIPAY_PRIVATE_KEY = _optional("ALIPAY_PRIVATE_KEY", "")
ALIPAY_PUBLIC_KEY = _optional("ALIPAY_PUBLIC_KEY", "")
ALIPAY_NOTIFY_URL = _optional("ALIPAY_NOTIFY_URL", "")
ALIPAY_RETURN_URL = _optional("ALIPAY_RETURN_URL", "")

# 支付宝是否已配置
ALIPAY_ENABLED = bool(ALIPAY_APP_ID and ALIPAY_PRIVATE_KEY and ALIPAY_PUBLIC_KEY)

# DeepSeek AI（自然语言 → 图表 JSON，可选）
DEEPSEEK_API_KEY = _optional("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = _optional(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/v1/chat/completions",
)
DEEPSEEK_MODEL = _optional("DEEPSEEK_MODEL", "deepseek-chat")
