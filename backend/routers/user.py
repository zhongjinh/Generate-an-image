#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth import user_payload
from backend.db import get_db
from backend.deps import require_user

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/info")
def user_info(user: dict = Depends(require_user)):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user WHERE id = %s", (user["id"],))
        row = cur.fetchone()
    conn.close()
    return {"user": user_payload(row)}
