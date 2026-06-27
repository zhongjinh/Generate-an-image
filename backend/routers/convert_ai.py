#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自然语言 AI 转 JSON API"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.ai_converter import AI_CHART_TYPES, natural_language_to_dict
from backend.vip import require_vip_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["convert"])


class ConvertAiBody(BaseModel):
    text: str
    chart_type: str


@router.post("/api/convert-ai")
def convert_ai(body: ConvertAiBody, _user: dict = Depends(require_vip_user)):
    """自然语言描述 → 图表 JSON（DeepSeek）"""
    try:
        chart_type = body.chart_type.strip().lower()
        if chart_type not in AI_CHART_TYPES:
            raise HTTPException(
                status_code=400,
                detail={"error": f"该图表类型不支持 AI 转换: {chart_type}"},
            )

        result = natural_language_to_dict(body.text, chart_type)
        result["type"] = chart_type

        logger.info("AI 转换成功: type=%s, title=%s", chart_type, result.get("title"))
        return {
            "success": True,
            "json": result,
            "message": f"AI 转换成功：{result.get('title', '')}",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)}) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI 转换失败: %s", str(e))
        raise HTTPException(status_code=500, detail={"error": "AI 转换失败，请稍后重试"}) from e


@router.post("/api/convert-ai-example")
def get_ai_example():
    """各 AI 图表类型的自然语言示例"""
    examples = {
        "flowchart": {
            "name": "流程图",
            "text": "用户登录流程：开始，输入账号密码，验证账号，判断是否通过，不通过则返回重新输入，通过则加载用户信息并跳转首页，结束。",
        },
        "architecture": {
            "name": "架构图",
            "text": "电商系统三层架构：前端有用户端（注册登录、商品浏览、下单支付）和管理端（用户管理、商品管理、订单管理）；后端有业务接口层（鉴权、订单服务、支付服务）和缓存层（Redis会话）；数据层 MySQL 存用户和订单数据，Redis 存会话。层间用 HTTP 和 JDBC 连接。",
        },
        "activity": {
            "name": "活动图",
            "text": "论坛发帖流程：用户登录系统，进入论坛，填写标题和内容，系统进行敏感词校验，若包含敏感词则提示修改并返回填写，若不包含则保存帖子并增加积分，最后显示发布结果，结束。",
        },
        "class": {
            "name": "类图",
            "text": "在线商城类图：User 类有 id、username、password 属性和 login、register 方法；Product 类有 productId、name、price 属性和 getDetail 方法；Order 类有 orderId、totalAmount 属性和 create、pay 方法。User 与 Order 是关联关系，Order 与 Product 是关联关系。",
        },
        "sequence": {
            "name": "序列图",
            "text": "用户登录序列图：用户向前端输入账号密码，前端调用登录接口，登录接口请求认证服务，认证服务查询数据库，数据库返回用户信息，认证服务返回 token，登录接口返回成功，前端跳转首页。",
        },
    }
    return {"examples": examples}
