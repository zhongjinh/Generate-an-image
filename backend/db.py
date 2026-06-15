#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite 数据库初始化与连接"""

from __future__ import annotations

import sqlite3

from backend.config import ADMIN_PASSWORD, DB_PATH, REGISTER_FREE_COUNT

DEFAULT_PACKAGES = [
    ("日卡", "day", 9.9, 50, 1),
    ("周卡", "week", 49.9, 300, 7),
    ("月卡", "month", 149.9, 1500, 30),
    ("年卡", "year", 999.9, 20000, 365),
]


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            phone TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0,
            remain_count INTEGER DEFAULT 0,
            vip_type TEXT DEFAULT '',
            vip_expire_time TEXT DEFAULT '',
            create_time TEXT DEFAULT (datetime('now', 'localtime')),
            is_disabled INTEGER DEFAULT 0
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vip_package (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT NOT NULL,
            type TEXT NOT NULL,
            price REAL NOT NULL,
            total_count INTEGER NOT NULL,
            valid_days INTEGER NOT NULL,
            is_enable INTEGER DEFAULT 1
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS order_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            package_id INTEGER NOT NULL,
            pay_amount REAL NOT NULL,
            pay_status TEXT DEFAULT 'pending',
            create_time TEXT DEFAULT (datetime('now', 'localtime')),
            finish_time TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES user(id),
            FOREIGN KEY (package_id) REFERENCES vip_package(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS file_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            json_content TEXT DEFAULT '',
            xml_content TEXT DEFAULT '',
            chart_type TEXT DEFAULT '',
            title TEXT DEFAULT '',
            create_time TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES user(id)
        )
        """
    )

    cur.execute("SELECT COUNT(*) FROM vip_package")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO vip_package (package_name, type, price, total_count, valid_days) VALUES (?, ?, ?, ?, ?)",
            DEFAULT_PACKAGES,
        )

    cur.execute("SELECT COUNT(*) FROM user WHERE username = 'admin'")
    if cur.fetchone()[0] == 0:
        from backend.auth import hash_password

        cur.execute(
            "INSERT INTO user (username, password, is_admin, remain_count) VALUES (?, ?, 1, ?)",
            ("admin", hash_password(ADMIN_PASSWORD), 99999),
        )

    conn.commit()
    conn.close()
