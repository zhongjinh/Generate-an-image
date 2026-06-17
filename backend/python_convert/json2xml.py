#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON → draw.io XML 转换引擎
各图表类型委托至 builders/ 目录下的参考脚本实现。
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import Any, Callable

from .adapters import (
    TEMPLATES,
    normalize,
    normalize_activity,
    normalize_architecture,
    normalize_attribute,
    normalize_class,
    normalize_er,
    normalize_flowchart,
    normalize_module,
    normalize_sequence,
    normalize_usecase,
    _is_template_activity,
)

_BUILDERS_DIR = Path(__file__).resolve().parent / "builders"


def _load_module(filename: str):
    path = _BUILDERS_DIR / filename
    name = "builders_" + filename.replace(".py", "").replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 builder: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_mo = _load_module("mo.py")
_er = _load_module("er.py")
_us = _load_module("us.py")
_class = _load_module("class_diagram.py")
_attr = _load_module("attr_diagram.py")
_fl = _load_module("fl.py")
_activity = _load_module("activity.py")
_activity_tpl = _load_module("activity_from_template.py")
_sequence = _load_module("sequence.py")
_sequence_puml = _load_module("sequence_plantuml_embed.py")
_plantuml_seq = _load_module("plantuml_sequence.py")
_architecture = _load_module("architecture.py")


def _tree_to_str(tree, *, xml_declaration: bool = True) -> str:
    buf = io.StringIO()
    tree.write(buf, encoding="unicode", xml_declaration=xml_declaration)
    return buf.getvalue()


def build_module_diagram(cfg: dict[str, Any]) -> str:
    cfg = normalize_module(cfg)
    return _tree_to_str(_mo.build_document(cfg))


def build_usecase_diagram(cfg: dict[str, Any]) -> str:
    cfg = normalize_usecase(cfg)
    model = _us.DiagramModel.from_dict(cfg)
    return _us.build_diagram(model)


def build_er_diagram(cfg: dict[str, Any]) -> str:
    cfg = normalize_er(cfg)
    return _tree_to_str(_er.build_document(cfg), xml_declaration=False)


def build_attribute_diagram(cfg: dict[str, Any]) -> str:
    cfg = normalize_attribute(cfg)
    sql = cfg.get("sql", "")
    if not sql:
        raise ValueError("属性图需要 sql 字段或 tables 数组（建表 SQL 格式）")
    tables = _attr.parse_create_tables(sql)
    if not tables:
        raise ValueError("未解析到任何表结构，请检查 tables 或 sql 内容")
    tables = tables[:1]
    tpl = Path(cfg.get("template_xml") or str(TEMPLATES / "attribute_diagram.xml"))
    return _attr.rebuild_diagram_xml(tpl, tables, grid_cols=1)


def build_class_diagram(cfg: dict[str, Any]) -> str:
    cfg = normalize_class(cfg)
    tpl = Path(cfg["template_xml"])
    if not tpl.is_absolute():
        tpl = TEMPLATES / tpl.name
    cfg = dict(cfg)
    cfg["template_xml"] = str(tpl)
    return _tree_to_str(_class.build_from_template(cfg), xml_declaration=False)


def build_activity_diagram(cfg: dict[str, Any]) -> str:
    cfg = normalize_activity(cfg)
    if _is_template_activity(cfg):
        tpl = Path(cfg["template_xml"])
        if not tpl.is_absolute():
            tpl = TEMPLATES / tpl.name
        cfg = dict(cfg)
        cfg["template_xml"] = str(tpl)
        return _tree_to_str(_activity_tpl.build_from_template(cfg), xml_declaration=False)
    return _tree_to_str(_activity.build_document(cfg))


def build_architecture_diagram(cfg: dict[str, Any]) -> str:
    cfg = normalize_architecture(cfg)
    return _tree_to_str(_architecture.build_document(cfg))


def build_sequence_diagram(cfg: dict[str, Any]) -> str:
    cfg = normalize_sequence(cfg)
    source = (cfg.get("_plantuml_source") or cfg.get("plantuml") or "").strip()
    if not source and cfg.get("participants") and cfg.get("messages"):
        source = _plantuml_seq.to_plantuml(cfg)
        cfg = dict(cfg)
        cfg["_plantuml_source"] = source

    if source:
        try:
            tree = _sequence_puml.build_from_cfg(cfg)
            return _tree_to_str(tree, xml_declaration=False)
        except Exception as exc:
            if cfg.get("_plantuml_source") or cfg.get("plantuml"):
                raise ValueError(f"PlantUML 序列图渲染失败: {exc}") from exc

    return _tree_to_str(_sequence.build_document(cfg))


def build_flowchart(cfg: dict[str, Any]) -> str:
    cfg = normalize_flowchart(cfg)
    return _tree_to_str(_fl.build_document(cfg))


BUILDERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "module": build_module_diagram,
    "usecase": build_usecase_diagram,
    "er": build_er_diagram,
    "attribute": build_attribute_diagram,
    "class": build_class_diagram,
    "activity": build_activity_diagram,
    "architecture": build_architecture_diagram,
    "sequence": build_sequence_diagram,
    "flowchart": build_flowchart,
}


def convert(input_str: str) -> str:
    text = input_str.strip()
    cfg = _parse_config(text)
    cfg = normalize(cfg)
    chart_type = cfg["type"]
    builder = BUILDERS.get(chart_type)
    if not builder:
        raise ValueError(f"不支持的图表类型: {chart_type}，支持: {', '.join(BUILDERS.keys())}")
    return builder(cfg)


def _parse_config(text: str) -> dict[str, Any]:
    plantuml_mod = _load_module("plantuml_sequence.py")

    if text.startswith("@startuml"):
        parsed = plantuml_mod.parse_plantuml_sequence(text)
        return plantuml_mod.attach_plantuml_source(parsed, text)

    try:
        cfg = json.loads(text)
    except json.JSONDecodeError:
        if plantuml_mod.is_plantuml_sequence(text):
            parsed = plantuml_mod.parse_plantuml_sequence(text)
            return plantuml_mod.attach_plantuml_source(parsed, text)
        raise

    if isinstance(cfg.get("plantuml"), str) and cfg.get("plantuml").strip():
        parsed = plantuml_mod.parse_plantuml_sequence(cfg["plantuml"])
        merged = plantuml_mod.attach_plantuml_source(parsed, cfg["plantuml"])
        if cfg.get("title"):
            merged["title"] = cfg["title"]
        return merged

    return cfg


def main() -> int:
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
