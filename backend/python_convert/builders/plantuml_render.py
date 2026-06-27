#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render PlantUML source to SVG via HTTP PlantUML server (stdlib only)."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
import zlib

DEFAULT_SERVER = "https://www.plantuml.com/plantuml/svg/"


def get_server_url() -> str:
    url = os.environ.get("PLANTUML_SERVER", DEFAULT_SERVER).strip()
    if not url.endswith("/"):
        url += "/"
    return url


def _encode6bit(b: int) -> str:
    if b < 10:
        return chr(48 + b)
    b -= 10
    if b < 26:
        return chr(65 + b)
    b -= 26
    if b < 26:
        return chr(97 + b)
    b -= 26
    if b == 0:
        return "-"
    if b == 1:
        return "_"
    return "?"


def _append3bytes(b1: int, b2: int, b3: int) -> str:
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F
    return _encode6bit(c1) + _encode6bit(c2) + _encode6bit(c3) + _encode6bit(c4)


def encode_plantuml(text: str) -> str:
    """PlantUML 官方 URL 编码（deflate + 6bit）。"""
    data = zlib.compress(text.encode("utf-8"))[2:-4]
    res = []
    i = 0
    while i < len(data):
        if i + 2 == len(data):
            res.append(_append3bytes(data[i], data[i + 1], 0))
        elif i + 1 == len(data):
            res.append(_append3bytes(data[i], 0, 0))
        else:
            res.append(_append3bytes(data[i], data[i + 1], data[i + 2]))
        i += 3
    return "".join(res)


def render_svg(plantuml_text: str, *, timeout: float = 60.0) -> bytes:
    text = plantuml_text.strip()
    if not text.startswith("@startuml"):
        text = f"@startuml\n{text}\n@enduml"

    server = get_server_url()
    url = server + encode_plantuml(text)

    req = urllib.request.Request(url, headers={"User-Agent": "DiagramGenerator/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = resp.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"PlantUML 服务不可用 ({server}): {exc.reason}") from exc
    except Exception as exc:
        raise RuntimeError(f"PlantUML 渲染失败: {exc}") from exc

    if not result:
        raise RuntimeError("PlantUML 返回空 SVG")
    if b"<svg" not in result[:200].lower() and b"<svg" not in result.lower()[:500]:
        snippet = result[:200].decode("utf-8", errors="replace")
        raise RuntimeError(f"PlantUML 未返回有效 SVG: {snippet}")
    return result
