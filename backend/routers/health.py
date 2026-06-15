#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter

from backend.converter import HAS_CONVERTER

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    return {"status": "ok", "converter": HAS_CONVERTER}
