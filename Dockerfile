FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 默认监听端口
ENV PORT=8000 HOST=0.0.0.0
EXPOSE 8000

# 生产中通常由反向代理终止 TLS；容器内默认使用 HTTP 启动
# 如需容器内 TLS，可设置 SSL_CERTFILE/SSL_KEYFILE 并改用 `python server.py`
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

