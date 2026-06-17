#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render PlantUML source to SVG via HTTP PlantUML server."""

from __future__ import annotations

import os
import urllib.error
import urllib.request

DEFAULT_SERVER = "http://www.plantuml.com/plantuml/svg/"


def get_server_url() -> str:
    url = os.environ.get("PLANTUML_SERVER", DEFAULT_SERVER).strip()
    if not url.endswith("/"):
        url += "/"
    return url


def render_svg(plantuml_text: str, *, timeout: float = 60.0) -> bytes:
    text = plantuml_text.strip()
    if not text.startswith("@startuml"):
        text = f"@startuml\n{text}\n@enduml"

    try:
        from plantuml import PlantUML
    except ImportError as exc:
        raise RuntimeError("缺少 plantuml 依赖，请执行: pip install plantuml") from exc

    server = get_server_url()
    client = PlantUML(url=server)
    try:
        result = client.processes(text)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"PlantUML 服务不可用 ({server}): {exc.reason}") from exc
    except Exception as exc:
        raise RuntimeError(f"PlantUML 渲染失败: {exc}") from exc

    if not result:
        raise RuntimeError("PlantUML 返回空 SVG")
    if isinstance(result, str):
        result = result.encode("utf-8")
    if b"<svg" not in result[:200].lower() and b"<svg" not in result.lower()[:500]:
        snippet = result[:200].decode("utf-8", errors="replace")
        raise RuntimeError(f"PlantUML 未返回有效 SVG: {snippet}")
    return result
