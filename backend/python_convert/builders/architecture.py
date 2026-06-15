#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 JSON 生成架构图（draw.io mxfile）。
版式与样式对齐 templates/architecture_diagram.xml（架构图.txt）。

- 三层 swimlane：前端交互 / 后端业务 / 数据持久
- 子分组：嵌套 swimlane（2 列网格 / 3 列纵排 / 单行横排 / 多组横排）
- 组件宽度按文字自适应；超出时自动换行并扩大外层容器
"""

from __future__ import annotations

import argparse
import html
import io
import json
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# ---------- 模板常量 ----------
MARGIN_X = 80
LAYER_W_MIN = 1000
TITLE_W = 500
TITLE_H = 40
TITLE_Y = 20
FIRST_LAYER_Y = 80
LAYER_V_GAP = 40
PAGE_W_MIN = 1169

NODE_H = 40
NODE_MIN_W = 120
NODE_MAX_W = 280
NODE_GAP = 16
ROW_GAP = 12
GROUP_PAD = 20
GROUP_GAP = 24
LAYER_PAD = 30

FONT_SIZE = 14

STYLE_TITLE = (
    "text;html=1;strokeColor=#000000;fillColor=none;align=center;"
    "verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=" + str(FONT_SIZE) + ";fontStyle=0"
)
STYLE_LAYER = (
    "swimlane;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;"
    "fontSize=" + str(FONT_SIZE) + ";fontStyle=0;startSize=40;swimlaneFillColor=none;"
)
STYLE_GROUP = (
    "swimlane;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;"
    "fontSize=" + str(FONT_SIZE) + ";fontStyle=0;startSize=35;swimlaneFillColor=none;"
)
STYLE_GROUP_SM = (
    "swimlane;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;"
    "fontSize=" + str(FONT_SIZE) + ";fontStyle=0;startSize=30;swimlaneFillColor=none;"
)
STYLE_NODE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#000000;"
    "fontSize=" + str(FONT_SIZE) + ";fontStyle=0;"
)
STYLE_EDGE = "endArrow=block;endFill=1;html=1;strokeWidth=2;strokeColor=#000000;"
STYLE_EDGE_LABEL = (
    "text;html=1;strokeColor=none;fillColor=none;align=center;"
    "verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=" + str(FONT_SIZE) + ";fontStyle=0;"
)

LAYER_HEIGHT_MIN = {
    "grid2x2": 240,
    "columns3": 240,
    "horizontal": 160,
    "horizontal_groups": 160,
}


def _esc(text: str) -> str:
    return html.escape(str(text))


def _new_id() -> str:
    return f"id-{uuid.uuid4().hex[:16]}"


def _cell(
    root: ET.Element,
    cell_id: str,
    *,
    parent: str = "1",
    vertex: bool = False,
    edge: bool = False,
    style: str = "",
    value: str = "",
    source: str | None = None,
    target: str | None = None,
    x: float = 0,
    y: float = 0,
    w: float = 0,
    h: float = 0,
) -> ET.Element:
    att: dict[str, str] = {"id": cell_id, "parent": parent}
    if vertex:
        att["vertex"] = "1"
    if edge:
        att["edge"] = "1"
    if style:
        att["style"] = style
    if value:
        att["value"] = value
    if source:
        att["source"] = source
    if target:
        att["target"] = target
    c = ET.SubElement(root, "mxCell", att)
    if edge:
        ET.SubElement(c, "mxGeometry", {"relative": "1", "as": "geometry"})
    elif w or h:
        ET.SubElement(
            c,
            "mxGeometry",
            {
                "x": str(int(round(x))),
                "y": str(int(round(y))),
                "width": str(int(round(w))),
                "height": str(int(round(h))),
                "as": "geometry",
            },
        )
    return c


def _node_names(items: list[Any]) -> list[str]:
    out: list[str] = []
    for item in items:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            out.append(str(item.get("name") or item.get("label") or ""))
        else:
            out.append(str(item))
    return [n for n in out if n]


def _text_width(text: str) -> float:
    w = 32.0
    for ch in text:
        w += 14.0 if ord(ch) > 127 else 8.0
    return max(float(NODE_MIN_W), min(float(NODE_MAX_W), w))


def _layout_nodes_row(
    nodes: list[str],
    *,
    start_y: float = 35.0,
    max_inner_w: float | None = None,
    wrap: bool = True,
) -> tuple[list[tuple[str, float, float, float, float]], float, float]:
    """按实际宽度顺序排布；必要时换行。返回 (placements, group_w, group_h)。"""
    if not nodes:
        return [], float(GROUP_PAD * 2), start_y + NODE_H + GROUP_PAD

    placements: list[tuple[str, float, float, float, float]] = []
    x = float(GROUP_PAD)
    y = float(start_y)
    row_start_x = x
    max_right = x
    row_bottom = y + NODE_H

    for name in nodes:
        nw = _text_width(name)
        if (
            wrap
            and max_inner_w is not None
            and x + nw > max_inner_w - GROUP_PAD
            and x > row_start_x
        ):
            y = row_bottom + ROW_GAP
            x = float(GROUP_PAD)
            row_start_x = x
            row_bottom = y + NODE_H

        placements.append((name, x, y, nw, float(NODE_H)))
        x += nw + NODE_GAP
        max_right = max(max_right, x - NODE_GAP)

    group_w = max_right + GROUP_PAD
    group_h = row_bottom + GROUP_PAD
    return placements, group_w, group_h


def _center_offset(container_w: float, content_w: float) -> float:
    return max(0.0, (container_w - content_w) / 2.0)


def _center_rows_in_group(
    placements: list[tuple[str, float, float, float, float]],
    group_w: float,
) -> list[tuple[str, float, float, float, float]]:
    if not placements:
        return placements
    rows: dict[float, list[tuple[str, float, float, float, float]]] = {}
    for p in placements:
        rows.setdefault(p[2], []).append(p)
    out: list[tuple[str, float, float, float, float]] = []
    for row_y in sorted(rows.keys()):
        items = rows[row_y]
        row_left = min(p[1] for p in items)
        row_right = max(p[1] + p[3] for p in items)
        row_w = row_right - row_left
        dx = (group_w - row_w) / 2.0 - row_left
        for name, nx, ny, nw, nh in items:
            out.append((name, nx + dx, ny, nw, nh))
    return out


def _detect_layout(groups: list[dict[str, Any]], components: list[Any]) -> str:
    if groups:
        explicit = str(groups[0].get("layout") or "")
        if explicit in LAYER_HEIGHT_MIN:
            return explicit
    explicit_layer = None
    for g in groups:
        if g.get("layout"):
            explicit_layer = str(g["layout"])
            break
    if explicit_layer in LAYER_HEIGHT_MIN:
        return explicit_layer

    if groups:
        n = len(groups)
        if n == 1:
            return "horizontal"
        if n == 2:
            counts = [len(_node_names(g.get("nodes") or g.get("components") or [])) for g in groups]
            if all(c >= 3 for c in counts):
                return "grid2x2"
            return "horizontal_groups"
        return "columns3"
    if components:
        return "horizontal"
    return "grid2x2"


def _estimate_layer_size(
    layout: str,
    groups: list[dict[str, Any]],
    components: list[Any],
    layer_w: float,
) -> tuple[float, float]:
    inner_w = layer_w - LAYER_PAD * 2

    if layout == "grid2x2":
        group_w = max(440.0, (inner_w - GROUP_GAP) / 2.0)
        max_gh = 160.0
        for group in groups[:2]:
            nodes = _node_names(group.get("nodes") or group.get("components") or [])
            cols = 2
            col_ws = [0.0, 0.0]
            for ni, name in enumerate(nodes[:8]):
                col_ws[ni % cols] = max(col_ws[ni % cols], _text_width(name))
            col_gap = 20.0
            usable = group_w - GROUP_PAD * 2 - col_gap
            cw0 = min(max(col_ws[0], usable / 2), usable - NODE_MIN_W)
            cw1 = usable - cw0
            rows = max(1, (len(nodes[:8]) + 1) // 2)
            gh = 35.0 + rows * (NODE_H + ROW_GAP) + GROUP_PAD
            max_gh = max(max_gh, gh)
        need_w = LAYER_PAD * 2 + group_w * 2 + GROUP_GAP
        return need_w, max(LAYER_HEIGHT_MIN["grid2x2"], max_gh + 55)

    if layout == "columns3":
        n = max(len(groups), 1)
        group_w = max(280.0, (inner_w - GROUP_GAP * (n - 1)) / n)
        max_gh = 165.0
        for group in groups[:6]:
            nodes = _node_names(group.get("nodes") or group.get("components") or [])
            nw = max((_text_width(x) for x in nodes), default=NODE_MIN_W)
            nw = min(nw, group_w - GROUP_PAD * 2)
            gh = 35.0 + len(nodes[:8]) * (NODE_H + ROW_GAP) + GROUP_PAD
            max_gh = max(max_gh, gh)
        need_w = LAYER_PAD * 2 + group_w * min(len(groups), 6) + GROUP_GAP * max(len(groups) - 1, 0)
        return need_w, max(LAYER_HEIGHT_MIN["columns3"], max_gh + 50)

    if layout == "horizontal_groups":
        total_w = LAYER_PAD
        max_gh = 90.0
        for group in groups:
            nodes = _node_names(group.get("nodes") or group.get("components") or [])
            _, gw, gh = _layout_nodes_row(nodes, start_y=35.0, max_inner_w=None, wrap=False)
            total_w += gw + GROUP_GAP
            max_gh = max(max_gh, gh)
        return total_w + LAYER_PAD, max(LAYER_HEIGHT_MIN["horizontal_groups"], max_gh + 50)

    # horizontal — 单组横排，可换行
    if groups:
        nodes = _node_names(groups[0].get("nodes") or groups[0].get("components") or [])
    else:
        nodes = _node_names(components)
    _, gw, gh = _layout_nodes_row(
        nodes,
        start_y=35.0,
        max_inner_w=inner_w - GROUP_PAD,
        wrap=True,
    )
    return LAYER_PAD * 2 + gw, max(LAYER_HEIGHT_MIN["horizontal"], gh + 50)


def _place_grid2x2(
    root: ET.Element,
    layer_id: str,
    groups: list[dict[str, Any]],
    layer_w: float,
    nid,
) -> None:
    inner_w = layer_w - LAYER_PAD * 2
    group_w = max(440.0, (inner_w - GROUP_GAP) / 2.0)
    content_w = group_w * min(len(groups[:2]), 2) + GROUP_GAP * max(min(len(groups[:2]), 2) - 1, 0)
    block_x = LAYER_PAD + _center_offset(inner_w, content_w)

    for gi, group in enumerate(groups[:2]):
        gx = block_x + gi * (group_w + GROUP_GAP)
        nodes = _node_names(group.get("nodes") or group.get("components") or [])
        col_gap = 20.0
        usable = group_w - GROUP_PAD * 2 - col_gap
        col_ws = [0.0, 0.0]
        for ni, name in enumerate(nodes[:8]):
            col_ws[ni % 2] = max(col_ws[ni % 2], _text_width(name))
        cw0 = min(max(col_ws[0], usable / 2), max(usable - NODE_MIN_W, NODE_MIN_W))
        cw1 = max(usable - cw0, NODE_MIN_W)
        cols = [(GROUP_PAD, cw0), (GROUP_PAD + cw0 + col_gap, cw1)]
        grid_left = cols[0][0]
        grid_right = cols[1][0] + cols[1][1]
        dx = (group_w - (grid_right - grid_left)) / 2.0 - grid_left
        cols = [(cols[0][0] + dx, cols[0][1]), (cols[1][0] + dx, cols[1][1])]

        gid = nid()
        rows = max(1, (len(nodes[:8]) + 1) // 2)
        gh = 35.0 + rows * (NODE_H + ROW_GAP) + GROUP_PAD
        _cell(
            root, gid, vertex=True, parent=layer_id,
            style=STYLE_GROUP, value=_esc(group.get("name", "")),
            x=gx, y=55, w=group_w, h=gh,
        )
        for ni, name in enumerate(nodes[:8]):
            col, row = ni % 2, ni // 2
            cx, cw = cols[col]
            cy = 35.0 + row * (NODE_H + ROW_GAP)
            _cell(
                root, nid(), vertex=True, parent=gid,
                style=STYLE_NODE, value=_esc(name),
                x=cx, y=cy, w=cw, h=NODE_H,
            )


def _place_columns3(
    root: ET.Element,
    layer_id: str,
    groups: list[dict[str, Any]],
    layer_w: float,
    nid,
) -> None:
    inner_w = layer_w - LAYER_PAD * 2
    n = max(len(groups[:6]), 1)
    group_w = max(280.0, (inner_w - GROUP_GAP * (n - 1)) / n)
    content_w = group_w * n + GROUP_GAP * max(n - 1, 0)
    block_x = LAYER_PAD + _center_offset(inner_w, content_w)

    for gi, group in enumerate(groups[:6]):
        gx = block_x + gi * (group_w + GROUP_GAP)
        nodes = _node_names(group.get("nodes") or group.get("components") or [])
        gh = 35.0 + len(nodes[:8]) * (NODE_H + ROW_GAP) + GROUP_PAD

        gid = nid()
        _cell(
            root, gid, vertex=True, parent=layer_id,
            style=STYLE_GROUP_SM, value=_esc(group.get("name", "")),
            x=gx, y=50, w=group_w, h=gh,
        )
        for ni, name in enumerate(nodes[:8]):
            nw = min(_text_width(name), group_w - GROUP_PAD * 2)
            nx = (group_w - nw) / 2.0
            _cell(
                root, nid(), vertex=True, parent=gid,
                style=STYLE_NODE, value=_esc(name),
                x=nx, y=35.0 + ni * (NODE_H + ROW_GAP),
                w=nw, h=NODE_H,
            )


def _place_horizontal(
    root: ET.Element,
    layer_id: str,
    groups: list[dict[str, Any]],
    components: list[Any],
    layer_w: float,
    nid,
) -> None:
    if groups:
        group = groups[0]
        gname = group.get("name", "")
        nodes = _node_names(group.get("nodes") or group.get("components") or [])
    else:
        gname = ""
        nodes = _node_names(components)

    inner_w = layer_w - LAYER_PAD * 2
    placements, gw, gh = _layout_nodes_row(
        nodes,
        start_y=35.0,
        max_inner_w=inner_w - GROUP_PAD,
        wrap=True,
    )
    centered = _center_rows_in_group(placements, gw)
    gx = LAYER_PAD + _center_offset(inner_w, gw)
    gid = nid()
    _cell(
        root, gid, vertex=True, parent=layer_id,
        style=STYLE_GROUP, value=_esc(gname),
        x=gx, y=50, w=gw, h=gh,
    )
    for name, nx, ny, nw, nh in centered:
        _cell(
            root, nid(), vertex=True, parent=gid,
            style=STYLE_NODE, value=_esc(name),
            x=nx, y=ny, w=nw, h=nh,
        )


def _place_horizontal_groups(
    root: ET.Element,
    layer_id: str,
    groups: list[dict[str, Any]],
    layer_w: float,
    nid,
) -> None:
    inner_w = layer_w - LAYER_PAD * 2
    group_sizes: list[tuple[list, float, float]] = []
    for group in groups:
        nodes = _node_names(group.get("nodes") or group.get("components") or [])
        placements, gw, gh = _layout_nodes_row(nodes, start_y=35.0, wrap=False)
        group_sizes.append((placements, gw, gh))

    content_w = sum(gw for _, gw, _ in group_sizes) + GROUP_GAP * max(len(group_sizes) - 1, 0)
    x = LAYER_PAD + _center_offset(inner_w, content_w)

    for group, (placements, gw, gh) in zip(groups, group_sizes):
        centered = _center_rows_in_group(placements, gw)
        gid = nid()
        _cell(
            root, gid, vertex=True, parent=layer_id,
            style=STYLE_GROUP, value=_esc(group.get("name", "")),
            x=x, y=50, w=gw, h=gh,
        )
        for name, nx, ny, nw, nh in centered:
            _cell(
                root, nid(), vertex=True, parent=gid,
                style=STYLE_NODE, value=_esc(name),
                x=nx, y=ny, w=nw, h=nh,
            )
        x += gw + GROUP_GAP


def build_mxgraph(cfg: dict[str, Any]) -> tuple[ET.Element, int, int]:
    title = str(cfg.get("title") or "系统架构图")
    layers = list(cfg.get("layers") or [])
    if not layers:
        raise ValueError("layers 不能为空")

    layer_plans: list[dict[str, Any]] = []
    for layer in layers:
        groups = list(layer.get("groups") or layer.get("subgraphs") or [])
        components = list(layer.get("components") or layer.get("nodes") or [])
        layout = str(layer.get("layout") or _detect_layout(groups, components))
        if layout not in LAYER_HEIGHT_MIN:
            layout = _detect_layout(groups, components)
        layer_plans.append({
            "layer": layer,
            "groups": groups,
            "components": components,
            "layout": layout,
        })

    layer_w = float(LAYER_W_MIN)
    for plan in layer_plans:
        need_w, _ = _estimate_layer_size(
            plan["layout"], plan["groups"], plan["components"], layer_w
        )
        layer_w = max(layer_w, need_w)

    for plan in layer_plans:
        _, need_h = _estimate_layer_size(
            plan["layout"], plan["groups"], plan["components"], layer_w
        )
        plan["height"] = need_h
        plan["width"] = layer_w

    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    prefix = uuid.uuid4().hex[:16] + "-"
    counter = [0]

    def nid() -> str:
        counter[0] += 1
        return f"{prefix}{counter[0]}"

    title_x = MARGIN_X + (layer_w - TITLE_W) / 2.0
    _cell(
        root, nid(), vertex=True, style=STYLE_TITLE, value=_esc(title),
        x=title_x, y=TITLE_Y, w=TITLE_W, h=TITLE_H,
    )

    layer_meta: list[tuple[str, float, float]] = []
    y = float(FIRST_LAYER_Y)

    for plan in layer_plans:
        layout = plan["layout"]
        layer_h = float(plan["height"])
        lid = nid()
        _cell(
            root, lid, vertex=True, style=STYLE_LAYER,
            value=_esc(plan["layer"].get("name", "")),
            x=MARGIN_X, y=y, w=layer_w, h=layer_h,
        )

        if layout == "grid2x2":
            _place_grid2x2(root, lid, plan["groups"], layer_w, nid)
        elif layout == "columns3":
            _place_columns3(root, lid, plan["groups"], layer_w, nid)
        elif layout == "horizontal_groups":
            _place_horizontal_groups(root, lid, plan["groups"], layer_w, nid)
        else:
            _place_horizontal(root, lid, plan["groups"], plan["components"], layer_w, nid)

        layer_meta.append((lid, y, layer_h))
        y += layer_h + LAYER_V_GAP

    links = list(cfg.get("links") or cfg.get("connections") or [])
    for i in range(len(layer_meta) - 1):
        src_id, src_y, src_h = layer_meta[i]
        tgt_id, tgt_y, _ = layer_meta[i + 1]
        _cell(root, nid(), edge=True, source=src_id, target=tgt_id, style=STYLE_EDGE)
        label = ""
        if i < len(links):
            link = links[i]
            if isinstance(link, str):
                label = link
            elif isinstance(link, dict):
                label = str(link.get("label") or link.get("name") or "")
        if label:
            mid_y = (src_y + src_h + tgt_y) / 2.0
            _cell(
                root, nid(), vertex=True, style=STYLE_EDGE_LABEL, value=_esc(label),
                x=MARGIN_X + layer_w / 2.0 + 10, y=mid_y - 10, w=100, h=20,
            )

    page_w = int(max(PAGE_W_MIN, MARGIN_X * 2 + layer_w))
    page_h = int(max(827, y + 20))
    return root, page_w, page_h


def build_document(cfg: dict[str, Any]) -> ET.ElementTree:
    root_el = ET.Element("mxfile", {"host": "app.diagrams.net"})
    diag = ET.SubElement(root_el, "diagram", {"name": "系统架构图", "id": _new_id()})
    graph_root, page_w, page_h = build_mxgraph(cfg)
    gm = ET.SubElement(
        diag,
        "mxGraphModel",
        {
            "dx": "1200", "dy": "800",
            "grid": "1", "gridSize": "10",
            "guides": "1", "tooltips": "1",
            "connect": "1", "arrows": "1",
            "fold": "0", "page": "1", "pageScale": "1",
            "pageWidth": str(page_w), "pageHeight": str(page_h),
            "math": "0", "shadow": "0",
        },
    )
    gm.append(graph_root)
    tree = ET.ElementTree(root_el)
    try:
        ET.indent(tree.getroot(), space="  ")
    except AttributeError:
        pass
    return tree


def main() -> int:
    ap = argparse.ArgumentParser(description="从 JSON 生成架构图 draw.io XML")
    ap.add_argument("input", nargs="?", help="JSON 文件路径，或 - 从 stdin")
    ap.add_argument("-o", "--output", type=Path, help="输出 .xml 路径")
    args = ap.parse_args()

    if args.input in (None, "-"):
        data = sys.stdin.read()
    else:
        data = Path(args.input).read_text(encoding="utf-8-sig")

    try:
        cfg = json.loads(data)
        tree = build_document(cfg)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    buf = io.StringIO()
    tree.write(buf, encoding="unicode", xml_declaration=True)
    text = buf.getvalue()

    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
        print(f"已写入: {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
