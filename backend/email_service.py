#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发送邮件验证码"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from backend.config import (
    DEBUG,
    SMTP_FROM,
    SMTP_FROM_NAME,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
    SMTP_PASSWORD,
)

logger = logging.getLogger(__name__)
SMTP_TIMEOUT = 15


def send_verification_code(to_email: str, code: str) -> None:
    if SMTP_HOST == "console":
        print(f"[SMTP console] 收件人: {to_email}  验证码: {code}")
        return

    subject = "图表在线生成器 - 注册验证码"
    body = (
        f"您的注册验证码是：{code}\n\n"
        "验证码 10 分钟内有效，请勿泄露给他人。\n\n"
        "如非本人操作，请忽略此邮件。"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr((SMTP_FROM_NAME, SMTP_FROM))
    msg["To"] = to_email

    try:
        if SMTP_USE_TLS:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(SMTP_USER, SMTP_PASSWORD)
                refused = server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                refused = server.send_message(msg)

        if refused:
            raise smtplib.SMTPException(f"部分收件人被拒: {refused}")
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        logger.exception("SMTP 发送失败: %s", to_email)
        raise RuntimeError(f"邮件发送失败: {exc}") from exc

    print(f"[SMTP] 验证码已发送至 {to_email}")
    logger.info("验证码已发送至 %s", to_email)
    if DEBUG:
        logger.debug("验证码: %s", code)
