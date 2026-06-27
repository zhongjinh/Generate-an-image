# -*- coding: utf-8 -*-
"""
根据 MySQL 风格建表 SQL，重写 draw.io / diagrams.net 属性图 XML（mxGraphModel）。

用法:
  python sql_to_attr_diagram.py --sql 1.sql --xml 属性图.xml
  python sql_to_attr_diagram.py --sql my.sql --xml 属性图.xml --out 新图.xml

说明:
  - 表数量与 CREATE TABLE 数量一致：SQL 里几个表就生成几个实体属性图（可多于或少于原 XML）。
  - 实体显示名优先用表尾 COMMENT='...'；自动去掉末尾的「表」字（如「用户表」→「用户」）。
  - 属性显示名用列上的 COMMENT；若列无 COMMENT 则用列名；同样去掉末尾「表」。
  - 含 PRIMARY KEY 的列在图中以下划线表示主键。
"""

from __future__ import annotations

import argparse
import html
import io
import math
import re
import sys
import uuid
from pathlib import Path
from typing import List, Optional, Tuple
from xml.etree import ElementTree as ET


def strip_trailing_biao(text: str) -> str:
    """去掉注释末尾的「表」字（可多次），用于实体/属性展示。"""
    if not text:
        return text
    s = text.strip()
    while s.endswith("表") and len(s) > 0:
        s = s[:-1].strip()
    return s or text.strip()


def escape_drawio_label(text: str, underline: bool = False) -> str:
    """生成 draw.io mxCell value 里 &lt;font&gt;... 的内层 HTML（已 XML 转义）。"""
    inner = html.escape(text, quote=False)
    if underline:
        inner = f"&lt;u&gt;{inner}&lt;/u&gt;"
    return (
        f"&lt;font style=&quot;font-size: 18px;&quot;&gt;{inner}&lt;/font&gt;"
    )


def _snap_rect_exit(ex: float, ey: float, eps: float = 1e-6) -> Tuple[float, float]:
    """将落在矩形四条边附近的相对坐标贴到 0/1，避免浮点误差；不得向内偏移。"""
    if ex < eps:
        ex = 0.0
    elif ex > 1.0 - eps:
        ex = 1.0
    if ey < eps:
        ey = 0.0
    elif ey > 1.0 - eps:
        ey = 1.0
    return ex, ey


def _clip01_eps(v: float, eps: float = 1e-6) -> float:
    """仅防止越出 [0,1]，不把点拉进图形内部。"""
    return max(eps, min(1.0 - eps, v))


def entity_exit_on_perimeter(
    cx: float, cy: float, ew: float, eh: float, target_x: float, target_y: float
) -> Tuple[float, float, float, float]:
    """
    从实体矩形指向目标的方向与矩形边界的交点。
    返回 (exitX, exitY, abs_x, abs_y)，后两者为画布上的端点，落在矩形边上。
    """
    ecx, ecy = cx + ew / 2.0, cy + eh / 2.0
    dx, dy = target_x - ecx, target_y - ecy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        sx, sy = cx + ew / 2.0, cy
        return 0.5, 0.0, sx, sy
    candidates: List[Tuple[float, float, float]] = []  # (t, hit_x, hit_y)
    if dx > 1e-12:
        t = (cx + ew - ecx) / dx
        if t > 0:
            hy = ecy + t * dy
            if cy - 1e-6 <= hy <= cy + eh + 1e-6:
                candidates.append((t, cx + ew, hy))
    if dx < -1e-12:
        t = (cx - ecx) / dx
        if t > 0:
            hy = ecy + t * dy
            if cy - 1e-6 <= hy <= cy + eh + 1e-6:
                candidates.append((t, cx, hy))
    if dy > 1e-12:
        t = (cy + eh - ecy) / dy
        if t > 0:
            hx = ecx + t * dx
            if cx - 1e-6 <= hx <= cx + ew + 1e-6:
                candidates.append((t, hx, cy + eh))
    if dy < -1e-12:
        t = (cy - ecy) / dy
        if t > 0:
            hx = ecx + t * dx
            if cx - 1e-6 <= hx <= cx + ew + 1e-6:
                candidates.append((t, hx, cy))
    if not candidates:
        sx, sy = cx + ew / 2.0, cy
        return 0.5, 0.0, sx, sy
    _t, hx, hy = min(candidates, key=lambda c: c[0])
    ex = (hx - cx) / ew
    ey = (hy - cy) / eh
    ex, ey = _snap_rect_exit(ex, ey)
    sx = cx + ex * ew
    sy = cy + ey * eh
    return ex, ey, sx, sy


def ellipse_entry_on_perimeter(
    ax: float,
    ay: float,
    aw: float,
    ah: float,
    toward_x: float,
    toward_y: float,
    spread_index: int,
    n_attrs: int,
) -> Tuple[float, float, float, float]:
    """
    在椭圆上取朝向实体的一侧的锚点。
    返回 (entryX, entryY, abs_x, abs_y)，后两者为画布上的端点，落在椭圆周上。
    """
    acx, acy = ax + aw / 2.0, ay + ah / 2.0
    vx, vy = toward_x - acx, toward_y - acy
    ln = math.hypot(vx, vy)
    if ln < 1e-9:
        acxb = ax + aw / 2.0
        syb = ay + ah
        return 0.5, 1.0, acxb, syb
    ux, uy = vx / ln, vy / ln
    if n_attrs > 1:
        max_rot = min(0.45, 0.55 * math.pi / float(n_attrs))
        span = (n_attrs - 1) / 2.0
        rot = max_rot * ((spread_index - span) / span if span > 1e-9 else 0.0)
    else:
        rot = 0.0
    c, s = math.cos(rot), math.sin(rot)
    rx = ux * c - uy * s
    ry = ux * s + uy * c
    a = aw / 2.0
    b = ah / 2.0
    denom = math.sqrt((rx / a) ** 2 + (ry / b) ** 2)
    if denom < 1e-12:
        acxb = ax + aw / 2.0
        syb = ay + ah
        return 0.5, 1.0, acxb, syb
    t = 1.0 / denom
    hx = acx + t * rx
    hy = acy + t * ry
    ix = (hx - ax) / aw
    iy = (hy - ay) / ah
    return _clip01_eps(ix), _clip01_eps(iy), hx, hy


def remove_sql_line_comments(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def parse_create_tables(sql: str) -> List[dict]:
    """
    解析多个 CREATE TABLE ... ; 返回
    [{"name": str, "table_comment": str, "columns": [(col, comment, is_pk), ...]}]
    """
    sql = remove_sql_line_comments(sql)
    tables: List[dict] = []
    pos = 0
    while pos < len(sql):
        m = re.search(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\(",
            sql[pos:],
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            break
        table_name = m.group(1)
        # m.end() 相对于本次搜索片段 sql[pos:]，表体内第一个字符下标为 pos + m.end()
        abs_after_open = pos + m.end()
        depth = 1
        j = abs_after_open
        while j < len(sql) and depth:
            c = sql[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            j += 1
        body = sql[abs_after_open : j - 1]
        tail = sql[j : min(j + 400, len(sql))]
        tcm = re.search(
            r"COMMENT\s*=\s*['\"]([^'\"]*)['\"]", tail, re.IGNORECASE
        )
        table_comment = tcm.group(1).strip() if tcm else ""

        columns: List[Tuple[str, str, bool]] = []
        for raw_line in body.splitlines():
            line = raw_line.strip().rstrip(",")
            if not line:
                continue
            up = line.upper()
            if up.startswith(("PRIMARY KEY", "KEY ", "UNIQUE ", "CONSTRAINT", "FOREIGN", "INDEX ", "FULLTEXT", "SPATIAL")):
                continue
            col_m = re.match(r"^`?(\w+)`?\s+", line)
            if not col_m:
                continue
            colname = col_m.group(1)
            is_pk = bool(re.search(r"\bPRIMARY\s+KEY\b", line, re.IGNORECASE))
            cm = re.search(r"COMMENT\s+'([^']*)'", line) or re.search(
                r'COMMENT\s*"([^"]*)"', line
            )
            col_comment = (cm.group(1).strip() if cm else colname)
            columns.append((colname, col_comment, is_pk))

        tables.append(
            {
                "name": table_name,
                "table_comment": table_comment,
                "columns": columns,
            }
        )
        pos = j
    return tables


def entity_display_name(table: dict) -> str:
    base = table["table_comment"] or table["name"]
    return strip_trailing_biao(base)


def attribute_display_name(_col: str, comment: str) -> str:
    return strip_trailing_biao(comment or _col)


def layout_tables(
    tables: List[dict],
    cols: int = 3,
    cell_margin: int = 40,
    min_cell_w: int = 420,
    min_cell_h: int = 420,
) -> List[Tuple[float, float, float, float]]:
    """
    为每个表返回 (origin_x, origin_y, cell_w, cell_h)，在网格中放置。
    """
    layouts: List[Tuple[float, float, float, float]] = []
    ncols = max(1, min(cols, len(tables) or 1))
    n = len(tables)
    max_attrs = max((len(t["columns"]) for t in tables), default=0)
    R = max(130.0, 22.0 * max(1, max_attrs))
    cell_w = max(min_cell_w, int(2 * R + 200))
    cell_h = max(min_cell_h, int(2 * R + 200))
    for idx in range(n):
        col = idx % ncols
        row = idx // ncols
        ox = cell_margin + col * (cell_w + cell_margin)
        oy = cell_margin + row * (cell_h + cell_margin)
        layouts.append((float(ox), float(oy), float(cell_w), float(cell_h)))
    return layouts


def build_mxcells_for_table(
    table_idx: int,
    table: dict,
    ox: float,
    oy: float,
    cell_w: float,
    cell_h: float,
    id_prefix: str,
) -> str:
    """生成单个实体属性图的所有 mxCell XML 片段（字符串）。"""
    EW, EH = 120.0, 60.0
    AW, AH = 120.0, 60.0
    cx = ox + (cell_w - EW) / 2.0
    cy = oy + (cell_h - EH) / 2.0
    cols = table["columns"]
    n = len(cols)
    R = max(130.0, 22.0 * max(1, n))

    ent_id = f"{id_prefix}-t{table_idx}-ent"
    lines: List[str] = []

    ent_label = entity_display_name(table)
    lines.append(
        f'        <mxCell id="{ent_id}" parent="1" style="rounded=0;whiteSpace=wrap;html=1;" '
        f'value="{escape_drawio_label(ent_label)}" vertex="1">\n'
        f'          <mxGeometry height="{int(EH)}" width="{int(EW)}" x="{int(cx)}" y="{int(cy)}" as="geometry" />\n'
        f"        </mxCell>"
    )

    for j, (colname, comment, is_pk) in enumerate(cols):
        attr_label = attribute_display_name(colname, comment)
        angle = 2 * math.pi * (j / max(n, 1)) - math.pi / 2
        ax = cx + EW / 2 - AW / 2 + R * math.cos(angle)
        ay = cy + EH / 2 - AH / 2 + R * math.sin(angle)
        aid = f"{id_prefix}-t{table_idx}-a{j}"
        lines.append(
            f'        <mxCell id="{aid}" parent="1" style="ellipse;whiteSpace=wrap;html=1;" '
            f'value="{escape_drawio_label(attr_label, underline=is_pk)}" vertex="1">\n'
            f'          <mxGeometry height="{int(AH)}" width="{int(AW)}" x="{int(ax)}" y="{int(ay)}" as="geometry" />\n'
            f"        </mxCell>"
        )
        acx, acy = ax + AW / 2.0, ay + AH / 2.0
        ecx, ecy = cx + EW / 2.0, cy + EH / 2.0
        ex, ey, sx, sy = entity_exit_on_perimeter(cx, cy, EW, EH, acx, acy)
        ix, iy, tx, ty = ellipse_entry_on_perimeter(ax, ay, AW, AH, ecx, ecy, j, n)
        eid = f"{id_prefix}-t{table_idx}-e{j}"
        edge_style = (
            f"endArrow=none;html=1;rounded=0;orthogonalEdgeStyle=0;curved=0;"
            f"jettySize=0;orthogonalLoop=0;"
            f"exitX={ex:.4f};exitY={ey:.4f};exitDx=0;exitDy=0;exitPerimeter=1;"
            f"entryX={ix:.4f};entryY={iy:.4f};entryDx=0;entryDy=0;entryPerimeter=1;"
        )
        lines.append(
            f'        <mxCell id="{eid}" edge="1" parent="1" source="{ent_id}" target="{aid}" '
            f'style="{edge_style}" value="">\n'
            f'          <mxGeometry relative="1" width="1" height="1" as="geometry">\n'
            f'            <mxPoint x="{sx:.2f}" y="{sy:.2f}" as="sourcePoint"/>\n'
            f'            <mxPoint x="{tx:.2f}" y="{ty:.2f}" as="targetPoint"/>\n'
            f"          </mxGeometry>\n"
            f"        </mxCell>"
        )

    return "\n".join(lines)


def rebuild_diagram_xml(
    template_path: Path,
    tables: List[dict],
    grid_cols: int,
) -> str:
    tree = ET.parse(template_path)
    root_el = tree.getroot()
    diagram = root_el.find("diagram")
    if diagram is None:
        raise SystemExit("XML 中未找到 <diagram> 节点")
    gmodel = diagram.find("mxGraphModel")
    if gmodel is None:
        raise SystemExit("XML 中未找到 <mxGraphModel> 节点")
    mx_root = gmodel.find("root")
    if mx_root is None:
        raise SystemExit("XML 中未找到 <root> 节点")

    for child in list(mx_root):
        mx_root.remove(child)

    c0 = ET.SubElement(mx_root, "mxCell", {"id": "0"})
    c1 = ET.SubElement(mx_root, "mxCell", {"id": "1", "parent": "0"})

    id_prefix = "sqlattr-" + uuid.uuid4().hex[:8]
    layouts = layout_tables(tables, cols=grid_cols)
    body_parts: List[str] = []
    for idx, table in enumerate(tables):
        ox, oy, cw, ch = layouts[idx]
        body_parts.append(
            build_mxcells_for_table(idx, table, ox, oy, cw, ch, id_prefix)
        )

    # 将新生成的顶点/边以文本形式插入（避免 ET 对 &lt; 再转义）
    tail_xml = "\n".join(body_parts)
    wrapped = f"<wrap>\n{tail_xml}\n</wrap>"
    frag = ET.fromstring(wrapped)
    for node in list(frag):
        mx_root.append(node)

    ET.register_namespace("", "")
    buf = io.BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    text = buf.getvalue().decode("utf-8")
    # ElementTree 默认 ns0: 替换回无前缀（与原文件一致）
    text = text.replace("ns0:", "").replace(" xmlns:ns0=\"http://www.w3.org/1999/xhtml\"", "")
    if text.startswith("<?xml"):
        nl = text.find("\n")
        text = text[nl + 1 :] if nl != -1 else text
    return text


def mxfile_xml_string_from_sql(
    sql: str,
    template_path: Path,
    *,
    grid_cols: int = 3,
) -> str:
    """
    从建表 SQL 字符串生成完整 mxfile XML 文本（无 XML 声明，与 rebuild_diagram_xml 一致）。
    用于多页合并脚本：解析出 <diagram> 再并入总 mxfile。
    """
    tables = parse_create_tables(sql)
    if not tables:
        raise ValueError("未解析到任何 CREATE TABLE，请检查 SQL。")
    return rebuild_diagram_xml(template_path, tables, grid_cols=grid_cols)


def main() -> None:
    ap = argparse.ArgumentParser(description="用建表 SQL 重写属性图 XML")
    ap.add_argument("--sql", required=True, help="建表 SQL 文件路径")
    ap.add_argument("--xml", required=True, help="模板 / 待替换的 draw.io XML")
    ap.add_argument("--out", default="", help="输出路径（默认同 --xml，即覆盖）")
    ap.add_argument(
        "--cols",
        type=int,
        default=3,
        help="属性图网格列数（行数随表数量自适应）",
    )
    args = ap.parse_args()

    sql_path = Path(args.sql)
    xml_path = Path(args.xml)
    out_path = Path(args.out) if args.out else xml_path

    if not sql_path.is_file():
        print(f"找不到 SQL: {sql_path}", file=sys.stderr)
        sys.exit(1)
    if not xml_path.is_file():
        print(f"找不到 XML: {xml_path}", file=sys.stderr)
        sys.exit(1)

    sql_text = sql_path.read_text(encoding="utf-8", errors="replace")
    tables = parse_create_tables(sql_text)
    if not tables:
        print("未解析到任何 CREATE TABLE，请检查 SQL 语法。", file=sys.stderr)
        sys.exit(2)

    new_xml = rebuild_diagram_xml(xml_path, tables, grid_cols=args.cols)
    new_xml = new_xml.replace("/><mxCell", "/>\n        <mxCell")
    out_path.write_text(new_xml, encoding="utf-8")
    print(f"已写入 {out_path.resolve()} ，共 {len(tables)} 个实体属性图。")


if __name__ == "__main__":
    main()
