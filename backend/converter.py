#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON → draw.io XML 转换模块加载"""

from __future__ import annotations

try:
    from backend.python_convert import convert as json_to_xml

    HAS_CONVERTER = True
except ImportError:
    HAS_CONVERTER = False
    json_to_xml = None  # type: ignore
