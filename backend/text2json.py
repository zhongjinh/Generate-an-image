#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本缩进格式转 JSON 格式

支持所有图表类型：
- module: 功能模块图
- usecase: 用例图
- er: E-R图
- activity: 活动图
- architecture: 架构图
- class: 类图
- flowchart: 流程图
- attribute: 属性图（支持 SQL 建表语句）
- sequence: 序列图
"""

from __future__ import annotations

import json
import re
from typing import Any


def parse_indent_text(text: str, chart_type: str = "module") -> dict[str, Any]:
    """
    解析缩进格式文本，转换为对应图表类型的 JSON

    规则：
    - 第一行（无缩进）= 标题
    - 第二级（2空格缩进）= 角色/分类/实体名称
    - 第三级（4空格缩进）= 模块/属性/步骤
    """
    if chart_type == "er":
        return _parse_er_text(text)
    if chart_type == "usecase":
        return _parse_usecase_text(text)
    if chart_type == "attribute":
        return _parse_attribute_sql(text)

    lines = text.strip().split('\n')
    if not lines:
        raise ValueError("输入内容为空")

    # 解析第一行作为标题
    title = lines[0].strip()
    if not title:
        raise ValueError("第一行必须是标题")

    # 解析后续行
    items_level2 = []  # 二级项
    items_level3 = []  # 三级项
    current_item = None

    for line in lines[1:]:
        if not line.strip():
            continue  # 跳过空行

        # 计算缩进级别
        indent = len(line) - len(line.lstrip())
        content = line.strip()

        if indent == 0:
            # 顶级内容，可能是标题的一部分
            title = content
        elif indent == 2:
            # 二级缩进
            current_item = {"name": content, "children": []}
            items_level2.append(current_item)
        elif indent >= 4:
            # 三级或更深缩进
            if current_item is None:
                current_item = {"name": "默认", "children": []}
                items_level2.append(current_item)
            current_item["children"].append(content)

    # 根据图表类型生成对应的 JSON
    return _build_chart_json(title, items_level2, chart_type)


def _build_chart_json(title: str, items: list, chart_type: str) -> dict:
    """根据图表类型构建对应的 JSON 结构"""

    if chart_type == "module":
        return _build_module(title, items)
    elif chart_type == "er":
        return _build_er(title, items)
    elif chart_type == "activity":
        return _build_activity(title, items)
    elif chart_type == "architecture":
        return _build_architecture(title, items)
    elif chart_type == "class":
        return _build_class(title, items)
    elif chart_type == "flowchart":
        return _build_flowchart(title, items)
    elif chart_type == "attribute":
        return _build_attribute(title, items)
    elif chart_type == "sequence":
        return _build_sequence(title, items)
    else:
        # 默认为功能模块图
        return _build_module(title, items)


def _build_module(title: str, items: list) -> dict:
    """功能模块图"""
    roles = []
    for item in items:
        roles.append({
            "name": item["name"],
            "modules": item["children"]
        })
    return {
        "type": "module",
        "title": title,
        "roles": roles
    }


def _parse_usecase_text(text: str) -> dict[str, Any]:
    """
    用例图文本格式：

    车主
      故障报修
        提交故障报修
        查询报修进度
      保养预约
        预约车辆保养

    - 第一行：参与者
    - 2 空格缩进：用例分组
    - 4 空格缩进：包含的子用例
    """
    lines = text.strip().split("\n")
    if not lines:
        raise ValueError("输入内容为空")

    actor = lines[0].strip()
    if not actor:
        raise ValueError("第一行必须是参与者")

    items_level2: list[dict[str, Any]] = []
    current_item: dict[str, Any] | None = None

    for line in lines[1:]:
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip())
        content = line.strip()

        if indent == 0:
            raise ValueError(f"用例行请使用缩进（参与者仅第一行）: {content}")
        if indent == 2:
            current_item = {"name": content, "children": []}
            items_level2.append(current_item)
        elif indent >= 4:
            if current_item is None:
                raise ValueError(f"子用例「{content}」需放在用例分组下（4 个空格缩进）")
            current_item["children"].append(content)

    return _build_usecase(actor, items_level2)


def _build_usecase(actor: str, items: list) -> dict:
    """用例图：第一行=参与者，二级=用例分组，三级=包含用例"""
    use_cases = []
    for item in items:
        use_cases.append({
            "name": item["name"],
            "includes": list(item["children"]) if item["children"] else [],
        })
    if not use_cases:
        raise ValueError("请至少输入一个用例（2 个空格缩进）")
    return {
        "type": "usecase",
        "title": actor,
        "diagram_name": f"{actor}用例图",
        "actor": actor,
        "use_cases": use_cases,
    }


def _parse_attribute_sql(text: str) -> dict[str, Any]:
    """属性图：直接粘贴 MySQL CREATE TABLE 建表语句"""
    sql = text.strip()
    if not sql:
        raise ValueError("请输入建表 SQL")
    if "CREATE TABLE" not in sql.upper():
        raise ValueError("请粘贴 MySQL CREATE TABLE 建表语句")
    return {
        "type": "attribute",
        "title": _guess_attribute_title(sql),
        "sql": sql,
    }


def _guess_attribute_title(sql: str) -> str:
    m = re.search(r"COMMENT\s*=\s*['\"]([^'\"]+)['\"]", sql, re.I)
    if m:
        name = m.group(1).strip()
        if name.endswith("表"):
            name = name[:-1]
        return f"{name}实体属性图"
    m = re.search(r"CREATE\s+TABLE\s+`?(\w+)`?", sql, re.I)
    if m:
        return f"{m.group(1)}实体属性图"
    return "实体属性图"


def _normalize_cardinality(raw: str) -> str:
    """将 1对多、一对多 等转为 1:N"""
    s = raw.strip().replace("：", ":").replace(" ", "")
    mapping = {
        "1对多": "1:N",
        "一对多": "1:N",
        "1比多": "1:N",
        "1对1": "1:1",
        "一对一": "1:1",
        "1比1": "1:1",
        "多对多": "N:M",
        "多对一": "N:1",
        "多对1": "N:1",
    }
    if s in mapping:
        return mapping[s]
    upper = s.upper()
    if re.match(r"^[1NM]+:[1NM]+$", upper):
        return upper
    raise ValueError(f"无法识别的基数格式: {raw}（支持 1:N、1:1、N:M、1对多 等）")


def _is_cardinality_token(token: str) -> bool:
    try:
        _normalize_cardinality(token)
        return True
    except ValueError:
        return False


def _parse_er_text(text: str) -> dict[str, Any]:
    """
  E-R 图文本格式：

  电商系统 ER 图
    用户
    订单
    商品
  ---
    用户 创建 订单 1:N
    用户 发表 评价 1:N
    商品 被评价 评价 1:N

  - 第一行：标题
  - `---` 上方：实体名（2 空格缩进，仅名称，无属性）
  - `---` 下方：关系行「实体A 关系名 实体B 基数」（2 空格缩进）
  - 基数支持：1:N、1:1、N:M、1对多、一对多、多对多 等；省略时默认 1:N
    """
    lines = text.strip().split("\n")
    if not lines:
        raise ValueError("输入内容为空")

    title = lines[0].strip()
    if not title:
        raise ValueError("第一行必须是标题")

    entities: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    section = "entities"

    def _add_relationship(line: str) -> None:
        # 用户 创建 订单 1:N / 用户 创建 订单 1对多
        parts = line.split()
        if len(parts) < 3:
            raise ValueError(f"关系行格式错误（需：实体A 关系名 实体B [基数]）: {line}")

        cardinality = "1:N"
        if _is_cardinality_token(parts[-1]):
            cardinality = _normalize_cardinality(parts[-1])
            parts = parts[:-1]

        if len(parts) < 3:
            raise ValueError(f"关系行格式错误（需：实体A 关系名 实体B [基数]）: {line}")

        rel = {
            "from": parts[0],
            "label": parts[1],
            "name": parts[1],
            "to": parts[2],
            "type": cardinality,
            "cardinality": cardinality,
        }
        relationships.append(rel)

    for line in lines[1:]:
        if not line.strip():
            continue

        stripped = line.strip()
        bare = stripped.rstrip(":").strip()

        if stripped == "---":
            section = "relationships"
            continue
        if bare in ("实体", "entities", "Entities"):
            section = "entities"
            continue
        if bare in ("关系", "relationships", "Relationships"):
            section = "relationships"
            continue

        indent = len(line) - len(line.lstrip())

        if section == "entities":
            if indent >= 2:
                entities.append({"name": stripped})
            else:
                raise ValueError(f"实体行请使用 2 个空格缩进: {stripped}")
        else:
            if indent < 2:
                raise ValueError(f"关系行请使用 2 个空格缩进: {stripped}")
            _add_relationship(stripped)

    if not entities:
        raise ValueError("请至少输入一个实体（--- 上方）")
    if not relationships:
        raise ValueError("请至少输入一条关系（--- 下方，格式：实体A 关系名 实体B [基数]）")

    entity_names = {e["name"] for e in entities}
    for rel in relationships:
        if rel["from"] not in entity_names:
            raise ValueError(f"关系中的实体不存在: {rel['from']}")
        if rel["to"] not in entity_names:
            raise ValueError(f"关系中的实体不存在: {rel['to']}")

    return {
        "type": "er",
        "title": title,
        "entities": entities,
        "relationships": relationships,
    }


def _build_er(title: str, items: list) -> dict:
    """E-R图（旧缩进格式，仅实体+属性，无关系）"""
    entities = []
    for item in items:
        attributes = []
        for child in item["children"]:
            # 解析属性格式：字段名 类型 约束
            parts = child.split()
            if len(parts) >= 2:
                attr = {
                    "name": parts[0],
                    "type": parts[1]
                }
                if len(parts) >= 3:
                    attr["constraint"] = " ".join(parts[2:])
                attributes.append(attr)
            else:
                attributes.append({"name": child, "type": "VARCHAR"})
        entities.append({
            "name": item["name"],
            "attributes": attributes
        })
    return {
        "type": "er",
        "title": title,
        "entities": entities
    }


def _build_activity(title: str, items: list) -> dict:
    """活动图"""
    steps = []
    for item in items:
        step = {
            "name": item["name"],
            "type": "normal"
        }
        if item["children"]:
            step["details"] = item["children"]
        steps.append(step)
    return {
        "type": "activity",
        "title": title,
        "steps": steps
    }


def _build_architecture(title: str, items: list) -> dict:
    """架构图"""
    layers = []
    for item in items:
        layer = {
            "name": item["name"],
            "components": item["children"]
        }
        layers.append(layer)
    return {
        "type": "architecture",
        "title": title,
        "layers": layers
    }


def _build_class(title: str, items: list) -> dict:
    """类图"""
    classes = []
    for item in items:
        cls = {
            "name": item["name"],
            "attributes": [],
            "methods": []
        }
        for child in item["children"]:
            # 判断是属性还是方法（包含括号的是方法）
            if "(" in child and ")" in child:
                cls["methods"].append(child)
            else:
                cls["attributes"].append(child)
        classes.append(cls)
    return {
        "type": "class",
        "title": title,
        "classes": classes
    }


def _build_flowchart(title: str, items: list) -> dict:
    """流程图"""
    nodes = []
    for i, item in enumerate(items):
        node = {
            "id": f"node_{i+1}",
            "label": item["name"],
            "type": "normal"
        }
        nodes.append(node)

    # 构建连线
    edges = []
    for i in range(len(nodes) - 1):
        edges.append({
            "from": f"node_{i+1}",
            "to": f"node_{i+2}"
        })

    return {
        "type": "flowchart",
        "title": title,
        "nodes": nodes,
        "edges": edges
    }


def _build_attribute(title: str, items: list) -> dict:
    """属性图（支持 SQL 建表语句）"""
    # 如果有子项，直接作为 SQL 使用
    sql_parts = []
    for item in items:
        # 将子项作为 CREATE TABLE 语句
        if item["children"]:
            # 构建 CREATE TABLE 语句
            columns = []
            for child in item["children"]:
                columns.append(f"    {child}")
            sql = f"CREATE TABLE {item['name']} (\n" + ",\n".join(columns) + "\n);"
            sql_parts.append(sql)
        else:
            # 如果没有子项，直接作为 SQL 语句
            sql_parts.append(item["name"])

    return {
        "type": "attribute",
        "title": title,
        "sql": "\n\n".join(sql_parts)
    }


def _build_sequence(title: str, items: list) -> dict:
    """序列图"""
    participants = []
    messages = []

    for item in items:
        participants.append(item["name"])
        # 为每个参与者添加消息
        for child in item["children"]:
            messages.append({
                "from": item["name"],
                "to": participants[0] if participants else "未知",
                "text": child
            })

    return {
        "type": "sequence",
        "title": title,
        "participants": participants,
        "messages": messages
    }


def text_to_json(text: str, chart_type: str = "module") -> str:
    """将缩进格式文本转换为 JSON 字符串"""
    data = parse_indent_text(text, chart_type)
    return json.dumps(data, ensure_ascii=False, indent=2)


def text_to_dict(text: str, chart_type: str = "module") -> dict:
    """将缩进格式文本转换为字典"""
    return parse_indent_text(text, chart_type)


# 测试代码
if __name__ == "__main__":
    test_text = """社区电商平台
  用户端
    首页展示
    商品搜索
    商品分类
  管理端
    数据看板
    商品上架"""

    print("输入文本：")
    print(test_text)
    print("\n功能模块图：")
    print(text_to_json(test_text, "module"))
    print("\n用例图：")
    print(text_to_json(test_text, "usecase"))
