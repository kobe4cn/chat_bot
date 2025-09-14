#!/usr/bin/env python3
"""
生成 GET /chat/stream 的短期签名 URL（适配 EventSource）。

示例：
  python scripts/gen_signed_url.py \
    --key YOUR_KEY --kid default \
    --session-id s1 --message 你好 \
    --base https://localhost:8000 --ttl 300

注意：
  - 计算签名规则与服务端一致：HMAC-SHA256-HEX(method, path, session_id, message, exp, nonce)。
  - 输出包含 query: session_id, message, exp, nonce, sig[, kid]。
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode, quote


def gen_signed_url(base: str, key: str, session_id: str, message: str, ttl: int, kid: str | None) -> str:
    path = "/chat/stream"
    exp = int(time.time()) + int(ttl)
    nonce = secrets.token_hex(8)
    to_sign = "\n".join(["GET", path, session_id, message, str(exp), nonce])
    sig = hmac.new(key.encode("utf-8"), to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    qs = {"session_id": session_id, "message": message, "exp": str(exp), "nonce": nonce, "sig": sig}
    if kid:
        qs["kid"] = kid
    return base.rstrip("/") + path + "?" + urlencode(qs, safe="")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000", help="服务基地址")
    ap.add_argument("--key", required=True, help="签名密钥（与服务端一致）")
    ap.add_argument("--kid", default=None, help="可选：密钥 ID（当服务端配置多密钥时建议提供）")
    ap.add_argument("--session-id", required=True)
    ap.add_argument("--message", required=True)
    ap.add_argument("--ttl", type=int, default=300, help="有效期（秒）")
    args = ap.parse_args()

    url = gen_signed_url(args.base, args.key, args.session_id, args.message, args.ttl, args.kid)
    print(url)


if __name__ == "__main__":
    main()

