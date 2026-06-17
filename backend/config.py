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
ADMIN_PASSWORD = _require("ADMIN_PASSWORD")

REGISTER_FREE_COUNT = _require_int("REGISTER_FREE_COUNT")
if REGISTER_FREE_COUNT < 0:
    raise RuntimeError("配置项 REGISTER_FREE_COUNT 不能为负数")

CONVERT_API_KEY = _require("CONVERT_API_KEY")
CONVERT_PORT = _require_int("CONVERT_PORT")
if CONVERT_PORT <= 0 or CONVERT_PORT > 65535:
    raise RuntimeError(f"配置项 CONVERT_PORT 必须在 1-65535 之间，当前值: {CONVERT_PORT}")

PUBLIC_CONVERT = _require_choice("PUBLIC_CONVERT", {"0", "1"}) == "1"

SMTP_HOST = _require("SMTP_HOST")
SMTP_PORT = _require_int("SMTP_PORT")
if SMTP_PORT <= 0 or SMTP_PORT > 65535:
    raise RuntimeError(f"配置项 SMTP_PORT 必须在 1-65535 之间，当前值: {SMTP_PORT}")
SMTP_USER = _require("SMTP_USER")
SMTP_PASSWORD = _require("SMTP_PASSWORD")
SMTP_FROM = _require("SMTP_FROM")
SMTP_FROM_NAME = _optional("SMTP_FROM_NAME", "图表在线生成器")
SMTP_USE_TLS = _require_choice("SMTP_USE_TLS", {"0", "1"}) == "1"
