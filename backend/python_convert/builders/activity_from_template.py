#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Template-based activity diagram: JSON text replacements on fixed draw.io XML."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

_FONT_SIZE = 13
_CJK_WIDTH = 11.0
_LATIN_WIDTH = 6.5
_LINE_HEIGHT = 17.0
_PAD_H = 10.0
_PAD_V = 8.0
_MAX_BOX_W = 132.0
_RHOMBUS_INSCRIBED = 0.68


def _norm_text(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</?div[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _display_lines(value: str) -> list[str]:
    text = html.unescape(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</?div[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    lines = [ln.strip() for ln in text.split("\n")]
    return lines if any(lines) else [""]


def _line_width(line: str, font_size: int = _FONT_SIZE) -> float:
    scale = font_size / _FONT_SIZE
    width = 0.0
    for ch in line:
        if ord(ch) > 127:
            width += _CJK_WIDTH * scale
        else:
            width += _LATIN_WIDTH * scale
    return width


def _font_size_from_style(style: str) -> int:
    m = re.search(r"fontSize=(\d+)", style or "")
    return int(m.group(1)) if m else _FONT_SIZE


def _char_width(ch: str, font_size: int) -> float:
    scale = font_size / _FONT_SIZE
    if ord(ch) > 127:
        return _CJK_WIDTH * scale
    return _LATIN_WIDTH * scale


def _wrap_lines(value: str, font_size: int, max_inner_w: float) -> list[str]:
    result: list[str] = []
    for paragraph in _display_lines(value):
        if not paragraph:
            result.append("")
            continue
        line = ""
        line_w = 0.0
        for ch in paragraph:
            cw = _char_width(ch, font_size)
            if line and line_w + cw > max_inner_w:
                result.append(line)
                line = ch
                line_w = cw
            else:
                line += ch
                line_w += cw
        if line:
            result.append(line)
    return result or [""]


def _estimate_box(value: str, style: str) -> tuple[float, float] | None:
    if not value or not value.strip():
        return None
    if cell_is_edge_style(style):
        return None

    font_size = _font_size_from_style(style)

    if "rhombus" in style:
        # 在接近模板宽度内换行，再按需小幅放大
        inner_max = 78.0
        lines = _wrap_lines(value, font_size, inner_max)
        max_line_w = max(_line_width(ln, font_size) for ln in lines)
        line_count = max(len(lines), 1)
        inner_w = max_line_w + _PAD_H
        inner_h = line_count * _LINE_HEIGHT + _PAD_V
        w = max(90.0, inner_w / _RHOMBUS_INSCRIBED)
        h = max(72.0, inner_h / 0.78, w * 0.26)
        return w, h

    if style.startswith("swimlane") or "swimlane;" in style:
        lines = _display_lines(value)
        max_line_w = max(_line_width(ln, font_size) for ln in lines)
        w = max(80.0, max_line_w + 28)
        return w, 40.0

    if "rounded=1" in style or style.startswith("rounded"):
        inner_max = _MAX_BOX_W - _PAD_H * 2
        lines = _wrap_lines(value, font_size, inner_max)
        max_line_w = max(_line_width(ln, font_size) for ln in lines)
        line_count = max(len(lines), 1)
        w = max(80.0, min(max_line_w + _PAD_H * 2, _MAX_BOX_W))
        h = max(36.0, line_count * _LINE_HEIGHT + _PAD_V * 2)
        return w, h

    return None


def cell_is_edge_style(style: str) -> bool:
    return "edgeStyle=" in (style or "")


def _resize_geometry(cell: ET.Element, new_w: float, new_h: float) -> None:
    geom = cell.find("mxGeometry")
    if geom is None:
        return
    try:
        old_x = float(geom.get("x", "0") or 0)
        old_y = float(geom.get("y", "0") or 0)
        old_w = float(geom.get("width", "0") or 0)
        old_h = float(geom.get("height", "0") or 0)
    except ValueError:
        return

    cx = old_x + old_w / 2.0
    cy = old_y + old_h / 2.0
    geom.set("x", str(int(round(cx - new_w / 2.0))))
    geom.set("y", str(int(round(cy - new_h / 2.0))))
    geom.set("width", str(int(round(new_w))))
    geom.set("height", str(int(round(new_h))))


def _fit_cell_geometry(cell: ET.Element) -> None:
    if cell.get("vertex") != "1":
        return
    style = cell.get("style") or ""
    value = cell.get("value") or ""
    if not value.strip():
        return

    needed = _estimate_box(value, style)
    if needed is None:
        return

    need_w, need_h = needed
    geom = cell.find("mxGeometry")
    if geom is None:
        return
    try:
        cur_w = float(geom.get("width", "0") or 0)
        cur_h = float(geom.get("height", "0") or 0)
    except ValueError:
        return

    new_w = max(cur_w, need_w)
    new_h = max(cur_h, need_h)
    if new_w > cur_w + 0.5 or new_h > cur_h + 0.5:
        _resize_geometry(cell, new_w, new_h)


def _build_replacements(cfg: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in cfg.get("nodes") or []:
        if not isinstance(item, dict):
            continue
        match = item.get("match_text") or item.get("match") or ""
        text = item.get("text") or item.get("value") or ""
        if match:
            mapping[str(match)] = str(text)
    for item in cfg.get("links") or []:
        if not isinstance(item, dict):
            continue
        match = item.get("match_text") or item.get("match") or ""
        text = item.get("text") or item.get("value") or ""
        if match:
            mapping[str(match)] = str(text)
    return mapping


def _replace_value(value: str, mapping: dict[str, str]) -> str:
    if value in mapping:
        return mapping[value]
    norm = _norm_text(value)
    for match, text in mapping.items():
        if _norm_text(match) == norm:
            return text
    return value


def build_from_template(cfg: dict[str, Any]) -> ET.ElementTree:
    tpl = cfg.get("template_xml") or "activity_diagram.xml"
    tpl_path = Path(str(tpl))
    if not tpl_path.is_absolute():
        tpl_path = _TEMPLATES / tpl_path.name
    if not tpl_path.exists():
        raise ValueError(f"活动图模板不存在: {tpl_path}")

    mapping = _build_replacements(cfg)
    tree = ET.parse(tpl_path)
    root = tree.getroot()

    title = cfg.get("title") or (cfg.get("meta") or {}).get("title") or ""
    if title:
        diagram = root.find(".//diagram")
        if diagram is not None:
            diagram.set("name", str(title))

    mx_root = root.find(".//mxGraphModel/root")
    if mx_root is None:
        raise ValueError("模板 XML 中找不到 mxGraphModel/root")

    for cell in mx_root.findall("mxCell"):
        value = cell.get("value")
        if value is None:
            continue
        new_value = _replace_value(value, mapping)
        if new_value != value:
            cell.set("value", new_value)

    for cell in mx_root.findall("mxCell"):
        _fit_cell_geometry(cell)

    return tree
