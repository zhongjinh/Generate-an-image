#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""登录失败锁定"""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.config import LOGIN_LOCKOUT_MINUTES, LOGIN_MAX_FAILURES


def _parse_time(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def is_account_locked(row: dict) -> tuple[bool, int]:
    locked_until = _parse_time(row.get("locked_until"))
    if locked_until and locked_until > datetime.now():
        remaining = int((locked_until - datetime.now()).total_seconds())
        return True, max(1, remaining // 60 or 1)
    return False, 0


def record_login_failure(cur, user_id: int) -> None:
    cur.execute(
        "SELECT login_failures FROM user WHERE id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    failures = int(row["login_failures"] or 0) + 1
    if failures >= LOGIN_MAX_FAILURES:
        locked_until = (datetime.now() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        cur.execute(
            "UPDATE user SET login_failures = %s, locked_until = %s WHERE id = %s",
            (failures, locked_until, user_id),
        )
    else:
        cur.execute(
            "UPDATE user SET login_failures = %s WHERE id = %s",
            (failures, user_id),
        )


def reset_login_failures(cur, user_id: int) -> None:
    cur.execute(
        "UPDATE user SET login_failures = 0, locked_until = NULL WHERE id = %s",
        (user_id,),
    )
