#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Template-based class diagram replacer for draw.io XML."""


import argparse
import io
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

TEXT_STYLE_FALLBACK = (
    "text;strokeColor=none;fillColor=none;align=left;verticalAlign=top;spacingLeft=4;"
    "spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;"
)
DIVIDER_STYLE_FALLBACK = (
    "line;strokeWidth=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;"
    "spacingLeft=3;spacingRight=3;rotatable=0;labelPosition=right;points=[];"
    "portConstraint=eastwest;strokeColor=inherit;"
)
MULT_STYLE = (
    "text;html=1;whiteSpace=wrap;strokeColor=none;fillColor=none;align=center;"
    "verticalAlign=middle;rounded=0;"
)
EDGE_STYLE_FALLBACK = "edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;rounded=0;"


def _new_id() -> str:
    return f"id-{uuid.uuid4().hex[:16]}"


def _to_s(v: float | int | str) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, int):
        return str(v)
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _norm_mult(v: Any) -> str:
    s = str(v).strip()
    if not s:
        return ""
    low = s.lower()
    if s == "*" or low in {"many", "n"}:
        return "N"
    if low == "m":
        return "M"
    return s


def _geom(cell: ET.Element, attrs: dict[str, str]) -> ET.Element:
    a = dict(attrs)
    a["as"] = "geometry"
    return ET.SubElement(cell, "mxGeometry", a)


def _rect_border_toward(x: float, y: float, w: float, h: float, tx: float, ty: float) -> tuple[float, float]:
    cx = x + w / 2.0
    cy = y + h / 2.0
    dx = tx - cx
    dy = ty - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return cx, cy
    sx = (w / 2.0) / abs(dx) if abs(dx) > 1e-9 else float("inf")
    sy = (h / 2.0) / abs(dy) if abs(dy) > 1e-9 else float("inf")
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def _y_of(c: ET.Element) -> float:
    g = c.find("mxGeometry")
    if g is None:
        return 0.0
    try:
        return float(g.get("y", "0") or 0.0)
    except ValueError:
        return 0.0


def _cell_center(c: ET.Element) -> tuple[float, float]:
    g = c.find("mxGeometry")
    if g is None:
        return 0.0, 0.0
    x = float(g.get("x", "0") or 0.0)
    y = float(g.get("y", "0") or 0.0)
    w = float(g.get("width", "60") or 60.0)
    h = float(g.get("height", "30") or 30.0)
    return x + w / 2.0, y + h / 2.0


def _load_cfg(path_or_stdin: str | None) -> dict[str, Any]:
    if path_or_stdin in (None, "-"):
        raw = sys.stdin.read()
    else:
        raw = Path(path_or_stdin).read_text(encoding="utf-8-sig")
    return json.loads(raw)


def _class_updates(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """支持单类与多类两种输入：
    - class: {...}
    - classes: [{...}, ...]
    """
    updates: list[dict[str, Any]] = []
    one = cfg.get("class")
    if isinstance(one, dict):
        updates.append(one)
    many = cfg.get("classes")
    if isinstance(many, list):
        updates.extend([x for x in many if isinstance(x, dict)])
    return updates


def _resolve_template_class_name(old: str, class_blocks: dict[str, dict[str, Any]]) -> str | None:
    if old in class_blocks:
        return old
    key = old.strip().lower()
    if not key:
        return None
    # exact case-insensitive
    for name in class_blocks.keys():
        if name.lower() == key:
            return name
    # fuzzy contains
    for name in class_blocks.keys():
        n = name.lower()
        if key in n or n in key:
            return name
    return None


def build_from_template(cfg: dict[str, Any]) -> ET.ElementTree:
    tpl = cfg.get("template_xml") or cfg.get("template") or "类图.xml"
    tpl_path = Path(str(tpl))
    if not tpl_path.exists():
        raise SystemExit(f"错误: template_xml 不存在: {tpl_path}")

    root_el = ET.parse(tpl_path).getroot()
    mx_root = root_el.find(".//mxGraphModel/root")
    if mx_root is None:
        raise SystemExit("错误: 模板 XML 中找不到 mxGraphModel/root")

    class_blocks: dict[str, dict[str, Any]] = {}
    children_by_parent: dict[str, list[ET.Element]] = {}

    for cell in mx_root.findall("mxCell"):
        p = cell.get("parent")
        if p:
            children_by_parent.setdefault(p, []).append(cell)

    for cell in mx_root.findall("mxCell"):
        style = cell.get("style", "") or ""
        if not style.startswith("swimlane;"):
            continue
        cid = cell.get("id")
        if not cid:
            continue
        name = (cell.get("value") or "").strip()
        g = cell.find("mxGeometry")
        x = float(g.get("x", "0") or 0.0) if g is not None else 0.0
        y = float(g.get("y", "0") or 0.0) if g is not None else 0.0
        w = float(g.get("width", "0") or 0.0) if g is not None else 0.0
        h = float(g.get("height", "0") or 0.0) if g is not None else 0.0
        class_blocks[name] = {
            "class_id": cid,
            "cell": cell,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "attr_ids": [],
            "method_ids": [],
            "text_style": TEXT_STYLE_FALLBACK,
            "divider_style": DIVIDER_STYLE_FALLBACK,
            "swimlane_style": style,
        }

    prototype_swimlane_style = next(
        (
            info["swimlane_style"]
            for info in class_blocks.values()
            if str(info.get("swimlane_style", "")).startswith("swimlane;")
        ),
        "swimlane;fontStyle=0;align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize=32;"
        "horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=0;marginBottom=0;"
        "fillColor=light-dark(#eeeeee,#1f2020);strokeColor=light-dark(#999999,#cccccc);fontColor=light-dark(#333333,#cccccc);",
    )

    for name, info in class_blocks.items():
        cid = info["class_id"]
        children = list(children_by_parent.get(cid, []))
        children.sort(key=_y_of)
        seen_div = False
        for ch in children:
            st = ch.get("style", "") or ""
            if st.startswith("line;strokeWidth=1;"):
                seen_div = True
                info["divider_style"] = st
                continue
            if not st.startswith("text;"):
                continue
            info["text_style"] = st
            if seen_div:
                info["method_ids"].append(ch.get("id"))
            else:
                info["attr_ids"].append(ch.get("id"))

    class_id_to_new_name: dict[str, str] = {}
    missing_updates: list[dict[str, Any]] = []
    for c in _class_updates(cfg):
        old = str(c.get("old_name") or c.get("template_name") or c.get("name") or "").strip()
        new = str(c.get("new_name") or c.get("name") or "").strip()
        if not old:
            continue
        resolved_old = _resolve_template_class_name(old, class_blocks)
        if not resolved_old:
            missing_updates.append(c)
            continue

        blk = class_blocks[resolved_old]
        cell_cls: ET.Element = blk["cell"]
        cell_cls.set("value", new)
        class_id_to_new_name[blk["class_id"]] = new

        attrs = [str(x) for x in (c.get("attributes") or [])]
        methods = [str(x) for x in (c.get("methods") or [])]

        style_cls = cell_cls.get("style", "") or ""
        m_start = re.search(r"startSize=([0-9]+(?:\\.[0-9]+)?)", style_cls)
        start = float(m_start.group(1)) if m_start else 32.0
        row_h = 32.0
        if blk["attr_ids"]:
            first_attr = next((x for x in mx_root.findall("mxCell") if x.get("id") == blk["attr_ids"][0]), None)
            if first_attr is not None:
                g = first_attr.find("mxGeometry")
                if g is not None:
                    try:
                        row_h = float(g.get("height", "32") or 32.0)
                    except ValueError:
                        row_h = 32.0

        for ch in list(children_by_parent.get(blk["class_id"], [])):
            st = ch.get("style", "") or ""
            if st.startswith("text;") or st.startswith("line;strokeWidth=1;"):
                mx_root.remove(ch)

        yy = start
        for v in attrs:
            r = ET.SubElement(
                mx_root,
                "mxCell",
                {
                    "id": _new_id(),
                    "parent": blk["class_id"],
                    "style": blk["text_style"],
                    "value": v,
                    "vertex": "1",
                },
            )
            _geom(r, {"y": _to_s(yy), "width": _to_s(blk["w"]), "height": _to_s(row_h)})
            yy += row_h

        d = ET.SubElement(
            mx_root,
            "mxCell",
            {
                "id": _new_id(),
                "parent": blk["class_id"],
                "style": blk["divider_style"],
                "vertex": "1",
            },
        )
        _geom(d, {"y": _to_s(yy), "width": _to_s(blk["w"]), "height": "8"})
        yy += 8.0

        for v in methods:
            r = ET.SubElement(
                mx_root,
                "mxCell",
                {
                    "id": _new_id(),
                    "parent": blk["class_id"],
                    "style": blk["text_style"],
                    "value": v,
                    "vertex": "1",
                },
            )
            _geom(r, {"y": _to_s(yy), "width": _to_s(blk["w"]), "height": _to_s(row_h)})
            yy += row_h

        g_cls = cell_cls.find("mxGeometry")
        if g_cls is not None:
            g_cls.set("height", _to_s(yy))
            blk["h"] = yy

    # 对模板中不存在的类，按模板风格新增类块，避免被跳过。
    if missing_updates:
        sample_w = next((float(v.get("w", 272.0)) for v in class_blocks.values()), 272.0)
        row_h = 32.0
        start_size = 32.0
        if class_blocks:
            first = next(iter(class_blocks.values()))
            first_cell = first.get("cell")
            if isinstance(first_cell, ET.Element):
                st = first_cell.get("style", "") or ""
                m_start = re.search(r"startSize=([0-9]+(?:\\.[0-9]+)?)", st)
                if m_start:
                    start_size = float(m_start.group(1))
            if first.get("attr_ids"):
                attr0 = next((x for x in mx_root.findall("mxCell") if x.get("id") == first["attr_ids"][0]), None)
                if attr0 is not None:
                    g0 = attr0.find("mxGeometry")
                    if g0 is not None:
                        row_h = float(g0.get("height", "32") or 32.0)

        xs = [float(info.get("x", 0.0)) for info in class_blocks.values()] or [0.0]
        ys = [float(info.get("y", 0.0)) for info in class_blocks.values()] or [0.0]
        hs = [float(info.get("h", 0.0)) for info in class_blocks.values()] or [0.0]
        min_x = min(xs)
        max_y = max(y + h for y, h in zip(ys, hs))
        col_gap = 72.0
        row_gap = 72.0
        cols = 4

        created = 0
        for c in missing_updates:
            new_name = str(c.get("new_name") or c.get("name") or c.get("template_name") or "").strip()
            if not new_name or new_name in class_blocks:
                continue
            attrs = [str(x) for x in (c.get("attributes") or [])]
            methods = [str(x) for x in (c.get("methods") or [])]
            total_h = start_size + (len(attrs) + len(methods)) * row_h + 8.0

            col = created % cols
            row = created // cols
            x = min_x + col * (sample_w + col_gap)
            y = max_y + row_gap + row * (total_h + row_gap)
            created += 1

            cls_id = _new_id()
            cls_cell = ET.SubElement(
                mx_root,
                "mxCell",
                {
                    "id": cls_id,
                    "parent": "1",
                    "style": prototype_swimlane_style,
                    "value": new_name,
                    "vertex": "1",
                },
            )
            _geom(cls_cell, {"x": _to_s(x), "y": _to_s(y), "width": _to_s(sample_w), "height": _to_s(total_h)})

            yy = start_size
            for v in attrs:
                r = ET.SubElement(
                    mx_root,
                    "mxCell",
                    {"id": _new_id(), "parent": cls_id, "style": TEXT_STYLE_FALLBACK, "value": v, "vertex": "1"},
                )
                _geom(r, {"y": _to_s(yy), "width": _to_s(sample_w), "height": _to_s(row_h)})
                yy += row_h
            d = ET.SubElement(
                mx_root,
                "mxCell",
                {"id": _new_id(), "parent": cls_id, "style": DIVIDER_STYLE_FALLBACK, "vertex": "1"},
            )
            _geom(d, {"y": _to_s(yy), "width": _to_s(sample_w), "height": "8"})
            yy += 8.0
            for v in methods:
                r = ET.SubElement(
                    mx_root,
                    "mxCell",
                    {"id": _new_id(), "parent": cls_id, "style": TEXT_STYLE_FALLBACK, "value": v, "vertex": "1"},
                )
                _geom(r, {"y": _to_s(yy), "width": _to_s(sample_w), "height": _to_s(row_h)})
                yy += row_h

            class_blocks[new_name] = {
                "class_id": cls_id,
                "cell": cls_cell,
                "x": x,
                "y": y,
                "w": sample_w,
                "h": yy,
                "attr_ids": [],
                "method_ids": [],
                "text_style": TEXT_STYLE_FALLBACK,
                "divider_style": DIVIDER_STYLE_FALLBACK,
                "swimlane_style": prototype_swimlane_style,
            }
            class_id_to_new_name[cls_id] = new_name

    mult_cells = []
    for c in mx_root.findall("mxCell"):
        st = c.get("style", "") or ""
        if not st.startswith("text;html=1;whiteSpace=wrap;"):
            continue
        val = (c.get("value") or "").strip().upper()
        if val in {"1", "N", "M", "*"}:
            mult_cells.append(c)

    used_mult_ids: set[str] = set()

    name_to_cid = {n: b["class_id"] for n, b in class_blocks.items()}
    for cid, new_name in class_id_to_new_name.items():
        name_to_cid[new_name] = cid

    def upsert_mult(value: str, px: float, py: float) -> None:
        best_cell = None
        best_d2 = None
        for c in mult_cells:
            cid = c.get("id") or ""
            if cid in used_mult_ids:
                continue
            cx, cy = _cell_center(c)
            d2 = (cx - px) ** 2 + (cy - py) ** 2
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best_cell = c

        if best_cell is None or (best_d2 is not None and best_d2 > 220.0 * 220.0):
            best_cell = ET.SubElement(
                mx_root,
                "mxCell",
                {
                    "id": _new_id(),
                    "parent": "1",
                    "style": MULT_STYLE,
                    "value": value,
                    "vertex": "1",
                },
            )
            _geom(best_cell, {"x": _to_s(px - 30), "y": _to_s(py - 15), "width": "60", "height": "30"})
            mult_cells.append(best_cell)
        else:
            best_cell.set("value", value)
            g = best_cell.find("mxGeometry")
            if g is None:
                g = _geom(best_cell, {})
            g.set("x", _to_s(px - 30))
            g.set("y", _to_s(py - 15))
            g.set("width", "60")
            g.set("height", "30")

        used_mult_ids.add(best_cell.get("id") or "")

    for rel in cfg.get("relations", []) or []:
        fn = str(rel.get("from") or "").strip()
        tn = str(rel.get("to") or "").strip()
        if not fn or not tn:
            continue
        src_id = name_to_cid.get(fn)
        dst_id = name_to_cid.get(tn)
        if not src_id or not dst_id:
            continue

        edge = None
        for e in mx_root.findall("mxCell"):
            if e.get("edge") == "1" and e.get("source") == src_id and e.get("target") == dst_id:
                edge = e
                break
        if edge is None:
            edge = ET.SubElement(
                mx_root,
                "mxCell",
                {
                    "id": _new_id(),
                    "edge": "1",
                    "parent": "1",
                    "source": src_id,
                    "target": dst_id,
                    "style": EDGE_STYLE_FALLBACK,
                    "value": "",
                },
            )
            _geom(edge, {"relative": "1", "width": "50", "height": "50"})

        src_blk = next((b for b in class_blocks.values() if b["class_id"] == src_id), None)
        dst_blk = next((b for b in class_blocks.values() if b["class_id"] == dst_id), None)
        if src_blk is None or dst_blk is None:
            continue

        sx, sy, sw, sh = src_blk["x"], src_blk["y"], src_blk["w"], src_blk["h"]
        tx, ty, tw, th = dst_blk["x"], dst_blk["y"], dst_blk["w"], dst_blk["h"]
        src_center = (sx + sw / 2.0, sy + sh / 2.0)
        dst_center = (tx + tw / 2.0, ty + th / 2.0)

        waypoints: list[tuple[float, float]] = []
        g = edge.find("mxGeometry")
        if g is not None:
            arr = g.find("Array")
            if arr is not None:
                for p in arr.findall("mxPoint"):
                    try:
                        px = float(p.get("x", "0") or 0.0)
                        py = float(p.get("y", "0") or 0.0)
                        waypoints.append((px, py))
                    except ValueError:
                        pass
        if not waypoints:
            sx, sy, sw, sh = src_blk["x"], src_blk["y"], src_blk["w"], src_blk["h"]
            tx, ty, tw, th = dst_blk["x"], dst_blk["y"], dst_blk["w"], dst_blk["h"]
            scx, scy = sx + sw / 2.0, sy + sh / 2.0
            tcx, tcy = tx + tw / 2.0, ty + th / 2.0
            if abs(scx - tcx) > abs(scy - tcy):
                midx = (scx + tcx) / 2.0
                waypoints = [(midx, scy), (midx, tcy)]
            else:
                midy = (scy + tcy) / 2.0
                waypoints = [(scx, midy), (tcx, midy)]

            if g is None:
                g = _geom(edge, {"relative": "1", "width": "50", "height": "50"})
            arr = g.find("Array")
            if arr is not None:
                g.remove(arr)
            arr = ET.SubElement(g, "Array", {"as": "points"})
            for px, py in waypoints:
                ET.SubElement(arr, "mxPoint", {"x": _to_s(px), "y": _to_s(py)})

        toward_s = waypoints[0] if waypoints else dst_center
        toward_t = waypoints[-1] if waypoints else src_center
        spx, spy = _rect_border_toward(sx, sy, sw, sh, toward_s[0], toward_s[1])
        tpx, tpy = _rect_border_toward(tx, ty, tw, th, toward_t[0], toward_t[1])

        fm = _norm_mult(rel.get("from_multiplicity", ""))
        tm = _norm_mult(rel.get("to_multiplicity", ""))
        if fm:
            upsert_mult(fm, spx, spy)
        if tm:
            upsert_mult(tm, tpx, tpy)

    return ET.ElementTree(root_el)


def main() -> int:
    ap = argparse.ArgumentParser(description="按模板复刻类图（替换类名/属性/方法/多重度）")
    ap.add_argument("input", nargs="?", default=None, help="JSON 文件路径，或 - 表示 stdin")
    ap.add_argument("-o", "--output", type=Path, help="输出 XML 文件路径")
    args = ap.parse_args()

    cfg = _load_cfg(args.input)
    tree = build_from_template(cfg)
    try:
        ET.indent(tree.getroot(), space="  ")
    except AttributeError:
        pass

    if args.output:
        tree.write(args.output, encoding="utf-8", xml_declaration=False)
        print(f"已写入: {args.output}", file=sys.stderr)
    else:
        buf = io.StringIO()
        tree.write(buf, encoding="unicode", xml_declaration=False)
        sys.stdout.write(buf.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


