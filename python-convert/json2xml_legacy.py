#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON → draw.io XML 转换引擎
支持 8 种图表类型：功能模块图、用例图、ER图、属性图、类图、活动图、架构图、序列图
"""

from __future__ import annotations
import html
import json
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _esc(text: str) -> str:
    return html.escape(str(text))


def _font(text: str, size: int = 24) -> str:
    return f'<font style="font-size: {size}px;">{_esc(text)}</font>'


def _id() -> str:
    return f"id-{uuid.uuid4().hex[:12]}"


def _cell(parent, cid, *, vertex=False, edge=False, style="", value="", source=None, target=None, x=0, y=0, w=0, h=0):
    att = {"id": cid, "parent": "1"}
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
    c = ET.SubElement(parent, "mxCell", att)
    if not edge and (w or h):
        g = ET.SubElement(c, "mxGeometry", {"x": str(x), "y": str(y), "width": str(w), "height": str(h)})
        g.set("as", "geometry")
    elif edge:
        g = ET.SubElement(c, "mxGeometry", {"relative": "1"})
        g.set("as", "geometry")
    return c


def _edge(parent, cid, x1, y1, x2, y2, style="endArrow=none;html=1;rounded=0;"):
    c = _cell(parent, cid, edge=True, style=style)
    g = c.find("mxGeometry")
    sp = ET.SubElement(g, "mxPoint", {"x": str(x1), "y": str(y1), "as": "sourcePoint"})
    tp = ET.SubElement(g, "mxPoint", {"x": str(x2), "y": str(y2), "as": "targetPoint"})
    return c


def _edge_from(parent, cid, source, x1, y1, x2, y2, style="endArrow=none;html=1;rounded=0;exitX=0.5;exitY=0;exitDx=0;exitDy=0;"):
    c = _cell(parent, cid, edge=True, style=style, source=source)
    g = c.find("mxGeometry")
    ET.SubElement(g, "mxPoint", {"x": str(x1), "y": str(y1), "as": "sourcePoint"})
    ET.SubElement(g, "mxPoint", {"x": str(x2), "y": str(y2), "as": "targetPoint"})
    return c


def _wrap_xml(root, page_w=1200, page_h=800):
    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net"})
    diag = ET.SubElement(mxfile, "diagram", {"name": "Page-1", "id": _id()})
    gm = ET.SubElement(diag, "mxGraphModel", {
        "dx": "2168", "dy": "1371", "grid": "1", "gridSize": "10",
        "guides": "1", "tooltips": "1", "connect": "1", "arrows": "1",
        "fold": "1", "page": "0", "pageScale": "1",
        "pageWidth": str(page_w), "pageHeight": str(page_h),
        "math": "0", "shadow": "0"
    })
    gm.append(root)
    return ET.tostring(mxfile, encoding="unicode", xml_declaration=True)


# ==================== 1. 功能模块图 ====================
def build_module_diagram(cfg: dict) -> str:
    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    title = cfg.get("title", "功能模块图")
    roles = cfg.get("roles", [])
    n = len(roles)

    bar_w, step, mod_h = 41, 46.5, 300
    role_w, role_h = 120, 60
    title_w, title_h = 456.5, 60
    title_y = -5
    top_y = 141
    role_y = 221
    spine_y = 340
    mod_y = 381

    max_mod = max((len(r.get("modules", [])) for r in roles), default=0)
    spacing = max(180, (max_mod - 1) * step + bar_w + 60) if max_mod > 0 else 180

    content_span = (n - 1) * spacing + (max(max_mod, 1) - 1) * step + bar_w
    page_w = max(827, int(content_span + 80), int(title_w + 80))
    mid_x = page_w / 2.0

    # title
    _cell(root, "c1", vertex=True,
          style="rounded=0;whiteSpace=wrap;html=1;strokeColor=default;align=center;verticalAlign=middle;fontFamily=Helvetica;fontSize=12;fontColor=default;fillColor=default;fontStyle=0",
          value=_font(title), x=mid_x - title_w/2, y=title_y, w=title_w, h=title_h)

    centers = [mid_x + (i - (n-1)/2) * spacing for i in range(n)]

    # top horizontal line
    xs = sorted(centers + [mid_x])
    _edge(root, "c2", xs[-1], top_y, xs[0], top_y)
    _edge(root, "c3", mid_x, top_y, mid_x, title_y + title_h)

    ci = 4
    for ri, r in enumerate(roles):
        cx = centers[ri]
        rvid = f"c{ci}"; ci += 1
        _cell(root, rvid, vertex=True, style="rounded=0;whiteSpace=wrap;html=1;",
              value=_font(r["name"]), x=cx - role_w/2, y=role_y, w=role_w, h=role_h)
        eid = f"c{ci}"; ci += 1
        _edge_from(root, eid, rvid, cx, role_y, cx, top_y)

        modules = r.get("modules", [])
        lefts = []
        if modules:
            span = (len(modules) - 1) * step + bar_w
            left0 = cx - span / 2
            lefts = [left0 + k * step for k in range(len(modules))]

        if lefts:
            lo = lefts[0] + bar_w/2
            hi = lefts[-1] + bar_w/2
            _edge(root, f"c{ci}", hi, spine_y, lo, spine_y); ci += 1
            _edge(root, f"c{ci}", cx, spine_y, cx, role_y + role_h); ci += 1

        for mi, lx in enumerate(lefts):
            mcid = f"c{ci}"; ci += 1
            _cell(root, mcid, vertex=True, style="rounded=0;whiteSpace=wrap;html=1;",
                  value=_font(modules[mi]), x=lx, y=mod_y, w=bar_w, h=mod_h)
            cxm = lx + bar_w/2
            _edge_from(root, f"c{ci}", mcid, cxm, mod_y, cxm, spine_y); ci += 1

    return _wrap_xml(root, page_w, mod_y + mod_h + 20)


# ==================== 2. 用例图 ====================
def build_usecase_diagram(cfg: dict) -> str:
    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    title = cfg.get("title", "用例图")
    actors = cfg.get("actors", [])
    usecases = cfg.get("usecases", [])
    relationships = cfg.get("relationships", [])

    actor_w, actor_h = 80, 40
    uc_w, uc_h = 160, 50
    margin = 60

    # layout actors on left, usecases on right
    actor_x = 80
    uc_x = 380
    total_h = max(len(actors), len(usecases)) * 100 + 120
    page_w = 700
    page_h = total_h + 100

    # title
    _cell(root, "c1", vertex=True,
          style="rounded=0;whiteSpace=wrap;html=1;align=center;fontSize=16;fontStyle=1;",
          value=_esc(title), x=page_w/2 - 150, y=10, w=300, h=40)

    ci = 2
    actor_ids = {}
    for i, a in enumerate(actors):
        ay = 80 + i * 100
        aid = f"c{ci}"; ci += 1
        # stickman-like: text label
        _cell(root, aid, vertex=True,
              style="shape=umlLifeline;perimeter=lifelinePerimeter;whiteSpace=wrap;html=1;container=0;collapsible=0;recursiveResize=0;outlineConnect=0;",
              value=_esc(a["name"]), x=actor_x, y=ay, w=actor_w, h=actor_h)
        actor_ids[a.get("id", a["name"])] = (aid, actor_x + actor_w, ay + actor_h/2)

    uc_ids = {}
    for i, uc in enumerate(usecases):
        uy = 80 + i * 100
        uid = f"c{ci}"; ci += 1
        _cell(root, uid, vertex=True,
              style="ellipse;whiteSpace=wrap;html=1;aspect=fixed;",
              value=_esc(uc["name"]), x=uc_x, y=uy, w=uc_w, h=uc_h)
        uc_ids[uc.get("id", uc["name"])] = (uid, uc_x, uy + uc_h/2)

    for rel in relationships:
        src = actor_ids.get(rel.get("actor", ""))
        tgt = uc_ids.get(rel.get("usecase", ""))
        if src and tgt:
            eid = f"c{ci}"; ci += 1
            _edge(root, eid, src[1], src[2], tgt[1], tgt[2], style="endArrow=none;html=1;rounded=0;")

    return _wrap_xml(root, page_w, page_h)


# ==================== 3. ER 图 ====================
def build_er_diagram(cfg: dict) -> str:
    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    title = cfg.get("title", "ER图")
    entities = cfg.get("entities", [])
    relationships = cfg.get("relationships", [])

    box_w = 200
    header_h = 36
    row_h = 28
    margin = 40
    gap_x = 80

    # calculate positions
    col_w = box_w + gap_x
    cols = max(1, int(len(entities) ** 0.5 + 0.5))
    page_w = cols * col_w + margin * 2
    x_start = margin

    ci = 1
    entity_pos = {}

    for i, ent in enumerate(entities):
        col = i % cols
        row = i // cols
        ex = x_start + col * col_w
        ey = 60 + row * (header_h + row_h * 8 + 40)
        attrs = ent.get("attributes", [])
        box_h = header_h + row_h * len(attrs)

        eid = f"c{ci}"; ci += 1
        # header
        _cell(root, eid, vertex=True,
              style="swimlane;startSize=36;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=14;",
              value=_esc(ent["name"]), x=ex, y=ey, w=box_w, h=box_h)
        entity_pos[ent.get("id", ent["name"])] = (ex, ey, box_w, box_h)

        for ai, attr in enumerate(attrs):
            aid = f"c{ci}"; ci += 1
            attr_style = "text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=4;spacingRight=4;overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontSize=12;"
            if attr.get("pk"):
                attr_style += "fontStyle=1;"
            prefix = "PK " if attr.get("pk") else ""
            _cell(root, aid, vertex=True, style=attr_style,
                  value=_esc(prefix + attr["name"]), x=ex, y=ey + header_h + ai * row_h, w=box_w, h=row_h)

    # relationships
    for rel in relationships:
        src_ent = entity_pos.get(rel.get("from", ""))
        tgt_ent = entity_pos.get(rel.get("to", ""))
        if src_ent and tgt_ent:
            rid = f"c{ci}"; ci += 1
            sx = src_ent[0] + src_ent[2]
            sy = src_ent[1] + src_ent[3] / 2
            tx = tgt_ent[0]
            ty = tgt_ent[1] + tgt_ent[3] / 2
            label = rel.get("label", "")
            style = "endArrow=none;html=1;rounded=0;"
            if rel.get("type") == "1:N":
                style = "endArrow=ERone;endFill=0;html=1;rounded=0;"
            elif rel.get("type") == "N:M":
                style = "endArrow=ERmany;endFill=0;startArrow=ERmany;startFill=0;html=1;rounded=0;"
            _edge(root, rid, sx, sy, tx, ty, style=style)

    page_h = 60 + ((len(entities) - 1) // cols + 1) * (header_h + row_h * 8 + 40) + 40
    return _wrap_xml(root, max(page_w, 600), page_h)


# ==================== 4. 属性图 ====================
def build_attribute_diagram(cfg: dict) -> str:
    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    title = cfg.get("title", "属性图")
    nodes = cfg.get("nodes", [])
    edges = cfg.get("edges", [])

    node_w, node_h = 180, 60
    margin = 60
    cols = max(1, int(len(nodes) ** 0.5 + 0.5))
    col_w = node_w + 80
    page_w = cols * col_w + margin * 2

    ci = 1
    node_pos = {}

    # title
    _cell(root, f"c{ci}", vertex=True,
          style="rounded=0;whiteSpace=wrap;html=1;align=center;fontSize=16;fontStyle=1;",
          value=_esc(title), x=page_w/2 - 150, y=10, w=300, h=40); ci += 1

    for i, node in enumerate(nodes):
        col = i % cols
        row = i // cols
        nx = margin + col * col_w
        ny = 70 + row * 120
        nid = f"c{ci}"; ci += 1
        label = node["name"]
        props = node.get("properties", [])
        if props:
            label += "\\n" + "\\n".join(f"{k}: {v}" for p in props for k, v in p.items())
        _cell(root, nid, vertex=True,
              style="ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#d5e8d4;strokeColor=#82b366;",
              value=_esc(label.replace("\\n", "\n")), x=nx, y=ny, w=node_w, h=node_h)
        node_pos[node.get("id", node["name"])] = (nx + node_w/2, ny + node_h/2)

    for edge in edges:
        src = node_pos.get(edge.get("from", ""))
        tgt = node_pos.get(edge.get("to", ""))
        if src and tgt:
            eid = f"c{ci}"; ci += 1
            _edge(root, eid, src[0], src[1], tgt[0], tgt[1],
                  style="endArrow=block;html=1;rounded=0;endFill=1;")
            if edge.get("label"):
                lid = f"c{ci}"; ci += 1
                mx = (src[0] + tgt[0]) / 2
                my = (src[1] + tgt[1]) / 2
                _cell(root, lid, vertex=True,
                      style="text;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=11;",
                      value=_esc(edge["label"]), x=mx - 40, y=my - 12, w=80, h=24)

    page_h = 70 + ((len(nodes) - 1) // cols + 1) * 120 + 40
    return _wrap_xml(root, max(page_w, 600), page_h)


# ==================== 5. 类图 ====================
def build_class_diagram(cfg: dict) -> str:
    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    title = cfg.get("title", "类图")
    classes = cfg.get("classes", [])
    relationships = cfg.get("relationships", [])

    box_w = 220
    header_h = 36
    row_h = 26

    ci = 1
    class_pos = {}

    # layout
    cols = max(1, int(len(classes) ** 0.5 + 0.5))
    col_w = box_w + 80
    margin = 60
    page_w = cols * col_w + margin * 2

    for i, cls in enumerate(classes):
        col = i % cols
        row = i // cols
        cx = margin + col * col_w
        cy = 60 + row * 260
        attrs = cls.get("attributes", [])
        methods = cls.get("methods", [])
        section_h = header_h + row_h * max(len(attrs), 1)
        total_h = section_h + row_h * max(len(methods), 1)

        cid = f"c{ci}"; ci += 1
        _cell(root, cid, vertex=True,
              style="swimlane;fontStyle=1;align=center;startSize=36;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=14;",
              value=_esc(cls["name"]), x=cx, y=cy, w=box_w, h=total_h)
        class_pos[cls.get("id", cls["name"])] = (cx, cy, box_w, total_h)

        # attributes
        for ai, attr in enumerate(attrs):
            aid = f"c{ci}"; ci += 1
            _cell(root, aid, vertex=True,
                  style="text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=4;overflow=hidden;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontSize=12;",
                  value=_esc(attr), x=cx, y=cy + header_h + ai * row_h, w=box_w, h=row_h)

        # separator line
        sep_id = f"c{ci}"; ci += 1
        _cell(root, sep_id, vertex=True,
              style="line;strokeWidth=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;spacingLeft=3;spacingRight=10;rotatable=0;labelPosition=left;points=[];portConstraint=eastwest;strokeColor=#6c8ebf;",
              value="", x=cx, y=cy + section_h - 1, w=box_w, h=row_h)

        # methods
        for mi, method in enumerate(methods):
            mid = f"c{ci}"; ci += 1
            _cell(root, mid, vertex=True,
                  style="text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=4;overflow=hidden;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontSize=12;",
                  value=_esc(method), x=cx, y=cy + section_h + mi * row_h, w=box_w, h=row_h)

    # relationships
    arrow_styles = {
        "inheritance": "endArrow=block;endFill=0;html=1;rounded=0;",
        "implementation": "endArrow=block;endFill=0;dashed=1;html=1;rounded=0;",
        "association": "endArrow=open;endFill=0;html=1;rounded=0;",
        "dependency": "endArrow=open;endFill=0;dashed=1;html=1;rounded=0;",
        "aggregation": "endArrow=diamond;endFill=0;html=1;rounded=0;",
        "composition": "endArrow=diamond;endFill=1;html=1;rounded=0;",
    }

    for rel in relationships:
        src = class_pos.get(rel.get("from", ""))
        tgt = class_pos.get(rel.get("to", ""))
        if src and tgt:
            rid = f"c{ci}"; ci += 1
            sx = src[0] + src[2]/2
            sy = src[1] + src[3]
            tx = tgt[0] + tgt[2]/2
            ty = tgt[1]
            style = arrow_styles.get(rel.get("type", "association"), "endArrow=open;html=1;rounded=0;")
            _edge(root, rid, sx, sy, tx, ty, style=style)
            if rel.get("label"):
                lid = f"c{ci}"; ci += 1
                mx = (sx + tx) / 2
                my = (sy + ty) / 2
                _cell(root, lid, vertex=True,
                      style="text;strokeColor=none;fillColor=none;align=center;fontSize=11;",
                      value=_esc(rel["label"]), x=mx - 40, y=my - 12, w=80, h=24)

    page_h = 60 + ((len(classes) - 1) // cols + 1) * 260 + 40
    return _wrap_xml(root, max(page_w, 600), page_h)


# ==================== 6. 活动图 ====================
def build_activity_diagram(cfg: dict) -> str:
    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    title = cfg.get("title", "活动图")
    nodes_list = cfg.get("nodes", [])
    flows = cfg.get("flows", [])

    node_w = 180
    node_h = 50
    margin = 60
    v_gap = 80

    ci = 1
    node_pos = {}

    # title
    _cell(root, f"c{ci}", vertex=True,
          style="rounded=0;whiteSpace=wrap;html=1;align=center;fontSize=16;fontStyle=1;",
          value=_esc(title), x=300, y=10, w=300, h=40); ci += 1

    for i, node in enumerate(nodes_list):
        nx = 300
        ny = 70 + i * (node_h + v_gap)
        nid = f"c{ci}"; ci += 1

        ntype = node.get("type", "action")
        if ntype == "start":
            style = "ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#000000;strokeColor=#000000;"
        elif ntype == "end":
            style = "ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#000000;strokeColor=#000000;"
        elif ntype == "decision":
            style = "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;"
        elif ntype == "swimlane":
            style = "swimlane;startSize=30;fillColor=#e1d5e7;strokeColor=#9673a6;"
        else:
            style = "rounded=1;whiteSpace=wrap;html=1;arcSize=20;fillColor=#d5e8d4;strokeColor=#82b366;"

        _cell(root, nid, vertex=True, style=style,
              value=_esc(node.get("name", "")), x=nx, y=ny, w=node_w, h=node_h)
        node_pos[node.get("id", node.get("name", str(i)))] = (nx + node_w/2, ny, nx + node_w/2, ny + node_h)

    for flow in flows:
        src = node_pos.get(flow.get("from", ""))
        tgt = node_pos.get(flow.get("to", ""))
        if src and tgt:
            fid = f"c{ci}"; ci += 1
            style = "endArrow=block;endFill=1;html=1;rounded=0;"
            if flow.get("dashed"):
                style = "endArrow=block;endFill=1;dashed=1;html=1;rounded=0;"
            _edge(root, fid, src[2], src[3], tgt[0], tgt[1], style=style)
            if flow.get("label"):
                lid = f"c{ci}"; ci += 1
                mx = (src[2] + tgt[0]) / 2
                my = (src[3] + tgt[1]) / 2
                _cell(root, lid, vertex=True,
                      style="text;strokeColor=none;fillColor=none;align=center;fontSize=11;",
                      value=_esc(flow["label"]), x=mx - 40, y=my - 12, w=80, h=24)

    page_h = 70 + len(nodes_list) * (node_h + v_gap) + 40
    return _wrap_xml(root, 700, page_h)


# ==================== 7. 架构图 ====================
def build_architecture_diagram(cfg: dict) -> str:
    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    title = cfg.get("title", "架构图")
    layers = cfg.get("layers", [])

    layer_w = 700
    layer_h = 100
    box_h = 60
    margin = 40
    v_gap = 30

    ci = 1

    # title
    _cell(root, f"c{ci}", vertex=True,
          style="rounded=0;whiteSpace=wrap;html=1;align=center;fontSize=16;fontStyle=1;",
          value=_esc(title), x=layer_w/2 - 150 + margin, y=10, w=300, h=40); ci += 1

    colors = [("#dae8fc", "#6c8ebf"), ("#d5e8d4", "#82b366"),
              ("#fff2cc", "#d6b656"), ("#e1d5e7", "#9673a6"),
              ("#f8cecc", "#b85450")]

    for li, layer in enumerate(layers):
        ly = 70 + li * (layer_h + v_gap)
        fill, stroke = colors[li % len(colors)]

        # layer container
        lid = f"c{ci}"; ci += 1
        components = layer.get("components", [])
        comp_count = max(len(components), 1)
        actual_w = max(layer_w, comp_count * 160 + 40)
        _cell(root, lid, vertex=True,
              style="swimlane;startSize=30;fillColor=" + fill + ";strokeColor=" + stroke + ";fontStyle=1;fontSize=13;",
              value=_esc(layer["name"]), x=margin, y=ly, w=actual_w, h=layer_h)

        # components inside
        comp_w = min(140, (actual_w - 40) / comp_count - 10)
        for ci2, comp in enumerate(components):
            cid = f"c{ci}"; ci += 1
            _cell(root, cid, vertex=True,
                  style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=" + stroke + ";fontSize=12;",
                  value=_esc(comp), x=margin + 20 + ci2 * (comp_w + 10), y=ly + 35, w=comp_w, h=40)

    # arrows between layers
    for li in range(len(layers) - 1):
        ly1 = 70 + li * (layer_h + v_gap) + layer_h
        ly2 = 70 + (li + 1) * (layer_h + v_gap)
        ax = margin + (max(layer_w, len(layers[li+1].get("components",[]))*160+40)) / 2
        aid = f"c{ci}"; ci += 1
        _edge(root, aid, ax, ly2, ax, ly1,
              style="endArrow=block;endFill=1;html=1;rounded=0;dashed=1;")

    page_h = 70 + len(layers) * (layer_h + v_gap) + 40
    page_w = max(layer_w + margin * 2, 800)
    return _wrap_xml(root, page_w, page_h)


# ==================== 8. 序列图 ====================
def build_sequence_diagram(cfg: dict) -> str:
    root = ET.Element("root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    title = cfg.get("title", "序列图")
    participants = cfg.get("participants", [])
    messages = cfg.get("messages", [])

    part_w = 120
    part_h = 50
    margin = 60
    col_gap = 160
    msg_gap = 60

    ci = 1
    part_x = {}

    # title
    total_w = len(participants) * col_gap + margin * 2
    _cell(root, f"c{ci}", vertex=True,
          style="rounded=0;whiteSpace=wrap;html=1;align=center;fontSize=16;fontStyle=1;",
          value=_esc(title), x=total_w/2 - 150, y=10, w=300, h=40); ci += 1

    for i, p in enumerate(participants):
        px = margin + i * col_gap + col_gap/2 - part_w/2
        pid = f"c{ci}"; ci += 1
        _cell(root, pid, vertex=True,
              style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;fontSize=13;",
              value=_esc(p["name"]), x=px, y=70, w=part_w, h=part_h)
        part_x[p.get("id", p["name"])] = px + part_w/2

        # lifeline
        lid = f"c{ci}"; ci += 1
        _cell(root, lid, vertex=True,
              style="line;strokeWidth=1;dashed=1;fillColor=none;align=left;verticalAlign=middle;spacingTop=-1;spacingLeft=3;spacingRight=10;rotatable=0;labelPosition=left;points=[];portConstraint=eastwest;strokeColor=#6c8ebf;",
              value="", x=px + part_w/2 - 1, y=70 + part_h, w=2, h=50 + len(messages) * msg_gap)

    for mi, msg in enumerate(messages):
        my = 130 + mi * msg_gap
        sx = part_x.get(msg.get("from", ""))
        tx = part_x.get(msg.get("to", ""))
        if sx and tx:
            mid = f"c{ci}"; ci += 1
            style = "endArrow=open;endFill=0;html=1;rounded=0;"
            if msg.get("type") == "return":
                style = "endArrow=open;endFill=0;dashed=1;html=1;rounded=0;"
            elif msg.get("type") == "self":
                style = "endArrow=open;endFill=0;html=1;rounded=0;edgeStyle=orthogonalEdgeStyle;"
            _edge(root, mid, sx, my, tx, my, style=style)
            if msg.get("label"):
                lid2 = f"c{ci}"; ci += 1
                mx = (sx + tx) / 2
                _cell(root, lid2, vertex=True,
                      style="text;strokeColor=none;fillColor=none;align=center;fontSize=12;",
                      value=_esc(msg["label"]), x=mx - 60, y=my - 16, w=120, h=20)

    page_h = 140 + len(messages) * msg_gap + 40
    page_w = total_w
    return _wrap_xml(root, max(page_w, 600), page_h)


# ==================== 分发入口 ====================
BUILDERS = {
    "module": build_module_diagram,
    "usecase": build_usecase_diagram,
    "er": build_er_diagram,
    "attribute": build_attribute_diagram,
    "class": build_class_diagram,
    "activity": build_activity_diagram,
    "architecture": build_architecture_diagram,
    "sequence": build_sequence_diagram,
}


def convert(json_str: str) -> str:
    cfg = json.loads(json_str)
    chart_type = cfg.get("type", "module")
    builder = BUILDERS.get(chart_type)
    if not builder:
        raise ValueError(f"不支持的图表类型: {chart_type}，支持: {', '.join(BUILDERS.keys())}")
    return builder(cfg)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="JSON → draw.io XML 转换")
    ap.add_argument("input", nargs="?", help="JSON 文件路径，或 - 从 stdin 读取")
    ap.add_argument("-o", "--output", help="输出 XML 文件路径")
    args = ap.parse_args()

    if args.input in (None, "-"):
        data = sys.stdin.read()
    else:
        data = Path(args.input).read_text(encoding="utf-8-sig")

    try:
        xml = convert(data)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    if args.output:
        Path(args.output).write_text(xml, encoding="utf-8")
        print(f"已生成: {args.output}", file=sys.stderr)
    else:
        print(xml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
