#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.auth import generate_token, hash_password, user_payload
from backend.db import REGISTER_FREE_COUNT, get_db
from backend.deps import _row_dict
from backend.verification import (
    issue_register_code,
    normalize_email,
    validate_email,
    verify_register_code,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
def login(body: LoginBody):
    account = body.email.strip() or body.username.strip()
    password = body.password
    if not account or not password:
        _raise(400, "请填写邮箱和密码")

    conn = get_db()
    hashed = hash_password(password)
    with conn.cursor() as cur:
        if "@" in account:
            cur.execute(
                "SELECT * FROM user WHERE email = %s AND password = %s",
                (normalize_email(account), hashed),
            )
        else:
            cur.execute(
                "SELECT * FROM user WHERE username = %s AND password = %s",
                (account, hashed),
            )
        row = cur.fetchone()
    conn.close()

    if not row:
        _raise(401, "邮箱或密码错误")
    if row["is_disabled"]:
        _raise(403, "账号已被禁用")

    user = _row_dict(row)
    token = generate_token(
        {"id": user["id"], "username": user["username"], "is_admin": user["is_admin"]}
    )
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
    if len(password) < 6:
        _raise(400, "密码至少 6 位")
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

    token = generate_token(
        {"id": row["id"], "username": row["username"], "is_admin": 0}
    )
    return {"token": token, "user": user_payload(row)}
