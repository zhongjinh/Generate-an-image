#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI 依赖：用户鉴权"""

from __future__ import annotations

from fastapi import Header, HTTPException

from backend.auth import verify_token
from backend.db import get_db


def _row_dict(row) -> dict:
    return dict(row) if row else {}


def get_current_user(authorization: str | None = Header(default=None)) -> dict | None:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None
    payload = verify_token(token)
    if not payload or "id" not in payload:
        return None

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user WHERE id = %s", (payload["id"],))
        row = cur.fetchone()
    conn.close()

    if not row:
        return None
    if int(payload.get("tv", 0)) != int(row.get("token_version") or 0):
        return None
    return _row_dict(row)


def require_user(authorization: str | None = Header(default=None)) -> dict:
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail={"error": "请先登录"})
    if user.get("is_disabled"):
        raise HTTPException(status_code=403, detail={"error": "账号已被禁用"})
    return user


def require_admin(authorization: str | None = Header(default=None)) -> dict:
    user = require_user(authorization)
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT is_admin, is_disabled FROM user WHERE id = %s", (user["id"],))
        row = cur.fetchone()
    conn.close()
    if not row or not row.get("is_admin"):
        raise HTTPException(status_code=403, detail={"error": "无管理员权限"})
    if row.get("is_disabled"):
        raise HTTPException(status_code=403, detail={"error": "账号已被禁用"})
    user["is_admin"] = True
    return user
