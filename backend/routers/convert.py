#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.converter import HAS_CONVERTER, json_to_xml
from backend.db import get_db
from backend.deps import require_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["convert"])


class ConvertBody(BaseModel):
    json_content: str = ""


def _is_vip_active(row: dict) -> bool:
    """检查会员是否有效"""
    # 管理员始终有效
    if row.get("is_admin"):
        return True

    # 检查邀请期间
    invite_expire = row.get("invite_expire_time")
    if invite_expire and isinstance(invite_expire, datetime) and invite_expire > datetime.now():
        return True

    # 检查 VIP 有效期
    vip_expire = row.get("vip_expire_time")
    if vip_expire:
        try:
            if isinstance(vip_expire, datetime):
                return vip_expire > datetime.now()
            # 字符串格式
            expire_time = datetime.strptime(str(vip_expire), "%Y-%m-%d %H:%M:%S")
            return expire_time > datetime.now()
        except (ValueError, TypeError):
            pass

    return False


@router.post("/convert-example")
def convert_example(body: ConvertBody):
    """示例渲染接口：无需登录，免费使用"""
    if not HAS_CONVERTER:
        raise HTTPException(status_code=500, detail={"error": "Python 转换模块未安装"})

    json_content = body.json_content
    if not json_content:
        raise HTTPException(status_code=400, detail={"error": "json_content 不能为空"})

    try:
        xml = json_to_xml(json_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)}) from e

    return {"success": True, "xml": xml}


@router.post("/convert")
def convert(body: ConvertBody, user: dict = Depends(require_user)):
    if not HAS_CONVERTER:
        raise HTTPException(status_code=500, detail={"error": "Python 转换模块未安装"})

    json_content = body.json_content
    if not json_content:
        raise HTTPException(status_code=400, detail={"error": "json_content 不能为空"})

    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user WHERE id = %s", (user["id"],))
        row = cur.fetchone()

        # 检查会员状态
        if not _is_vip_active(row):
            conn.close()
            raise HTTPException(
                status_code=403,
                detail={"error": "会员已过期，请续费后使用"}
            )

        try:
            xml = json_to_xml(json_content)
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=400, detail={"error": str(e)}) from e

        # 记录使用
        cfg = json.loads(json_content)
        cur.execute(
            "INSERT INTO file_record (user_id, json_content, xml_content, chart_type, title) VALUES (%s, %s, %s, %s, %s)",
            (
                user["id"],
                json_content,
                xml,
                cfg.get("type", ""),
                cfg.get("title", ""),
            ),
        )
    conn.commit()

    # 获取最新用户信息
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM user WHERE id = %s", (user["id"],))
        updated = cur.fetchone()
    conn.close()

    # 计算会员剩余时间
    vip_remaining = 0
    vip_expire = updated.get("vip_expire_time")
    if vip_expire:
        try:
            if isinstance(vip_expire, datetime):
                expire_time = vip_expire
            else:
                expire_time = datetime.strptime(str(vip_expire), "%Y-%m-%d %H:%M:%S")
            if expire_time > datetime.now():
                vip_remaining = int((expire_time - datetime.now()).total_seconds())
        except (ValueError, TypeError):
            pass

    return {
        "success": True,
        "xml": xml,
        "vip_active": _is_vip_active(updated),
        "vip_remaining": vip_remaining,
    }
