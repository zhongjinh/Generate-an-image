FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt cryptography

COPY backend ./backend
COPY run.py .

# 前端需在构建阶段 npm run build 后复制 dist
COPY frontend/dist ./frontend/dist

EXPOSE 8765

# 生产环境通过 .env 或 docker run -e 注入配置
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
