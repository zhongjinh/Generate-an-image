#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize frontend JSON to reference-script formats."""

from __future__ import annotations

from pathlib import Path
from typing import Any

TEMPLATES = Path(__file__).resolve().parent / "templates"


def detect_type(cfg: dict[str, Any]) -> str:
    explicit = cfg.get("type")
    if explicit:
        return str(explicit)
    if cfg.get("roles"):
        return "module"
    if cfg.get("use_cases") or cfg.get("actor"):
        return "usecase"
    if cfg.get("entities") and cfg.get("relationships"):
        return "er"
    if cfg.get("sql") or cfg.get("tables"):
        return "attribute"
    if cfg.get("classes"):
        return "class"
    if cfg.get("layers"):
        return "architecture"
    if cfg.get("plantuml"):
        return "sequence"
    if cfg.get("participants") and cfg.get("messages"):
        return "sequence"
    if cfg.get("nodes") and _is_template_activity(cfg):
        return "activity"
    if cfg.get("nodes") and cfg.get("flows"):
        return "activity"
    if cfg.get("steps"):
        return "flowchart"
    return "module"


def normalize(cfg: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(cfg)
    cfg["type"] = detect_type(cfg)
    fn = {
        "module": normalize_module,
        "usecase": normalize_usecase,
        "er": normalize_er,
        "attribute": normalize_attribute,
        "class": normalize_class,
        "activity": normalize_activity,
        "architecture": normalize_architecture,
        "sequence": normalize_sequence,
        "flowchart": normalize_flowchart,
    }.get(cfg["type"])
    return fn(cfg) if fn else cfg


def normalize_module(cfg: dict[str, Any]) -> dict[str, Any]:
    out = dict(cfg)
    if not out.get("title"):
        out["title"] = (
            cfg.get("diagram_name")
            or cfg.get("figure")
            or "功能模块图"
        )
    return out


def normalize_usecase(cfg: dict[str, Any]) -> dict[str, Any]:
    if cfg.get("use_cases") or cfg.get("actor"):
        return cfg

    actors = cfg.get("actors") or []
    actor = actors[0]["name"] if actors else "用户"
    use_cases = []
    for uc in cfg.get("usecases") or []:
        name = uc.get("name") or uc.get("id") or "用例"
        use_cases.append({"name": name, "includes": uc.get("includes") or []})

    return {
        **cfg,
        "actor": actor,
        "use_cases": use_cases,
        "diagram_name": cfg.get("title") or cfg.get("diagram_name") or "用例图",
    }


def normalize_er(cfg: dict[str, Any]) -> dict[str, Any]:
    entities = []
    for e in cfg.get("entities") or []:
        name = str(e.get("name") or "").strip()
        attrs: list[str] = []
        for a in e.get("attributes") or []:
            if isinstance(a, dict):
                label = str(a.get("name") or "").strip()
                if a.get("pk") and label:
                    label = f"{label} (PK)"
                if label:
                    attrs.append(label)
            elif a:
                attrs.append(str(a).strip())
        entities.append({"name": name, "attributes": attrs})

    relationships = []
    for r in cfg.get("relationships") or []:
        relationships.append({
            "from": r.get("from"),
            "to": r.get("to"),
            "name": r.get("name") or r.get("label") or "联系",
            "cardinality": r.get("cardinality") or r.get("type") or "1:N",
        })

    out = dict(cfg)
    out["entities"] = entities
    out["relationships"] = relationships
    return out


def normalize_attribute(cfg: dict[str, Any]) -> dict[str, Any]:
    if cfg.get("sql"):
        return cfg

    lines = ["-- generated from JSON"]
    tables_list = list(cfg.get("tables") or [])
    if len(tables_list) > 1:
        tables_list = tables_list[:1]
    for table in tables_list:
        tname = table.get("name") or table.get("table") or "entity"
        comment = table.get("comment") or tname
        cols = table.get("columns") or table.get("attributes") or []
        lines.append(f"CREATE TABLE `{tname}` (")
        col_lines = []
        for col in cols:
            if isinstance(col, dict):
                cname = col.get("name") or col.get("column") or "col"
                ccomment = col.get("comment") or cname
                pk = " PRIMARY KEY" if col.get("pk") else ""
                col_lines.append(f"  `{cname}` VARCHAR(64){pk} COMMENT '{ccomment}'")
            else:
                col_lines.append(f"  `{col}` VARCHAR(64) COMMENT '{col}'")
        lines.append(",\n".join(col_lines))
        lines.append(f") COMMENT='{comment}';")
        lines.append("")

    if len(lines) > 1:
        return {**cfg, "sql": "\n".join(lines)}

    return cfg


def normalize_class(cfg: dict[str, Any]) -> dict[str, Any]:
    tpl = cfg.get("template_xml") or cfg.get("template") or str(TEMPLATES / "class_diagram.xml")
    classes = []
    for c in cfg.get("classes") or []:
        classes.append({
            "template_name": c.get("template_name") or c.get("name"),
            "name": c.get("name"),
            "attributes": c.get("attributes") or [],
            "methods": c.get("methods") or [],
        })
    rels = cfg.get("relations") or cfg.get("relationships") or []
    return {
        **cfg,
        "template_xml": tpl,
        "classes": classes,
        "relations": rels,
    }


def _is_template_activity(cfg: dict[str, Any]) -> bool:
    nodes = cfg.get("nodes") or []
    return any(
        isinstance(n, dict) and (n.get("match_text") or n.get("match"))
        for n in nodes
    )


def normalize_activity(cfg: dict[str, Any]) -> dict[str, Any]:
    if _is_template_activity(cfg):
        title = cfg.get("title") or (cfg.get("meta") or {}).get("title", "")
        tpl = cfg.get("template_xml") or str(TEMPLATES / "activity_diagram.xml")
        return {
            **cfg,
            "title": title,
            "template_xml": tpl,
            "nodes": list(cfg.get("nodes") or []),
            "links": list(cfg.get("links") or []),
        }

    nodes = []
    for n in cfg.get("nodes") or []:
        nodes.append({
            "id": n.get("id") or n.get("name", ""),
            "name": n.get("name", ""),
            "type": n.get("type", "action"),
        })
    flows = []
    for f in cfg.get("flows") or []:
        flows.append({
            "from": f.get("from", ""),
            "to": f.get("to", ""),
            "label": f.get("label", ""),
            "dashed": f.get("dashed", False),
        })
    return {
        **cfg,
        "nodes": nodes,
        "flows": flows,
        "lanes": cfg.get("lanes"),
    }


def normalize_architecture(cfg: dict[str, Any]) -> dict[str, Any]:
    layers = []
    for layer in cfg.get("layers") or []:
        groups = layer.get("groups") or layer.get("subgraphs") or []
        norm_groups = []
        for g in groups:
            norm_groups.append({
                "name": g.get("name", ""),
                "nodes": g.get("nodes") or g.get("components") or [],
            })
        layers.append({
            "name": layer.get("name", ""),
            "components": layer.get("components") or layer.get("nodes") or [],
            "groups": norm_groups,
        })
    return {
        **cfg,
        "layers": layers,
        "links": cfg.get("links") or cfg.get("connections") or [],
    }


def normalize_sequence(cfg: dict[str, Any]) -> dict[str, Any]:
    participants = []
    for p in cfg.get("participants") or []:
        participants.append({
            "id": p.get("id") or p.get("name", ""),
            "name": p.get("name", ""),
        })
    messages = []
    for m in cfg.get("messages") or []:
        messages.append({
            "from": m.get("from", ""),
            "to": m.get("to", ""),
            "label": m.get("label", ""),
            "type": m.get("type", "sync"),
        })
    return {
        **cfg,
        "participants": participants,
        "messages": messages,
        "boxes": cfg.get("boxes"),
    }


def normalize_flowchart(cfg: dict[str, Any]) -> dict[str, Any]:
    steps = []
    for s in cfg.get("steps") or []:
        step: dict[str, Any] = {
            "id": int(s["id"]),
            "type": str(s["type"]),
            "text": str(s["text"]),
        }
        if s.get("branches"):
            step["branches"] = s["branches"]
        steps.append(step)
    return {
        **cfg,
        "steps": steps,
    }
