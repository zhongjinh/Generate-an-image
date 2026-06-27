#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.auth import generate_token, hash_password, user_payload, verify_password
from backend.config import ADMIN_USERNAME
from backend.db import REGISTER_FREE_COUNT, get_db
from backend.deps import _row_dict
from backend.login_guard import is_account_locked, record_login_failure, reset_login_failures
from backend.security import get_client_ip, rate_limiter
from backend.verification import (
    issue_register_code,
    normalize_email,
    validate_email,
    verify_register_code,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_RESERVED_USERNAMES = {ADMIN_USERNAME, "admin", "root", "administrator", "system", "test"}


def _raise(status: int, msg: str):
    raise HTTPException(status_code=status, detail={"error": msg})


class LoginBody(BaseModel):
    email: str = ""
    username: str = ""
    password: str = ""


class RegisterBody(BaseModel):
    email: str = ""
    password: str = ""
    code: str = ""


class SendCodeBody(BaseModel):
    email: str = ""


def _username_from_email(email: str) -> str:
    local = email.split("@", 1)[0]
    name = re.sub(r"[^a-zA-Z0-9_]", "_", local).strip("_") or "user"
    if len(name) < 3:
        name = (name + "usr")[:3]
    return name[:20]


def _unique_username(conn, base: str) -> str:
    candidate = base[:20]
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM user WHERE username = %s", (candidate,))
        if not cur.fetchone():
            return candidate
        for i in range(1, 1000):
            suffix = str(i)
            truncated = base[: 20 - len(suffix)] + suffix
            cur.execute("SELECT id FROM user WHERE username = %s", (truncated,))
            if not cur.fetchone():
                return truncated
    _raise(500, "无法生成用户名，请稍后重试")
    return ""


def _login_rate_key(request: Request, account: str) -> str:
    ip = get_client_ip(request)
    return f"login:{ip}:{account.lower()}"


@router.post("/send-code")
def send_code(body: SendCodeBody):
    email = body.email.strip()
    if not email:
        _raise(400, "请填写邮箱")
    try:
        return issue_register_code(email)
    except ValueError as exc:
        _raise(400, str(exc))
    except RuntimeError as exc:
        _raise(500, str(exc))
    except Exception:
        _raise(500, "验证码发送失败，请检查邮件配置或稍后重试")


@router.post("/login")
def login(body: LoginBody, request: Request):
    account = body.email.strip() or body.username.strip()
    password = body.password
    if not account or not password:
        _raise(400, "请填写账号和密码")
    if len(password) > 128:
        _raise(400, "密码格式无效")

    # 管理员账号更严格的 IP 限流
    is_admin_attempt = account.lower() == ADMIN_USERNAME
    limit = (3, 600) if is_admin_attempt else (10, 300)
    rate_key = _login_rate_key(request, account)
    if not rate_limiter.is_allowed(rate_key, limit[0], limit[1]):
        _raise(429, "登录尝试过于频繁，请稍后再试")

    conn = get_db()
    with conn.cursor() as cur:
        if "@" in account:
            cur.execute(
                "SELECT * FROM user WHERE email = %s",
                (normalize_email(account),),
            )
        else:
            cur.execute(
                "SELECT * FROM user WHERE username = %s",
                (account,),
            )
        row = cur.fetchone()

        if row:
            locked, minutes = is_account_locked(row)
            if locked:
                conn.close()
                _raise(429, f"账号已锁定，请 {minutes} 分钟后再试")

        valid = bool(row and verify_password(password, row["password"]))
        if not valid:
            if row:
                record_login_failure(cur, row["id"])
                conn.commit()
            conn.close()
            time.sleep(0.5)
            _raise(401, "账号或密码错误")

        if row["is_disabled"]:
            conn.close()
            _raise(403, "账号已被禁用")

        reset_login_failures(cur, row["id"])
        conn.commit()

        token = generate_token(row["id"], row.get("token_version") or 0)
        user = _row_dict(row)
    conn.close()

    return {"token": token, "user": user_payload(row)}


@router.post("/register")
def register(body: RegisterBody):
    email = normalize_email(body.email)
    password = body.password
    code = body.code.strip()

    if not email or not password or not code:
        _raise(400, "请填写邮箱、验证码和密码")
    if not validate_email(email):
        _raise(400, "邮箱格式不正确")
    if len(password) < 8:
        _raise(400, "密码至少 8 位")
    if len(password) > 128:
        _raise(400, "密码过长")
    if not verify_register_code(email, code):
        _raise(400, "验证码错误或已过期")

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM user WHERE email = %s", (email,))
        exists = cur.fetchone()
        if exists:
            conn.close()
            _raise(400, "该邮箱已注册")

        username = _unique_username(conn, _username_from_email(email))
        if username.lower() in _RESERVED_USERNAMES:
            username = _unique_username(conn, f"u_{username}")

        cur.execute(
            """
            INSERT INTO user (username, password, email, remain_count)
            VALUES (%s, %s, %s, %s)
            """,
            (username, hash_password(password), email, REGISTER_FREE_COUNT),
        )
        user_id = cur.lastrowid
        cur.execute("SELECT * FROM user WHERE id = %s", (user_id,))
        row = cur.fetchone()
    conn.commit()
    conn.close()

    token = generate_token(row["id"], row.get("token_version") or 0)
    return {"token": token, "user": user_payload(row)}
