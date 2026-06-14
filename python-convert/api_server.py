#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python HTTP 接口服务 - 供 Cloudflare Worker 调用
接收 JSON，返回 draw.io XML
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# 加入当前目录到 path
sys.path.insert(0, str(Path(__file__).parent))
from json2xml import convert, BUILDERS

API_KEY = os.environ.get("CONVERT_API_KEY", "diagram-convert-secret-key")
PORT = int(os.environ.get("PORT", "5000"))
PUBLIC_CONVERT = os.environ.get("PUBLIC_CONVERT", "1") != "0"


class ConvertHandler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _json_response(self, data, status=200):
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._json_response({"status": "ok", "types": list(BUILDERS.keys())})
        elif self.path == "/types":
            self._json_response({"types": list(BUILDERS.keys())})
        else:
            self._json_response({"error": "Not Found"}, 404)

    def _authorized(self) -> bool:
        if PUBLIC_CONVERT:
            return True
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {API_KEY}"

    def do_POST(self):
        if not self._authorized():
            self._json_response({"error": "Unauthorized"}, 401)
            return

        if self.path == "/convert":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                json_content = data.get("json_content", "")
                if not json_content and isinstance(data.get("type"), str):
                    json_content = json.dumps(data, ensure_ascii=False)
                if not json_content:
                    self._json_response({"error": "json_content 不能为空"}, 400)
                    return
                xml = convert(json_content)
                self._json_response({"success": True, "xml": xml})
            except json.JSONDecodeError as e:
                self._json_response({"error": f"JSON 解析错误: {str(e)}"}, 400)
            except ValueError as e:
                self._json_response({"error": str(e)}, 400)
            except Exception as e:
                self._json_response({"error": f"转换失败: {str(e)}"}, 500)
        else:
            self._json_response({"error": "Not Found"}, 404)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def main():
    server = HTTPServer(("0.0.0.0", PORT), ConvertHandler)
    print(f"转换服务启动: http://0.0.0.0:{PORT}")
    print(f"支持图表类型: {', '.join(BUILDERS.keys())}")
    print(f"API Key: {API_KEY[:8]}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()
