#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 JSON 生成序列图（draw.io mxfile）。
版式与样式对齐 PlantUML 参考（序列图/序列图.txt）。

- 参与者：矩形框，顶部对齐
- 生命线：虚线垂直线
- 消息：水平箭头
- 返回消息：虚线箭头
- 自消息：环形折线
- 泳道（box 分区）：swimlane 容器

用法:
  python sequence.py sequence.json -o 序列图.xml
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

FONT_MSG = 14
FONT_PART = 14

STYLE_PARTICIPANT = (
    "rounded=0;whiteSpace=wrap;html=1;"
    "fillColor=#dae8fc;strokeColor=#6c8ebf;"
    "fontStyle=0;fontSize=14;"
)
STYLE_LIFELINE = (
    "line;strokeWidth=1;dashed=1;fillColor=none;"
    "align=left;verticalAlign=middle;spacingTop=-1;"
    "spacingLeft=3;spacingRight=10;rotatable=0;"
    "labelPosition=left;points=[];portConstraint=eastwest;"
    "strokeColor=#6c8ebf;"
)
STYLE_MSG = "endArrow=open;endFill=0;html=1;rounded=0;"
STYLE_MSG_RETURN = "endArrow=open;endFill=0;dashed=1;html=1;rounded=0;"
STYLE_MSG_SELF = (
    "endArrow=open;endFill=0;html=1;rounded=0;"
    "edgeStyle=orthogonalEdgeStyle;"
)
STYLE_MSG_LABEL = (
    "edgeLabel;html=1;align=center;verticalAlign=middle;"
    "resizable=0;points=[];fontSize=13;"
)
STYLE_SWIMLANE = (
    "swimlane;startSize=30;"
    "fillColor=#e1d5e7;strokeColor=#9673a6;"
)

PART_W = 120
PART_H = 50
COL_GAP = 160
MSG_GAP = 60
MARGIN = 60
TOP_Y = 70


def _font(text: str, size: int = FONT_MSG) -> str:
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


def _edge_simple(
    root: ET.Element,
    eid: str,
    source: str,
    target: str,
    style: str,
) -> None:
    att: dict[str, str] = {
        "id": eid, "edge": "1", "parent": "1",
        "source": source, "target": target,
        "style": style, "value": "",
    }
    c = ET.SubElement(root, "mxCell", att)
    g = ET.SubElement(c, "mxGeometry", {"relative": "1"})
    g.set("as", "geometry")


def build_mxgraph(cfg: dict[str, Any]) -> tuple[ET.Element, int, int]:
    title = cfg.get("title", "序列图")
    participants_raw = list(cfg.get("participants") or [])
    messages = list(cfg.get("messages") or [])
    boxes = cfg.get("boxes")  # optional swimlane grouping

    if not participants_raw:
        raise ValueError("participants 不能为空")

    n_parts = len(participants_raw)
    total_w = n_parts * COL_GAP + MARGIN * 2

    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    prefix = uuid.uuid4().hex[:16] + "-"
    ci = [0]

    def nid() -> str:
        ci[0] += 1
        return f"{prefix}{ci[0]}"

    # participant positions (center x)
    part_ids: dict[str, str] = {}
    part_cx: dict[str, float] = {}

    # swimlane boxes
    if boxes:
        for box in boxes:
            bid = nid()
            box_start = box.get("start", 0)
            box_end = box.get("end", n_parts - 1)
            bx = MARGIN + box_start * COL_GAP - 10
            bw = (box_end - box_start + 1) * COL_GAP + 20
            bh = TOP_Y + len(messages) * MSG_GAP + PART_H + 40
            _cell(
                root, bid, vertex=True,
                style=STYLE_SWIMLANE,
                value=_font(box.get("name", ""), 14),
                x=bx, y=MARGIN, w=bw, h=bh,
            )

    # participants
    for i, p in enumerate(participants_raw):
        pid = nid()
        pname = p.get("name", "")
        part_ids[p.get("id", pname)] = pid
        px = MARGIN + i * COL_GAP + COL_GAP / 2 - PART_W / 2
        cx = px + PART_W / 2
        part_cx[p.get("id", pname)] = cx

        _cell(
            root, pid, vertex=True,
            style=STYLE_PARTICIPANT,
            value=_font(pname, FONT_PART),
            x=px, y=TOP_Y, w=PART_W, h=PART_H,
        )

        # lifeline
        lid = nid()
        lifeline_h = PART_H + 20 + len(messages) * MSG_GAP
        _cell(
            root, lid, vertex=True,
            style=STYLE_LIFELINE,
            value="",
            x=cx - 1, y=TOP_Y + PART_H, w=2, h=lifeline_h,
        )

    # messages
    for mi, msg in enumerate(messages):
        my = TOP_Y + PART_H + 30 + mi * MSG_GAP
        from_id = msg.get("from", "")
        to_id = msg.get("to", "")
        label = msg.get("label", "")
        msg_type = msg.get("type", "sync")

        src_pid = part_ids.get(from_id)
        tgt_pid = part_ids.get(to_id)
        if not src_pid or not tgt_pid:
            continue

        sx = part_cx.get(from_id, 400)
        tx = part_cx.get(to_id, 600)

        if from_id == to_id:
            # self-message
            eid = nid()
            loop_w = 40
            _edge_simple(root, eid, src_pid, tgt_pid, STYLE_MSG_SELF)
            # label
            if label:
                lid = nid()
                _cell(
                    root, lid, vertex=True, parent=eid,
                    style=STYLE_MSG_LABEL,
                    value=_font(label, FONT_MSG),
                    x=sx + loop_w + 5, y=my - 10, w=120, h=20,
                )
        else:
            style = STYLE_MSG_RETURN if msg_type == "return" else STYLE_MSG
            eid = nid()
            _edge_simple(root, eid, src_pid, tgt_pid, style)
            # label
            if label:
                lid = nid()
                mx = (sx + tx) / 2
                _cell(
                    root, lid, vertex=True, parent=eid,
                    style=STYLE_MSG_LABEL,
                    value=_font(label, FONT_MSG),
                    x=mx - 60, y=my - 16, w=120, h=20,
                )

    page_h = TOP_Y + PART_H + 30 + len(messages) * MSG_GAP + 60
    page_w = total_w

    return root, max(page_w, 600), page_h


def build_document(cfg: dict[str, Any]) -> ET.ElementTree:
    root_el = ET.Element("mxfile", {"host": "app.diagrams.net"})
    diag = ET.SubElement(root_el, "diagram", {
        "name": "Page-1",
        "id": _new_id(),
    })
    graph_root, page_w, page_h = build_mxgraph(cfg)
    gm = ET.SubElement(diag, "mxGraphModel", {
        "dx": "1414", "dy": "777",
        "grid": "0", "gridSize": "10",
        "guides": "0", "tooltips": "1",
        "connect": "0", "arrows": "0",
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
    ap = argparse.ArgumentParser(description="从 JSON 生成序列图 draw.io XML")
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
