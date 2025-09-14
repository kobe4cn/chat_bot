"""应用启动入口（可选），支持从配置读取 TLS 证书启动。

用法：
    python server.py            # 依据 .env / 环境变量读取证书并启用 HTTPS
    python server.py --http     # 强制以 HTTP 启动
"""

from __future__ import annotations

import argparse
import uvicorn
from config import settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="以 HTTP 启动，忽略证书")
    args = parser.parse_args()

    ssl_kwargs = {}
    if not args.http and settings.ssl_certfile and settings.ssl_keyfile:
        ssl_kwargs = dict(
            ssl_certfile=settings.ssl_certfile,
            ssl_keyfile=settings.ssl_keyfile,
            ssl_keyfile_password=settings.ssl_keyfile_password,
        )

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()

