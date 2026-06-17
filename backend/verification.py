#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""邮箱验证码存储与校验"""

from __future__ import annotations

import logging
import random
import re
from datetime import datetime, timedelta

from backend.db import get_db
from backend.email_service import send_verification_code

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
CODE_TTL_MINUTES = 10
SEND_COOLDOWN_SECONDS = 60


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match(normalize_email(email)))


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_db_time(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")


def issue_register_code(email: str) -> dict:
    email = normalize_email(email)
    if not validate_email(email):
        raise ValueError("邮箱格式不正确")

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM user WHERE email = %s", (email,))
        exists = cur.fetchone()
        if exists:
            conn.close()
            raise ValueError("该邮箱已注册")

        cur.execute(
            """
            SELECT created_at FROM email_verification
            WHERE email = %s AND purpose = 'register'
            ORDER BY id DESC LIMIT 1
            """,
            (email,),
        )
        recent = cur.fetchone()
        if recent:
            created = _parse_db_time(recent["created_at"])
            if datetime.now() - created < timedelta(seconds=SEND_COOLDOWN_SECONDS):
                conn.close()
                raise ValueError(f"发送过于频繁，请 {SEND_COOLDOWN_SECONDS} 秒后再试")

        code = f"{random.randint(0, 999999):06d}"
        expires = (datetime.now() + timedelta(minutes=CODE_TTL_MINUTES)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cur.execute(
            """
            INSERT INTO email_verification (email, code, purpose, expires_at)
            VALUES (%s, %s, 'register', %s)
            """,
            (email, code, expires),
        )
    conn.commit()
    conn.close()

    try:
        send_verification_code(email, code)
    except Exception:
        logger.exception("发送验证码邮件失败: %s", email)
        raise RuntimeError("验证码发送失败，请检查邮件配置或稍后重试") from None

    return {"success": True, "message": "验证码已发送，请查收邮件"}


def verify_register_code(email: str, code: str) -> bool:
    email = normalize_email(email)
    code = code.strip()
    if not code:
        return False

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, code, expires_at, used FROM email_verification
            WHERE email = %s AND purpose = 'register'
            ORDER BY id DESC LIMIT 1
            """,
            (email,),
        )
        row = cur.fetchone()
        if not row or row["used"]:
            conn.close()
            return False
        if _parse_db_time(row["expires_at"]) < datetime.now():
            conn.close()
            return False
        if row["code"] != code:
            conn.close()
            return False

        cur.execute(
            "UPDATE email_verification SET used = 1 WHERE id = %s", (row["id"],)
        )
    conn.commit()
    conn.close()
    return True
