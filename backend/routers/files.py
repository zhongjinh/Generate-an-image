#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.db import get_db
from backend.deps import _row_dict, require_user

router = APIRouter(prefix="/api/files", tags=["files"])


class SaveFileBody(BaseModel):
    json_content: str = ""
    xml_content: str = ""
    chart_type: str = ""
    title: str = ""


@router.get("")
def get_files(user: dict = Depends(require_user)):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, chart_type, title, create_time FROM file_record WHERE user_id = %s ORDER BY create_time DESC LIMIT 100",
            (user["id"],),
        )
        rows = cur.fetchall()
    conn.close()
    return {"files": [_row_dict(r) for r in rows]}


@router.post("")
def save_file(body: SaveFileBody, user: dict = Depends(require_user)):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO file_record (user_id, json_content, xml_content, chart_type, title) VALUES (%s, %s, %s, %s, %s)",
            (
                user["id"],
                body.json_content,
                body.xml_content,
                body.chart_type,
                body.title,
            ),
        )
    conn.commit()
    conn.close()
    return {"success": True}
