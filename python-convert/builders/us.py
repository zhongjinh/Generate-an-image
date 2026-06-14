#!/usr/bin/env python3
"""
从结构化数据生成 / 覆盖 diagrams.net（draw.io）用例图 XML。

改法与手工编辑一致：
  - 左：UML 参与者（actor）
  - 中：二级用例（椭圆）
  - 右：三级用例（椭圆）；二级→三级为虚线，标签为 <<include>>
  - 无三级的二级只连参与者，不画 include

用法：
  python us.py
  python us.py -c usecase_model.json -o 用例图.xml
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any
from xml.sax.saxutils import escape as xml_escape


# ---------- 样式（与现有 用例图.xml 保持一致，勿随意改） ----------
ACTOR_STYLE = (
    "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;"
    "html=1;outlineConnect=0;"
)
ELLIPSE_STYLE = "ellipse;whiteSpace=wrap;html=1;"
EDGE_ASSOC_STYLE = (
    "endArrow=classic;html=1;rounded=0;"
    "entryX=0.05;entryY=0.703;entryDx=0;entryDy=0;entryPerimeter=0;"
    "exitX=1;exitDx=0;exitDy=0;exitPerimeter=0;"
)
EDGE_INCLUDE_STYLE = "endArrow=classic;dashed=1;html=1;rounded=0;endFill=1;"
EDGE_LABEL_STYLE = (
    "edgeLabel;html=1;align=center;verticalAlign=middle;"
    "resizable=0;points=[];fontSize=15;"
)
INCLUDE_STEREO_XML = "&amp;lt;include&amp;gt;"

ACTOR_W, ACTOR_H = 30, 60
ELLIPSE_W, ELLIPSE_H = 102, 45
SEC_X = 430
TERT_X = 665
ACTOR_X = 280
SRC_EDGE_X = SEC_X + ELLIPSE_W  # 532
TERT_ROW_STEP = 50
GROUP_PAD = 10
LEAF_AFTER_STACK = 55
TERT_START_Y = 365

MXGRAPH_ATTRS = (
    'dx="1414" dy="777" grid="0" gridSize="10" guides="0" tooltips="1" '
    'connect="0" arrows="0" fold="1" page="0" pageScale="1" '
    'pageWidth="827" pageHeight="1169" math="0" shadow="0"'
)


def _attr_text(s: str) -> str:
    return xml_escape(s, {"'": "&apos;", '"': "&quot;"})


@dataclass
class SecondLevel:
    name: str
    includes: list[str] = field(default_factory=list)


@dataclass
class DiagramModel:
    actor: str
    use_cases: list[SecondLevel]
    diagram_name: str = "Page-1"
    diagram_id: str = "EG3ABlFq46mU1kXmPdiP"
    actor_cell_id: str = "9-5MaiP8lBFPep8I0sSv-2"

    @staticmethod
    def from_dict(d: dict[str, Any]) -> DiagramModel:
        raw = d.get("use_cases") or []
        cases: list[SecondLevel] = []
        for item in raw:
            if isinstance(item, str):
                cases.append(SecondLevel(name=item, includes=[]))
            else:
                cases.append(
                    SecondLevel(
                        name=str(item["name"]),
                        includes=list(item.get("includes") or []),
                    )
                )
        return DiagramModel(
            actor=str(d.get("actor") or "参与者"),
            use_cases=cases,
            diagram_name=str(d.get("diagram_name") or "Page-1"),
            diagram_id=str(d.get("diagram_id") or "EG3ABlFq46mU1kXmPdiP"),
            actor_cell_id=str(d.get("actor_cell_id") or "9-5MaiP8lBFPep8I0sSv-2"),
        )


DEFAULT_MODEL_JSON: dict[str, Any] = {
    "actor": "业主",
    "use_cases": [
        {
            "name": "电费管理",
            "includes": ["用户缴费", "用户退费", "查看电费"],
        },
        {
            "name": "水费管理",
            "includes": ["用户缴费", "用户退费", "查看水费"],
        },
        {
            "name": "小区公告",
            "includes": ["用户查看", "公告列表"],
        },
        {
            "name": "业主报修",
            "includes": ["用户报修", "用户处理"],
        },
        {"name": "报修管理", "includes": []},
    ],
}


def _exit_y_for_assoc(index: int, total: int) -> str:
    if total <= 1:
        return "0.5"
    t = index / (total - 1)
    y = 0.3333333333333333 + t * (0.6666666666666666 - 0.3333333333333333)
    return repr(y)


def build_diagram(model: DiagramModel) -> str:
    if not model.use_cases:
        raise ValueError("use_cases 不能为空，至少需要一个二级用例。")
    nsec = len(model.use_cases)
    sec_ids: list[str] = []
    for i in range(nsec):
        if i == 0:
            sec_ids.append("9-5MaiP8lBFPep8I0sSv-3")
        elif i == 1:
            sec_ids.append("9-5MaiP8lBFPep8I0sSv-4")
        elif i == 2:
            sec_ids.append("9-5MaiP8lBFPep8I0sSv-5")
        elif i == 3:
            sec_ids.append("9-5MaiP8lBFPep8I0sSv-6")
        elif i == 4:
            sec_ids.append("9-5MaiP8lBFPep8I0sSv-8")
        else:
            sec_ids.append(f"uc-sec-{i}")

    # ----- 布局：先铺三级，再让二级垂直对齐到对应子集中心；无子级排在栈后 -----
    tert_entries: list[tuple[str, float, int]] = []  # (label, y_top, sec_index)
    y = float(TERT_START_Y)
    sec_y: list[float | None] = [None] * nsec

    for si, sl in enumerate(model.use_cases):
        ch = sl.includes
        if ch:
            tops: list[float] = []
            for name in ch:
                tops.append(y)
                tert_entries.append((name, y, si))
                y += TERT_ROW_STEP
            y += GROUP_PAD
            mid = (tops[0] + ELLIPSE_H / 2.0 + tops[-1] + ELLIPSE_H / 2.0) / 2.0
            sec_y[si] = mid - ELLIPSE_H / 2.0

    max_stack = y - GROUP_PAD
    leaf_y = max_stack + LEAF_AFTER_STACK
    for si, sl in enumerate(model.use_cases):
        if not sl.includes:
            sec_y[si] = leaf_y
            leaf_y += TERT_ROW_STEP + 20

    lines: list[str] = [
        '<mxfile host="app.diagrams.net">',
        f'  <diagram name="{_attr_text(model.diagram_name)}" id="{_attr_text(model.diagram_id)}">',
        f"    <mxGraphModel {MXGRAPH_ATTRS}>",
        "      <root>",
        '        <mxCell id="0" />',
        '        <mxCell id="1" parent="0" />',
    ]

    # 参与者垂直大致居中
    assert all(s is not None for s in sec_y)
    sec_y_f = [float(s) for s in sec_y]
    sec_bottoms = [sec_y_f[i] + ELLIPSE_H for i in range(nsec)]
    tert_bottoms = [e[1] + ELLIPSE_H for e in tert_entries]
    all_bottom = max(sec_bottoms + tert_bottoms + [TERT_START_Y + ACTOR_H])
    all_top = min(sec_y_f[i] for i in range(nsec))
    if tert_entries:
        all_top = min(all_top, min(e[1] for e in tert_entries))
    actor_y = (all_top + all_bottom) / 2.0 - ACTOR_H / 2.0

    aid = model.actor_cell_id
    lines.append(
        f'        <mxCell id="{aid}" parent="1" style="{ACTOR_STYLE}" '
        f'value="{_attr_text(model.actor)}" vertex="1">'
        f'\n          <mxGeometry height="{ACTOR_H}" width="{ACTOR_W}" '
        f'x="{ACTOR_X}" y="{actor_y:.0f}" as="geometry" />'
        f"\n        </mxCell>"
    )

    for i, sl in enumerate(model.use_cases):
        sy = sec_y_f[i]
        sid = sec_ids[i]
        lines.append(
            f'        <mxCell id="{sid}" parent="1" style="{ELLIPSE_STYLE}" '
            f'value="{_attr_text(sl.name)}" vertex="1">'
            f'\n          <mxGeometry height="{ELLIPSE_H}" width="{ELLIPSE_W}" '
            f'x="{SEC_X}" y="{sy:.0f}" as="geometry" />'
            f"\n        </mxCell>"
        )

    assoc_edge_ids = ["9-5MaiP8lBFPep8I0sSv-10", "9-5MaiP8lBFPep8I0sSv-11", "9-5MaiP8lBFPep8I0sSv-12",
                      "9-5MaiP8lBFPep8I0sSv-13", "9-5MaiP8lBFPep8I0sSv-14"]
    for i in range(nsec):
        eid = assoc_edge_ids[i] if i < len(assoc_edge_ids) else f"uc-ae-{i}"
        exit_y = _exit_y_for_assoc(i, nsec)
        sid = sec_ids[i]
        sy = sec_y_f[i]
        tcx = SEC_X
        tcy = sy + ELLIPSE_H * 0.48
        acx = ACTOR_X + ACTOR_W
        acy = actor_y + ACTOR_H * float(exit_y)
        # target 必须是独立 XML 属性，不能写进 style，否则引号会破坏 style="..." 属性。
        style = EDGE_ASSOC_STYLE + f"exitY={exit_y};"
        lines.append(
            f'        <mxCell id="{eid}" edge="1" parent="1" source="{aid}" '
            f'target="{sid}" style="{style}" value="">'
            f"\n          <mxGeometry height=\"50\" relative=\"1\" width=\"50\" as=\"geometry\">"
            f'\n            <mxPoint x="{acx:.0f}" y="{acy:.0f}" as="sourcePoint" />'
            f'\n            <mxPoint x="{tcx:.0f}" y="{tcy:.0f}" as="targetPoint" />'
            f"\n          </mxGeometry>"
            f"\n        </mxCell>"
        )

    # 三级椭圆 id：前几个沿用旧 id 便于 diff，其余 uc-ter-N
    def tert_id(k: int) -> str:
        fixed = {
            0: "9-5MaiP8lBFPep8I0sSv-28",
            1: "9-5MaiP8lBFPep8I0sSv-32",
            2: "9-5MaiP8lBFPep8I0sSv-35",
        }
        return fixed.get(k, f"uc-ter-{k}")

    tert_id_by_index: dict[int, str] = {}
    for k in range(len(tert_entries)):
        tert_id_by_index[k] = tert_id(k)

    for k, (label, yt, _) in enumerate(tert_entries):
        tid = tert_id_by_index[k]
        lines.append(
            f'        <mxCell id="{tid}" parent="1" style="{ELLIPSE_STYLE}" '
            f'value="{_attr_text(label)}" vertex="1">'
            f'\n          <mxGeometry height="{ELLIPSE_H}" width="{ELLIPSE_W}" '
            f'x="{TERT_X}" y="{yt:.0f}" as="geometry" />'
            f"\n        </mxCell>"
        )

    # include 边 + 标签
    include_edge_ids = [
        "9-5MaiP8lBFPep8I0sSv-26",
        "yzy-i2",
        "yzy-i3",
        "9-5MaiP8lBFPep8I0sSv-30",
        "yzy-w2",
        "yzy-w3",
        "9-5MaiP8lBFPep8I0sSv-33",
        "yzy-n2",
        "9-5MaiP8lBFPep8I0sSv-39",
        "yzy-r2",
    ]
    include_label_ids = [
        "9-5MaiP8lBFPep8I0sSv-27",
        "yzy-i2l",
        "yzy-i3l",
        "9-5MaiP8lBFPep8I0sSv-31",
        "yzy-w2l",
        "yzy-w3l",
        "9-5MaiP8lBFPep8I0sSv-34",
        "yzy-n2l",
        "9-5MaiP8lBFPep8I0sSv-40",
        "yzy-r2l",
    ]
    ei = 0
    for si, sl in enumerate(model.use_cases):
        if not sl.includes:
            continue
        idxs = [k for k, e in enumerate(tert_entries) if e[2] == si]
        n = len(idxs)
        sy = sec_y_f[si]
        sec_cy = sy + ELLIPSE_H / 2.0
        for j, tk in enumerate(idxs):
            _, yt, _ = tert_entries[tk]
            tid = tert_id_by_index[tk]
            if n == 1:
                src_y = sec_cy
            else:
                src_y = sec_cy - 12.0 + (24.0 * j / (n - 1))
            tgt_y = yt + ELLIPSE_H * 0.49
            eid = (
                include_edge_ids[ei]
                if ei < len(include_edge_ids)
                else f"uc-ie-{ei}"
            )
            lid = (
                include_label_ids[ei]
                if ei < len(include_label_ids)
                else f"uc-iel-{ei}"
            )
            ei += 1
            lines.append(
                f'        <mxCell id="{eid}" edge="1" parent="1" '
                f'style="{EDGE_INCLUDE_STYLE}" value="">'
                f"\n          <mxGeometry height=\"50\" relative=\"1\" width=\"50\" as=\"geometry\">"
                f'\n            <mxPoint x="{SRC_EDGE_X}" y="{src_y:.0f}" as="sourcePoint" />'
                f'\n            <mxPoint x="{TERT_X}" y="{tgt_y:.0f}" as="targetPoint" />'
                f"\n          </mxGeometry>"
                f"\n        </mxCell>"
            )
            lines.append(
                f'        <mxCell id="{lid}" connectable="0" parent="{eid}" '
                f'style="{EDGE_LABEL_STYLE}" value="{INCLUDE_STEREO_XML}" vertex="1">'
                f'\n          <mxGeometry relative="1" x="-0.1257" as="geometry">'
                f"\n            <mxPoint as=\"offset\" />"
                f"\n          </mxGeometry>"
                f"\n        </mxCell>"
            )

    lines.extend(
        [
            "      </root>",
            "    </mxGraphModel>",
            "  </diagram>",
            "</mxfile>",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="按数据模型生成用例图 draw.io XML")
    p.add_argument(
        "-c",
        "--config",
        help="JSON 配置文件（缺省使用内置业主示例）",
    )
    p.add_argument(
        "-o",
        "--output",
        default="用例图.xml",
        help="输出 XML 路径（默认：用例图.xml）",
    )
    args = p.parse_args()
    if args.config:
        with open(args.config, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = DEFAULT_MODEL_JSON
    model = DiagramModel.from_dict(data)
    xml = build_diagram(model)
    out = args.output
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(xml)
    print(f"Wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
