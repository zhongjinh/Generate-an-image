#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MySQL 数据库初始化与连接"""

from __future__ import annotations

import pymysql
import pymysql.cursors

from backend.config import (
    ADMIN_PASSWORD,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
    REGISTER_FREE_COUNT,
)

DEFAULT_PACKAGES = [
    ("日卡", "day", 9.9, 50, 1),
    ("周卡", "week", 49.9, 300, 7),
    ("月卡", "month", 149.9, 1500, 30),
    ("年卡", "year", 999.9, 20000, 365),
]


def _get_server_conn():
    """获取不指定数据库的连接（用于创建数据库）"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_db() -> pymysql.Connection:
    """获取数据库连接"""
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=15,
    )
    return conn


def init_db() -> None:
    # 先创建数据库（如果不存在）
    conn = _get_server_conn()
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    conn.close()

    # 连接到目标数据库，创建表
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `user` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `username` VARCHAR(255) NOT NULL UNIQUE,
                `password` VARCHAR(255) NOT NULL,
                `email` VARCHAR(255) DEFAULT NULL,
                `phone` VARCHAR(50) DEFAULT '',
                `is_admin` TINYINT DEFAULT 0,
                `remain_count` INT DEFAULT 0,
                `vip_type` VARCHAR(50) DEFAULT '',
                `vip_expire_time` VARCHAR(50) DEFAULT '',
                `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
                `is_disabled` TINYINT DEFAULT 0,
                UNIQUE INDEX `idx_user_email` (`email`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `email_verification` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `email` VARCHAR(255) NOT NULL,
                `code` VARCHAR(10) NOT NULL,
                `purpose` VARCHAR(50) DEFAULT 'register',
                `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                `expires_at` DATETIME NOT NULL,
                `used` TINYINT DEFAULT 0,
                INDEX `idx_ev_email` (`email`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `vip_package` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `package_name` VARCHAR(100) NOT NULL,
                `type` VARCHAR(50) NOT NULL,
                `price` DECIMAL(10,2) NOT NULL,
                `total_count` INT NOT NULL,
                `valid_days` INT NOT NULL,
                `is_enable` TINYINT DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `order_record` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `order_id` VARCHAR(100) NOT NULL UNIQUE,
                `user_id` INT NOT NULL,
                `package_id` INT NOT NULL,
                `pay_amount` DECIMAL(10,2) NOT NULL,
                `pay_status` VARCHAR(20) DEFAULT 'pending',
                `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
                `finish_time` DATETIME DEFAULT NULL,
                FOREIGN KEY (`user_id`) REFERENCES `user`(`id`),
                FOREIGN KEY (`package_id`) REFERENCES `vip_package`(`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `file_record` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `user_id` INT NOT NULL,
                `json_content` LONGTEXT,
                `xml_content` LONGTEXT,
                `chart_type` VARCHAR(50) DEFAULT '',
                `title` VARCHAR(255) DEFAULT '',
                `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (`user_id`) REFERENCES `user`(`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        # 插入默认 VIP 套餐
        cur.execute("SELECT COUNT(*) AS cnt FROM `vip_package`")
        if cur.fetchone()["cnt"] == 0:
            cur.executemany(
                "INSERT INTO `vip_package` (`package_name`, `type`, `price`, `total_count`, `valid_days`) "
                "VALUES (%s, %s, %s, %s, %s)",
                DEFAULT_PACKAGES,
            )

        # 插入管理员账号
        cur.execute("SELECT COUNT(*) AS cnt FROM `user` WHERE `username` = 'admin'")
        if cur.fetchone()["cnt"] == 0:
            from backend.auth import hash_password

            cur.execute(
                "INSERT INTO `user` (`username`, `password`, `is_admin`, `remain_count`) VALUES (%s, %s, 1, %s)",
                ("admin", hash_password(ADMIN_PASSWORD), 99999),
            )

    conn.commit()
    conn.close()
