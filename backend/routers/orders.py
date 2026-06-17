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
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM vip_package WHERE is_enable = 1 ORDER BY price ASC")
        rows = cur.fetchall()
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
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM vip_package WHERE id = %s AND is_enable = 1", (package_id,)
        )
        pkg = cur.fetchone()
        if not pkg:
            conn.close()
            raise HTTPException(status_code=404, detail={"error": "套餐不存在或已下架"})

        order_id = f"ORD{int(time.time())}{uuid.uuid4().hex[:6].upper()}"
        cur.execute(
            "INSERT INTO order_record (order_id, user_id, package_id, pay_amount) VALUES (%s, %s, %s, %s)",
            (order_id, user["id"], pkg["id"], pkg["price"]),
        )

        expire_time = (datetime.now() + timedelta(days=pkg["valid_days"])).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cur.execute(
            "UPDATE user SET vip_type = %s, vip_expire_time = %s, remain_count = remain_count + %s WHERE id = %s",
            (pkg["type"], expire_time, pkg["total_count"], user["id"]),
        )
        cur.execute(
            "UPDATE order_record SET pay_status = %s, finish_time = NOW() WHERE order_id = %s",
            ("paid", order_id),
        )
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user WHERE id = %s", (user["id"],))
        row = cur.fetchone()
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
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.*, p.package_name FROM order_record o
            LEFT JOIN vip_package p ON o.package_id = p.id
            WHERE o.user_id = %s ORDER BY o.create_time DESC LIMIT 50
            """,
            (user["id"],),
        )
        rows = cur.fetchall()
    conn.close()
    return {"orders": [_row_dict(r) for r in rows]}
