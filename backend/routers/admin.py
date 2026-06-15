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
    rows = conn.execute(
        """
        SELECT id, username, phone, is_admin, remain_count, vip_type,
               vip_expire_time, create_time, is_disabled
        FROM user ORDER BY create_time DESC
        """
    ).fetchall()
    conn.close()
    return {"users": [_row_dict(r) for r in rows]}


@router.get("/orders")
def admin_orders(_: dict = Depends(require_admin)):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT o.*, p.package_name, u.username FROM order_record o
        LEFT JOIN vip_package p ON o.package_id = p.id
        LEFT JOIN user u ON o.user_id = u.id
        ORDER BY o.create_time DESC LIMIT 200
        """
    ).fetchall()
    conn.close()
    return {"orders": [_row_dict(r) for r in rows]}


@router.get("/stats")
def admin_stats(_: dict = Depends(require_admin)):
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) AS c FROM user").fetchone()["c"]
    today_users = conn.execute(
        "SELECT COUNT(*) AS c FROM user WHERE date(create_time) = date('now', 'localtime')"
    ).fetchone()["c"]
    total_orders = conn.execute(
        "SELECT COUNT(*) AS c FROM order_record WHERE pay_status = 'paid'"
    ).fetchone()["c"]
    total_revenue = conn.execute(
        "SELECT COALESCE(SUM(pay_amount), 0) AS t FROM order_record WHERE pay_status = 'paid'"
    ).fetchone()["t"]
    today_charts = conn.execute(
        "SELECT COUNT(*) AS c FROM file_record WHERE date(create_time) = date('now', 'localtime')"
    ).fetchone()["c"]
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
    conn.execute("UPDATE user SET remain_count = ? WHERE id = ?", (body.count, user_id))
    conn.commit()
    conn.close()
    return {"success": True}


@router.put("/users/{user_id}/disable")
def disable_user(user_id: int, _: dict = Depends(require_admin)):
    conn = get_db()
    row = conn.execute(
        "SELECT is_disabled FROM user WHERE id = ?", (user_id,)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE user SET is_disabled = ? WHERE id = ?",
            (0 if row["is_disabled"] else 1, user_id),
        )
        conn.commit()
    conn.close()
    return {"success": True}


class UpdatePackageBody(BaseModel):
    package_name: str | None = None
    price: float | None = None
    total_count: int | None = None
    valid_days: int | None = None
    is_enable: bool | None = None


@router.put("/packages/{package_id}")
def update_package(
    package_id: int, body: UpdatePackageBody, _: dict = Depends(require_admin)
):
    conn = get_db()
    conn.execute(
        """
        UPDATE vip_package SET package_name=?, price=?, total_count=?, valid_days=?, is_enable=?
        WHERE id=?
        """,
        (
            body.package_name,
            body.price,
            body.total_count,
            body.valid_days,
            1 if body.is_enable else 0,
            package_id,
        ),
    )
    conn.commit()
    conn.close()
    return {"success": True}
