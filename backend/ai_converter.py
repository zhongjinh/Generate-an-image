#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自然语言 → 图表 JSON（DeepSeek API）"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

from backend.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
from backend.python_convert.adapters import normalize

logger = logging.getLogger(__name__)

AI_CHART_TYPES = frozenset({"flowchart", "architecture", "activity", "class", "sequence"})

_SYSTEM = (
    "你是专业的软件工程图表配置生成器。"
    "根据用户的自然语言描述，生成严格符合 schema 的 JSON 配置。"
    "只输出一个 JSON 对象，不要 markdown 代码块，不要任何解释文字。"
)

_SCHEMA_HINTS: dict[str, str] = {
    "flowchart": """
图表类型：flowchart（流程图）
JSON 格式：
{
  "type": "flowchart",
  "title": "流程标题",
  "steps": [
    {"id": 1, "type": "开始", "text": "开始"},
    {"id": 2, "type": "输入", "text": "输入账号密码"},
    {"id": 3, "type": "处理", "text": "验证账号"},
    {"id": 4, "type": "判断", "text": "验证通过？", "branches": {"否": 2}},
    {"id": 5, "type": "输出", "text": "跳转首页"},
    {"id": 6, "type": "结束", "text": "结束"}
  ]
}
步骤 type 只能是：开始、结束、输入、输出、处理、判断。
判断节点的「是」默认连到 id+1；「否」等在 branches 里指定目标 id。
steps 至少 3 步，id 从 1 连续递增。
""",
    "architecture": """
图表类型：architecture（系统架构图）
JSON 格式：
{
  "type": "architecture",
  "title": "系统架构图标题",
  "links": ["HTTP/HTTPS", "JDBC/SQL"],
  "layers": [
    {
      "name": "前端交互层",
      "groups": [
        {"name": "用户端", "nodes": ["注册登录", "商品浏览"]},
        {"name": "管理端", "nodes": ["用户管理", "订单管理"]}
      ]
    },
    {
      "name": "后端业务层",
      "groups": [
        {"name": "业务接口", "nodes": ["用户鉴权", "订单服务"]}
      ]
    },
    {
      "name": "数据持久层",
      "groups": [
        {"name": "MySQL", "nodes": ["用户数据", "订单数据"]}
      ]
    }
  ]
}
layers 通常 2-4 层；links 长度 = layers 数 - 1。
""",
    "activity": """
图表类型：activity（活动图 / UML 活动图）
JSON 格式（使用 nodes + flows，不要用 match_text）：
{
  "type": "activity",
  "title": "活动图标题",
  "nodes": [
    {"id": "start", "name": "开始", "type": "start"},
    {"id": "a1", "name": "填写表单", "type": "action"},
    {"id": "d1", "name": "是否通过?", "type": "decision"},
    {"id": "end", "name": "结束", "type": "end"}
  ],
  "flows": [
    {"from": "start", "to": "a1"},
    {"from": "a1", "to": "d1"},
    {"from": "d1", "to": "end", "label": "是"},
    {"from": "d1", "to": "a1", "label": "否"}
  ]
}
节点 type：start、end、action、decision。至少包含 start、end 和一个 action。
""",
    "class": """
图表类型：class（UML 类图）
JSON 格式：
{
  "type": "class",
  "title": "类图标题",
  "classes": [
    {
      "name": "User",
      "attributes": ["- id: Long", "- username: String"],
      "methods": ["+ login(): boolean", "+ logout(): void"]
    },
    {
      "name": "Order",
      "attributes": ["- orderId: String", "- amount: BigDecimal"],
      "methods": ["+ pay(): void"]
    }
  ],
  "relationships": [
    {"from": "User", "to": "Order", "type": "association"}
  ]
}
relationships 的 type 可用：inheritance、association、composition、aggregation。
属性和方法用 UML 可见性前缀：+ public、- private、# protected。
""",
    "sequence": """
图表类型：sequence（UML 序列图）
JSON 格式（使用 plantuml 字段）：
{
  "type": "sequence",
  "title": "序列图标题",
  "plantuml": "@startuml\\nactor \\"用户\\" as User\\nparticipant \\"前端\\" as FE\\nparticipant \\"服务\\" as API\\ndatabase \\"数据库\\" as DB\\nUser -> FE: 1. 输入账号\\nFE -> API: 2. 提交登录\\nAPI -> DB: 3. 查询用户\\nDB --> API: 4. 返回数据\\nAPI --> FE: 5. 登录成功\\nFE --> User: 6. 跳转首页\\n@enduml"
}
plantuml 必须是完整 PlantUML 序列图，以 @startuml 开头、@enduml 结尾。
参与者 3-6 个，消息 5-12 条，使用中文标注。
""",
}


def _extract_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            raise ValueError(f"AI 返回内容无法解析为 JSON: {exc}") from exc
        data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise ValueError("AI 返回的 JSON 必须是对象")
    return data


def _call_deepseek(system: str, user: str) -> str:
    if not DEEPSEEK_API_KEY:
        raise ValueError("AI 服务未配置，请在 .env 中设置 DEEPSEEK_API_KEY")
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.error("DeepSeek API 错误 %s: %s", exc.code, detail)
        raise ValueError(f"AI 服务请求失败 ({exc.code})") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"AI 服务连接失败: {exc.reason}") from exc

    choices = result.get("choices") or []
    if not choices:
        raise ValueError("AI 服务返回为空")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("AI 服务未返回内容")
    return content


def natural_language_to_dict(text: str, chart_type: str) -> dict[str, Any]:
    chart_type = chart_type.strip().lower()
    if chart_type not in AI_CHART_TYPES:
        raise ValueError(f"不支持 AI 转换的图表类型: {chart_type}")

    user_text = text.strip()
    if not user_text:
        raise ValueError("请输入自然语言描述")

    schema = _SCHEMA_HINTS[chart_type]
    system = f"{_SYSTEM}\n\n{schema}"
    user_prompt = f"请根据以下描述生成 {chart_type} 图表的 JSON 配置：\n\n{user_text}"

    logger.info("AI 转换开始: chart_type=%s, len=%d", chart_type, len(user_text))
    content = _call_deepseek(system, user_prompt)
    data = _extract_json(content)
    data["type"] = chart_type

    if not data.get("title"):
        data["title"] = user_text[:30]

    normalized = normalize(data)
    return normalized
