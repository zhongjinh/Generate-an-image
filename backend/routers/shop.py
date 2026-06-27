#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地发卡商店 API
用户选择套餐 → 直接生成兑换码 → 返回给用户
（生产环境应替换为真正的支付流程）
"""

from __future__ import annotations

import logging
import random
import string

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.config import ALLOW_SHOP_DEMO
from backend.db import get_db
from backend.deps import _row_dict, require_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["shop"])


def _generate_code(length: int = 8) -> str:
    chars = string.ascii_uppercase.replace("O", "").replace("I", "") + string.digits.replace("0", "").replace("1", "")
    return "".join(random.choices(chars, k=length))


class BuyBody(BaseModel):
    package_id: int


@router.post("/api/shop/buy")
def buy_package(body: BuyBody, user: dict = Depends(require_user)):
    if not ALLOW_SHOP_DEMO:
        raise HTTPException(status_code=403, detail={"error": "该接口已关闭"})
    """
    购买套餐（本地演示版）
    直接生成兑换码返回给用户，无需真实支付
    """
    package_id = body.package_id
    if not package_id:
        raise HTTPException(status_code=400, detail={"error": "请选择套餐"})

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 查询套餐
            cur.execute("SELECT * FROM vip_package WHERE id = %s AND is_enable = 1", (package_id,))
            pkg = cur.fetchone()
            if not pkg:
                raise HTTPException(status_code=404, detail={"error": "套餐不存在或已下架"})

            # 生成兑换码
            for _retry in range(10):
                code = _generate_code(8)
                try:
                    cur.execute(
                        "INSERT INTO redeem_code (code, package_id, valid_days) VALUES (%s, %s, %s)",
                        (code, pkg["id"], pkg["valid_days"]),
                    )
                    break
                except Exception:
                    continue
            else:
                raise HTTPException(status_code=500, detail={"error": "生成兑换码失败，请重试"})

            # 记录订单
            order_id = f"SHOP{int(__import__('time').time())}{_generate_code(6)}"
            cur.execute(
                """
                INSERT INTO order_record (order_id, user_id, package_id, pay_amount, pay_status, pay_method)
                VALUES (%s, %s, %s, %s, 'paid', 'shop')
                """,
                (order_id, user["id"], pkg["id"], pkg["price"]),
            )

        conn.commit()

        logger.info("用户购买套餐: user_id=%s, package=%s, code=%s", user["id"], pkg["package_name"], code)

        return {
            "success": True,
            "code": code,
            "package_name": pkg["package_name"],
            "valid_days": float(pkg["valid_days"]),
            "price": float(pkg["price"]),
            "message": f"购买成功！您的兑换码是：{code}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("购买异常: %s", str(e))
        raise HTTPException(status_code=500, detail={"error": "购买失败，请稍后重试"})
    finally:
        conn.close()
