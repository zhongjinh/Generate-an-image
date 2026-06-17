#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse PlantUML sequence diagram text into sequence JSON for draw.io builder."""

from __future__ import annotations

import re
from typing import Any

_PART_TYPES = (
    "participant",
    "actor",
    "boundary",
    "control",
    "entity",
    "database",
    "collections",
    "queue",
)

_PART_RE = re.compile(
    rf"^({'|'.join(_PART_TYPES)})\s+"
    r'(?:"([^"]+)"|(\S+))'
    r"(?:\s+as\s+(\S+))?"
    r"(?:\s+#\S+)?"
    r"\s*$",
    re.IGNORECASE,
)

_MSG_RE = re.compile(
    r"^(?P<from>.+?)\s+"
    r"(?P<arrow>-->>|->>|-->|-\\>|--|-\|>|->)"
    r"\s+(?P<to>[^:]+?)"
    r"(?:\s*:\s*(?P<label>.*))?\s*$"
)

_BOX_RE = re.compile(r'^box\s+(?:"([^"]+)"|(\S+))\s*$', re.IGNORECASE)
_SKIP_PREFIXES = (
    "@startuml",
    "@enduml",
    "!pragma",
    "skinparam",
    "hide ",
    "show ",
    "autonumber",
    "activate ",
    "deactivate ",
    "destroy ",
    "create ",
    "newpage",
    "hnote ",
    "rnote ",
    "note ",
)


def _strip_comment(line: str) -> str:
    if line.lstrip().startswith("'"):
        return ""
    if "//" in line:
        line = line.split("//", 1)[0]
    return line.rstrip()


def _should_skip(line: str) -> bool:
    low = line.lower()
    return any(low.startswith(p) for p in _SKIP_PREFIXES)


def _msg_type(arrow: str) -> str:
    a = arrow.replace("\\", "")
    if a in {"-->", "--", "-->>"}:
        return "return"
    return "sync"


def _resolve_alias(name: str, alias_map: dict[str, str], name_map: dict[str, str]) -> str:
    key = name.strip()
    if key in alias_map:
        return alias_map[key]
    if key in name_map:
        return name_map[key]
    return key


def _format_label(label: str) -> str:
    return label.replace("\\n", "<br>").replace("\n", "<br>")


def parse_plantuml_sequence(text: str) -> dict[str, Any]:
    """PlantUML sequence text -> {type, title, participants, messages, boxes?}."""
    lines = text.replace("\r\n", "\n").split("\n")
    title = "序列图"
    participants_order: list[str] = []
    alias_map: dict[str, str] = {}  # alias/id -> canonical id
    display_names: dict[str, str] = {}  # id -> display name
    name_map: dict[str, str] = {}  # display name -> id
    messages: list[dict[str, str]] = []
    boxes: list[dict[str, Any]] = []
    box_stack: list[dict[str, Any]] = []

    def add_participant(display: str, alias: str | None) -> str:
        pid = (alias or display).strip()
        display = display.strip()
        if pid not in alias_map:
            participants_order.append(pid)
            alias_map[pid] = pid
            display_names[pid] = display
            name_map[display] = pid
        return pid

    def ensure_participant(name: str) -> str:
        key = name.strip()
        if key in alias_map:
            return alias_map[key]
        if key in name_map:
            return name_map[key]
        return add_participant(key, key)

    for raw in lines:
        line = _strip_comment(raw).strip()
        if not line:
            continue
        if _should_skip(line):
            continue

        low = line.lower()
        if low.startswith("title "):
            title = line[6:].strip().strip('"')
            continue

        m_box = _BOX_RE.match(line)
        if m_box:
            box_name = m_box.group(1) or m_box.group(2) or "box"
            box_stack.append({
                "name": box_name,
                "start": max(len(participants_order) - 1, 0),
            })
            continue
        if low in {"end box", "endbox"}:
            if box_stack:
                box = box_stack.pop()
                box["end"] = max(len(participants_order) - 1, box["start"])
                if box["end"] >= box["start"]:
                    boxes.append(box)
            continue
        if low in {"end", "else", "elseif"} or low.startswith(
            ("alt ", "loop ", "opt ", "par ", "critical ", "break ", "group ")
        ):
            continue

        m_part = _PART_RE.match(line)
        if m_part:
            display = m_part.group(2) or m_part.group(3) or ""
            alias = m_part.group(4)
            add_participant(display, alias)
            continue

        m_msg = _MSG_RE.match(line)
        if m_msg:
            from_raw = m_msg.group("from").strip()
            to_raw = m_msg.group("to").strip()
            label = _format_label((m_msg.group("label") or "").strip())
            arrow = m_msg.group("arrow")

            from_id = ensure_participant(from_raw)
            to_id = ensure_participant(to_raw)
            messages.append({
                "from": from_id,
                "to": to_id,
                "label": label,
                "type": _msg_type(arrow),
            })
            continue

    if not participants_order and messages:
        seen: list[str] = []
        for msg in messages:
            for pid in (msg["from"], msg["to"]):
                if pid not in seen:
                    seen.append(pid)
                    display_names.setdefault(pid, pid)
                    alias_map.setdefault(pid, pid)
        participants_order = seen

    if not participants_order:
        raise ValueError("PlantUML 中未找到参与者或消息")

    participants = [
        {"id": pid, "name": display_names.get(pid, pid)}
        for pid in participants_order
    ]

    cfg: dict[str, Any] = {
        "type": "sequence",
        "title": title,
        "participants": participants,
        "messages": messages,
    }
    if boxes:
        cfg["boxes"] = boxes
    return cfg


def is_plantuml_sequence(text: str) -> bool:
    t = text.strip()
    if t.startswith("@startuml"):
        return True
    if "->" in t or "-->" in t:
        return bool(_PART_RE.match(t.split("\n")[0].strip()) or _MSG_RE.search(t))
    return False


def to_plantuml(cfg: dict[str, Any]) -> str:
    """Convert sequence JSON (participants/messages) to PlantUML text."""
    lines = ["@startuml"]
    title = cfg.get("title")
    if title:
        lines.append(f"title {title}")
    for p in cfg.get("participants") or []:
        name = str(p.get("name") or p.get("id") or "").strip()
        pid = str(p.get("id") or name).strip()
        ptype = str(p.get("type") or "participant").lower()
        if ptype not in _PART_TYPES:
            ptype = "participant"
        if name and pid and name != pid:
            lines.append(f'{ptype} "{name}" as {pid}')
        elif name:
            lines.append(f'{ptype} "{name}"')
        elif pid:
            lines.append(f"{ptype} {pid}")
    if lines[-1] != "":
        lines.append("")
    for m in cfg.get("messages") or []:
        frm = str(m.get("from", "")).strip()
        to = str(m.get("to", "")).strip()
        label = str(m.get("label", "")).strip()
        arrow = "-->" if m.get("type") == "return" else "->"
        if label:
            label = label.replace("\n", "\\n")
            lines.append(f"{frm} {arrow} {to}: {label}")
        else:
            lines.append(f"{frm} {arrow} {to}")
    lines.append("@enduml")
    return "\n".join(lines)


def attach_plantuml_source(cfg: dict[str, Any], source: str) -> dict[str, Any]:
    out = dict(cfg)
    out["_plantuml_source"] = source.strip()
    out["type"] = "sequence"
    return out
