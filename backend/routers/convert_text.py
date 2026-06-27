#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本格式转换 API
支持缩进格式文本转 JSON 图表配置
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.text2json import text_to_dict
from backend.vip import require_vip_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["convert"])


class ConvertTextBody(BaseModel):
    text: str
    chart_type: str = "module"  # 默认为功能模块图


@router.post("/api/convert-text")
def convert_text(body: ConvertTextBody, _user: dict = Depends(require_vip_user)):
    """
    将缩进格式文本转换为 JSON 图表配置

    输入格式（每级缩进2个空格）：
    社区电商平台
      用户端
        首页展示
        商品搜索
      管理端
        数据看板

    输出：标准的图表 JSON 配置
    """
    try:
        text = body.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail={"error": "输入内容为空"})

        # 转换为 JSON
        result = text_to_dict(text, body.chart_type)

        # 设置图表类型
        result["type"] = body.chart_type

        if body.chart_type == "er":
            ent_n = len(result.get("entities", []))
            rel_n = len(result.get("relationships", []))
            logger.info("文本转换成功: title=%s, entities=%d, relationships=%d", result.get("title"), ent_n, rel_n)
            return {
                "success": True,
                "json": result,
                "message": f"转换成功，共 {ent_n} 个实体、{rel_n} 条关系",
            }

        if body.chart_type == "usecase":
            uc_n = len(result.get("use_cases", []))
            actor = result.get("actor", "用户")
            logger.info("文本转换成功: title=%s, actor=%s, use_cases=%d", result.get("title"), actor, uc_n)
            return {
                "success": True,
                "json": result,
                "message": f"转换成功，参与者「{actor}」，共 {uc_n} 个用例",
            }

        if body.chart_type == "attribute":
            logger.info("文本转换成功: title=%s (SQL)", result.get("title"))
            return {
                "success": True,
                "json": result,
                "message": f"转换成功：{result.get('title', '属性图')}",
            }

        count = len(result.get("roles") or [])
        logger.info("文本转换成功: title=%s, count=%d", result.get("title"), count)

        return {
            "success": True,
            "json": result,
            "message": f"转换成功，共 {count} 项",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except Exception as e:
        logger.error("文本转换失败: %s", str(e))
        raise HTTPException(status_code=500, detail={"error": "转换失败，请检查输入格式"})


@router.post("/api/convert-text-example")
def get_convert_example():
    """
    获取文本格式示例
    """
    examples = {
        "module": {
            "name": "功能模块图",
            "text": """在线教育平台
  学生端
    课程浏览
    视频学习
    在线练习
    考试测评
    学习记录
    证书领取
    讨论交流
    个人中心
  教师端
    课程管理
    课件上传
    作业批改
    考试出题
    成绩统计
    学生管理
    直播授课
    答疑解惑
  管理端
    平台数据
    用户管理
    课程审核
    财务管理
    内容监管
    系统设置"""
        },
        "er": {
            "name": "E-R 图",
            "text": """电商系统 ER 图
  管理员
  用户
  订单
  订单详情
  购物车
  公告
---
  管理员 管理 用户 1:N
  用户 创建 订单 1:N
  订单 包含 订单详情 1:N
  用户 创建 购物车 1:N
  用户 查看 公告 1:N
  购物车 包含 订单 1:N"""
        },
        "usecase": {
            "name": "用例图",
            "text": """车主
  故障报修
    提交故障报修
    查询报修进度
    取消报修
  保养预约
    预约车辆保养
    查询预约记录
    取消预约
  维修查询
    查询维修订单
    查询维修信息
  留言反馈
    留言交流
    提交意见反馈
  公告服务
    浏览公告
    查看聊天记录
  个人中心
    收藏服务
    修改个人信息"""
        },
        "attribute": {
            "name": "属性图",
            "text": """CREATE TABLE `user` (
  `user_id` VARCHAR(64) PRIMARY KEY COMMENT '用户ID',
  `username` VARCHAR(64) COMMENT '用户名',
  `password` VARCHAR(64) COMMENT '密码',
  `nickname` VARCHAR(64) COMMENT '昵称',
  `phone` VARCHAR(20) COMMENT '手机号',
  `email` VARCHAR(64) COMMENT '邮箱',
  `role` VARCHAR(32) COMMENT '角色',
  `balance` DECIMAL(10,2) COMMENT '账户余额',
  `last_login` DATETIME COMMENT '最后登录时间'
) COMMENT='用户';"""
        },
    }

    return {"examples": examples}
