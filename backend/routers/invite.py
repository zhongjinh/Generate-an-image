#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邀请功能 API
- 生成邀请码
- 接受邀请（获得30分钟无限使用）
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.db import get_db
from backend.deps import require_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invite", tags=["invite"])

# 邀请后无限使用时长（分钟）
INVITE_FREE_MINUTES = 30


@router.get("/code")
def get_invite_code(user: dict = Depends(require_user)):
    """获取或生成邀请码"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 检查是否已有邀请码
            cur.execute("SELECT invite_code FROM user WHERE id = %s", (user["id"],))
            row = cur.fetchone()

            if row and row.get("invite_code"):
                return {"invite_code": row["invite_code"]}

            # 生成新邀请码
            code = secrets.token_urlsafe(16)[:16]
            cur.execute(
                "UPDATE user SET invite_code = %s WHERE id = %s",
                (code, user["id"]),
            )
            conn.commit()

            logger.info("用户 %s 生成邀请码: %s", user["id"], code)
            return {"invite_code": code}
    finally:
        conn.close()


class AcceptInviteBody(BaseModel):
    code: str = ""


@router.post("/accept")
def accept_invite(body: AcceptInviteBody, user: dict = Depends(require_user)):
    """接受邀请，获得30分钟无限使用"""
    code = body.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail={"error": "请输入邀请码"})

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 检查邀请码是否有效（不能邀请自己）
            cur.execute(
                "SELECT id, username FROM user WHERE invite_code = %s AND id != %s",
                (code, user["id"]),
            )
            inviter = cur.fetchone()

            if not inviter:
                raise HTTPException(status_code=400, detail={"error": "邀请码无效"})

            # 检查是否已在邀请有效期内（避免重复接受）
            cur.execute(
                "SELECT invite_expire_time FROM user WHERE id = %s",
                (user["id"],),
            )
            current = cur.fetchone()
            if current and current.get("invite_expire_time"):
                expire = current["invite_expire_time"]
                if isinstance(expire, datetime) and expire > datetime.now():
                    raise HTTPException(
                        status_code=400,
                        detail={"error": f"您已在邀请有效期内，到期时间: {expire.strftime('%H:%M:%S')}"},
                    )

            # 设置邀请有效期
            expire_time = datetime.now() + timedelta(minutes=INVITE_FREE_MINUTES)
            cur.execute(
                "UPDATE user SET invite_expire_time = %s WHERE id = %s",
                (expire_time, user["id"]),
            )
            conn.commit()

            logger.info(
                "用户 %s 接受邀请，邀请人: %s，有效期至: %s",
                user["id"],
                inviter["username"],
                expire_time,
            )

            return {
                "success": True,
                "message": f"邀请成功！{INVITE_FREE_MINUTES} 分钟内无限使用",
                "expire_time": expire_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
    finally:
        conn.close()


@router.get("/status")
def invite_status(user: dict = Depends(require_user)):
    """查询邀请状态"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT invite_expire_time FROM user WHERE id = %s",
                (user["id"],),
            )
            row = cur.fetchone()

            if row and row.get("invite_expire_time"):
                expire = row["invite_expire_time"]
                if isinstance(expire, datetime) and expire > datetime.now():
                    remaining = (expire - datetime.now()).total_seconds()
                    return {
                        "active": True,
                        "expire_time": expire.strftime("%Y-%m-%d %H:%M:%S"),
                        "remaining_seconds": int(remaining),
                    }

            return {"active": False}
    finally:
        conn.close()
