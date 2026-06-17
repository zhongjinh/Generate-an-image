#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FastAPI 应用入口"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from email.utils import formataddr

from backend.config import DEBUG, FRONTEND_DIST
from backend.db import init_db
from backend.routers import admin, auth, convert, files, health, orders, user

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

app = FastAPI(title="图表在线生成器", docs_url="/api/docs" if DEBUG else None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(content=exc.detail, status_code=exc.status_code)
    return JSONResponse(content={"error": str(exc.detail)}, status_code=exc.status_code)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(convert.router)
app.include_router(files.router)
app.include_router(orders.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup():
    init_db()
    from backend.config import SMTP_FROM, SMTP_FROM_NAME, SMTP_HOST, SMTP_PORT, SMTP_USE_TLS

    print(
        f"[SMTP] 邮件服务: {SMTP_HOST}:{SMTP_PORT} "
        f"TLS={'on' if SMTP_USE_TLS else 'off'} "
        f"FROM={formataddr((SMTP_FROM_NAME, SMTP_FROM))}"
    )


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")


def create_app() -> FastAPI:
    return app
