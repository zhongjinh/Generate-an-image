#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.auth import generate_token, hash_password, user_payload
from backend.db import REGISTER_FREE_COUNT, get_db
from backend.deps import _row_dict

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _raise(status: int, msg: str):
    raise HTTPException(status_code=status, detail={"error": msg})


class LoginBody(BaseModel):
    username: str = ""
    password: str = ""


class RegisterBody(BaseModel):
    username: str = ""
    password: str = ""
    phone: str = ""


@router.post("/login")
def login(body: LoginBody):
    username = body.username.strip()
    password = body.password
    if not username or not password:
        _raise(400, "请填写用户名和密码")

    conn = get_db()
    row = conn.execute(
        "SELECT * FROM user WHERE username = ? AND password = ?",
        (username, hash_password(password)),
    ).fetchone()
    conn.close()

    if not row:
        _raise(401, "用户名或密码错误")
    if row["is_disabled"]:
        _raise(403, "账号已被禁用")

    user = _row_dict(row)
    token = generate_token(
        {"id": user["id"], "username": user["username"], "is_admin": user["is_admin"]}
    )
    return {"token": token, "user": user_payload(row)}


@router.post("/register")
def register(body: RegisterBody):
    username = body.username.strip()
    password = body.password
    phone = body.phone.strip()

    if not username or not password:
        _raise(400, "请填写用户名和密码")
    if len(username) < 3 or len(username) > 20:
        _raise(400, "用户名长度 3-20 位")
    if len(password) < 6:
        _raise(400, "密码至少 6 位")

    conn = get_db()
    exists = conn.execute(
        "SELECT id FROM user WHERE username = ?", (username,)
    ).fetchone()
    if exists:
        conn.close()
        _raise(400, "用户名已存在")

    cur = conn.execute(
        "INSERT INTO user (username, password, phone, remain_count) VALUES (?, ?, ?, ?)",
        (username, hash_password(password), phone, REGISTER_FREE_COUNT),
    )
    user_id = cur.lastrowid
    row = conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    conn.commit()
    conn.close()

    token = generate_token(
        {"id": row["id"], "username": row["username"], "is_admin": 0}
    )
    return {"token": token, "user": user_payload(row)}
