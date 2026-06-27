#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
支付宝支付接口
使用 RSA2 签名方式
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from backend.auth import user_payload
from backend.config import (
    ALIPAY_APP_ID,
    ALIPAY_ENABLED,
    ALIPAY_NOTIFY_URL,
    ALIPAY_PRIVATE_KEY,
    ALIPAY_PUBLIC_KEY,
    ALIPAY_RETURN_URL,
)
from backend.db import get_db
from backend.deps import _row_dict, require_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["payment"])

# 支付宝正式环境网关
ALIPAY_GATEWAY = "https://openapi.alipay.com/gateway.do"

# 签名方式
SIGN_TYPE = "RSA2"
CHARSET = "utf-8"


def _format_private_key(private_key_str: str) -> str:
    """格式化私钥，添加头尾"""
    # 清理密钥字符串
    private_key_str = private_key_str.strip()
    private_key_str = private_key_str.replace('\n', '').replace('\r', '').replace(' ', '')

    # 如果已经有头尾，直接返回
    if private_key_str.startswith('-----BEGIN'):
        return private_key_str

    # 尝试 PKCS#8 格式（支付宝推荐）
    return f"-----BEGIN PRIVATE KEY-----\n{private_key_str}\n-----END PRIVATE KEY-----"


def _format_public_key(public_key_str: str) -> str:
    """格式化公钥，添加头尾"""
    # 清理密钥字符串
    public_key_str = public_key_str.strip()
    public_key_str = public_key_str.replace('\n', '').replace('\r', '').replace(' ', '')

    # 如果已经有头尾，直接返回
    if public_key_str.startswith('-----BEGIN'):
        return public_key_str

    return f"-----BEGIN PUBLIC KEY-----\n{public_key_str}\n-----END PUBLIC KEY-----"


def _rsa_sign(sign_content: str, private_key_str: str) -> str:
    """RSA2 签名"""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        private_key_pem = _format_private_key(private_key_str)

        # 尝试加载私钥
        try:
            private_key = load_pem_private_key(private_key_pem.encode(), password=None)
        except Exception as e:
            # 如果 PKCS#8 格式失败，尝试 PKCS#1 格式
            logger.warning("PKCS#8 格式加载失败，尝试 PKCS#1 格式: %s", str(e))
            private_key_pem = f"-----BEGIN RSA PRIVATE KEY-----\n{private_key_str}\n-----END RSA PRIVATE KEY-----"
            private_key = load_pem_private_key(private_key_pem.encode(), password=None)

        signature = private_key.sign(
            sign_content.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        logger.error("RSA签名失败: %s", str(e))
        raise


def _rsa_verify(sign_content: str, signature: str, public_key_str: str) -> bool:
    """RSA2 验签"""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import load_pem_public_key

        public_key_pem = _format_public_key(public_key_str)
        public_key = load_pem_public_key(public_key_pem.encode())

        signature_bytes = base64.b64decode(signature)

        public_key.verify(
            signature_bytes,
            sign_content.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        logger.error("RSA验签失败: %s", str(e))
        return False


def _build_sign_params(params: dict) -> str:
    """构建待签名字符串"""
    # 过滤空值和 sign 参数
    filtered = {k: v for k, v in params.items() if v and k != 'sign'}
    # 按 key 排序
    sorted_params = sorted(filtered.items())
    # 拼接（确保值不被截断）
    parts = []
    for k, v in sorted_params:
        parts.append(f'{k}={v}')
    return '&'.join(parts)


class CreatePaymentBody(BaseModel):
    package_id: int


@router.post("/api/payment/create")
def create_payment(body: CreatePaymentBody, user: dict = Depends(require_user)):
    """创建支付宝支付订单"""
    if not ALIPAY_ENABLED:
        raise HTTPException(status_code=503, detail={"error": "支付宝支付未配置，请联系管理员"})

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

            # 生成订单号
            order_id = f"ALI{int(time.time())}{uuid.uuid4().hex[:6].upper()}"

            # 创建订单
            cur.execute(
                """
                INSERT INTO order_record (order_id, user_id, package_id, pay_amount, pay_status, pay_method)
                VALUES (%s, %s, %s, %s, 'pending', 'alipay')
                """,
                (order_id, user["id"], pkg["id"], pkg["price"]),
            )
        conn.commit()

        # 构建支付宝请求参数
        notify_url = ALIPAY_NOTIFY_URL or "http://127.0.0.1:8765/api/payment/notify"
        return_url = ALIPAY_RETURN_URL or "http://127.0.0.1:8765/pay"

        # 使用当面付（不需要签约）
        biz_content = json.dumps({
            "out_trade_no": order_id,
            "total_amount": str(float(pkg["price"])),
            "subject": f"图表在线生成器 - {pkg['package_name']}",
            "body": f"会员套餐 - {pkg['package_name']}",
            "timeout_express": "30m",
            "product_code": "FACE_TO_FACE_PAYMENT"
        }, ensure_ascii=False)

        params = {
            "app_id": ALIPAY_APP_ID,
            "method": "alipay.trade.precreate",
            "charset": CHARSET,
            "sign_type": SIGN_TYPE,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "notify_url": notify_url,
            "return_url": return_url,
            "biz_content": biz_content,
        }

        # 生成签名
        sign_content = _build_sign_params(params)
        sign = _rsa_sign(sign_content, ALIPAY_PRIVATE_KEY)
        params["sign"] = sign

        # 构建支付表单 HTML
        form_html = _build_alipay_form(params)

        logger.info("创建支付宝订单: order_id=%s, amount=%s", order_id, float(pkg["price"]))

        return {
            "success": True,
            "order_id": order_id,
            "pay_form": form_html,
            "package_name": pkg["package_name"],
            "pay_amount": float(pkg["price"]),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("创建支付订单异常: %s", str(e))
        raise HTTPException(status_code=500, detail={"error": "创建支付订单失败"})
    finally:
        conn.close()


def _build_alipay_form(params: dict) -> str:
    """构建支付宝支付表单 HTML"""
    import html

    # charset 必须放在 URL 查询字符串中
    gateway_url = f"{ALIPAY_GATEWAY}?charset={CHARSET}"

    form_fields = ""
    for key, value in params.items():
        # 对值进行 HTML 转义
        escaped_value = html.escape(str(value))
        form_fields += f'<input type="hidden" name="{key}" value="{escaped_value}">\n'

    return f"""
    <form id="alipay_form" name="punchout_form" method="post" action="{gateway_url}">
        {form_fields}
        <input type="submit" value="立即支付" style="display:none">
    </form>
    <script>document.forms[0].submit();</script>
    """


@router.get("/api/payment/status/{order_id}")
def get_payment_status(order_id: str, user: dict = Depends(require_user)):
    """查询支付订单状态"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM order_record WHERE order_id = %s AND user_id = %s",
                (order_id, user["id"]),
            )
            order = cur.fetchone()

            if not order:
                raise HTTPException(status_code=404, detail={"error": "订单不存在"})

            return {
                "order_id": order["order_id"],
                "status": order["pay_status"],
                "pay_amount": float(order["pay_amount"]),
                "pay_method": order.get("pay_method", ""),
                "create_time": str(order["create_time"]),
            }
    finally:
        conn.close()


@router.post("/api/payment/notify")
async def payment_notify(request: Request):
    """
    支付宝异步通知

    安全措施：
    1. 验证签名
    2. 验证金额
    3. 幂等处理
    """
    if not ALIPAY_ENABLED:
        return PlainTextResponse("fail")

    # 获取所有参数
    form_data = await request.form()
    params = {k: str(v) for k, v in form_data.items()}

    logger.info("收到支付宝通知: %s", params)

    # 提取关键参数
    order_id = params.get("out_trade_no", "")
    trade_no = params.get("trade_no", "")
    total_amount = params.get("total_amount", "0")
    trade_status = params.get("trade_status", "")

    if not order_id:
        return PlainTextResponse("fail")

    # 验证签名
    sign = params.get("sign", "")
    sign_content = _build_sign_params(params)
    if not _rsa_verify(sign_content, sign, ALIPAY_PUBLIC_KEY):
        logger.warning("签名验证失败: order_id=%s", order_id)
        return PlainTextResponse("fail")

    # 验证交易状态
    if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        logger.info("交易未成功: order_id=%s, status=%s", order_id, trade_status)
        return PlainTextResponse("fail")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 查询订单
            cur.execute("SELECT * FROM order_record WHERE order_id = %s", (order_id,))
            order = cur.fetchone()

            if not order:
                logger.warning("订单不存在: %s", order_id)
                return PlainTextResponse("fail")

            # 幂等检查
            if order["pay_status"] == "paid":
                return PlainTextResponse("success")

            # 验证金额
            if abs(float(total_amount) - float(order["pay_amount"])) > 0.01:
                logger.warning("金额不匹配: expected=%s, got=%s", order["pay_amount"], total_amount)
                return PlainTextResponse("fail")

            # 更新订单状态
            cur.execute(
                """
                UPDATE order_record
                SET pay_status = 'paid', trade_no = %s, finish_time = NOW()
                WHERE order_id = %s AND pay_status = 'pending'
                """,
                (trade_no, order_id),
            )

            if cur.rowcount == 0:
                return PlainTextResponse("success")

            # 查询套餐信息
            cur.execute("SELECT * FROM vip_package WHERE id = %s", (order["package_id"],))
            pkg = cur.fetchone()

            if pkg:
                # 激活 VIP
                now = datetime.now()
                cur.execute("SELECT vip_expire_time FROM user WHERE id = %s", (order["user_id"],))
                user_row = cur.fetchone()

                if user_row and user_row.get("vip_expire_time"):
                    current_expire = user_row["vip_expire_time"]
                    if isinstance(current_expire, datetime) and current_expire > now:
                        expire_time = (current_expire + timedelta(days=float(pkg["valid_days"])))
                    else:
                        expire_time = (now + timedelta(days=float(pkg["valid_days"])))
                else:
                    expire_time = (now + timedelta(days=float(pkg["valid_days"])))

                expire_str = expire_time.strftime("%Y-%m-%d %H:%M:%S")
                cur.execute(
                    "UPDATE user SET vip_type = %s, vip_expire_time = %s WHERE id = %s",
                    (pkg["type"], expire_str, order["user_id"]),
                )

                logger.info("支付宝支付成功: order_id=%s, user_id=%s, package=%s",
                           order_id, order["user_id"], pkg["package_name"])

        conn.commit()
        return PlainTextResponse("success")

    except Exception as e:
        logger.error("处理支付宝通知异常: %s", str(e))
        return PlainTextResponse("fail")
    finally:
        conn.close()


@router.get("/api/payment/check/{order_id}")
def check_payment(order_id: str, user: dict = Depends(require_user)):
    """检查支付状态（前端轮询）"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM order_record WHERE order_id = %s AND user_id = %s",
                (order_id, user["id"]),
            )
            order = cur.fetchone()

            if not order:
                raise HTTPException(status_code=404, detail={"error": "订单不存在"})

            paid = order["pay_status"] == "paid"

            # 如果已支付，返回更新后的用户信息
            user_info = None
            if paid:
                cur.execute("SELECT * FROM user WHERE id = %s", (user["id"],))
                user_row = cur.fetchone()
                if user_row:
                    user_info = user_payload(user_row)

            return {
                "paid": paid,
                "order_id": order_id,
                "status": order["pay_status"],
                "user": user_info,
            }
    finally:
        conn.close()
