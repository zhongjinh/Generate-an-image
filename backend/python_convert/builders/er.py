#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 JSON 生成 E-R 图（draw.io mxfile），**版式与单元样式对齐仓库内 E-R图.xml**：

- 实体：`rounded=0;whiteSpace=wrap;html=1;` + `<font style="font-size: 17px;">` 主名称（可选 `attributes` 小字，模板可只用 `name`）
- 布局：默认 **中心实体 + 其余围一圈**（`center_entity` 可指定；否则优先名为「用户」的实体，再否则取关系最多的实体）
- 关系：菱形 `rhombus;whiteSpace=wrap;html=1;rounded=0;`
- 连线：`endArrow=none;html=1;rounded=0;`，`mxCell` 设 `source`/`target` 绑定实体、菱形、关系属性椭圆；首段实体侧可带 `exitX/exitY`，`mxGeometry` 保留 `mxPoint` 锚点
- 基数（如 1、N）：绝对坐标放在对应线段几何中点（`font-size: 17px`）
- 多行缩进；默认不写 XML 声明（与 E-R图.xml 一致）

用法:
  python json_to_er_diagram.py er_diagram.template.json -o E-R图.xml
  python json_to_er_diagram.py er_diagram.library.json -o E-R图.xml
  python json_to_er_diagram.py er_diagram.example.json -o E-R图.xml
  python json_to_er_diagram.py - < my.json

可选 JSON 键: `center_entity`；`pageWidth` / `pageHeight`；`ring_scale`（外圈半径系数，默认约 1.08）；
`relationship_lane_spacing`（同对实体多条关系时菱形错开像素，默认 48）；`page_margin`（画布留白，默认 240）；
`satellite_order`: `graph`（默认，按关系把外圈排近）或 `json`（严格按 entities 顺序）。
大示例见 er_diagram.library.json。

依赖: 标准库；建议 Python 3.9+（用于 ET.indent）。
"""

from __future__ import annotations

import argparse
import html
import io
import itertools
import json
import math
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# 与 E-R图.xml 中一致
ENTITY_STYLE = "rounded=0;whiteSpace=wrap;html=1;"
RHOMBUS_STYLE = "rhombus;whiteSpace=wrap;html=1;rounded=0;"
REL_ATTR_ELLIPSE_STYLE = "ellipse;whiteSpace=wrap;html=1;"
EDGE_PLAIN = "endArrow=none;html=1;rounded=0;"

DEFAULT_PAGE_W = 1703
DEFAULT_PAGE_H = 1169
FONT_SIZE = 17
GRID_H_SPACING = 400.0
GRID_V_SPACING = 250.0
GRID_ORIGIN_X = 100.0
GRID_ORIGIN_Y = 100.0
DIAMOND_GAP = 50.0


def _diagram_id() -> str:
    return f"id-{uuid.uuid4().hex[:16]}"


def _id_chain() -> tuple[str, itertools.count]:
    prefix = f"{uuid.uuid4().hex[:20]}-"
    return prefix, itertools.count(200)


def _font_label(text: str, px: int) -> str:
    return f'<font style="font-size: {px}px;">{html.escape(text)}</font>'


def _entity_value(name: str, attributes: list[str]) -> str:
    body = _font_label(name, FONT_SIZE)
    if attributes:
        lines = "<br/>".join(html.escape(a) for a in attributes)
        body += f'<br/><font style="font-size: 12px;">{lines}</font>'
    return body


def _parse_cardinality(
    card: Any,
    near_from: Any,
    near_to: Any,
) -> tuple[str, str]:
    if near_from is not None and str(near_from).strip():
        a = str(near_from).strip()
    else:
        a = ""
    if near_to is not None and str(near_to).strip():
        b = str(near_to).strip()
    else:
        b = ""
    if a and b:
        return a, b
    if card is None or not str(card).strip():
        return "1", "N"
    s = str(card).replace("：", ":")
    parts = [p.strip() for p in s.split(":") if p.strip()]
    if len(parts) >= 2:
        return parts[0][:8], parts[1][:8]
    return "1", "N"


def _rect_center(x: float, y: float, w: float, h: float) -> tuple[float, float]:
    return x + w / 2.0, y + h / 2.0


def _rect_border_toward(
    x: float, y: float, w: float, h: float, tcx: float, tcy: float
) -> tuple[float, float]:
    cx, cy = _rect_center(x, y, w, h)
    dx, dy = tcx - cx, tcy - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return cx, cy
    if abs(dx) >= abs(dy):
        px = x + w if dx > 0 else x
        py = cy
        return px, py
    px = cx
    py = y + h if dy > 0 else y
    return px, py


def _rhombus_border_toward(
    rx: float, ry: float, rw: float, rh: float, tcx: float, tcy: float
) -> tuple[float, float]:
    cx, cy = _rect_center(rx, ry, rw, rh)
    dx, dy = tcx - cx, tcy - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return cx, cy
    if abs(dx) >= abs(dy):
        return (rx + rw if dx > 0 else rx, cy)
    return (cx, ry + rh if dy > 0 else ry)


def _rhombus_corners(rx: float, ry: float, rw: float, rh: float) -> dict[int, tuple[float, float]]:
    """菱形角点编号：1=上，2=右，3=下，4=左。"""
    cx, cy = _rect_center(rx, ry, rw, rh)
    return {
        1: (cx, ry),
        2: (rx + rw, cy),
        3: (cx, ry + rh),
        4: (rx, cy),
    }


def _ellipse_border_toward(
    cx: float, cy: float, w: float, h: float, tx: float, ty: float
) -> tuple[float, float]:
    """椭圆上朝向目标点的边缘锚点。"""
    dx, dy = tx - cx, ty - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return cx, cy
    a = w / 2.0
    b = h / 2.0
    scale = math.sqrt((dx * dx) / (a * a) + (dy * dy) / (b * b))
    if scale < 1e-6:
        return cx, cy
    return cx + dx / scale, cy + dy / scale


def _l_elbow_point(from_pos: dict[str, float], to_pos: dict[str, float]) -> tuple[float, float]:
    """L 形折线肘点：先沿主轴走直线，再转向目标。"""
    from_cx, from_cy = from_pos["center_x"], from_pos["center_y"]
    to_cx, to_cy = to_pos["center_x"], to_pos["center_y"]
    dx, dy = to_cx - from_cx, to_cy - from_cy
    if abs(dx) >= abs(dy):
        return to_cx, from_cy
    return from_cx, to_cy


def _relationship_layout_kind(from_pos: dict[str, float], to_pos: dict[str, float]) -> str:
    dx = to_pos["center_x"] - from_pos["center_x"]
    dy = to_pos["center_y"] - from_pos["center_y"]
    if abs(dy) <= from_pos["height"] * 0.8:
        return "horizontal"
    if abs(dx) <= from_pos["width"] * 0.8:
        return "vertical"
    return "diagonal"


def _nearest_corner_idx(corners: dict[int, tuple[float, float]], px: float, py: float) -> int:
    return min(corners.keys(), key=lambda k: (corners[k][0] - px) ** 2 + (corners[k][1] - py) ** 2)


def _opp_corner_idx(i: int) -> int:
    return {1: 3, 2: 4, 3: 1, 4: 2}[i]


def _corner_toward_point(rx: float, ry: float, rw: float, rh: float, px: float, py: float) -> int:
    cx, cy = _rect_center(rx, ry, rw, rh)
    dx, dy = px - cx, py - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return 4
    if abs(dx) >= abs(dy):
        return 4 if dx < 0 else 2
    return 1 if dy < 0 else 3


def _adjacent_corners(i: int) -> list[int]:
    return {1: [2, 4], 2: [1, 3], 3: [2, 4], 4: [1, 3]}[i]


def _conn_pos(x: float, y: float, w: float, h: float) -> dict[str, float]:
    return {
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "center_x": x + w / 2.0,
        "center_y": y + h / 2.0,
        "top_y": y,
        "bottom_y": y + h,
    }


def _pick_connection_corners(
    rx: float,
    ry: float,
    rw: float,
    rh: float,
    from_pos: dict[str, float],
    to_pos: dict[str, float],
) -> tuple[int, int]:
    from_cx, from_cy = from_pos["center_x"], from_pos["center_y"]
    to_cx, to_cy = to_pos["center_x"], to_pos["center_y"]
    in_idx = _corner_toward_point(rx, ry, rw, rh, from_cx, from_cy)
    dx_e, dy_e = to_cx - from_cx, to_cy - from_cy
    corners = _rhombus_corners(rx, ry, rw, rh)

    if abs(dy_e) <= from_pos["height"] * 0.8:
        if in_idx == 4:
            out_idx = 2
        elif in_idx == 2:
            out_idx = 4
        else:
            out_idx = 2 if to_cx > from_cx else 4
    elif abs(dx_e) <= from_pos["width"] * 0.8:
        if in_idx == 1:
            out_idx = 3
        elif in_idx == 3:
            out_idx = 1
        else:
            out_idx = 3 if to_cy > from_cy else 1
    else:
        mx, my = rx + rw / 2.0, ry + rh / 2.0
        if abs(dx_e) >= abs(dy_e):
            in_idx = 4 if from_cx <= mx else 2
            out_idx = 1 if to_cy < my else 3
        else:
            in_idx = 3 if from_cy <= my else 1
            out_idx = 4 if to_cx < mx else 2
        if out_idx not in _adjacent_corners(in_idx):
            out_idx = min(
                _adjacent_corners(in_idx),
                key=lambda k: (corners[k][0] - to_cx) ** 2 + (corners[k][1] - to_cy) ** 2,
            )
    if in_idx == out_idx:
        out_idx = _opp_corner_idx(in_idx)
    return in_idx, out_idx


def _entry_attrs(x: float, y: float, w: float, h: float, scx: float, scy: float) -> str:
    cx, cy = _rect_center(x, y, w, h)
    dx, dy = scx - cx, scy - cy
    if abs(dx) >= abs(dy):
        if dx >= 0:
            return "entryX=1;entryY=0.5;entryDx=0;entryDy=0;"
        return "entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
    if dy >= 0:
        return "entryX=0.5;entryY=1;entryDx=0;entryDy=0;"
    return "entryX=0.5;entryY=0;entryDx=0;entryDy=0;"


def _rhombus_corner_attrs(corner_idx: int, is_entry: bool) -> str:
    prefix = "entry" if is_entry else "exit"
    attrs = {
        1: f"{prefix}X=0.5;{prefix}Y=0;{prefix}Dx=0;{prefix}Dy=0;",
        2: f"{prefix}X=1;{prefix}Y=0.5;{prefix}Dx=0;{prefix}Dy=0;",
        3: f"{prefix}X=0.5;{prefix}Y=1;{prefix}Dx=0;{prefix}Dy=0;",
        4: f"{prefix}X=0;{prefix}Y=0.5;{prefix}Dx=0;{prefix}Dy=0;",
    }
    return attrs[corner_idx]


def _orthogonal_waypoint(sx: float, sy: float, tx: float, ty: float) -> tuple[float, float] | None:
    if abs(sx - tx) < 1e-6 or abs(sy - ty) < 1e-6:
        return None
    if abs(tx - sx) >= abs(ty - sy):
        return tx, sy
    return sx, ty


def _segment_midpoint(
    sx: float,
    sy: float,
    tx: float,
    ty: float,
    waypoint: tuple[float, float] | None,
) -> tuple[float, float]:
    """线段几何中点；L 形折线取较长那段的中点。"""
    if waypoint is None:
        return (sx + tx) / 2.0, (sy + ty) / 2.0
    wx, wy = waypoint
    l1 = math.hypot(wx - sx, wy - sy)
    l2 = math.hypot(tx - wx, ty - wy)
    if l1 >= l2:
        return (sx + wx) / 2.0, (sy + wy) / 2.0
    return (wx + tx) / 2.0, (wy + ty) / 2.0


def _exit_attrs(x: float, y: float, w: float, h: float, tcx: float, tcy: float) -> str:
    cx, cy = _rect_center(x, y, w, h)
    dx, dy = tcx - cx, tcy - cy
    if abs(dx) >= abs(dy):
        if dx >= 0:
            return "exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
        return "exitX=0;exitY=0.5;exitDx=0;exitDy=0;"
    if dy >= 0:
        return "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
    return "exitX=0.5;exitY=0;exitDx=0;exitDy=0;"


def _fmt_num(v: float) -> str:
    r = round(v, 2)
    if r == int(r):
        return str(int(r))
    return f"{r:.2f}".rstrip("0").rstrip(".")


def _mxcell_vertex(
    root: ET.Element,
    cell_id: str,
    style: str,
    value: str,
    x: float,
    y: float,
    w: float,
    h: float,
) -> None:
    c = ET.SubElement(
        root,
        "mxCell",
        {
            "id": cell_id,
            "value": value,
            "style": style,
            "vertex": "1",
            "parent": "1",
        },
    )
    g = ET.SubElement(
        c,
        "mxGeometry",
        {
            "x": _fmt_num(x),
            "y": _fmt_num(y),
            "width": _fmt_num(w),
            "height": _fmt_num(h),
            "as": "geometry",
        },
    )


def _mxcell_edge_points(
    root: ET.Element,
    cell_id: str,
    style: str,
    value: str,
    sx: float,
    sy: float,
    tx: float,
    ty: float,
    *,
    source: str | None = None,
    target: str | None = None,
) -> None:
    att: dict[str, str] = {
        "id": cell_id,
        "value": value,
        "style": style,
        "edge": "1",
        "parent": "1",
    }
    if source:
        att["source"] = source
    if target:
        att["target"] = target
    c = ET.SubElement(root, "mxCell", att)
    g = ET.SubElement(
        c,
        "mxGeometry",
        {
            "width": "50",
            "height": "50",
            "relative": "1",
            "as": "geometry",
        },
    )
    ET.SubElement(
        g,
        "mxPoint",
        {"x": _fmt_num(sx), "y": _fmt_num(sy), "as": "sourcePoint"},
    )
    waypoint = _orthogonal_waypoint(sx, sy, tx, ty)
    if waypoint:
        arr = ET.SubElement(g, "Array", {"as": "points"})
        ET.SubElement(
            arr,
            "mxPoint",
            {"x": _fmt_num(waypoint[0]), "y": _fmt_num(waypoint[1])},
        )
    ET.SubElement(
        g,
        "mxPoint",
        {"x": _fmt_num(tx), "y": _fmt_num(ty), "as": "targetPoint"},
    )


CARD_LABEL_W = 28.0
CARD_LABEL_H = 24.0
CARD_LABEL_STYLE = (
    "text;html=1;strokeColor=none;fillColor=none;align=center;"
    "verticalAlign=middle;whiteSpace=wrap;rounded=0;"
)


def _primary_segment_vector(
    sx: float,
    sy: float,
    tx: float,
    ty: float,
    waypoint: tuple[float, float] | None,
) -> tuple[float, float]:
    if waypoint is None:
        return tx - sx, ty - sy
    wx, wy = waypoint
    l1 = math.hypot(wx - sx, wy - sy)
    l2 = math.hypot(tx - wx, ty - wy)
    if l1 >= l2:
        return wx - sx, wy - sy
    return tx - wx, ty - wy


def _mxcell_cardinality_label(
    root: ET.Element,
    cell_id: str,
    text: str,
    sx: float,
    sy: float,
    tx: float,
    ty: float,
    waypoint: tuple[float, float] | None = None,
) -> None:
    """基数标签放在线段中点上方（水平线）或左侧（垂直线）。"""
    mx, my = _segment_midpoint(sx, sy, tx, ty, waypoint)
    dx, dy = _primary_segment_vector(sx, sy, tx, ty, waypoint)
    gap = 6.0
    if abs(dx) >= abs(dy):
        lx = mx - CARD_LABEL_W / 2.0
        ly = my - CARD_LABEL_H - gap
    else:
        lx = mx - CARD_LABEL_W - gap
        ly = my - CARD_LABEL_H / 2.0
    _mxcell_vertex(
        root,
        cell_id,
        CARD_LABEL_STYLE,
        _font_label(text, FONT_SIZE),
        lx,
        ly,
        CARD_LABEL_W,
        CARD_LABEL_H,
    )


def _entity_size(name: str, attributes: list[str]) -> tuple[float, float]:
    w = max(120.0, min(220.0, 14.0 * max(len(name), 8) + 24.0))
    if not attributes:
        return w, 60.0
    h = 60.0 + min(260.0, 16.0 * len(attributes))
    return w, min(320.0, max(60.0, h))


def _order_satellites_graph(
    hub: str, others: list[str], rel_pairs: list[tuple[str, str]]
) -> list[str]:
    """把外圈实体排成圆周顺序，使「互不连中心」的边两端尽量在环上相邻，缩短连线。"""
    oset = frozenset(others)
    adj: dict[str, set[str]] = {u: set() for u in others}
    for a, b in rel_pairs:
        if a == hub or b == hub:
            continue
        if a in oset and b in oset:
            adj[a].add(b)
            adj[b].add(a)
    if not others:
        return []
    remaining = set(others)
    start = max(others, key=lambda u: len(adj[u]))
    order: list[str] = [start]
    remaining.remove(start)
    idx = {u: i for i, u in enumerate(others)}
    while remaining:
        last = order[-1]
        best_u: str | None = None
        best_key: tuple[int, int, int] = (-1, -1, -1)
        for u in remaining:
            k0 = len(adj[u] & {last})
            k1 = len(adj[u] & set(order))
            key = (k0, k1, idx[u])
            if key > best_key:
                best_key = key
                best_u = u
        assert best_u is not None
        if best_key[0] == 0 and best_key[1] == 0:
            best_u = min(remaining, key=lambda u: (idx[u], u))
        order.append(best_u)
        remaining.remove(best_u)
    return order


def _choose_hub(names: list[str], rel_endpoints: list[tuple[str, str]], cfg: dict[str, Any]) -> str:
    ce = cfg.get("center_entity")
    if ce is not None:
        s = str(ce).strip()
        if s and s in names:
            return s
    if "用户" in names:
        return "用户"
    if not rel_endpoints:
        return names[0]
    deg: dict[str, int] = {n: 0 for n in names}
    for a, b in rel_endpoints:
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1
    return max(names, key=lambda n: deg.get(n, 0))


def _layout_hub(
    names: list[str],
    sizes: dict[str, tuple[float, float]],
    hub: str,
    others: list[str],
    pw: float,
    ph: float,
    *,
    ring_scale: float = 1.0,
) -> dict[str, tuple[float, float, float, float]]:
    """中心实体在画布中心，外圈实体按给定顺序逆时针均匀分布在圆周上。"""
    cx, cy = pw / 2.0, ph / 2.0
    pos: dict[str, tuple[float, float, float, float]] = {}
    hw, hh = sizes[hub]
    pos[hub] = (cx - hw / 2.0, cy - hh / 2.0, hw, hh)
    m = len(others)
    if m == 0:
        return pos
    max_w = max(sizes[n][0] for n in others)
    max_h = max(sizes[n][1] for n in others)
    # 外圈半径略保守，避免线过长；需要更紧/更松用 ring_scale
    base = 210.0 + 44.0 * math.sqrt(m) + 0.14 * (max_w + max_h)
    R = max(300.0, min(720.0, base)) * ring_scale
    for i, nm in enumerate(others):
        ang = 2 * math.pi * i / m - math.pi / 2.0
        w, h = sizes[nm]
        ex = cx + R * math.cos(ang) - w / 2.0
        ey = cy + R * math.sin(ang) - h / 2.0
        pos[nm] = (ex, ey, w, h)
    return pos


def _rhombus_size(rel_name: str) -> tuple[float, float]:
    w = max(120.0, min(260.0, 14.0 * max(len(rel_name), 4) + 46.0))
    return w, 80.0


def _overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float], pad: float = 0.0) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 + pad <= bx0 or bx1 + pad <= ax0 or ay1 + pad <= by0 or by1 + pad <= ay0)


def _nudge_until_free(
    box: tuple[float, float, float, float],
    occupied: list[tuple[float, float, float, float]],
    *,
    dir_x: float,
    dir_y: float,
    step: float = 40.0,
    tries: int = 30,
    pad: float = 20.0,
) -> tuple[float, float, float, float]:
    """
    沿给定方向平移，直到与已占用框不重叠。
    用于菱形/椭圆轻量避让，尽量保持原有样式与大体布局。
    """
    x0, y0, x1, y1 = box
    if not occupied:
        return box
    norm = math.hypot(dir_x, dir_y) or 1.0
    ux, uy = dir_x / norm, dir_y / norm
    cur = box
    for _ in range(tries):
        if not any(_overlap(cur, o, pad=pad) for o in occupied):
            return cur
        x0, y0, x1, y1 = cur
        cur = (x0 + ux * step, y0 + uy * step, x1 + ux * step, y1 + uy * step)
    return cur


def _snap_to_orthogonal(dx: float, dy: float) -> tuple[float, float]:
    """
    将方向向量对齐到水平、垂直或45度方向，使连线更规整。
    """
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return 0.0, 0.0
    angle = math.atan2(dy, dx)
    # 将角度对齐到 0, 45, 90, 135, 180, -135, -90, -45 度
    snap_angle = round(angle / (math.pi / 4)) * (math.pi / 4)
    return math.cos(snap_angle), math.sin(snap_angle)


def _rel_attr_sides(r: dict[str, Any]) -> tuple[list[str], list[str]]:
    """
    关系属性（椭圆）支持写法：
    - relation_attributes_left / relation_attributes_right
    - relation_attributes（自动从左到右最多分配 4 个）
    每侧最多 2 个。
    """
    left = [str(x).strip() for x in (r.get("relation_attributes_left") or []) if str(x).strip()]
    right = [str(x).strip() for x in (r.get("relation_attributes_right") or []) if str(x).strip()]
    if not left and not right:
        both = [str(x).strip() for x in (r.get("relation_attributes") or []) if str(x).strip()]
        left = both[:2]
        right = both[2:4]
    return left[:2], right[:2]


def _build_undirected_adj(relationships: list[dict[str, Any]]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = {}
    for rel in relationships:
        a, b = str(rel.get("from") or "").strip(), str(rel.get("to") or "").strip()
        if not a or not b:
            continue
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return adj


def _occupied_rows_at_col(grid: dict[str, tuple[int, int]], col: int) -> set[int]:
    return {row for c, row in grid.values() if c == col}


def _next_row_above(col: int, grid: dict[str, tuple[int, int]], base_row: int) -> int:
    occupied = _occupied_rows_at_col(grid, col)
    r = base_row - 1
    while r in occupied:
        r -= 1
    return r


def _next_row_below(col: int, grid: dict[str, tuple[int, int]], base_row: int) -> int:
    occupied = _occupied_rows_at_col(grid, col)
    r = base_row + 1
    while r in occupied:
        r += 1
    return r


def _occupied_cols_at_row(grid: dict[str, tuple[int, int]], row: int) -> set[int]:
    return {col for col, r in grid.values() if r == row}


def _next_col_left(col: int, grid: dict[str, tuple[int, int]], row: int) -> int:
    occupied = _occupied_cols_at_row(grid, row)
    c = col - 1
    while c in occupied:
        c -= 1
    return c


def _next_col_right(col: int, grid: dict[str, tuple[int, int]], row: int) -> int:
    occupied = _occupied_cols_at_row(grid, row)
    c = col + 1
    while c in occupied:
        c += 1
    return c


_LEFT_REL_HINTS = ("查看", "浏览", "查询", "阅读", "访问", "获取")
_BELOW_REL_HINTS = ("创建", "拥有", "生成", "加入", "添加", "收藏", "包含")
_RIGHT_REL_HINTS = ("发布", "提交", "发送", "推送")


def _rel_label(rel: dict[str, Any]) -> str:
    return str(rel.get("label") or rel.get("name") or "").strip()


def _preferred_attachment_side(rel_label: str, slot: int) -> str:
    for hint in _LEFT_REL_HINTS:
        if hint in rel_label:
            return "left"
    for hint in _BELOW_REL_HINTS:
        if hint in rel_label:
            return "below"
    for hint in _RIGHT_REL_HINTS:
        if hint in rel_label:
            return "right"
    return ("below", "left", "right")[slot % 3]


def _layout_vertical_attachments(
    spine: list[str],
    names: list[str],
    relationships: list[dict[str, Any]],
) -> dict[str, tuple[int, int]]:
    """按关系在主链实体正上/正下/左右放置支线实体，与列表顺序无关。"""
    spine_set = set(spine)
    name_set = set(names)
    grid: dict[str, tuple[int, int]] = {}
    for idx, name in enumerate(spine):
        grid[name] = (idx, 0)
    placed = set(spine)

    outgoing: dict[str, list[tuple[str, str]]] = {}
    for rel in relationships:
        fr = str(rel.get("from") or "").strip()
        to = str(rel.get("to") or "").strip()
        if not fr or not to or fr == to:
            continue
        if fr not in name_set or to not in name_set:
            continue
        if fr in spine_set and to not in spine_set:
            outgoing.setdefault(fr, []).append((to, _rel_label(rel)))

    for anchor in spine:
        items = outgoing.get(anchor, [])
        side_slot = 0
        for to, label in items:
            if to in placed:
                continue
            side = _preferred_attachment_side(label, side_slot)
            side_slot += 1
            fcol, frow = grid[anchor]
            if side == "left":
                grid[to] = (_next_col_left(fcol, grid, frow), frow)
            elif side == "right":
                grid[to] = (_next_col_right(fcol, grid, frow), frow)
            else:
                grid[to] = (fcol, _next_row_below(fcol, grid, frow))
            placed.add(to)

    for _ in range(max(len(names) * 2, 1)):
        progressed = False
        for rel in relationships:
            fr = str(rel.get("from") or "").strip()
            to = str(rel.get("to") or "").strip()
            if not fr or not to or fr == to:
                continue
            if fr not in name_set or to not in name_set:
                continue

            if to in placed and fr not in placed and fr not in spine_set:
                tcol, trow = grid[to]
                grid[fr] = (tcol, _next_row_above(tcol, grid, trow))
                placed.add(fr)
                progressed = True
            elif fr in placed and to not in placed and to not in spine_set:
                fcol, frow = grid[fr]
                grid[to] = (fcol, _next_row_below(fcol, grid, frow))
                placed.add(to)
                progressed = True
        if not progressed:
            break
    return grid


def _find_main_chain(hub: str, names: list[str], relationships: list[dict[str, Any]]) -> list[str]:
    directed: dict[str, list[str]] = {}
    undirected = _build_undirected_adj(relationships)
    for rel in relationships:
        fr = str(rel.get("from") or "").strip()
        to = str(rel.get("to") or "").strip()
        if fr and to:
            directed.setdefault(fr, []).append(to)

    chain = [hub]
    visited = {hub}
    current = hub
    while True:
        candidates = [n for n in directed.get(current, []) if n in names and n not in visited]
        if not candidates:
            break
        nxt = max(
            candidates,
            key=lambda n: (
                len([m for m in directed.get(n, []) if m in names and m not in visited]),
                len(undirected.get(n, set())),
                len(n),
            ),
        )
        chain.append(nxt)
        visited.add(nxt)
        current = nxt
    return chain


def _layout_top_row(
    off_spine: list[str],
    spine: list[str],
    relationships: list[dict[str, Any]],
) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    if not off_spine:
        return result

    spine_cols = {name: idx for idx, name in enumerate(spine)}
    hub_col = spine_cols.get(spine[0], 0)

    if "商品" in off_spine:
        result["商品"] = (hub_col, -1)
    if "评价" in off_spine:
        order_col = spine_cols.get("订单", hub_col + 1)
        result["评价"] = (order_col, -1)
    if "分类" in off_spine:
        product_col = result.get("商品", (hub_col, -1))[0]
        result["分类"] = (product_col - 1, -1)

    remaining = [n for n in off_spine if n not in result]
    used_cols = {c for c, _ in result.values()}
    col = hub_col - 2
    for name in remaining:
        while col in used_cols:
            col -= 1
        result[name] = (col, -1)
        used_cols.add(col)
        col -= 1
    return result


def _layout_grid(
    names: list[str],
    sizes: dict[str, tuple[float, float]],
    relationships: list[dict[str, Any]],
    hub: str,
) -> dict[str, tuple[float, float, float, float]]:
    """网格布局：主链水平展开，与主链有关系的实体按关系叠放在正上/正下方。"""
    spine = _find_main_chain(hub, names, relationships)
    grid = _layout_vertical_attachments(spine, names, relationships)
    placed = set(grid.keys())

    off_spine = [n for n in names if n not in placed]
    for name, pos in _layout_top_row(off_spine, spine, relationships).items():
        if name not in grid:
            grid[name] = pos

    for name in names:
        if name not in grid:
            max_col = max((c for c, _ in grid.values()), default=0)
            grid[name] = (max_col + 1, 1)

    by_col: dict[int, list[str]] = {}
    for name, (col, _row) in grid.items():
        by_col.setdefault(col, []).append(name)

    pos: dict[str, tuple[float, float, float, float]] = {}
    for col, ents in by_col.items():
        max_w = max(sizes[n][0] for n in ents)
        col_center_x = GRID_ORIGIN_X + col * GRID_H_SPACING + max_w / 2.0
        for name in ents:
            _col, row = grid[name]
            w, h = sizes[name]
            x = col_center_x - w / 2.0
            y = GRID_ORIGIN_Y + row * GRID_V_SPACING
            pos[name] = (x, y, w, h)
    return pos


def _diamond_candidates(
    from_pos: dict[str, float], to_pos: dict[str, float], rw: float, rh: float
) -> list[tuple[float, float, bool]]:
    from_cx, from_cy = from_pos["center_x"], from_pos["center_y"]
    to_cx, to_cy = to_pos["center_x"], to_pos["center_y"]
    dx, dy = to_cx - from_cx, to_cy - from_cy
    candidates: list[tuple[float, float, bool]] = []

    if abs(dy) <= from_pos["height"] * 0.8:
        candidates.append(((from_cx + to_cx) / 2 - rw / 2, (from_cy + to_cy) / 2 - rh / 2, False))
    elif abs(dx) <= from_pos["width"] * 0.8:
        candidates.append(((from_cx + to_cx) / 2 - rw / 2, (from_cy + to_cy) / 2 - rh / 2, False))
    else:
        ex, ey = _l_elbow_point(from_pos, to_pos)
        candidates.append((ex - rw / 2, ey - rh / 2, False))
        if abs(dx) >= abs(dy):
            candidates.append((
                from_pos["x"] + from_pos["width"] + DIAMOND_GAP,
                from_cy - rh / 2,
                False,
            ))
            candidates.append((
                (from_cx + to_cx) / 2 - rw / 2,
                from_cy - rh / 2,
                False,
            ))
        else:
            if dy > 0:
                gap_y = from_pos["bottom_y"] + DIAMOND_GAP
            else:
                gap_y = from_pos["top_y"] - rh - DIAMOND_GAP
            candidates.append((from_cx - rw / 2, gap_y, dy < 0))
            candidates.append((
                from_cx - rw / 2,
                (from_cy + to_cy) / 2 - rh / 2,
                dy < 0,
            ))

    seen: set[tuple[int, int]] = set()
    unique: list[tuple[float, float, bool]] = []
    for x, y, prefer_up in candidates:
        key = (round(x), round(y))
        if key not in seen:
            seen.add(key)
            unique.append((x, y, prefer_up))
    return unique


def _score_rhombus_box(
    x: float,
    y: float,
    rw: float,
    rh: float,
    from_pos: dict[str, float],
    to_pos: dict[str, float],
    occupied: list[tuple[float, float, float, float]],
) -> float:
    score = 0.0
    box = (x, y, x + rw, y + rh)
    for ob in occupied:
        if _overlap(box, ob, pad=16.0):
            score += 1000.0
    cands = _diamond_candidates(from_pos, to_pos, rw, rh)
    if cands:
        ideal_x, ideal_y, _ = cands[0]
        score += abs(x - ideal_x) * 0.2 + abs(y - ideal_y) * 0.3
    return score


def _find_best_rhombus_position(
    from_pos: dict[str, float],
    to_pos: dict[str, float],
    rw: float,
    rh: float,
    occupied: list[tuple[float, float, float, float]],
) -> tuple[float, float]:
    best_xy: tuple[float, float] | None = None
    best_score = float("inf")
    for base_x, base_y, prefer_up in _diamond_candidates(from_pos, to_pos, rw, rh):
        r_box = (base_x, base_y, base_x + rw, base_y + rh)
        nudged = _nudge_until_free(
            r_box,
            occupied,
            dir_x=0.0,
            dir_y=-1.0 if prefer_up else 1.0,
            step=max(36.0, rh * 0.6),
            tries=30,
            pad=16.0,
        )
        nx, ny = nudged[0], nudged[1]
        score = _score_rhombus_box(nx, ny, rw, rh, from_pos, to_pos, occupied)
        if score < best_score:
            best_score = score
            best_xy = (nx, ny)
    if best_xy is None:
        cands = _diamond_candidates(from_pos, to_pos, rw, rh)
        if cands:
            return cands[0][0], cands[0][1]
        return from_pos["center_x"] - rw / 2, from_pos["center_y"] - rh / 2
    return best_xy


def _sort_relationships_for_diamonds(
    rels: list[tuple[str, str, str, str, str, list[str], list[str]]],
    pos: dict[str, tuple[float, float, float, float]],
) -> list[tuple[str, str, str, str, str, list[str], list[str]]]:
    def sort_key(item: tuple[str, str, str, str, str, list[str], list[str]]) -> tuple[int, float]:
        fr, to, *_ = item
        x1, y1, w1, h1 = pos[fr]
        x2, y2, w2, h2 = pos[to]
        dy = abs((y1 + h1 / 2) - (y2 + h2 / 2))
        dx = abs((x1 + w1 / 2) - (x2 + w2 / 2))
        same_row = dy <= h1 * 0.8
        return (0 if same_row else 1, dx + dy)

    return sorted(rels, key=sort_key)


def build_mxgraph(cfg: dict[str, Any]) -> tuple[ET.Element, int, int]:
    entities_raw: list[dict[str, Any]] = list(cfg.get("entities") or [])
    rels_raw: list[dict[str, Any]] = list(cfg.get("relationships") or [])

    if not entities_raw:
        raise ValueError("entities 至少包含 1 个实体")

    entities: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for i, e in enumerate(entities_raw):
        if not isinstance(e, dict):
            raise ValueError(f"entities[{i}] 须为对象")
        name = str(e.get("name") or "").strip()
        if not name:
            raise ValueError(f"entities[{i}].name 不能为空")
        if name in seen:
            raise ValueError(f"重复实体名: {name}")
        seen.add(name)
        attrs = [str(a).strip() for a in (e.get("attributes") or []) if str(a).strip()]
        entities.append((name, attrs))

    names = [n for n, _ in entities]
    name_to_i = {n: i for i, n in enumerate(names)}

    rels: list[tuple[str, str, str, str, str, list[str], list[str]]] = []
    for i, r in enumerate(rels_raw):
        if not isinstance(r, dict):
            raise ValueError(f"relationships[{i}] 须为对象")
        fr = str(r.get("from") or "").strip()
        to = str(r.get("to") or "").strip()
        if not fr or not to:
            raise ValueError(f"relationships[{i}] 须包含 from 与 to")
        if fr not in name_to_i or to not in name_to_i:
            raise ValueError(f"relationships[{i}] 引用未知实体: {fr} -> {to}")
        rel_label = str(r.get("name") or "联系").strip() or "联系"
        c1, c2 = _parse_cardinality(
            r.get("cardinality"),
            r.get("cardinality_near_from"),
            r.get("cardinality_near_to"),
        )
        left_attrs, right_attrs = _rel_attr_sides(r)
        rels.append((fr, to, rel_label, c1, c2, left_attrs, right_attrs))

    sizes = {nm: _entity_size(nm, attrs) for nm, attrs in entities}
    pw, ph = int(cfg.get("pageWidth") or DEFAULT_PAGE_W), int(cfg.get("pageHeight") or DEFAULT_PAGE_H)
    rel_endpoints = [(fr, to) for fr, to, _, _, _, _, _ in rels] if rels else []
    hub = _choose_hub(names, rel_endpoints, cfg)
    layout_mode = str(cfg.get("layout", "grid")).strip().lower()
    if layout_mode == "hub":
        ring_scale = float(cfg.get("ring_scale", 1.08))
        others_raw = [n for n in names if n != hub]
        order_mode = str(cfg.get("satellite_order", "graph")).strip().lower()
        if order_mode == "json":
            others_ord = others_raw
        else:
            others_ord = _order_satellites_graph(hub, others_raw, rel_endpoints)
        pos = _layout_hub(
            names,
            sizes,
            hub,
            others_ord,
            float(pw),
            float(ph),
            ring_scale=ring_scale,
        )
    else:
        pos = _layout_grid(names, sizes, rels_raw, hub)
    lane = float(cfg.get("relationship_lane_spacing", 48.0))
    hub_x, hub_y, hub_w, hub_h = pos[hub]
    hub_cx, hub_cy = _rect_center(hub_x, hub_y, hub_w, hub_h)

    prefix, id_counter = _id_chain()

    def nid() -> str:
        return f"{prefix}{next(id_counter)}"

    eid: dict[str, str] = {nm: nid() for nm in names}

    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    occupied: list[tuple[float, float, float, float]] = []

    for nm, attrs in entities:
        x, y, w, h = pos[nm]
        _mxcell_vertex(
            root,
            eid[nm],
            ENTITY_STYLE,
            _entity_value(nm, attrs),
            x,
            y,
            w,
            h,
        )
        occupied.append((x, y, x + w, y + h))

    rh_extrema: list[tuple[float, float, float, float]] = []

    pair_counts: dict[tuple[str, str], int] = {}
    for fr, to, rel_label, c_from, c_to, left_attrs, right_attrs in _sort_relationships_for_diamonds(rels, pos):
        x1, y1, w1, h1 = pos[fr]
        x2, y2, w2, h2 = pos[to]
        from_pos = _conn_pos(x1, y1, w1, h1)
        to_pos = _conn_pos(x2, y2, w2, h2)
        rw, rh = _rhombus_size(rel_label)

        if layout_mode == "hub":
            key = (fr, to) if fr <= to else (to, fr)
            idx = pair_counts.get(key, 0)
            pair_counts[key] = idx + 1
            rcx1, rcy1 = from_pos["center_x"], from_pos["center_y"]
            rcx2, rcy2 = to_pos["center_x"], to_pos["center_y"]
            dx, dy = rcx2 - rcx1, rcy2 - rcy1
            ln = math.hypot(dx, dy) or 1.0
            ox, oy = -dy / ln, dx / ln
            mid0x, mid0y = (rcx1 + rcx2) / 2.0, (rcy1 + rcy2) / 2.0
            hx, hy = mid0x - hub_cx, mid0y - hub_cy
            if (fr != hub and to != hub) and (ox * hx + oy * hy) < 0:
                ox, oy = -ox, -oy
            ox, oy = _snap_to_orthogonal(ox, oy)
            off = float(idx) * lane
            mx = mid0x + ox * off
            my = mid0y + oy * off
            if fr != hub and to != hub:
                outward_bias = float(cfg.get("relationship_outward_bias", 120.0))
                hv = math.hypot(hx, hy) or 1.0
                mx += (hx / hv) * outward_bias
                my += (hy / hv) * outward_bias
            rx = mx - rw / 2.0
            ry = my - rh / 2.0
            r_box = _nudge_until_free(
                (rx, ry, rx + rw, ry + rh),
                occupied,
                dir_x=ox,
                dir_y=oy,
                step=max(36.0, lane * 0.7),
                tries=24,
                pad=16.0,
            )
            rx, ry = r_box[0], r_box[1]
        else:
            rx, ry = _find_best_rhombus_position(from_pos, to_pos, rw, rh, occupied)

        mx, my = rx + rw / 2.0, ry + rh / 2.0
        rh_extrema.append((rx, ry, rx + rw, ry + rh))
        occupied.append((rx, ry, rx + rw, ry + rh))

        in_idx, out_idx = _pick_connection_corners(rx, ry, rw, rh, from_pos, to_pos)
        corners = _rhombus_corners(rx, ry, rw, rh)
        tx1, ty1 = corners[in_idx]
        sx1, sy1 = _rect_border_toward(x1, y1, w1, h1, tx1, ty1)
        sx2, sy2 = corners[out_idx]
        tx2, ty2 = _rect_border_toward(x2, y2, w2, h2, sx2, sy2)

        rid = nid()
        _mxcell_vertex(
            root,
            rid,
            RHOMBUS_STYLE,
            _font_label(rel_label, FONT_SIZE),
            rx,
            ry,
            rw,
            rh,
        )

        st1 = (
            EDGE_PLAIN
            + _exit_attrs(x1, y1, w1, h1, tx1, ty1)
            + _rhombus_corner_attrs(in_idx, is_entry=True)
        )
        e1 = nid()
        wp1 = _orthogonal_waypoint(sx1, sy1, tx1, ty1)
        _mxcell_edge_points(
            root,
            e1,
            st1,
            "",
            sx1,
            sy1,
            tx1,
            ty1,
            source=eid[fr],
            target=rid,
        )
        _mxcell_cardinality_label(root, nid(), c_from, sx1, sy1, tx1, ty1, wp1)

        st2 = (
            EDGE_PLAIN
            + _rhombus_corner_attrs(out_idx, is_entry=False)
            + _entry_attrs(x2, y2, w2, h2, sx2, sy2)
        )
        e2 = nid()
        wp2 = _orthogonal_waypoint(sx2, sy2, tx2, ty2)
        _mxcell_edge_points(
            root,
            e2,
            st2,
            "",
            sx2,
            sy2,
            tx2,
            ty2,
            source=rid,
            target=eid[to],
        )
        _mxcell_cardinality_label(root, nid(), c_to, sx2, sy2, tx2, ty2, wp2)

        # 关系属性（椭圆）：挂在另外两个角（非进/出角）
        attr_w, attr_h = 120.0, 54.0
        corner_gap = 110.0
        stack_gap = 80.0
        side_corners = [k for k in (1, 2, 3, 4) if k not in (in_idx, out_idx)]
        c_a = corners[side_corners[0]]
        c_b = corners[side_corners[1]]
        # 按 x 从小到大分配左右，保持 left/right 语义稳定
        left_corner = c_a if c_a[0] <= c_b[0] else c_b
        right_corner = c_b if c_a[0] <= c_b[0] else c_a
        ldx, ldy = left_corner[0] - mx, left_corner[1] - my
        rdx, rdy = right_corner[0] - mx, right_corner[1] - my
        lnorm = math.hypot(ldx, ldy) or 1.0
        rnorm = math.hypot(rdx, rdy) or 1.0
        # 将属性方向对齐到水平/垂直/45度
        ldx_snap, ldy_snap = _snap_to_orthogonal(ldx / lnorm, ldy / lnorm)
        rdx_snap, rdy_snap = _snap_to_orthogonal(rdx / rnorm, rdy / rnorm)
        for j, txt in enumerate(left_attrs[:2]):
            base_x = left_corner[0] + ldx_snap * corner_gap
            base_y = left_corner[1] + ldy_snap * corner_gap
            ay = base_y + (j - (len(left_attrs) - 1) / 2.0) * stack_gap
            ax = base_x
            a_box = _nudge_until_free(
                (ax - attr_w / 2.0, ay - attr_h / 2.0, ax + attr_w / 2.0, ay + attr_h / 2.0),
                occupied,
                dir_x=ldx_snap,
                dir_y=ldy_snap,
                step=36.0,
                tries=20,
                pad=16.0,
            )
            ax = (a_box[0] + a_box[2]) / 2.0
            ay = (a_box[1] + a_box[3]) / 2.0
            a_id = nid()
            _mxcell_vertex(
                root,
                a_id,
                REL_ATTR_ELLIPSE_STYLE,
                _font_label(txt, FONT_SIZE),
                a_box[0],
                a_box[1],
                attr_w,
                attr_h,
            )
            rh_extrema.append((a_box[0], a_box[1], a_box[2], a_box[3]))
            occupied.append((a_box[0], a_box[1], a_box[2], a_box[3]))
            es = nid()
            ex, ey = left_corner
            sx, sy = _ellipse_border_toward(ax, ay, attr_w, attr_h, ex, ey)
            _mxcell_edge_points(
                root,
                es,
                EDGE_PLAIN,
                "",
                sx,
                sy,
                ex,
                ey,
                source=a_id,
                target=rid,
            )

        for j, txt in enumerate(right_attrs[:2]):
            base_x = right_corner[0] + rdx_snap * corner_gap
            base_y = right_corner[1] + rdy_snap * corner_gap
            ay = base_y + (j - (len(right_attrs) - 1) / 2.0) * stack_gap
            ax = base_x
            a_box = _nudge_until_free(
                (ax - attr_w / 2.0, ay - attr_h / 2.0, ax + attr_w / 2.0, ay + attr_h / 2.0),
                occupied,
                dir_x=rdx_snap,
                dir_y=rdy_snap,
                step=36.0,
                tries=20,
                pad=16.0,
            )
            ax = (a_box[0] + a_box[2]) / 2.0
            ay = (a_box[1] + a_box[3]) / 2.0
            a_id = nid()
            _mxcell_vertex(
                root,
                a_id,
                REL_ATTR_ELLIPSE_STYLE,
                _font_label(txt, FONT_SIZE),
                a_box[0],
                a_box[1],
                attr_w,
                attr_h,
            )
            rh_extrema.append((a_box[0], a_box[1], a_box[2], a_box[3]))
            occupied.append((a_box[0], a_box[1], a_box[2], a_box[3]))
            es = nid()
            ex, ey = right_corner
            sx, sy = _ellipse_border_toward(ax, ay, attr_w, attr_h, ex, ey)
            _mxcell_edge_points(
                root,
                es,
                EDGE_PLAIN,
                "",
                sx,
                sy,
                ex,
                ey,
                source=a_id,
                target=rid,
            )

    margin = float(cfg.get("page_margin", 240.0))
    min_x = min((pos[n][0] for n in names), default=0.0)
    min_y = min((pos[n][1] for n in names), default=0.0)
    max_x = max((pos[n][0] + pos[n][2] for n in names), default=float(pw))
    max_y = max((pos[n][1] + pos[n][3] for n in names), default=float(ph))
    for rx0, ry0, rx1, ry1 in rh_extrema:
        min_x = min(min_x, rx0)
        min_y = min(min_y, ry0)
        max_x = max(max_x, rx1)
        max_y = max(max_y, ry1)
    need_w = int(max(float(pw), max_x + margin, 2 * margin + max_x - min_x))
    need_h = int(max(float(ph), max_y + margin, 2 * margin + max_y - min_y))

    return root, need_w, need_h


def build_document(cfg: dict[str, Any]) -> ET.ElementTree:
    root_el = ET.Element("mxfile", {"host": "app.diagrams.net"})
    diag = ET.SubElement(root_el, "diagram", {"name": "Page-1", "id": _diagram_id()})
    graph_root, page_w, page_h = build_mxgraph(cfg)
    # 属性顺序与 E-R图.xml 中 mxGraphModel 一致
    gm = ET.SubElement(
        diag,
        "mxGraphModel",
        {
            "dx": str(cfg.get("dx") or "288"),
            "dy": str(cfg.get("dy") or "818"),
            "grid": "1",
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
            "math": "0",
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


def _write_mxfile(tree: ET.ElementTree, path: Path | None) -> None:
    enc = "utf-8"
    if path is not None:
        with path.open("w", encoding=enc, newline="\n") as f:
            tree.write(f, encoding="unicode", xml_declaration=False)
    else:
        buf = io.StringIO()
        tree.write(buf, encoding="unicode", xml_declaration=False)
        sys.stdout.write(buf.getvalue())


def main() -> int:
    ap = argparse.ArgumentParser(description="从 JSON 生成 E-R 图 draw.io XML（版式对齐 E-R图.xml）")
    ap.add_argument(
        "input",
        nargs="?",
        type=str,
        default=None,
        help="JSON 文件路径，或 - 表示从标准输入读取",
    )
    ap.add_argument("-o", "--output", type=Path, help="输出 .xml 路径（默认 stdout）")
    args = ap.parse_args()

    src = args.input
    if src in (None, "-"):
        data = sys.stdin.read()
    else:
        data = Path(src).read_text(encoding="utf-8-sig")

    try:
        cfg = json.loads(data)
        tree = build_document(cfg)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    if args.output:
        _write_mxfile(tree, args.output)
        print(f"已写入: {args.output}", file=sys.stderr)
    else:
        _write_mxfile(tree, None)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
