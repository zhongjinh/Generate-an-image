#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表在线生成器 - 本地服务
静态页面 + 用户/管理员 + 会员套餐 + 绘图次数
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

CONVERT_DIR = ROOT.parent / "Online-Diagram-Generator" / "python-convert"
sys.path.insert(0, str(CONVERT_DIR))

from backend.auth import generate_token, hash_password, user_payload, verify_token
from backend.db import REGISTER_FREE_COUNT, get_db, init_db

try:
    from json2xml import convert as json_to_xml
    HAS_CONVERTER = True
except ImportError:
    HAS_CONVERTER = False
    json_to_xml = None

PORT = int(os.environ.get("PORT", "8765"))


def _row_dict(row) -> dict:
    return dict(row) if row else {}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type,Authorization",
        )

    def _json(self, data, status=200):
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        if not raw:
            return {}
        return json.loads(raw)

    def _get_user(self):
        auth = self.headers.get("Authorization", "")
        token = auth.replace("Bearer ", "").strip()
        if not token:
            return None
        payload = verify_token(token)
        if not payload or "id" not in payload:
            return None
        conn = get_db()
        row = conn.execute("SELECT * FROM user WHERE id = ?", (payload["id"],)).fetchone()
        conn.close()
        return _row_dict(row) if row else None

    def _require_user(self):
        user = self._get_user()
        if not user:
            return None, self._json({"error": "请先登录"}, 401)
        if user.get("is_disabled"):
            return None, self._json({"error": "账号已被禁用"}, 403)
        return user, None

    def _require_admin(self):
        user, err = self._require_user()
        if err:
            return None, err
        if not user.get("is_admin"):
            return None, self._json({"error": "无管理员权限"}, 403)
        return user, None

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        routes = {
            "/api/health": self._handle_health,
            "/api/user/info": self._handle_user_info,
            "/api/files": self._handle_get_files,
            "/api/vip/packages": self._handle_get_packages,
            "/api/orders": self._handle_get_orders,
            "/api/admin/users": self._handle_admin_users,
            "/api/admin/orders": self._handle_admin_orders,
            "/api/admin/stats": self._handle_admin_stats,
        }
        if path in routes:
            return routes[path]()
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        routes = {
            "/api/auth/login": self._handle_login,
            "/api/auth/register": self._handle_register,
            "/api/convert": self._handle_convert,
            "/api/files": self._handle_save_file,
            "/api/orders": self._handle_create_order,
        }
        if path in routes:
            return routes[path]()
        return self._json({"error": "Not Found"}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path

        m = re.match(r"/api/admin/users/(\d+)/count$", path)
        if m:
            return self._handle_reset_count(m.group(1))

        m = re.match(r"/api/admin/users/(\d+)/disable$", path)
        if m:
            return self._handle_disable_user(m.group(1))

        m = re.match(r"/api/admin/packages/(\d+)$", path)
        if m:
            return self._handle_update_package(m.group(1))

        return self._json({"error": "Not Found"}, 404)

    # ---------- 公开 ----------

    def _handle_health(self):
        return self._json({"status": "ok", "converter": HAS_CONVERTER})

    def _handle_get_packages(self):
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM vip_package WHERE is_enable = 1 ORDER BY price ASC"
        ).fetchall()
        conn.close()
        return self._json({"packages": [_row_dict(r) for r in rows]})

    # ---------- 认证 ----------

    def _handle_login(self):
        data = self._read_body()
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return self._json({"error": "请填写用户名和密码"}, 400)

        conn = get_db()
        row = conn.execute(
            "SELECT * FROM user WHERE username = ? AND password = ?",
            (username, hash_password(password)),
        ).fetchone()
        conn.close()

        if not row:
            return self._json({"error": "用户名或密码错误"}, 401)
        if row["is_disabled"]:
            return self._json({"error": "账号已被禁用"}, 403)

        user = _row_dict(row)
        token = generate_token(
            {"id": user["id"], "username": user["username"], "is_admin": user["is_admin"]}
        )
        return self._json({"token": token, "user": user_payload(row)})

    def _handle_register(self):
        data = self._read_body()
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        phone = (data.get("phone") or "").strip()

        if not username or not password:
            return self._json({"error": "请填写用户名和密码"}, 400)
        if len(username) < 3 or len(username) > 20:
            return self._json({"error": "用户名长度 3-20 位"}, 400)
        if len(password) < 6:
            return self._json({"error": "密码至少 6 位"}, 400)

        conn = get_db()
        exists = conn.execute(
            "SELECT id FROM user WHERE username = ?", (username,)
        ).fetchone()
        if exists:
            conn.close()
            return self._json({"error": "用户名已存在"}, 400)

        cur = conn.execute(
            "INSERT INTO user (username, password, phone, remain_count) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), phone, REGISTER_FREE_COUNT),
        )
        user_id = cur.lastrowid
        row = conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
        conn.commit()
        conn.close()

        token = generate_token(
            {"id": row["id"], "username": row["username"], "is_admin": 0}
        )
        return self._json({"token": token, "user": user_payload(row)})

    def _handle_user_info(self):
        user, err = self._require_user()
        if err:
            return err
        conn = get_db()
        row = conn.execute("SELECT * FROM user WHERE id = ?", (user["id"],)).fetchone()
        conn.close()
        return self._json({"user": user_payload(row)})

    # ---------- 绘图 ----------

    def _handle_convert(self):
        user, err = self._require_user()
        if err:
            return err

        if not HAS_CONVERTER:
            return self._json({"error": "Python 转换模块未安装"}, 500)

        data = self._read_body()
        json_content = data.get("json_content", "")
        if not json_content:
            return self._json({"error": "json_content 不能为空"}, 400)

        conn = get_db()
        row = conn.execute("SELECT * FROM user WHERE id = ?", (user["id"],)).fetchone()
        if not row["is_admin"] and row["remain_count"] <= 0:
            conn.close()
            return self._json({"error": "生成次数已用完，请购买会员"}, 403)

        try:
            xml = json_to_xml(json_content)
        except Exception as e:
            conn.close()
            return self._json({"error": str(e)}, 400)

        if not row["is_admin"]:
            conn.execute(
                "UPDATE user SET remain_count = remain_count - 1 WHERE id = ? AND remain_count > 0",
                (user["id"],),
            )

        cfg = json.loads(json_content)
        conn.execute(
            "INSERT INTO file_record (user_id, json_content, xml_content, chart_type, title) VALUES (?, ?, ?, ?, ?)",
            (
                user["id"],
                json_content,
                xml,
                cfg.get("type", ""),
                cfg.get("title", ""),
            ),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT remain_count FROM user WHERE id = ?", (user["id"],)
        ).fetchone()
        conn.close()

        return self._json({
            "success": True,
            "xml": xml,
            "remain_count": updated["remain_count"],
        })

    def _handle_get_files(self):
        user, err = self._require_user()
        if err:
            return err
        conn = get_db()
        rows = conn.execute(
            "SELECT id, chart_type, title, create_time FROM file_record WHERE user_id = ? ORDER BY create_time DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
        conn.close()
        return self._json({"files": [_row_dict(r) for r in rows]})

    def _handle_save_file(self):
        user, err = self._require_user()
        if err:
            return err
        data = self._read_body()
        conn = get_db()
        conn.execute(
            "INSERT INTO file_record (user_id, json_content, xml_content, chart_type, title) VALUES (?, ?, ?, ?, ?)",
            (
                user["id"],
                data.get("json_content", ""),
                data.get("xml_content", ""),
                data.get("chart_type", ""),
                data.get("title", ""),
            ),
        )
        conn.commit()
        conn.close()
        return self._json({"success": True})

    # ---------- 会员订单 ----------

    def _handle_create_order(self):
        user, err = self._require_user()
        if err:
            return err

        data = self._read_body()
        package_id = data.get("package_id")
        if not package_id:
            return self._json({"error": "请选择套餐"}, 400)

        conn = get_db()
        pkg = conn.execute(
            "SELECT * FROM vip_package WHERE id = ? AND is_enable = 1", (package_id,)
        ).fetchone()
        if not pkg:
            conn.close()
            return self._json({"error": "套餐不存在或已下架"}, 404)

        order_id = f"ORD{int(time.time())}{uuid.uuid4().hex[:6].upper()}"
        conn.execute(
            "INSERT INTO order_record (order_id, user_id, package_id, pay_amount) VALUES (?, ?, ?, ?)",
            (order_id, user["id"], pkg["id"], pkg["price"]),
        )

        expire_time = (datetime.now() + timedelta(days=pkg["valid_days"])).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        conn.execute(
            "UPDATE user SET vip_type = ?, vip_expire_time = ?, remain_count = remain_count + ? WHERE id = ?",
            (pkg["type"], expire_time, pkg["total_count"], user["id"]),
        )
        conn.execute(
            "UPDATE order_record SET pay_status = ?, finish_time = datetime('now', 'localtime') WHERE order_id = ?",
            ("paid", order_id),
        )
        conn.commit()

        row = conn.execute("SELECT * FROM user WHERE id = ?", (user["id"],)).fetchone()
        conn.close()

        return self._json({
            "success": True,
            "order_id": order_id,
            "message": "购买成功",
            "user": user_payload(row),
        })

    def _handle_get_orders(self):
        user, err = self._require_user()
        if err:
            return err
        conn = get_db()
        rows = conn.execute(
            """
            SELECT o.*, p.package_name FROM order_record o
            LEFT JOIN vip_package p ON o.package_id = p.id
            WHERE o.user_id = ? ORDER BY o.create_time DESC LIMIT 50
            """,
            (user["id"],),
        ).fetchall()
        conn.close()
        return self._json({"orders": [_row_dict(r) for r in rows]})

    # ---------- 管理员 ----------

    def _handle_admin_users(self):
        _, err = self._require_admin()
        if err:
            return err
        conn = get_db()
        rows = conn.execute(
            """
            SELECT id, username, phone, is_admin, remain_count, vip_type,
                   vip_expire_time, create_time, is_disabled
            FROM user ORDER BY create_time DESC
            """
        ).fetchall()
        conn.close()
        return self._json({"users": [_row_dict(r) for r in rows]})

    def _handle_admin_orders(self):
        _, err = self._require_admin()
        if err:
            return err
        conn = get_db()
        rows = conn.execute(
            """
            SELECT o.*, p.package_name, u.username FROM order_record o
            LEFT JOIN vip_package p ON o.package_id = p.id
            LEFT JOIN user u ON o.user_id = u.id
            ORDER BY o.create_time DESC LIMIT 200
            """
        ).fetchall()
        conn.close()
        return self._json({"orders": [_row_dict(r) for r in rows]})

    def _handle_admin_stats(self):
        _, err = self._require_admin()
        if err:
            return err
        conn = get_db()
        total_users = conn.execute("SELECT COUNT(*) AS c FROM user").fetchone()["c"]
        today_users = conn.execute(
            "SELECT COUNT(*) AS c FROM user WHERE date(create_time) = date('now', 'localtime')"
        ).fetchone()["c"]
        total_orders = conn.execute(
            "SELECT COUNT(*) AS c FROM order_record WHERE pay_status = 'paid'"
        ).fetchone()["c"]
        total_revenue = conn.execute(
            "SELECT COALESCE(SUM(pay_amount), 0) AS t FROM order_record WHERE pay_status = 'paid'"
        ).fetchone()["t"]
        today_charts = conn.execute(
            "SELECT COUNT(*) AS c FROM file_record WHERE date(create_time) = date('now', 'localtime')"
        ).fetchone()["c"]
        conn.close()
        return self._json({
            "total_users": total_users,
            "today_users": today_users,
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "today_charts": today_charts,
        })

    def _handle_reset_count(self, user_id: str):
        _, err = self._require_admin()
        if err:
            return err
        data = self._read_body()
        count = int(data.get("count", 0))
        conn = get_db()
        conn.execute("UPDATE user SET remain_count = ? WHERE id = ?", (count, user_id))
        conn.commit()
        conn.close()
        return self._json({"success": True})

    def _handle_disable_user(self, user_id: str):
        _, err = self._require_admin()
        if err:
            return err
        conn = get_db()
        row = conn.execute(
            "SELECT is_disabled FROM user WHERE id = ?", (user_id,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE user SET is_disabled = ? WHERE id = ?",
                (0 if row["is_disabled"] else 1, user_id),
            )
            conn.commit()
        conn.close()
        return self._json({"success": True})

    def _handle_update_package(self, package_id: str):
        _, err = self._require_admin()
        if err:
            return err
        data = self._read_body()
        conn = get_db()
        conn.execute(
            """
            UPDATE vip_package SET package_name=?, price=?, total_count=?, valid_days=?, is_enable=?
            WHERE id=?
            """,
            (
                data.get("package_name"),
                data.get("price"),
                data.get("total_count"),
                data.get("valid_days"),
                1 if data.get("is_enable") else 0,
                package_id,
            ),
        )
        conn.commit()
        conn.close()
        return self._json({"success": True})

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def main():
    init_db()
    print("=" * 50)
    print("  图表在线生成器")
    print("=" * 50)
    print(f"目录: {ROOT}")
    print(f"数据库: {ROOT / 'data' / 'app.db'}")
    print(f"转换模块: {'可用' if HAS_CONVERTER else '不可用'}")
    print(f"访问: http://127.0.0.1:{PORT}")
    print("管理员: admin / admin123")
    print("新用户注册赠送 1 次生成次数")
    print("按 Ctrl+C 停止")
    print("=" * 50)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
