#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 JSON 生成功能模块图（draw.io / diagrams.net 的 mxfile XML）。

JSON 只需填写内容与角色（任意多个），布局在脚本内固定，无需写 layout。

用法:
  python mo.py mo.json -o 功能模块图.xml
  python mo.py - < my.json
  python mo.py in.json -o out.xml --trim

依赖: 标准库；加 --trim 时会尝试调用同目录 trim_drawio_horizontal_edges.py 裁剪横线。

连线说明: 边的 mxGeometry 须带 as=geometry（与 diagrams.net 导出一致），否则部分环境下线段不显示。
"""

from __future__ import annotations

import argparse
import html
import io
import itertools
import json
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# 与 diagrams.net 导出线一致；边必须有 mxGeometry as="geometry" 才会稳定显示
EDGE_STYLE = "endArrow=none;html=1;rounded=0;"
EDGE_STYLE_EXIT = "endArrow=none;html=1;rounded=0;exitX=0.5;exitY=0;exitDx=0;exitDy=0;"
TITLE_STYLE = (
    "rounded=0;whiteSpace=wrap;html=1;strokeColor=default;align=center;"
    "verticalAlign=middle;fontFamily=Helvetica;fontSize=12;fontColor=default;"
    "fillColor=default;fontStyle=0"
)
BOX_STYLE = "rounded=0;whiteSpace=wrap;html=1;"

# 内置布局（与原先手写图一致，勿在 JSON 中重复配置）
_L = {
    "mid_x": 452.0,
    "title_x": 227.5,
    "title_width": 456.5,
    "title_height": 60.0,
    "title_y": -5.0,
    "role_box_width": 120.0,
    "role_box_height": 60.0,
    "role_y": 221.0,
    "top_bar_y": 141.0,
    "spine_y": 340.0,
    "module_y": 381.0,
    "module_box_height": 300.0,
    "bar_width": 41.0,
    "column_step": 46.5,
    "font_size": 14,
    "role_spacing_base": 180.0,
    "min_cluster_gap": 60.0,
    "page_margin": 40.0,
    "page_width_min": 827.0,
}


def _font_value(text: str, font_size: int = 14) -> str:
    """draw.io 存 HTML 片段；由 ElementTree 写入时会正确转义为 &lt;font ...&gt;。"""
    inner = html.escape(text)
    return f'<font style="font-size: {font_size}px;">{inner}</font>'


def _span_value(text: str, font_size: int = 14) -> str:
    inner = html.escape(text)
    return f'<span style="font-size: {font_size}px;">{inner}</span>'


def _new_id() -> str:
    return f"id-{uuid.uuid4().hex[:16]}"


def _cell(
    parent: ET.Element,
    cell_id: str,
    *,
    vertex: bool = False,
    edge: bool = False,
    parent_id: str | None = "1",
    style: str = "",
    value: str | None = None,
    source: str | None = None,
    **geom: Any,
) -> ET.Element:
    att: dict[str, str] = {"id": cell_id}
    if parent_id is not None:
        att["parent"] = parent_id
    if vertex:
        att["vertex"] = "1"
    if edge:
        att["edge"] = "1"
    if style:
        att["style"] = style
    if value is not None:
        att["value"] = str(value)
    if source:
        att["source"] = source
    c = ET.SubElement(parent, "mxCell", att)
    if geom:
        g = ET.SubElement(c, "mxGeometry", {k: str(v) for k, v in geom.items() if v is not None})
        g.set("as", "geometry")
    return c


def _edge_geometry(
    parent_el: ET.Element,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    relative: bool = True,
) -> None:
    g = parent_el.find("mxGeometry")
    if g is None:
        g = ET.SubElement(parent_el, "mxGeometry")
    g.set("height", "50")
    g.set("width", "50")
    if relative:
        g.set("relative", "1")
    g.set("as", "geometry")
    p1 = ET.SubElement(g, "mxPoint")
    p1.set("x", str(x1))
    p1.set("y", str(y1))
    p1.set("as", "sourcePoint")
    p2 = ET.SubElement(g, "mxPoint")
    p2.set("x", str(x2))
    p2.set("y", str(y2))
    p2.set("as", "targetPoint")


def _role_centers(n: int, mid_x: float, role_spacing: float) -> list[float]:
    """n 个角色沿 mid_x 对称分布，间距为相邻中心距 role_spacing。"""
    if n <= 0:
        return []
    return [mid_x + (i - (n - 1) / 2.0) * role_spacing for i in range(n)]


def _module_left_edges(
    role_center: float,
    n_mod: int,
    bar_w: float,
    step: float,
) -> list[float]:
    if n_mod <= 0:
        return []
    span = (n_mod - 1) * step + bar_w
    left0 = role_center - span / 2.0
    return [left0 + k * step for k in range(n_mod)]


def build_mxgraph(cfg: dict[str, Any]) -> tuple[ET.Element, int]:
    if "title" not in cfg:
        raise ValueError("JSON 须包含 title")
    title = str(cfg["title"])
    roles: list[dict[str, Any]] = list(cfg.get("roles") or [])
    n_roles = len(roles)

    title_w = _L["title_width"]
    title_h = _L["title_height"]
    title_y = _L["title_y"]
    title_bottom = title_y + title_h
    rb_w = _L["role_box_width"]
    rb_h = _L["role_box_height"]
    role_y = _L["role_y"]
    top_y = _L["top_bar_y"]
    spine_y = _L["spine_y"]
    mod_y = _L["module_y"]
    mod_h = _L["module_box_height"]
    bar_w = _L["bar_width"]
    step = _L["column_step"]
    font_size = _L["font_size"]
    middle_conn = True
    margin = _L["page_margin"]

    max_mod = max((len(r.get("modules") or []) for r in roles), default=0)
    role_spacing = _L["role_spacing_base"]
    if max_mod > 0:
        cluster_w = (max_mod - 1) * step + bar_w
        if n_roles >= 2:
            min_center_dist = cluster_w + _L["min_cluster_gap"]
            role_spacing = max(role_spacing, min_center_dist)
    else:
        cluster_w = rb_w

    # 固定画布宽度 827 时，多角色大模块会把中心挤到画布外，连线看不见；按内容加宽 pageWidth 并居中
    content_span = (n_roles - 1) * role_spacing + cluster_w
    page_width = max(
        _L["page_width_min"],
        content_span + 2 * margin,
        title_w + 2 * margin,
    )
    mid_x = page_width / 2.0
    title_x = (page_width - title_w) / 2.0

    root = ET.Element("root")
    _cell(root, "0", parent_id=None)
    _cell(root, "1", parent_id="0")

    nid = itertools.count(1)

    def cid() -> str:
        return f"c{next(nid)}"

    # 标题
    tid = cid()
    _cell(
        root,
        tid,
        vertex=True,
        style=TITLE_STYLE,
        value=_font_value(title, font_size),
        x=title_x,
        y=title_y,
        width=title_w,
        height=title_h,
    )

    centers = _role_centers(n_roles, mid_x, role_spacing)
    role_bottom = role_y + rb_h

    # 顶层横线：覆盖所有角色竖线与标题竖线在 top_y 的交点
    xs_top = list(centers)
    xs_top.append(mid_x)
    xs_top.sort()
    h_top_id = cid()
    ht = _cell(root, h_top_id, edge=True, style=EDGE_STYLE, value="")
    _edge_geometry(ht, xs_top[-1], top_y, xs_top[0], top_y)

    # 标题 -> 顶层横线
    v_title = cid()
    vt = _cell(root, v_title, edge=True, style=EDGE_STYLE, value="")
    _edge_geometry(vt, mid_x, top_y, mid_x, title_bottom)

    role_vertex_ids: list[str] = []
    role_module_boxes: list[list[tuple[str, float]]] = []

    for ri, r in enumerate(roles):
        name = r["name"]
        modules: list[str] = list(r.get("modules") or [])
        cx = centers[ri]
        rbx = cx - rb_w / 2.0

        rvid = cid()
        role_vertex_ids.append(rvid)
        _cell(
            root,
            rvid,
            vertex=True,
            style=BOX_STYLE,
            value=_font_value(name, font_size),
            x=rbx,
            y=role_y,
            width=rb_w,
            height=rb_h,
        )

        # 角色 -> 顶层横线
        ev = cid()
        e1 = _cell(
            root,
            ev,
            edge=True,
            style=EDGE_STYLE_EXIT,
            value="",
            source=rvid,
        )
        _edge_geometry(e1, cx, role_y, cx, top_y)

        lefts = _module_left_edges(cx, len(modules), bar_w, step)
        mod_row: list[tuple[str, float]] = []
        for mi, mod_name in enumerate(modules):
            lx = lefts[mi]
            mcid = cid()
            val = _font_value(mod_name, font_size)
            if len(mod_name) > 8:
                val = _span_value(mod_name, font_size)
            _cell(
                root,
                mcid,
                vertex=True,
                style=BOX_STYLE,
                value=val,
                x=lx,
                y=mod_y,
                width=bar_w,
                height=mod_h,
            )
            cx_mod = lx + bar_w / 2.0
            mod_row.append((mcid, cx_mod))

        role_module_boxes.append(mod_row)

        # 该列三级横线
        if lefts:
            hsp = cid()
            lo = lefts[0] + bar_w / 2.0
            hi = lefts[-1] + bar_w / 2.0
            hs = _cell(root, hsp, edge=True, style=EDGE_STYLE, value="")
            _edge_geometry(hs, hi, spine_y, lo, spine_y)

        if middle_conn and lefts:
            mc = cid()
            e2 = _cell(root, mc, edge=True, style=EDGE_STYLE, value="")
            _edge_geometry(e2, cx, spine_y, cx, role_bottom)

        # 模块竖线
        for mcid, cx_mod in mod_row:
            ve = cid()
            e3 = _cell(
                root,
                ve,
                edge=True,
                style=EDGE_STYLE_EXIT,
                value="",
                source=mcid,
            )
            _edge_geometry(e3, cx_mod, mod_y, cx_mod, spine_y)

    return root, int(page_width)


def build_document(cfg: dict[str, Any]) -> ET.ElementTree:
    root_el = ET.Element("mxfile", {"host": "app.diagrams.net"})
    diag = ET.SubElement(root_el, "diagram", {"name": "Page-1", "id": _new_id()})
    gm = ET.SubElement(
        diag,
        "mxGraphModel",
        {
            "dx": "2168",
            "dy": "1371",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "0",
            "pageScale": "1",
            "pageHeight": "1169",
            "math": "0",
            "shadow": "0",
        },
    )
    graph_root, page_w = build_mxgraph(cfg)
    gm.set("pageWidth", str(page_w))
    gm.append(graph_root)
    tree = ET.ElementTree(root_el)
    return tree


def main() -> int:
    ap = argparse.ArgumentParser(description="从 JSON 生成功能模块图 draw.io XML")
    ap.add_argument(
        "input",
        nargs="?",
        type=str,
        default=None,
        help="JSON 文件路径，或 - 表示从标准输入读取",
    )
    ap.add_argument("-o", "--output", type=Path, help="输出 .xml 路径（默认 stdout）")
    ap.add_argument(
        "--trim",
        action="store_true",
        help="生成后调用 trim_drawio_horizontal_edges 裁剪水平线（同 y 多段横线可能不适用）",
    )
    args = ap.parse_args()

    src = args.input
    if src in (None, "-"):
        data = sys.stdin.read()
    else:
        data = Path(src).read_text(encoding="utf-8-sig")
    if data.startswith("\ufeff"):
        data = data[1:]

    cfg = json.loads(data)
    try:
        tree = build_document(cfg)
    except (ValueError, KeyError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    if args.trim:
        try:
            from trim_drawio_horizontal_edges import process_document

            r = tree.getroot().find(".//mxGraphModel/root")
            if r is not None:
                process_document(r)
        except Exception as e:
            print(f"警告: 水平线裁剪未执行: {e}", file=sys.stderr)

    out: io.StringIO | Path
    if args.output:
        out_path = args.output
        tree.write(out_path, encoding="utf-8", xml_declaration=True)
        print(f"已写入: {out_path}", file=sys.stderr)
    else:
        buf = io.StringIO()
        tree.write(buf, encoding="unicode", xml_declaration=True)
        sys.stdout.write(buf.getvalue())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())