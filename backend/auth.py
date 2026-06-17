#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""认证：密码哈希与 JWT Token"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

from backend.config import JWT_SECRET


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token(payload: dict) -> str:
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
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
        return json.loads(base64.urlsafe_b64decode(parts[1] + body_pad))
    except Exception:
        return None


def user_payload(row) -> dict:
    email = ""
    try:
        email = row["email"] or ""
    except (KeyError, IndexError):
        pass
    return {
        "id": row["id"],
        "username": row["username"],
        "email": email,
        "is_admin": bool(row["is_admin"]),
        "remain_count": row["remain_count"],
        "vip_type": row["vip_type"] or "",
        "vip_expire_time": row["vip_expire_time"] or "",
    }
