#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MySQL 数据库初始化与连接"""

from __future__ import annotations

import pymysql
import pymysql.cursors

from backend.config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
    REGISTER_FREE_COUNT,
)

DEFAULT_PACKAGES = [
    ("半小时", "half_hour", 1.9, 0, 0.0208),   # 30分钟 = 0.0208天
    ("1小时", "hour", 2.9, 0, 0.0417),         # 1小时 = 0.0417天
    ("2小时", "two_hour", 4.9, 0, 0.0833),     # 2小时 = 0.0833天
    ("日卡", "day", 6.9, 0, 1),
    ("周卡", "week", 29.9, 0, 7),
    ("月卡", "month", 69.9, 0, 30),
    ("年卡", "year", 399.9, 0, 365),
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
                `valid_days` DECIMAL(10,4) NOT NULL,
                `buy_link` VARCHAR(500) DEFAULT '',
                `is_enable` TINYINT DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        # 迁移：修改 valid_days 为 DECIMAL 类型
        cur.execute(
            f"SELECT DATA_TYPE FROM information_schema.COLUMNS "
            f"WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'vip_package' AND COLUMN_NAME = 'valid_days'",
            (MYSQL_DATABASE,),
        )
        col_type = cur.fetchone()
        if col_type and col_type["DATA_TYPE"] == "int":
            cur.execute("ALTER TABLE `vip_package` MODIFY COLUMN `valid_days` DECIMAL(10,4) NOT NULL")

        # 迁移：为 vip_package 添加 buy_link 字段
        cur.execute(
            f"SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS "
            f"WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'vip_package' AND COLUMN_NAME = 'buy_link'",
            (MYSQL_DATABASE,),
        )
        if cur.fetchone()["cnt"] == 0:
            cur.execute("ALTER TABLE `vip_package` ADD COLUMN `buy_link` VARCHAR(500) DEFAULT ''")

        # 迁移：安全字段 token_version / login_failures / locked_until
        for col, ddl in (
            ("token_version", "ALTER TABLE `user` ADD COLUMN `token_version` INT DEFAULT 0"),
            ("login_failures", "ALTER TABLE `user` ADD COLUMN `login_failures` INT DEFAULT 0"),
            ("locked_until", "ALTER TABLE `user` ADD COLUMN `locked_until` DATETIME DEFAULT NULL"),
        ):
            cur.execute(
                f"SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS "
                f"WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'user' AND COLUMN_NAME = %s",
                (MYSQL_DATABASE, col),
            )
            if cur.fetchone()["cnt"] == 0:
                cur.execute(ddl)

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `order_record` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `order_id` VARCHAR(100) NOT NULL UNIQUE,
                `user_id` INT NOT NULL,
                `package_id` INT NOT NULL,
                `pay_amount` DECIMAL(10,2) NOT NULL,
                `pay_status` VARCHAR(20) DEFAULT 'pending',
                `pay_method` VARCHAR(20) DEFAULT '',
                `trade_no` VARCHAR(64) DEFAULT '',
                `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
                `finish_time` DATETIME DEFAULT NULL,
                `notify_time` DATETIME DEFAULT NULL,
                FOREIGN KEY (`user_id`) REFERENCES `user`(`id`),
                FOREIGN KEY (`package_id`) REFERENCES `vip_package`(`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        # 迁移：为旧表添加新字段
        for col, col_def in [
            ("pay_method", "VARCHAR(20) DEFAULT ''"),
            ("trade_no", "VARCHAR(64) DEFAULT ''"),
            ("notify_time", "DATETIME DEFAULT NULL"),
        ]:
            cur.execute(
                f"SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS "
                f"WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'order_record' AND COLUMN_NAME = %s",
                (MYSQL_DATABASE, col),
            )
            if cur.fetchone()["cnt"] == 0:
                cur.execute(f"ALTER TABLE `order_record` ADD COLUMN `{col}` {col_def}")

        # 迁移：为 user 表添加邀请相关字段
        for col, col_def in [
            ("invite_code", "VARCHAR(32) DEFAULT ''"),
            ("invite_expire_time", "DATETIME DEFAULT NULL"),
        ]:
            cur.execute(
                f"SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS "
                f"WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'user' AND COLUMN_NAME = %s",
                (MYSQL_DATABASE, col),
            )
            if cur.fetchone()["cnt"] == 0:
                cur.execute(f"ALTER TABLE `user` ADD COLUMN `{col}` {col_def}")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `redeem_code` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `code` VARCHAR(32) NOT NULL UNIQUE,
                `package_id` INT NOT NULL,
                `valid_days` DECIMAL(10,4) NOT NULL,
                `is_used` TINYINT DEFAULT 0,
                `used_by` INT DEFAULT NULL,
                `used_at` DATETIME DEFAULT NULL,
                `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX `idx_rc_code` (`code`),
                INDEX `idx_rc_used` (`is_used`)
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

        # 插入/更新默认 VIP 套餐
        cur.execute("SELECT COUNT(*) AS cnt FROM `vip_package`")
        existing_count = cur.fetchone()["cnt"]

        if existing_count == 0:
            # 首次插入
            cur.executemany(
                "INSERT INTO `vip_package` (`package_name`, `type`, `price`, `total_count`, `valid_days`) "
                "VALUES (%s, %s, %s, %s, %s)",
                DEFAULT_PACKAGES,
            )
        else:
            # 更新现有套餐（根据 type 匹配）
            for pkg in DEFAULT_PACKAGES:
                cur.execute(
                    "UPDATE `vip_package` SET `package_name` = %s, `price` = %s, `total_count` = %s, `valid_days` = %s "
                    "WHERE `type` = %s",
                    (pkg[0], pkg[2], pkg[3], pkg[4], pkg[1]),
                )
            # 如果套餐数量不同，插入缺失的
            if existing_count < len(DEFAULT_PACKAGES):
                existing_types = set()
                cur.execute("SELECT `type` FROM `vip_package`")
                for row in cur.fetchall():
                    existing_types.add(row["type"])
                for pkg in DEFAULT_PACKAGES:
                    if pkg[1] not in existing_types:
                        cur.execute(
                            "INSERT INTO `vip_package` (`package_name`, `type`, `price`, `total_count`, `valid_days`) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            pkg,
                        )

        # 插入管理员账号（用户名来自 ADMIN_USERNAME，非固定 admin）
        cur.execute("SELECT COUNT(*) AS cnt FROM `user` WHERE `is_admin` = 1")
        if cur.fetchone()["cnt"] == 0:
            from backend.auth import hash_password

            cur.execute(
                "INSERT INTO `user` (`username`, `password`, `is_admin`, `remain_count`) VALUES (%s, %s, 1, %s)",
                (ADMIN_USERNAME, hash_password(ADMIN_PASSWORD), 99999),
            )

    conn.commit()
    conn.close()
