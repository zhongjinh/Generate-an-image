#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 JSON 生成活动图（draw.io mxfile）。
版式与样式对齐 .pos 模板参考（活动图/pos_from_template.py）。

- 开始 / 结束：实心椭圆
- 动作：圆角矩形
- 判断：菱形
- 泳道：swimlane 容器
- 连线：orthogonalEdgeStyle

用法:
  python activity.py activity.json -o 活动图.xml
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

FONT_MAIN = 14

STYLE_START = (
    "ellipse;whiteSpace=wrap;html=1;aspect=fixed;"
    "fillColor=#000000;strokeColor=#000000;"
)
STYLE_END = (
    "ellipse;whiteSpace=wrap;html=1;aspect=fixed;"
    "fillColor=#000000;strokeColor=#000000;"
)
STYLE_ACTION = (
    "rounded=1;whiteSpace=wrap;html=1;arcSize=20;"
    "fillColor=#d5e8d4;strokeColor=#82b366;"
)
STYLE_DECISION = (
    "rhombus;whiteSpace=wrap;html=1;"
    "fillColor=#fff2cc;strokeColor=#d6b656;"
)
STYLE_SWIMLANE = (
    "swimlane;startSize=30;"
    "fillColor=#e1d5e7;strokeColor=#9673a6;"
)
STYLE_EDGE = (
    "endArrow=block;endFill=1;html=1;rounded=0;"
    "edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto;"
)
STYLE_EDGE_DASHED = (
    "endArrow=block;endFill=1;dashed=1;html=1;rounded=0;"
    "edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto;"
)
STYLE_EDGE_LABEL = (
    "edgeLabel;html=1;align=center;verticalAlign=middle;"
    "resizable=0;points=[];fontSize=13;"
)

NODE_W = 180
NODE_H = 50
STEP_Y = 110
MARGIN = 60
SWIMLANE_PAD = 20


def _font(text: str, size: int = FONT_MAIN) -> str:
    return f'<font style="font-size: {size}px;">{html.escape(text)}</font>'


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
    if not edge and (w or h):
        g = ET.SubElement(c, "mxGeometry", {
            "x": str(int(x)), "y": str(int(y)),
            "width": str(int(w)), "height": str(int(h)),
        })
        g.set("as", "geometry")
    elif edge:
        g = ET.SubElement(c, "mxGeometry", {"relative": "1"})
        g.set("as", "geometry")
    return c


def _edge_with_points(
    root: ET.Element,
    eid: str,
    source: str,
    target: str,
    style: str,
    points: list[tuple[float, float]] | None = None,
) -> None:
    att: dict[str, str] = {
        "id": eid, "edge": "1", "parent": "1",
        "source": source, "target": target,
        "style": style, "value": "",
    }
    c = ET.SubElement(root, "mxCell", att)
    g = ET.SubElement(c, "mxGeometry", {"relative": "1"})
    g.set("as", "geometry")
    if points:
        arr = ET.SubElement(g, "Array", {"as": "points"})
        for px, py in points:
            ET.SubElement(arr, "mxPoint", {"x": str(int(px)), "y": str(int(py))})


def _node_style(ntype: str) -> str:
    if ntype == "start":
        return STYLE_START
    if ntype == "end":
        return STYLE_END
    if ntype == "decision":
        return STYLE_DECISION
    if ntype == "swimlane":
        return STYLE_SWIMLANE
    return STYLE_ACTION


def _layout_nodes(
    nodes: list[dict[str, Any]],
    lanes: list[dict[str, Any]] | None,
) -> dict[str, tuple[float, float, float, float]]:
    """计算节点位置。支持泳道分组。"""
    pos: dict[str, tuple[float, float, float, float]] = {}

    if lanes:
        lane_w = max(NODE_W + 80, 260)
        total_w = len(lanes) * lane_w + MARGIN * 2
        node_y_idx: dict[str, int] = {}
        for i, n in enumerate(nodes):
            nid = n.get("id", n.get("name", str(i)))
            node_y_idx[nid] = i

        for li, lane in enumerate(lanes):
            lx = MARGIN + li * lane_w
            lane_nodes = lane.get("nodes", [])
            for ni, nid in enumerate(lane_nodes):
                idx = node_y_idx.get(nid, ni)
                nx = lx + (lane_w - NODE_W) / 2
                ny = MARGIN + 40 + idx * STEP_Y
                pos[nid] = (nx, ny, NODE_W, NODE_H)
    else:
        cx = 400
        for i, n in enumerate(nodes):
            nid = n.get("id", n.get("name", str(i)))
            ny = MARGIN + i * STEP_Y
            pos[nid] = (cx - NODE_W / 2, ny, NODE_W, NODE_H)

    return pos


def build_mxgraph(cfg: dict[str, Any]) -> tuple[ET.Element, int, int]:
    title = cfg.get("title", "活动图")
    nodes_raw = list(cfg.get("nodes") or [])
    flows = list(cfg.get("flows") or [])
    lanes = cfg.get("lanes")

    if not nodes_raw:
        raise ValueError("nodes 不能为空")

    pos = _layout_nodes(nodes_raw, lanes)

    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    prefix = uuid.uuid4().hex[:16] + "-"
    id_map: dict[str, str] = {}
    ci = [0]

    def nid() -> str:
        ci[0] += 1
        return f"{prefix}{ci[0]}"

    # swimlanes
    if lanes:
        lane_w = max(NODE_W + 80, 260)
        for li, lane in enumerate(lanes):
            lid = nid()
            lane["__cell_id"] = lid
            lx = MARGIN + li * lane_w
            _cell(
                root, lid, vertex=True,
                style=STYLE_SWIMLANE,
                value=_font(lane.get("name", ""), 14),
                x=lx, y=MARGIN,
                w=lane_w,
                h=len(nodes_raw) * STEP_Y + 40,
            )

    # nodes
    for i, n in enumerate(nodes_raw):
        name = n.get("name", "")
        nid_str = n.get("id", name)
        ntype = n.get("type", "action")
        cid = nid()
        id_map[nid_str] = cid
        x, y, w, h = pos.get(nid_str, (300, MARGIN + i * STEP_Y, NODE_W, NODE_H))
        _cell(
            root, cid, vertex=True,
            style=_node_style(ntype),
            value=_font(name),
            x=x, y=y, w=w, h=h,
        )

    # flows / edges
    for flow in flows:
        from_id = flow.get("from", "")
        to_id = flow.get("to", "")
        src = id_map.get(from_id)
        tgt = id_map.get(to_id)
        if not src or not tgt:
            continue
        label = flow.get("label", "")
        dashed = flow.get("dashed", False)
        style = STYLE_EDGE_DASHED if dashed else STYLE_EDGE
        eid = nid()

        if label:
            # edge + label
            _edge_with_points(root, eid, src, tgt, style)
            lid = nid()
            sx, sy, sw, sh = pos.get(from_id, (0, 0, NODE_W, NODE_H))
            tx, ty, tw, th = pos.get(to_id, (0, 0, NODE_W, NODE_H))
            mx = (sx + sw / 2 + tx + tw / 2) / 2
            my = (sy + sh + ty) / 2
            _cell(
                root, lid, vertex=True,
                parent=eid,
                style=STYLE_EDGE_LABEL,
                value=_font(label, 13),
                x=mx - 30, y=my - 10, w=60, h=20,
            )
        else:
            _edge_with_points(root, eid, src, tgt, style)

    # page size
    max_y = max((p[1] + p[3] for p in pos.values()), default=600)
    max_x = max((p[0] + p[2] for p in pos.values()), default=800)
    page_w = int(max(800, max_x + MARGIN * 2))
    page_h = int(max(600, max_y + MARGIN))

    return root, page_w, page_h


def build_document(cfg: dict[str, Any]) -> ET.ElementTree:
    root_el = ET.Element("mxfile", {"host": "app.diagrams.net"})
    diag = ET.SubElement(root_el, "diagram", {
        "name": "Page-1",
        "id": _new_id(),
    })
    graph_root, page_w, page_h = build_mxgraph(cfg)
    gm = ET.SubElement(diag, "mxGraphModel", {
        "dx": "1414", "dy": "777",
        "grid": "1", "gridSize": "10",
        "guides": "1", "tooltips": "1",
        "connect": "1", "arrows": "1",
        "fold": "1", "page": "0", "pageScale": "1",
        "pageWidth": str(page_w), "pageHeight": str(page_h),
        "math": "0", "shadow": "0",
    })
    gm.append(graph_root)
    tree = ET.ElementTree(root_el)
    try:
        ET.indent(tree.getroot(), space="  ")
    except AttributeError:
        pass
    return tree


def main() -> int:
    ap = argparse.ArgumentParser(description="从 JSON 生成活动图 draw.io XML")
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
