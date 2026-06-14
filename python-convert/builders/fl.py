#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 JSON 生成流程图（draw.io mxfile），**形状与样式对齐仓库内 流程图.xml**：

- 开始 / 结束：`shape=mxgraph.flowchart.terminator`
- 输入 / 输出：平行四边形 `shape=parallelogram;perimeter=parallelogramPerimeter;...`
- 处理：长方形 `whiteSpace=wrap;html=1;strokeWidth=2;`
- 判断：菱形 `rhombus;...`
- 连线：`edgeStyle=orthogonalEdgeStyle;...`
- **判断**：**「是」一律顺延到 `id+1`（主列、普通连线）**；JSON 里写「是」可省略或与 `id+1` 一致。**「否」不顺延**，走**外侧折线**；前向「否」（目标 `> id+1`）及其顺延链排在**右侧列**；回指上方的「否」只走外线、节点仍在主列
- `结束` 不再自动连下一 id，避免误连到异常支路

JSON 结构见 flowchart_login.example.json、flowchart_long.example.json。

用法:
  python json_to_flowchart.py flowchart_login.example.json -o 流程图.xml
  python json_to_flowchart.py - < data.json
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

FONT_MAIN = 14
FONT_EDGE = 14

STYLE_TERMINATOR = "strokeWidth=2;html=1;shape=mxgraph.flowchart.terminator;whiteSpace=wrap;"
STYLE_PARALLELOGRAM = (
    "shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;"
    "fixedSize=1;strokeWidth=2;"
)
STYLE_RECT = "whiteSpace=wrap;html=1;strokeWidth=2;"
STYLE_RHOMBUS = "rhombus;whiteSpace=wrap;html=1;strokeWidth=2;"
EDGE_STYLE_BASE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"
)

DEFAULT_PAGE_W = 2000
DEFAULT_PAGE_H = 1700
STEP_Y = 100
RHOMBUS_DOWN_GAP = 20
START_Y = 320
CENTER_X = 1000


def _font_value(text: str, px: int = FONT_MAIN) -> str:
    return f'<font style="font-size: {px}px;">{html.escape(text)}</font>'


def _shape_size(kind: str) -> tuple[float, float]:
    if kind == "terminator":
        return 100.0, 60.0
    if kind == "parallelogram":
        return 150.0, 60.0
    if kind == "rhombus":
        return 190.0, 80.0
    return 120.0, 60.0


def _map_step_type(t: str) -> str:
    t = str(t).strip()
    if t in ("开始", "结束"):
        return "terminator"
    if t in ("输入", "输出"):
        return "parallelogram"
    if t in ("处理",):
        return "rect"
    if t in ("判断",):
        return "rhombus"
    raise ValueError(f"未知步骤类型: {t}（支持：开始、结束、输入、输出、处理、判断）")


def _style_for_kind(kind: str) -> str:
    return {
        "terminator": STYLE_TERMINATOR,
        "parallelogram": STYLE_PARALLELOGRAM,
        "rect": STYLE_RECT,
        "rhombus": STYLE_RHOMBUS,
    }[kind]


def _infer_edges(steps: list[dict[str, Any]]) -> list[tuple[int, int, str | None]]:
    by_id = {int(s["id"]): s for s in steps}
    ids = sorted(by_id.keys())
    edges: list[tuple[int, int, str | None]] = []
    for sid in ids:
        s = by_id[sid]
        typ = str(s.get("type", "")).strip()
        if typ == "判断":
            br = s.get("branches") or {}
            # 「是」固定顺延到下一 id（与 JSON 中「是」可重复，以顺延为准）
            if sid + 1 in by_id:
                edges.append((sid, sid + 1, "是"))
            for lab, tid in br.items():
                lab_s = str(lab).strip()
                if lab_s == "是":
                    continue
                edges.append((sid, int(tid), lab_s or None))
            continue
        # 「结束」不再有向下的顺序连线，避免与跳级分支（如 否→15）冲突
        if typ == "结束":
            continue
        if sid + 1 in by_id:
            edges.append((sid, sid + 1, None))
    return edges


def _no_branch_forward_seeds(steps: list[dict[str, Any]]) -> set[int]:
    """
    前向「否」分支目标（目标 id > 菱形 id+1，即不占顺延位），用于右侧列种子。
    「否→2」等回指不满足，不排侧栏。
    """
    out: set[int] = set()
    for s in steps:
        if str(s.get("type", "")).strip() != "判断":
            continue
        sid = int(s["id"])
        for lab, tid in (s.get("branches") or {}).items():
            if str(lab).strip() != "否":
                continue
            t = int(tid)
            if t > sid + 1:
                out.add(t)
    return out


def _right_column_ids(
    steps: list[dict[str, Any]],
    edges: list[tuple[int, int, str | None]],
) -> set[int]:
    """
    前向「否」目标及其沿 id+1 顺延的支路（如 15→16），排到右侧列。
    """
    by_id = {int(s["id"]): s for s in steps}
    seeds = _no_branch_forward_seeds(steps)
    if not seeds:
        return set()
    edge_set = {(a, b) for a, b, _ in edges}
    right: set[int] = set()
    for t0 in seeds:
        k = t0
        while k in by_id:
            right.add(k)
            if (k, k + 1) in edge_set and k + 1 in by_id:
                k += 1
            else:
                break
    return right


def _layout(
    steps: list[dict[str, Any]],
    edges: list[tuple[int, int, str | None]],
) -> dict[int, tuple[float, float, float, float, str]]:
    """主列居中纵向排布；前向「否」支路整段排到右侧列。"""
    by_id = {int(s["id"]): s for s in steps}
    ids = sorted(by_id.keys())
    right_ids = _right_column_ids(steps, edges)
    main_ids = [i for i in ids if i not in right_ids]

    out: dict[int, tuple[float, float, float, float, str]] = {}
    y = float(START_Y)
    for sid in main_ids:
        s = by_id[sid]
        kind = _map_step_type(s["type"])
        w, h = _shape_size(kind)
        x = CENTER_X - w / 2.0
        out[sid] = (x, y, w, h, kind)
        y += STEP_Y
        if kind == "rhombus":
            y += RHOMBUS_DOWN_GAP

    if not right_ids:
        return out

    RIGHT_X_OFF = 250.0
    # 右侧列：锚在「指向它的判断」中最靠下的菱形之下，再纵向堆叠
    incoming_from_main: dict[int, list[int]] = {}
    for a, b, _ in edges:
        if b in right_ids and a not in right_ids:
            incoming_from_main.setdefault(b, []).append(a)

    order_r = sorted(right_ids)
    anchor_parents: list[int] = []
    for r in order_r:
        anchor_parents.extend(incoming_from_main.get(r, []))
    if anchor_parents:
        ap = max(anchor_parents, key=lambda p: out[p][1] + out[p][3])
        ay = out[ap][1] + out[ap][3] + 50.0
    else:
        ay = float(START_Y)

    for j, rid in enumerate(order_r):
        s = by_id[rid]
        kind = _map_step_type(s["type"])
        w, h = _shape_size(kind)
        x = CENTER_X + RIGHT_X_OFF - w / 2.0
        y = ay + j * STEP_Y
        out[rid] = (x, y, w, h, kind)

    return out


def _rhombus_outward_lane_waypoints(
    fr: tuple[float, float, float, float, str],
    to: tuple[float, float, float, float, str],
    *,
    lane_gap: float = 80.0,
) -> list[tuple[float, float]]:
    """
    菱形右侧先水平外扩再竖直走向目标（与回边同一套折点逻辑）：
    用于「否」等外侧分支；「是」顺延不用此折线。
    """
    x1, y1, w1, h1, _ = fr
    x2, y2, w2, h2, _t = to
    sx = x1 + w1
    sy = y1 + h1 / 2.0
    lane = max(sx, x2 + w2) + lane_gap
    ty = y2 + h2 / 2.0
    return [(lane, sy), (lane, ty)]


def _rhombus_outward_edge_style() -> str:
    return (
        EDGE_STYLE_BASE
        + "exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
        + "entryX=1;entryY=0.5;entryDx=0;entryDy=0;"
    )


# 兼容旧名
_loopback_waypoints = _rhombus_outward_lane_waypoints


def _add_vertex(
    root: ET.Element,
    cell_id: str,
    style: str,
    value: str,
    geom: tuple[float, float, float, float],
) -> None:
    x, y, w, h = geom
    c = ET.SubElement(
        root,
        "mxCell",
        {
            "id": cell_id,
            "parent": "1",
            "style": style,
            "value": value,
            "vertex": "1",
        },
    )
    g = ET.SubElement(
        c,
        "mxGeometry",
        {
            "height": str(int(round(h))),
            "width": str(int(round(w))),
            "x": str(int(round(x))),
            "y": str(int(round(y))),
            "as": "geometry",
        },
    )


def _add_edge(
    root: ET.Element,
    eid: str,
    source: str,
    target: str,
    style: str,
    value: str,
    *,
    points: list[tuple[float, float]] | None = None,
) -> None:
    att: dict[str, str] = {
        "id": eid,
        "edge": "1",
        "parent": "1",
        "source": source,
        "target": target,
        "style": style,
        "value": value,
    }
    c = ET.SubElement(root, "mxCell", att)
    g = ET.SubElement(
        c,
        "mxGeometry",
        {"relative": "1", "as": "geometry"},
    )
    if points:
        arr = ET.SubElement(g, "Array", {"as": "points"})
        for px, py in points:
            ET.SubElement(arr, "mxPoint", {"x": str(int(round(px))), "y": str(int(round(py)))})


def build_mxgraph(cfg: dict[str, Any]) -> tuple[ET.Element, int, int]:
    steps = list(cfg.get("steps") or [])
    if not steps:
        raise ValueError("steps 不能为空")
    for i, s in enumerate(steps):
        if "id" not in s or "type" not in s or "text" not in s:
            raise ValueError(f"steps[{i}] 须含 id、type、text")

    edges = _infer_edges(steps)
    layout = _layout(steps, edges)
    id_to_cell: dict[int, str] = {}
    prefix = uuid.uuid4().hex[:16] + "-"
    id_ctr = itertools.count(200)

    def nid() -> str:
        return f"{prefix}{next(id_ctr)}"

    for sid in sorted(layout.keys()):
        id_to_cell[sid] = nid()

    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    for sid in sorted(layout.keys()):
        s = next(x for x in steps if int(x["id"]) == sid)
        kind = _map_step_type(s["type"])
        x, y, w, h, _ = layout[sid]
        _add_vertex(
            root,
            id_to_cell[sid],
            _style_for_kind(kind),
            _font_value(str(s["text"]).strip()),
            (x, y, w, h),
        )

    for a, b, elabel in edges:
        fr = layout[a]
        to = layout[b]
        ev = _font_value(elabel, FONT_EDGE) if elabel else ""
        eid = nid()
        _y1 = fr[1] + fr[3] / 2.0
        _y2 = to[1] + to[3] / 2.0
        pts = None
        st = EDGE_STYLE_BASE
        if elabel:
            st += "fontSize=14;"
        kind_fr = fr[4]
        # 回边 / 自下往上：右侧外扩
        if b < a or _y2 < _y1 - 8.0:
            pts = _loopback_waypoints(fr, to)
            st = _rhombus_outward_edge_style()
            if elabel:
                st += "fontSize=14;"
        # 菱形出发且非「是」顺延：否等一律走外侧（含前向否到侧栏）
        elif kind_fr == "rhombus" and elabel != "是":
            pts = _rhombus_outward_lane_waypoints(
                fr, to, lane_gap=100.0 if (b > a + 1) else 80.0
            )
            st = _rhombus_outward_edge_style()
            if elabel:
                st += "fontSize=14;"
        # 「是」顺延：主列普通垂直连线，不外扩
        _add_edge(root, eid, id_to_cell[a], id_to_cell[b], st, ev, points=pts)

    pw = int(cfg.get("pageWidth") or DEFAULT_PAGE_W)
    ph = int(cfg.get("pageHeight") or DEFAULT_PAGE_H)
    return root, pw, ph


def build_document(cfg: dict[str, Any]) -> ET.ElementTree:
    root_el = ET.Element("mxfile", {"host": "app.diagrams.net"})
    diag = ET.SubElement(
        root_el,
        "diagram",
        {"name": "Page-1", "id": f"id-{uuid.uuid4().hex[:16]}"},
    )
    graph_root, page_w, page_h = build_mxgraph(cfg)
    gm = ET.SubElement(
        diag,
        "mxGraphModel",
        {
            "dx": str(cfg.get("dx") or "1037"),
            "dy": str(cfg.get("dy") or "863"),
            "grid": str(cfg.get("grid", "0")),
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "0",
            "pageScale": "1",
            "pageWidth": str(page_w),
            "pageHeight": str(page_h),
            "math": str(cfg.get("math", "1")),
            "shadow": "0",
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
    ap = argparse.ArgumentParser(description="从 JSON 生成流程图 draw.io XML（对齐 流程图.xml）")
    ap.add_argument("input", nargs="?", help="JSON 路径，或 - 表示 stdin")
    ap.add_argument("-o", "--output", type=Path, help="输出 .xml")
    args = ap.parse_args()

    if args.input in (None, "-"):
        raw = sys.stdin.read()
    else:
        raw = Path(args.input).read_text(encoding="utf-8-sig")

    try:
        cfg = json.loads(raw)
        tree = build_document(cfg)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    buf = io.StringIO()
    tree.write(buf, encoding="unicode", xml_declaration=False)
    text = buf.getvalue()
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
        print(f"已写入: {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
