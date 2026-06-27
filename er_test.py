#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ER 图渲染脚本
智能布局算法：自动美观分布实体

输入：JSON 文件
输出：XML 文件（draw.io 格式）

使用方法：
  python er_test.py input.json output.xml
"""

import json
import sys
import uuid
from typing import Dict, List, Tuple, Set, Optional


def generate_id():
    """生成唯一 ID"""
    return uuid.uuid4().hex[:16]


DIAMOND_W = 100
DIAMOND_H = 60
DIAMOND_GAP = 50
FONT_SIZE = 17
CARD_LABEL_W = 28.0
CARD_LABEL_H = 24.0
CARD_LABEL_STYLE = (
    "text;html=1;strokeColor=none;fillColor=none;align=center;"
    "verticalAlign=middle;whiteSpace=wrap;rounded=0;"
)


def _append_cardinality_label(
    xml_parts: List[str],
    text: str,
    sx: float,
    sy: float,
    tx: float,
    ty: float,
) -> None:
    """基数标签放在线段几何中点"""
    wp = _orthogonal_waypoint(sx, sy, tx, ty)
    mx, my = _segment_midpoint(sx, sy, tx, ty, wp)
    x = mx - CARD_LABEL_W / 2.0
    y = my - CARD_LABEL_H / 2.0
    label_id = generate_id()
    xml_parts.append(
        f'        <mxCell id="{label_id}" value="&lt;font style=&quot;font-size: {FONT_SIZE}px;&quot;&gt;'
        f'{text}&lt;/font&gt;" style="{CARD_LABEL_STYLE}" vertex="1" parent="1">'
    )
    xml_parts.append(
        f'          <mxGeometry x="{x}" y="{y}" width="{CARD_LABEL_W}" height="{CARD_LABEL_H}" as="geometry" />'
    )
    xml_parts.append('        </mxCell>')


def _rect_center(x: float, y: float, w: float, h: float) -> Tuple[float, float]:
    return x + w / 2, y + h / 2


def _rect_border_toward(x: float, y: float, w: float, h: float, tcx: float, tcy: float) -> Tuple[float, float]:
    """矩形边缘上朝向目标点的连接点"""
    cx, cy = _rect_center(x, y, w, h)
    dx, dy = tcx - cx, tcy - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return cx, cy
    if abs(dx) >= abs(dy):
        return (x + w if dx > 0 else x, cy)
    return (cx, y + h if dy > 0 else y)


def _rhombus_corners(rx: float, ry: float, rw: float, rh: float) -> Dict[int, Tuple[float, float]]:
    """菱形四个端点：1=上，2=右，3=下，4=左"""
    cx, cy = _rect_center(rx, ry, rw, rh)
    return {
        1: (cx, ry),
        2: (rx + rw, cy),
        3: (cx, ry + rh),
        4: (rx, cy),
    }


def _corner_toward_point(rx: float, ry: float, rw: float, rh: float, px: float, py: float) -> int:
    """菱形上朝向外部点的角：1=上，2=右，3=下，4=左"""
    cx, cy = _rect_center(rx, ry, rw, rh)
    dx, dy = px - cx, py - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return 4
    if abs(dx) >= abs(dy):
        return 4 if dx < 0 else 2
    return 1 if dy < 0 else 3


def _opp_corner_idx(i: int) -> int:
    return {1: 3, 2: 4, 3: 1, 4: 2}[i]


def _adjacent_corners(i: int) -> List[int]:
    return {1: [2, 4], 2: [1, 3], 3: [2, 4], 4: [1, 3]}[i]


def _l_elbow_point(from_pos: dict, to_pos: dict) -> Tuple[float, float]:
    from_cx, from_cy = from_pos["center_x"], from_pos["center_y"]
    to_cx, to_cy = to_pos["center_x"], to_pos["center_y"]
    dx, dy = to_cx - from_cx, to_cy - from_cy
    if abs(dx) >= abs(dy):
        return to_cx, from_cy
    return from_cx, to_cy


def _pick_connection_corners(
    rx: float, ry: float, rw: float, rh: float, from_pos: dict, to_pos: dict
) -> Tuple[int, int]:
    """按走线方式选择菱形入/出角：水平对穿、垂直连通、L 形相邻角"""
    from_cx, from_cy = from_pos["center_x"], from_pos["center_y"]
    to_cx, to_cy = to_pos["center_x"], to_pos["center_y"]
    in_idx = _corner_toward_point(rx, ry, rw, rh, from_cx, from_cy)

    dx_e = to_cx - from_cx
    dy_e = to_cy - from_cy
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


def _boxes_overlap(
    a: Tuple[float, float, float, float],
    b: Tuple[float, float, float, float],
    pad: float = 0.0,
) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw + pad <= bx or bx + bw + pad <= ax or ay + ah + pad <= by or by + bh + pad <= ay)


def _diamond_candidates(from_pos: dict, to_pos: dict) -> List[Tuple[float, float, bool]]:
    """生成菱形候选位置（x, y, prefer_up_nudge）"""
    from_cx, from_cy = from_pos["center_x"], from_pos["center_y"]
    to_cx, to_cy = to_pos["center_x"], to_pos["center_y"]
    dx, dy = to_cx - from_cx, to_cy - from_cy
    candidates: List[Tuple[float, float, bool]] = []

    if abs(dy) <= from_pos["height"] * 0.8:
        mx = (from_cx + to_cx) / 2 - DIAMOND_W / 2
        my = (from_cy + to_cy) / 2 - DIAMOND_H / 2
        candidates.append((mx, my, False))
    elif abs(dx) <= from_pos["width"] * 0.8:
        mx = (from_cx + to_cx) / 2 - DIAMOND_W / 2
        my = (from_cy + to_cy) / 2 - DIAMOND_H / 2
        candidates.append((mx, my, False))
    else:
        ex, ey = _l_elbow_point(from_pos, to_pos)
        candidates.append((ex - DIAMOND_W / 2, ey - DIAMOND_H / 2, False))
        if abs(dx) >= abs(dy):
            candidates.append((
                from_pos["x"] + from_pos["width"] + DIAMOND_GAP,
                from_cy - DIAMOND_H / 2,
                False,
            ))
            candidates.append((
                (from_cx + to_cx) / 2 - DIAMOND_W / 2,
                from_cy - DIAMOND_H / 2,
                False,
            ))
        else:
            if dy > 0:
                gap_y = from_pos["bottom_y"] + DIAMOND_GAP
            else:
                gap_y = from_pos["top_y"] - DIAMOND_H - DIAMOND_GAP
            candidates.append((from_cx - DIAMOND_W / 2, gap_y, dy < 0))
            candidates.append((
                from_cx - DIAMOND_W / 2,
                (from_cy + to_cy) / 2 - DIAMOND_H / 2,
                dy < 0,
            ))

    seen = set()
    unique: List[Tuple[float, float, bool]] = []
    for item in candidates:
        key = (round(item[0]), round(item[1]))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _diamond_position(from_pos: dict, to_pos: dict) -> Tuple[float, float, bool]:
    """菱形默认位置（兼容旧接口）"""
    cands = _diamond_candidates(from_pos, to_pos)
    return cands[0] if cands else (0.0, 0.0, False)


def _score_diamond_box(
    x: float, y: float, from_pos: dict, to_pos: dict, occupied: List[Tuple[float, float, float, float]]
) -> float:
    """分数越低越好：重叠严重惩罚，偏离理想位置轻惩罚"""
    box = (x, y, DIAMOND_W, DIAMOND_H)
    score = 0.0
    for ob in occupied:
        if _boxes_overlap(box, ob, pad=16):
            score += 1000.0
    ideal_x, ideal_y, _ = _diamond_position(from_pos, to_pos)
    score += abs(x - ideal_x) * 0.2 + abs(y - ideal_y) * 0.3
    return score


def _sort_relationships_for_diamonds(relationships: list, entity_positions: dict) -> list:
    """先放置同行关系的菱形，再处理跨行关系，减少避让挤压"""
    def sort_key(rel: dict) -> Tuple[int, float]:
        fp = entity_positions.get(rel["from"], {})
        tp = entity_positions.get(rel["to"], {})
        if not fp or not tp:
            return (1, 0.0)
        dy = abs(fp["center_y"] - tp["center_y"])
        dx = abs(fp["center_x"] - tp["center_x"])
        same_row = dy <= fp.get("height", 60) * 0.8
        return (0 if same_row else 1, dx + dy)

    return sorted(relationships, key=sort_key)


def _find_best_diamond_position(
    from_pos: dict,
    to_pos: dict,
    occupied: List[Tuple[float, float, float, float]],
) -> Tuple[float, float]:
    """在候选位置与偏移中选取无重叠或重叠最少的菱形位置"""
    best_xy: Optional[Tuple[float, float]] = None
    best_score = float("inf")

    for base_x, base_y, prefer_up in _diamond_candidates(from_pos, to_pos):
        nx, ny = _nudge_diamond(base_x, base_y, DIAMOND_W, DIAMOND_H, occupied, prefer_up=prefer_up)
        score = _score_diamond_box(nx, ny, from_pos, to_pos, occupied)
        if score < best_score:
            best_score = score
            best_xy = (nx, ny)

    if best_xy is None:
        dx, dy = _diamond_position(from_pos, to_pos)
        return dx, dy
    return best_xy


def _nudge_diamond(
    x: float,
    y: float,
    w: float,
    h: float,
    occupied: List[Tuple[float, float, float, float]],
    prefer_up: bool = False,
) -> Tuple[float, float]:
    """避免菱形与已有区域重叠，优先向上或向下错开"""
    gap = 20
    up = [(0.0, -i * (h + gap)) for i in range(30)]
    down = [(0.0, i * (h + gap)) for i in range(1, 15)]
    horiz: List[Tuple[float, float]] = []
    for i in range(1, 12):
        horiz.append((i * (w + gap), 0.0))
        horiz.append((-i * (w + gap), 0.0))

    if prefer_up:
        offsets = [(0.0, 0.0)] + horiz + up[1:] + down
    else:
        offsets = [(0.0, 0.0)] + horiz + down + up[1:]

    for ox, oy in offsets:
        nx, ny = x + ox, y + oy
        conflict = False
        for bx, by, bw, bh in occupied:
            if not (nx + w + gap < bx or bx + bw + gap < nx or ny + h + gap < by or by + bh + gap < ny):
                conflict = True
                break
        if not conflict:
            return nx, ny
    return x, y


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


def _orthogonal_waypoint(sx: float, sy: float, tx: float, ty: float) -> Optional[Tuple[float, float]]:
    """非水平/垂直线段时插入一个直角折点"""
    if abs(sx - tx) < 1e-6 or abs(sy - ty) < 1e-6:
        return None
    if abs(tx - sx) >= abs(ty - sy):
        return (tx, sy)
    return (sx, ty)


def _segment_midpoint(
    sx: float,
    sy: float,
    tx: float,
    ty: float,
    waypoint: Optional[Tuple[float, float]],
) -> Tuple[float, float]:
    if waypoint is None:
        return (sx + tx) / 2.0, (sy + ty) / 2.0
    wx, wy = waypoint
    l1 = math.hypot(wx - sx, wy - sy)
    l2 = math.hypot(tx - wx, ty - wy)
    if l1 >= l2:
        return (sx + wx) / 2.0, (sy + wy) / 2.0
    return (wx + tx) / 2.0, (wy + ty) / 2.0


def _append_edge_geometry(
    xml_parts: List[str], sx: float, sy: float, tx: float, ty: float
) -> None:
    xml_parts.append('          <mxGeometry width="50" height="50" relative="1" as="geometry">')
    xml_parts.append(f'            <mxPoint x="{sx}" y="{sy}" as="sourcePoint" />')
    waypoint = _orthogonal_waypoint(sx, sy, tx, ty)
    if waypoint:
        xml_parts.append('            <Array as="points">')
        xml_parts.append(f'              <mxPoint x="{waypoint[0]}" y="{waypoint[1]}" />')
        xml_parts.append('            </Array>')
    xml_parts.append(f'            <mxPoint x="{tx}" y="{ty}" as="targetPoint" />')
    xml_parts.append('          </mxGeometry>')


def _append_edge_label(
    xml_parts: List[str],
    text: str,
    sx: float,
    sy: float,
    tx: float,
    ty: float,
) -> None:
    _append_cardinality_label(xml_parts, text, sx, sy, tx, ty)


class ERLayout:
    """ER 图布局管理器 - 树形布局"""

    def __init__(self, entity_width=150, entity_height=60, h_spacing=400, v_spacing=250):
        self.entity_width = entity_width
        self.entity_height = entity_height
        self.h_spacing = h_spacing  # 水平间距（加大）
        self.v_spacing = v_spacing  # 垂直间距（加大）
        self.entities = {}  # name -> position info
        self.occupied = set()  # 已占用的网格位置 (row, col)

    def find_position(self, from_entity: str, direction: str = "right") -> Tuple[float, float]:
        """找到最佳放置位置"""
        if from_entity not in self.entities:
            # 第一个实体，放在 (0, 0)
            return self._grid_to_pos(0, 0)

        ref = self.entities[from_entity]
        ref_row, ref_col = ref["row"], ref["col"]

        # 根据方向尝试不同位置
        attempts = []

        if direction == "right":
            # 优先右边，然后上、下
            attempts = [
                (ref_row, ref_col + 1),      # 右边
                (ref_row - 1, ref_col + 1),   # 右上
                (ref_row + 1, ref_col + 1),   # 右下
                (ref_row - 1, ref_col),        # 上边
                (ref_row + 1, ref_col),        # 下边
            ]
        elif direction == "left":
            attempts = [
                (ref_row, ref_col - 1),      # 左边
                (ref_row - 1, ref_col - 1),   # 左上
                (ref_row + 1, ref_col - 1),   # 左下
                (ref_row - 1, ref_col),        # 上边
                (ref_row + 1, ref_col),        # 下边
            ]
        elif direction == "bottom":
            attempts = [
                (ref_row + 1, ref_col),      # 下边
                (ref_row + 1, ref_col - 1),   # 左下
                (ref_row + 1, ref_col + 1),   # 右下
                (ref_row, ref_col - 1),        # 左边
                (ref_row, ref_col + 1),        # 右边
            ]
        else:  # top
            attempts = [
                (ref_row - 1, ref_col),      # 上边
                (ref_row - 1, ref_col - 1),   # 左上
                (ref_row - 1, ref_col + 1),   # 右上
                (ref_row, ref_col - 1),        # 左边
                (ref_row, ref_col + 1),        # 右边
            ]

        # 找到第一个空闲位置
        for row, col in attempts:
            if (row, col) not in self.occupied:
                return self._grid_to_pos(row, col)

        # 如果都满了，向外扩展
        for offset in range(1, 10):
            for row, col in [
                (ref_row, ref_col + offset),
                (ref_row + offset, ref_col),
                (ref_row - offset, ref_col),
                (ref_row, ref_col - offset),
            ]:
                if (row, col) not in self.occupied:
                    return self._grid_to_pos(row, col)

        # 最后兜底
        return self._grid_to_pos(ref_row, ref_col + 3)

    def _grid_to_pos(self, row: int, col: int) -> Tuple[float, float]:
        """网格坐标转像素坐标"""
        x = 100 + col * self.h_spacing
        y = 100 + row * self.v_spacing
        return (x, y)

    def add_entity(self, name: str, x: float, y: float):
        """添加实体"""
        # 计算网格位置
        col = round((x - 100) / self.h_spacing)
        row = round((y - 100) / self.v_spacing)

        self.entities[name] = {
            "x": x,
            "y": y,
            "row": row,
            "col": col,
            "width": self.entity_width,
            "height": self.entity_height,
            "center_x": x + self.entity_width / 2,
            "center_y": y + self.entity_height / 2,
            "right_x": x + self.entity_width,
            "left_x": x,
            "top_y": y,
            "bottom_y": y + self.entity_height,
        }
        self.occupied.add((row, col))


def build_tree(entities: list, relationships: list) -> dict:
    """构建实体关系邻接表"""
    adj = {}
    for entity in entities:
        adj[entity["name"]] = []

    for rel in relationships:
        from_name = rel["from"]
        to_name = rel["to"]
        rel_type = rel.get("type", "1:N")
        label = rel.get("label", "")

        adj[from_name].append({"to": to_name, "type": rel_type, "label": label, "direction": "right"})
        if rel_type == "N:M":
            adj[to_name].append({"to": from_name, "type": rel_type, "label": label, "direction": "left"})

    return adj


def _choose_hub(names: List[str], relationships: list) -> str:
    if "用户" in names:
        return "用户"
    degree: Dict[str, int] = {n: 0 for n in names}
    for rel in relationships:
        degree[rel["from"]] = degree.get(rel["from"], 0) + 1
        degree[rel["to"]] = degree.get(rel["to"], 0) + 1
    return max(names, key=lambda n: degree.get(n, 0))


def _build_undirected_adj(relationships: list) -> Dict[str, Set[str]]:
    adj: Dict[str, Set[str]] = {}
    for rel in relationships:
        a, b = rel["from"], rel["to"]
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    return adj


def _occupied_rows_at_col(grid: Dict[str, Tuple[int, int]], col: int) -> Set[int]:
    return {row for c, row in grid.values() if c == col}


def _next_row_above(col: int, grid: Dict[str, Tuple[int, int]], base_row: int) -> int:
    occupied = _occupied_rows_at_col(grid, col)
    r = base_row - 1
    while r in occupied:
        r -= 1
    return r


def _next_row_below(col: int, grid: Dict[str, Tuple[int, int]], base_row: int) -> int:
    occupied = _occupied_rows_at_col(grid, col)
    r = base_row + 1
    while r in occupied:
        r += 1
    return r


def _occupied_cols_at_row(grid: Dict[str, Tuple[int, int]], row: int) -> Set[int]:
    return {col for col, r in grid.values() if r == row}


def _next_col_left(col: int, grid: Dict[str, Tuple[int, int]], row: int) -> int:
    occupied = _occupied_cols_at_row(grid, row)
    c = col - 1
    while c in occupied:
        c -= 1
    return c


def _next_col_right(col: int, grid: Dict[str, Tuple[int, int]], row: int) -> int:
    occupied = _occupied_cols_at_row(grid, row)
    c = col + 1
    while c in occupied:
        c += 1
    return c


_LEFT_REL_HINTS = ("查看", "浏览", "查询", "阅读", "访问", "获取")
_BELOW_REL_HINTS = ("创建", "拥有", "生成", "加入", "添加", "收藏", "包含")
_RIGHT_REL_HINTS = ("发布", "提交", "发送", "推送")


def _rel_label(rel: dict) -> str:
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
    spine: List[str],
    names: List[str],
    relationships: list,
) -> Dict[str, Tuple[int, int]]:
    spine_set = set(spine)
    name_set = set(names)
    grid: Dict[str, Tuple[int, int]] = {}
    for idx, name in enumerate(spine):
        grid[name] = (idx, 0)
    placed = set(spine)

    outgoing: Dict[str, List[Tuple[str, str]]] = {}
    for rel in relationships:
        fr, to = rel["from"], rel["to"]
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
            fr, to = rel["from"], rel["to"]
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


def _find_main_chain(hub: str, names: List[str], relationships: list) -> List[str]:
    """从中心实体沿有向边延伸主链（如 用户→订单→订单详情），不拐回支线实体"""
    directed: Dict[str, List[str]] = {}
    undirected = _build_undirected_adj(relationships)
    for rel in relationships:
        directed.setdefault(rel["from"], []).append(rel["to"])

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
    off_spine: List[str],
    spine: List[str],
    relationships: list,
) -> Dict[str, Tuple[int, int]]:
    """顶行布局：商品-被评价-评价 等同排展开，避免与主链菱形重叠"""
    result: Dict[str, Tuple[int, int]] = {}
    if not off_spine:
        return result

    spine_cols = {name: idx for idx, name in enumerate(spine)}
    hub_col = spine_cols.get(spine[0], 0)
    rel_from: Dict[str, Set[str]] = {}
    rel_to: Dict[str, Set[str]] = {}
    for rel in relationships:
        rel_from.setdefault(rel["from"], set()).add(rel["to"])
        rel_to.setdefault(rel["to"], set()).add(rel["from"])

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


def arrange_entities(entities: list, relationships: list) -> dict:
    """智能排列实体：主链水平展开，支线实体按关系叠放在正上/正下方"""
    layout = ERLayout()

    if not entities:
        return layout.entities

    names = [e["name"] for e in entities]
    hub = _choose_hub(names, relationships)
    spine = _find_main_chain(hub, names, relationships)

    grid = _layout_vertical_attachments(spine, names, relationships)
    placed = set(grid.keys())

    off_spine = [n for n in names if n not in placed]
    for name, pos in _layout_top_row(off_spine, spine, relationships).items():
        if name not in grid:
            grid[name] = pos

    unplaced = [n for n in names if n not in grid]
    for entity_name in unplaced:
        max_col = max((c for c, _ in grid.values()), default=0)
        grid[entity_name] = (max_col + 1, 1)

    for name, (col, row) in grid.items():
        x, y = layout._grid_to_pos(row, col)
        layout.add_entity(name, x, y)

    return layout.entities


def generate_er_xml(data: dict) -> str:
    """根据 JSON 数据生成 draw.io XML"""
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])

    # 智能排列实体
    entity_positions = arrange_entities(entities, relationships)

    # 开始生成 XML
    xml_parts = [
        '<mxfile host="app.diagrams.net">',
        f'  <diagram name="Page-1" id="{generate_id()}">',
        '    <mxGraphModel dx="288" dy="818" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="1703" pageHeight="1169" math="0" shadow="0">',
        '      <root>',
        '        <mxCell id="0" />',
        '        <mxCell id="1" parent="0" />',
    ]

    # 绘制实体
    entity_ids = {}
    for entity in entities:
        name = entity["name"]
        if name not in entity_positions:
            continue

        pos = entity_positions[name]
        entity_id = generate_id()
        entity_ids[name] = entity_id

        xml_parts.append(f'        <mxCell id="{entity_id}" value="&lt;font style=&quot;font-size: {FONT_SIZE}px;&quot;&gt;{name}&lt;/font&gt;" style="rounded=0;whiteSpace=wrap;html=1;" vertex="1" parent="1">')
        xml_parts.append(f'          <mxGeometry x="{pos["x"]}" y="{pos["y"]}" width="{pos["width"]}" height="{pos["height"]}" as="geometry" />')
        xml_parts.append('        </mxCell>')

    # 绘制关系和连线
    diamond_occupied: List[Tuple[float, float, float, float]] = [
        (pos["x"], pos["y"], pos["width"], pos["height"])
        for pos in entity_positions.values()
    ]
    for rel in _sort_relationships_for_diamonds(relationships, entity_positions):
        from_name = rel.get("from")
        to_name = rel.get("to")
        rel_type = rel.get("type", "1:N")
        label = rel.get("label", "")

        if from_name not in entity_positions or to_name not in entity_positions:
            continue

        from_pos = entity_positions[from_name]
        to_pos = entity_positions[to_name]

        # 菱形位置：多候选评分，避免与实体/其他菱形重叠
        diamond_x, diamond_y = _find_best_diamond_position(from_pos, to_pos, diamond_occupied)
        diamond_occupied.append((diamond_x, diamond_y, DIAMOND_W, DIAMOND_H))

        # 绘制菱形（关系）
        diamond_id = generate_id()
        xml_parts.append(f'        <mxCell id="{diamond_id}" value="&lt;font style=&quot;font-size: {FONT_SIZE}px;&quot;&gt;{label}&lt;/font&gt;" style="rhombus;whiteSpace=wrap;html=1;rounded=0;" vertex="1" parent="1">')
        xml_parts.append(f'          <mxGeometry x="{diamond_x}" y="{diamond_y}" width="{DIAMOND_W}" height="{DIAMOND_H}" as="geometry" />')
        xml_parts.append('        </mxCell>')

        # 连线从菱形角点进出（水平直通 / 垂直连通 / L 形折线）
        corners = _rhombus_corners(diamond_x, diamond_y, DIAMOND_W, DIAMOND_H)
        in_idx, out_idx = _pick_connection_corners(
            diamond_x, diamond_y, DIAMOND_W, DIAMOND_H, from_pos, to_pos
        )

        line1_tx, line1_ty = corners[in_idx]
        line1_sx, line1_sy = _rect_border_toward(
            from_pos["x"], from_pos["y"], from_pos["width"], from_pos["height"],
            line1_tx, line1_ty,
        )
        line2_sx, line2_sy = corners[out_idx]
        line2_tx, line2_ty = _rect_border_toward(
            to_pos["x"], to_pos["y"], to_pos["width"], to_pos["height"],
            line2_sx, line2_sy,
        )

        line1_style = (
            "endArrow=none;html=1;rounded=0;"
            + _exit_attrs(from_pos["x"], from_pos["y"], from_pos["width"], from_pos["height"], line1_tx, line1_ty)
            + _rhombus_corner_attrs(in_idx, is_entry=True)
        )
        line2_style = (
            "endArrow=none;html=1;rounded=0;"
            + _rhombus_corner_attrs(out_idx, is_entry=False)
            + _entry_attrs(to_pos["x"], to_pos["y"], to_pos["width"], to_pos["height"], line2_sx, line2_sy)
        )

        # 连线 1
        line1_id = generate_id()
        xml_parts.append(f'        <mxCell id="{line1_id}" value="" style="{line1_style}" edge="1" parent="1" source="{entity_ids[from_name]}" target="{diamond_id}">')
        _append_edge_geometry(xml_parts, line1_sx, line1_sy, line1_tx, line1_ty)
        xml_parts.append('        </mxCell>')

        label1_text = "1" if rel_type in ["1:N", "1:1"] else "N"
        _append_edge_label(xml_parts, label1_text, line1_sx, line1_sy, line1_tx, line1_ty)

        # 连线 2
        line2_id = generate_id()
        xml_parts.append(f'        <mxCell id="{line2_id}" value="" style="{line2_style}" edge="1" parent="1" source="{diamond_id}" target="{entity_ids[to_name]}">')
        _append_edge_geometry(xml_parts, line2_sx, line2_sy, line2_tx, line2_ty)
        xml_parts.append('        </mxCell>')

        label2_text = "N" if rel_type in ["1:N", "N:M"] else "1"
        _append_edge_label(xml_parts, label2_text, line2_sx, line2_sy, line2_tx, line2_ty)

    # XML 尾部
    xml_parts.extend([
        '      </root>',
        '    </mxGraphModel>',
        '  </diagram>',
        '</mxfile>',
    ])

    return '\n'.join(xml_parts)


def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("使用方法: python er_test.py input.json output.xml")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # 读取 JSON
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 生成 XML
    xml_content = generate_er_xml(data)

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print(f"[OK] 已生成 ER 图: {output_file}")
    print(f"   - 实体数量: {len(data.get('entities', []))}")
    print(f"   - 关系数量: {len(data.get('relationships', []))}")


if __name__ == "__main__":
    main()
