#!/usr/bin/env python3
"""
生成自签名 TLS 证书并写入 .env。

生成内容：certs/cert.pem, certs/key.pem
写入/更新 .env：
  SSL_CERTFILE=certs/cert.pem
  SSL_KEYFILE=certs/key.pem

依赖：系统安装了 openssl。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERT_DIR = ROOT / "certs"
CERT_FILE = CERT_DIR / "cert.pem"
KEY_FILE = CERT_DIR / "key.pem"
ENV_FILE = ROOT / ".env"


def have_openssl() -> bool:
    try:
        subprocess.run(["openssl", "version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception:
        return False


def generate_self_signed(force: bool = False) -> None:
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    if CERT_FILE.exists() and KEY_FILE.exists() and not force:
        print(f"证书已存在：{CERT_FILE} {KEY_FILE}（使用 --force 重新生成）")
        return

    if not have_openssl():
        print("未检测到 openssl，请安装后重试。macOS 可用: brew install openssl。", file=sys.stderr)
        sys.exit(2)

    # 生成自签名证书（包含 SAN: localhost, 127.0.0.1）
    cmd = [
        "openssl", "req", "-x509", "-nodes",
        "-newkey", "rsa:2048",
        "-keyout", str(KEY_FILE),
        "-out", str(CERT_FILE),
        "-days", "365",
        "-subj", "/CN=localhost",
        "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("openssl 生成证书失败：", e, file=sys.stderr)
        sys.exit(e.returncode)


def upsert_env() -> None:
    env_lines: list[str] = []
    if ENV_FILE.exists():
        env_lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

    def set_kv(lines: list[str], key: str, value: str) -> list[str]:
        found = False
        out: list[str] = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                out.append(f"{key}={value}")
                found = True
            else:
                out.append(line)
        if not found:
            out.append(f"{key}={value}")
        return out

    env_lines = set_kv(env_lines, "SSL_CERTFILE", str(CERT_FILE.relative_to(ROOT)))
    env_lines = set_kv(env_lines, "SSL_KEYFILE", str(KEY_FILE.relative_to(ROOT)))
    ENV_FILE.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    print(f"已更新 .env: SSL_CERTFILE, SSL_KEYFILE")


def main() -> None:
    force = "--force" in sys.argv
    generate_self_signed(force=force)
    upsert_env()
    print(f"生成完成：\n  证书: {CERT_FILE}\n  私钥: {KEY_FILE}")


if __name__ == "__main__":
    main()

