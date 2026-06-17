#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.converter import HAS_CONVERTER, json_to_xml
from backend.db import get_db
from backend.deps import require_user

router = APIRouter(prefix="/api", tags=["convert"])


class ConvertBody(BaseModel):
    json_content: str = ""


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
        if not row["is_admin"] and row["remain_count"] <= 0:
            conn.close()
            raise HTTPException(status_code=403, detail={"error": "生成次数已用完，请购买会员"})

        try:
            xml = json_to_xml(json_content)
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=400, detail={"error": str(e)}) from e

        if not row["is_admin"]:
            cur.execute(
                "UPDATE user SET remain_count = remain_count - 1 WHERE id = %s AND remain_count > 0",
                (user["id"],),
            )

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

    with conn.cursor() as cur:
        cur.execute("SELECT remain_count FROM user WHERE id = %s", (user["id"],))
        updated = cur.fetchone()
    conn.close()

    return {
        "success": True,
        "xml": xml,
        "remain_count": updated["remain_count"],
    }
