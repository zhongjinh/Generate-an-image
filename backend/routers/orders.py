#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import user_payload
from backend.db import get_db
from backend.deps import _row_dict, require_user

router = APIRouter(tags=["orders"])


@router.get("/api/vip/packages")
def get_packages():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM vip_package WHERE is_enable = 1 ORDER BY price ASC"
    ).fetchall()
    conn.close()
    return {"packages": [_row_dict(r) for r in rows]}


class CreateOrderBody(BaseModel):
    package_id: int | None = None


@router.post("/api/orders")
def create_order(body: CreateOrderBody, user: dict = Depends(require_user)):
    package_id = body.package_id
    if not package_id:
        raise HTTPException(status_code=400, detail={"error": "请选择套餐"})

    conn = get_db()
    pkg = conn.execute(
        "SELECT * FROM vip_package WHERE id = ? AND is_enable = 1", (package_id,)
    ).fetchone()
    if not pkg:
        conn.close()
        raise HTTPException(status_code=404, detail={"error": "套餐不存在或已下架"})

    order_id = f"ORD{int(time.time())}{uuid.uuid4().hex[:6].upper()}"
    conn.execute(
        "INSERT INTO order_record (order_id, user_id, package_id, pay_amount) VALUES (?, ?, ?, ?)",
        (order_id, user["id"], pkg["id"], pkg["price"]),
    )

    expire_time = (datetime.now() + timedelta(days=pkg["valid_days"])).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn.execute(
        "UPDATE user SET vip_type = ?, vip_expire_time = ?, remain_count = remain_count + ? WHERE id = ?",
        (pkg["type"], expire_time, pkg["total_count"], user["id"]),
    )
    conn.execute(
        "UPDATE order_record SET pay_status = ?, finish_time = datetime('now', 'localtime') WHERE order_id = ?",
        ("paid", order_id),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM user WHERE id = ?", (user["id"],)).fetchone()
    conn.close()

    return {
        "success": True,
        "order_id": order_id,
        "message": "购买成功",
        "user": user_payload(row),
    }


@router.get("/api/orders")
def get_orders(user: dict = Depends(require_user)):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT o.*, p.package_name FROM order_record o
        LEFT JOIN vip_package p ON o.package_id = p.id
        WHERE o.user_id = ? ORDER BY o.create_time DESC LIMIT 50
        """,
        (user["id"],),
    ).fetchall()
    conn.close()
    return {"orders": [_row_dict(r) for r in rows]}
