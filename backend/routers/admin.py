#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.db import get_db
from backend.deps import _row_dict, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def admin_users(_: dict = Depends(require_admin)):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, username, email, phone, is_admin, remain_count, vip_type,
                   vip_expire_time, create_time, is_disabled
            FROM user ORDER BY create_time DESC
            """
        )
        rows = cur.fetchall()
    conn.close()
    return {"users": [_row_dict(r) for r in rows]}


@router.get("/orders")
def admin_orders(_: dict = Depends(require_admin)):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.*, p.package_name, u.username FROM order_record o
            LEFT JOIN vip_package p ON o.package_id = p.id
            LEFT JOIN user u ON o.user_id = u.id
            ORDER BY o.create_time DESC LIMIT 200
            """
        )
        rows = cur.fetchall()
    conn.close()
    return {"orders": [_row_dict(r) for r in rows]}


@router.get("/stats")
def admin_stats(_: dict = Depends(require_admin)):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM user")
        total_users = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM user WHERE DATE(create_time) = CURDATE()")
        today_users = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM order_record WHERE pay_status = 'paid'")
        total_orders = cur.fetchone()["c"]
        cur.execute("SELECT COALESCE(SUM(pay_amount), 0) AS t FROM order_record WHERE pay_status = 'paid'")
        total_revenue = cur.fetchone()["t"]
        cur.execute("SELECT COUNT(*) AS c FROM file_record WHERE DATE(create_time) = CURDATE()")
        today_charts = cur.fetchone()["c"]
    conn.close()
    return {
        "total_users": total_users,
        "today_users": today_users,
        "total_orders": total_orders,
        "total_revenue": float(total_revenue),
        "today_charts": today_charts,
    }


class ResetCountBody(BaseModel):
    count: int = 0


@router.put("/users/{user_id}/count")
def reset_count(user_id: int, body: ResetCountBody, _: dict = Depends(require_admin)):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("UPDATE user SET remain_count = %s WHERE id = %s", (body.count, user_id))
    conn.commit()
    conn.close()
    return {"success": True}


@router.put("/users/{user_id}/disable")
def disable_user(user_id: int, _: dict = Depends(require_admin)):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT is_disabled FROM user WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if row:
            new_disabled = 0 if row["is_disabled"] else 1
            cur.execute(
                """
                UPDATE user SET is_disabled = %s,
                    token_version = token_version + 1,
                    login_failures = 0,
                    locked_until = NULL
                WHERE id = %s
                """,
                (new_disabled, user_id),
            )
    conn.commit()
    conn.close()
    return {"success": True}


class UpdatePackageBody(BaseModel):
    package_name: str | None = None
    price: float | None = None
    total_count: int | None = None
    valid_days: int | None = None
    buy_link: str | None = None
    is_enable: bool | None = None


@router.put("/packages/{package_id}")
def update_package(
    package_id: int, body: UpdatePackageBody, _: dict = Depends(require_admin)
):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE vip_package SET package_name=%s, price=%s, total_count=%s, valid_days=%s, buy_link=%s, is_enable=%s
            WHERE id=%s
            """,
            (
                body.package_name,
                body.price,
                body.total_count,
                body.valid_days,
                body.buy_link or '',
                1 if body.is_enable else 0,
                package_id,
            ),
        )
    conn.commit()
    conn.close()
    return {"success": True}
