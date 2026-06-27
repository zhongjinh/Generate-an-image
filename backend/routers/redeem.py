#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兑换码相关 API"""

from __future__ import annotations

import logging
import random
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import user_payload
from backend.db import get_db
from backend.deps import _row_dict, require_admin, require_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["redeem"])


def _generate_code(length: int = 8) -> str:
    """生成随机兑换码（大写字母+数字，排除容易混淆的字符）"""
    chars = string.ascii_uppercase.replace("O", "").replace("I", "") + string.digits.replace("0", "").replace("1", "")
    return "".join(random.choices(chars, k=length))


def _activate_vip(cur, user_id: int, valid_days: float, package_type: str) -> str:
    """
    激活/累加 VIP 时间（复用自 orders.py 的逻辑）

    Returns:
        新的过期时间字符串
    """
    now = datetime.now()
    cur.execute("SELECT vip_expire_time FROM user WHERE id = %s", (user_id,))
    user_row = cur.fetchone()

    if user_row and user_row.get("vip_expire_time"):
        current_expire = user_row["vip_expire_time"]
        if isinstance(current_expire, datetime) and current_expire > now:
            # 会员未过期，从当前过期时间累加
            expire_time = current_expire + timedelta(days=valid_days)
        else:
            # 已过期，从现在开始
            expire_time = now + timedelta(days=valid_days)
    else:
        expire_time = now + timedelta(days=valid_days)

    expire_str = expire_time.strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "UPDATE user SET vip_type = %s, vip_expire_time = %s WHERE id = %s",
        (package_type, expire_str, user_id),
    )
    return expire_str


# ─── 用户端 API ───────────────────────────────────────────


class RedeemBody(BaseModel):
    code: str


@router.post("/api/redeem")
def redeem_code(body: RedeemBody, user: dict = Depends(require_user)):
    """用户输入兑换码激活 VIP"""
    code = body.code.strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail={"error": "请输入兑换码"})

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 查找兑换码
            cur.execute(
                "SELECT * FROM redeem_code WHERE code = %s",
                (code,),
            )
            rc = cur.fetchone()

            if not rc:
                raise HTTPException(status_code=404, detail={"error": "兑换码不存在"})

            if rc["is_used"]:
                raise HTTPException(status_code=400, detail={"error": "该兑换码已被使用"})

            # 查询关联套餐
            cur.execute("SELECT * FROM vip_package WHERE id = %s", (rc["package_id"],))
            pkg = cur.fetchone()

            # 激活 VIP
            expire_str = _activate_vip(cur, user["id"], float(rc["valid_days"]), pkg["type"] if pkg else "")

            # 标记兑换码已使用
            cur.execute(
                "UPDATE redeem_code SET is_used = 1, used_by = %s, used_at = NOW() WHERE id = %s",
                (user["id"], rc["id"]),
            )

            # 记录到 order_record（方便统计）
            order_id = f"RC{int(datetime.now().timestamp())}{_generate_code(6)}"
            cur.execute(
                """
                INSERT INTO order_record (order_id, user_id, package_id, pay_amount, pay_status, pay_method)
                VALUES (%s, %s, %s, 0, 'paid', 'redeem')
                """,
                (order_id, user["id"], rc["package_id"]),
            )

            conn.commit()

            # 返回更新后的用户信息
            cur.execute("SELECT * FROM user WHERE id = %s", (user["id"],))
            updated_user = cur.fetchone()

            logger.info("兑换码使用成功: code=%s, user_id=%s, package=%s", code, user["id"], rc["package_id"])

            return {
                "success": True,
                "message": f"兑换成功！VIP 有效期至 {expire_str}",
                "expire_time": expire_str,
                "user": user_payload(updated_user),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("兑换码使用异常: %s", str(e))
        raise HTTPException(status_code=500, detail={"error": "兑换失败，请稍后重试"})
    finally:
        conn.close()


@router.get("/api/redeem/history")
def redeem_history(user: dict = Depends(require_user)):
    """用户兑换记录"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rc.code, rc.used_at, p.package_name, p.valid_days
                FROM redeem_code rc
                LEFT JOIN vip_package p ON rc.package_id = p.id
                WHERE rc.used_by = %s
                ORDER BY rc.used_at DESC
                LIMIT 50
                """,
                (user["id"],),
            )
            rows = cur.fetchall()
        return {"records": [_row_dict(r) for r in rows]}
    finally:
        conn.close()


# ─── 管理员 API ───────────────────────────────────────────


class GenerateCodesBody(BaseModel):
    package_id: int
    count: int = 10


@router.post("/api/redeem/admin/generate")
def generate_codes(body: GenerateCodesBody, _: dict = Depends(require_admin)):
    """管理员批量生成兑换码"""
    if body.count < 1 or body.count > 500:
        raise HTTPException(status_code=400, detail={"error": "数量范围 1-500"})

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 查询套餐
            cur.execute("SELECT * FROM vip_package WHERE id = %s", (body.package_id,))
            pkg = cur.fetchone()
            if not pkg:
                raise HTTPException(status_code=404, detail={"error": "套餐不存在"})

            # 批量生成
            codes = []
            for _ in range(body.count):
                for _retry in range(10):  # 防重复重试
                    code = _generate_code(8)
                    try:
                        cur.execute(
                            "INSERT INTO redeem_code (code, package_id, valid_days) VALUES (%s, %s, %s)",
                            (code, body.package_id, pkg["valid_days"]),
                        )
                        codes.append(code)
                        break
                    except Exception:
                        continue  # 重复码，重试

            conn.commit()

            logger.info("管理员生成兑换码: count=%d, package=%s", len(codes), pkg["package_name"])

            return {
                "success": True,
                "count": len(codes),
                "codes": codes,
                "package_name": pkg["package_name"],
                "valid_days": float(pkg["valid_days"]),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("生成兑换码异常: %s", str(e))
        raise HTTPException(status_code=500, detail={"error": "生成失败"})
    finally:
        conn.close()


@router.get("/api/redeem/admin/list")
def list_codes(
    status: str = "all",
    package_id: int | None = None,
    _: dict = Depends(require_admin),
):
    """管理员查询兑换码列表"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            where_clauses = []
            params = []

            if status == "unused":
                where_clauses.append("rc.is_used = 0")
            elif status == "used":
                where_clauses.append("rc.is_used = 1")

            if package_id:
                where_clauses.append("rc.package_id = %s")
                params.append(package_id)

            where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            cur.execute(
                f"""
                SELECT rc.*, p.package_name, u.username AS used_by_name
                FROM redeem_code rc
                LEFT JOIN vip_package p ON rc.package_id = p.id
                LEFT JOIN user u ON rc.used_by = u.id
                {where_sql}
                ORDER BY rc.created_at DESC
                LIMIT 500
                """,
                tuple(params),
            )
            rows = cur.fetchall()

        return {"codes": [_row_dict(r) for r in rows]}
    finally:
        conn.close()


@router.delete("/api/redeem/admin/{code_id}")
def delete_code(code_id: int, _: dict = Depends(require_admin)):
    """删除未使用的兑换码"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT is_used FROM redeem_code WHERE id = %s", (code_id,))
            rc = cur.fetchone()
            if not rc:
                raise HTTPException(status_code=404, detail={"error": "兑换码不存在"})
            if rc["is_used"]:
                raise HTTPException(status_code=400, detail={"error": "已使用的兑换码不能删除"})

            cur.execute("DELETE FROM redeem_code WHERE id = %s", (code_id,))
        conn.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("删除兑换码异常: %s", str(e))
        raise HTTPException(status_code=500, detail={"error": "删除失败"})
    finally:
        conn.close()
