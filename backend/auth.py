#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""认证：密码哈希与 JWT Token"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from backend.config import JWT_EXPIRE_HOURS, JWT_SECRET

_PWD_PREFIX = "pbkdf2$"


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256，比裸 SHA256 更安全。"""
    salt = hashlib.sha256(f"{JWT_SECRET}:pwd".encode()).digest()[:16]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return _PWD_PREFIX + base64.urlsafe_b64encode(salt + digest).decode().rstrip("=")


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith(_PWD_PREFIX):
        try:
            raw = base64.urlsafe_b64decode(stored[len(_PWD_PREFIX) :] + "==")
            salt, expected = raw[:16], raw[16:]
            digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
            return hmac.compare_digest(digest, expected)
        except Exception:
            return False
    # 兼容旧版 SHA256 哈希
    legacy = hashlib.sha256(password.encode()).hexdigest()
    return hmac.compare_digest(legacy, stored)


def generate_token(user_id: int, token_version: int = 0) -> str:
    data = {"id": user_id, "tv": int(token_version or 0)}
    data["exp"] = int(time.time()) + JWT_EXPIRE_HOURS * 3600
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
    message = f"{header}.{body}"
    sig = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
    signature = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{message}.{signature}"


def verify_token(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        message = f"{parts[0]}.{parts[1]}"
        pad = "=" * (-len(parts[2]) % 4)
        expected_sig = hmac.new(
            JWT_SECRET.encode(), message.encode(), hashlib.sha256
        ).digest()
        actual_sig = base64.urlsafe_b64decode(parts[2] + pad)
        if not hmac.compare_digest(actual_sig, expected_sig):
            return None
        body_pad = "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + body_pad))
        exp = payload.get("exp")
        if exp is not None and int(exp) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def user_payload(row) -> dict:
    from datetime import datetime

    email = ""
    try:
        email = row["email"] or ""
    except (KeyError, IndexError):
        pass

    # 计算会员状态
    vip_active = False
    vip_remaining = 0
    try:
        if row.get("is_admin"):
            vip_active = True
        else:
            vip_expire = row.get("vip_expire_time")
            if vip_expire:
                if isinstance(vip_expire, datetime):
                    expire_time = vip_expire
                else:
                    expire_time = datetime.strptime(str(vip_expire), "%Y-%m-%d %H:%M:%S")
                if expire_time > datetime.now():
                    vip_active = True
                    vip_remaining = int((expire_time - datetime.now()).total_seconds())

            # 检查邀请期间
            invite_expire = row.get("invite_expire_time")
            if invite_expire and isinstance(invite_expire, datetime) and invite_expire > datetime.now():
                vip_active = True
                remaining = int((invite_expire - datetime.now()).total_seconds())
                vip_remaining = max(vip_remaining, remaining)
    except (KeyError, IndexError, TypeError, ValueError):
        pass

    return {
        "id": row["id"],
        "username": row["username"],
        "email": email,
        "is_admin": bool(row["is_admin"]),
        "vip_type": row["vip_type"] or "",
        "vip_expire_time": row["vip_expire_time"] or "",
        "vip_active": vip_active,
        "vip_remaining": vip_remaining,
    }
