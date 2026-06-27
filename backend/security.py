#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全中间件：反爬虫、限流、请求校验"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from threading import Lock

import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.config import APP_CLIENT_TOKEN, CORS_ORIGINS, DEBUG, INTERNAL_API_SECRET, TRUSTED_HOSTS

# ── 客户端 IP（Cloudflare / 反向代理） ──────────────────────────────

_CF_IP_HEADERS = ("CF-Connecting-IP", "True-Client-IP", "X-Real-IP")

# 常见爬虫 / 脚本 UA（小写匹配片段）
_BLOCKED_UA_FRAGMENTS = (
    "scrapy", "curl/", "wget/", "python-requests", "python-urllib",
    "httpx/", "aiohttp/", "go-http-client", "java/", "libwww",
    "httpclient", "okhttp", "postman", "insomnia", "paw/",
    "semrush", "ahrefs", "mj12bot", "dotbot", "petalbot",
    "bytespider", "gptbot", "claudebot", "headlesschrome",
)

# 允许无浏览器 UA 的路径
_UA_BYPASS_PATHS = {"/api/health", "/api/payment/notify"}


def get_client_ip(request: Request) -> str:
    for header in _CF_IP_HEADERS:
        value = request.headers.get(header, "").strip()
        if value:
            return value.split(",")[0].strip()

    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()

    if request.client:
        return request.client.host
    return "unknown"


# ── 限流 ────────────────────────────────────────────────────────────

class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            hits = self._buckets[key]
            self._buckets[key] = hits = [t for t in hits if t > cutoff]
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def retry_after(self, key: str, window_seconds: int) -> int:
        with self._lock:
            hits = self._buckets.get(key, [])
            if not hits:
                return window_seconds
            oldest = min(hits)
            return max(1, int(window_seconds - (time.monotonic() - oldest)))


rate_limiter = RateLimiter()

RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/auth/login": (10, 300),
    "/api/auth/send-code": (5, 300),
    "/api/auth/register": (10, 300),
    "/api/admin": (60, 60),
    "/api/convert-ai": (15, 60),
    "/api/convert-text": (20, 60),
    "/api/convert-example": (8, 60),
    "/api/convert-ai-example": (10, 60),
    "/api/convert-text-example": (10, 60),
}

GLOBAL_API_LIMIT = (180, 60)


def _match_rate_limit(path: str) -> tuple[int, int] | None:
    for prefix, rule in sorted(RATE_LIMITS.items(), key=lambda x: -len(x[0])):
        if path == prefix or path.startswith(prefix + "/"):
            return rule
    return None


# ── 安全响应头 ──────────────────────────────────────────────────────

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
    "Cache-Control": "no-store",
}

if not DEBUG:
    SECURITY_HEADERS["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            if key not in response.headers and not (
                key == "Cache-Control" and request.url.path.startswith("/assets")
            ):
                response.headers[key] = value
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        ip = get_client_ip(request)

        if path.startswith("/api") and request.method != "OPTIONS":
            if not rate_limiter.is_allowed(f"global:{ip}", GLOBAL_API_LIMIT[0], GLOBAL_API_LIMIT[1]):
                return JSONResponse(status_code=429, content={"error": "请求过于频繁，请稍后再试"})

        rule = _match_rate_limit(path)
        if rule and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            limit, window = rule
            key = f"{ip}:{path}"
            if not rate_limiter.is_allowed(key, limit, window):
                retry = rate_limiter.retry_after(key, window)
                return JSONResponse(
                    status_code=429,
                    content={"error": f"请求过于频繁，请 {retry} 秒后再试"},
                    headers={"Retry-After": str(retry)},
                )
        return await call_next(request)


class AntiBotMiddleware(BaseHTTPMiddleware):
    """拦截脚本爬虫；生产环境校验前端客户端令牌。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith("/api") or path in _UA_BYPASS_PATHS:
            return await call_next(request)

        ua = (request.headers.get("user-agent") or "").strip()
        ua_lower = ua.lower()

        if not ua or len(ua) < 10:
            return JSONResponse(status_code=403, content={"error": "Forbidden"})

        for frag in _BLOCKED_UA_FRAGMENTS:
            if frag in ua_lower:
                return JSONResponse(status_code=403, content={"error": "Forbidden"})

        if not DEBUG and APP_CLIENT_TOKEN:
            token = request.headers.get("X-Client-Token", "")
            if not token or not hmac.compare_digest(token, APP_CLIENT_TOKEN):
                return JSONResponse(status_code=403, content={"error": "Forbidden"})

        if not DEBUG and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")
            if CORS_ORIGINS and origin:
                if origin not in CORS_ORIGINS:
                    return JSONResponse(status_code=403, content={"error": "Forbidden"})
            elif CORS_ORIGINS and not origin and not referer:
                return JSONResponse(status_code=403, content={"error": "Forbidden"})

        return await call_next(request)


class RequestSizeMiddleware(BaseHTTPMiddleware):
    MAX_BODY = 512 * 1024  # 512 KB

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length", "")
            if content_length.isdigit() and int(content_length) > self.MAX_BODY:
                return JSONResponse(status_code=413, content={"error": "请求体过大"})
        return await call_next(request)


class TrustedHostMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not TRUSTED_HOSTS:
            return await call_next(request)

        host = request.headers.get("host", "").split(":")[0].lower()
        if host in {"127.0.0.1", "localhost"}:
            return await call_next(request)
        if host and host not in TRUSTED_HOSTS:
            return JSONResponse(status_code=400, content={"error": "Invalid Host header"})
        return await call_next(request)


def get_cors_origins() -> list[str]:
    if DEBUG:
        return ["*"]
    return CORS_ORIGINS or []


_INTERNAL_BYPASS_PATHS = {
    "/api/health",
    "/api/payment/notify",
}


class InternalApiGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if DEBUG or not INTERNAL_API_SECRET:
            return await call_next(request)

        path = request.url.path
        if not path.startswith("/api") or path in _INTERNAL_BYPASS_PATHS:
            return await call_next(request)

        secret = request.headers.get("X-Internal-Secret", "")
        if not secret or not hmac.compare_digest(secret, INTERNAL_API_SECRET):
            return JSONResponse(status_code=403, content={"error": "Forbidden"})
        return await call_next(request)
