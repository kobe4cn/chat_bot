% 智能对话服务（FastAPI + LangChain）

一个支持流式响应（SSE）与 TLS 的简易对话服务，整合 FastAPI、LangChain（Tongyi/DashScope），内置会话管理、开发用 CORS、可选 API Key 鉴权、基础限流、请求体大小限制与日志脱敏。

## 快速开始
- 环境与依赖
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
- 启动（HTTP 开发）
  - `uvicorn main:app --reload`
- 启动（HTTPS，本地自签证书）
  - 生成证书并写入 .env：`python scripts/generate_self_signed_cert.py`
  - 运行：`python server.py`

## API 一览
- `GET /health` 健康检查
- `POST /chat` 标准回复（JSON：`{message, session_id}`）
- `POST /chat/stream` SSE 流式（可携带 `X-API-Key`）
- `GET /chat/stream` SSE 流式（适配 EventSource；如启用鉴权，使用“签名 URL”）
- `GET /sessions/{session_id}/history`、`DELETE /sessions/{session_id}`

## HTTPS 测试与示例
- curl（自签证书用 `-k`）
  - `curl -k https://localhost:8000/health`
  - `curl -k -s -X POST https://localhost:8000/chat -H 'Content-Type: application/json' -d '{"message":"你好","session_id":"c1"}'`
  - `curl -k -N -X POST https://localhost:8000/chat/stream -H 'Content-Type: application/json' -d '{"message":"你好","session_id":"s1"}'`
  - `curl -k -N 'https://localhost:8000/chat/stream?session_id=s2&message=你好'`
- 前端演示
  - 启动静态服：`python -m http.server 8080 --directory examples`
  - CORS：在 `config.py` 将 `allowed_origins=["http://localhost:8080"]`
  - 打开：`http://localhost:8080/sse_post_stream.html`（POST）或 `.../sse_get_eventsource.html`（GET）

## 鉴权与签名 URL
- 开启鉴权：`.env` 设置 `INTERNAL_API_KEY=<secret>` 与 `require_api_key=True`
  - 生成密钥：`openssl rand -hex 32` 或 `python -c 'import secrets,base64;print(base64.b64encode(secrets.token_bytes(32)).decode())'`
  - POST 请求头：`X-API-Key: <secret>`
- GET/EventSource 使用“签名 URL”（短期有效）
  - 生成：`python scripts/gen_signed_url.py --key <KEY> --kid <KID?> --session-id s1 --message 你好 --base https://localhost:8000 --ttl 300`
  - 浏览器：`new EventSource(<上述URL>)`

## 运行测试
- `pytest -q`

## 更多文档
- 使用与启动手册：`spec/usage.md`
- 升级与实现说明：`spec/upgrade.md`

