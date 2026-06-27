#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会员状态校验"""

from __future__ import annotations

from datetime import datetime

from fastapi import Depends, HTTPException

from backend.db import get_db
from backend.deps import require_user


def is_vip_active(row: dict) -> bool:
    if row.get("is_admin"):
        return True

    invite_expire = row.get("invite_expire_time")
    if invite_expire and isinstance(invite_expire, datetime) and invite_expire > datetime.now():
        return True

    vip_expire = row.get("vip_expire_time")
    if vip_expire:
        try:
            if isinstance(vip_expire, datetime):
                return vip_expire > datetime.now()
            expire_time = datetime.strptime(str(vip_expire), "%Y-%m-%d %H:%M:%S")
            return expire_time > datetime.now()
        except (ValueError, TypeError):
            pass
    return False


def require_vip_user(user: dict = Depends(require_user)) -> dict:
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user WHERE id = %s", (user["id"],))
        row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail={"error": "请先登录"})
    if row.get("is_disabled"):
        raise HTTPException(status_code=403, detail={"error": "账号已被禁用"})
    if not is_vip_active(row):
        raise HTTPException(status_code=403, detail={"error": "会员已过期，请续费后使用"})
    return dict(row)
