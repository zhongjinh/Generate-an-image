#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build draw.io mxfile with embedded PlantUML SVG (same format as draw.io PlantUML export)."""

from __future__ import annotations

import base64
import importlib.util
import json
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_BUILDERS_DIR = Path(__file__).resolve().parent


def _render_svg(plantuml_text: str) -> bytes:
    path = _BUILDERS_DIR / "plantuml_render.py"
    spec = importlib.util.spec_from_file_location("_plantuml_render", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.render_svg(plantuml_text)


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _svg_size(svg_bytes: bytes) -> tuple[float, float]:
    text = svg_bytes.decode("utf-8", errors="replace")
    m = re.search(r'viewBox="0\s+0\s+([\d.]+)\s+([\d.]+)"', text)
    if m:
        return float(m.group(1)), float(m.group(2))
    mw = re.search(r'\bwidth="([\d.]+)"', text)
    mh = re.search(r'\bheight="([\d.]+)"', text)
    if mw and mh:
        return float(mw.group(1)), float(mh.group(1))
    return 838.0, 629.0


def build_document(plantuml_text: str, *, title: str = "序列图") -> ET.ElementTree:
    svg_bytes = _render_svg(plantuml_text)
    svg_w, svg_h = _svg_size(svg_bytes)

    margin_x = 30.0
    margin_y = 40.0
    page_w = max(827, int(svg_w + margin_x * 2))
    page_h = max(1169, int(svg_h + margin_y * 2))

    display_w = min(svg_w, page_w - margin_x * 2)
    scale = display_w / svg_w if svg_w else 1.0
    display_h = svg_h * scale

    b64 = base64.b64encode(svg_bytes).decode("ascii")
    image_style = (
        "shape=image;noLabel=1;verticalAlign=top;aspect=fixed;imageAspect=0;"
        f"image=data:image/svg+xml,{b64}"
    )

    plant_data = json.dumps(
        {"data": plantuml_text.strip(), "format": "svg"},
        ensure_ascii=False,
    )

    root_el = ET.Element("mxfile", {"host": "app.diagrams.net"})
    diagram = ET.SubElement(root_el, "diagram", {
        "name": title or "序列图",
        "id": _new_id(),
    })
    model = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "1200",
        "dy": "800",
        "grid": "1",
        "gridSize": "10",
        "guides": "1",
        "tooltips": "1",
        "connect": "1",
        "arrows": "1",
        "fold": "1",
        "page": "1",
        "pageScale": "1",
        "pageWidth": str(page_w),
        "pageHeight": str(page_h),
        "math": "0",
        "shadow": "0",
    })
    mx_root = ET.SubElement(model, "root")
    ET.SubElement(mx_root, "mxCell", {"id": "0"})
    ET.SubElement(mx_root, "mxCell", {"id": "1", "parent": "0"})

    uo_id = _new_id()
    uo = ET.SubElement(mx_root, "UserObject", {
        "label": "",
        "plantUmlData": plant_data,
        "id": uo_id,
    })
    cell = ET.SubElement(uo, "mxCell", {
        "parent": "1",
        "style": image_style,
        "vertex": "1",
    })
    geom = ET.SubElement(cell, "mxGeometry", {
        "x": str(int(margin_x)),
        "y": str(int(margin_y)),
        "width": str(round(display_w, 2)),
        "height": str(round(display_h, 2)),
        "as": "geometry",
    })

    tree = ET.ElementTree(root_el)
    try:
        ET.indent(tree.getroot(), space="  ")
    except AttributeError:
        pass
    return tree


def build_from_cfg(cfg: dict[str, Any]) -> ET.ElementTree:
    source = (cfg.get("_plantuml_source") or cfg.get("plantuml") or "").strip()
    if not source:
        raise ValueError("缺少 PlantUML 源码")
    title = cfg.get("title") or "序列图"
    return build_document(source, title=title)
