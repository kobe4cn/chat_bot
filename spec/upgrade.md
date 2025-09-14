% 升级说明（TLS 与流式响应）

## 概览
本次升级引入集中化配置、TLS 启动支持、自签名证书生成脚本，以及基于 SSE 的流式响应接口，提升可用性与开发体验，同时改进会话与可测试性。

## 主要变更
- 配置中心：新增 `config.py`，统一 `model_name`、`temperature`、`history_limit`、`host`、`port` 与 TLS 参数（`SSL_CERTFILE`、`SSL_KEYFILE`、`SSL_KEYFILE_PASSWORD`）。从 `.env`/环境变量加载。
- 流式接口：
  - `POST /chat/stream`（SSE）：请求体携带消息，逐条 `data:` 推送，结束 `event: end`。
  - `GET /chat/stream`（SSE）：兼容原生 EventSource，参数通过 query（`message`、`session_id`）。
- ChatChain：`initialize` 读取配置；新增 `stream_message(...)` 基于 LangChain `astream` 产出分片。
- 会话管理：`SessionManager` 接收 `history_limit`（来自配置）。
- TLS 启动：`server.py` 支持依据 `.env` 的证书路径以 HTTPS 启动；`python server.py --http` 可强制 HTTP。
- 证书生成：`scripts/generate_self_signed_cert.py` 使用 openssl 生成 `certs/cert.pem` 与 `certs/key.pem`，并自动写入 `.env`。`.gitignore` 新增忽略 `certs/`。
- 测试与示例：
  - `tests/test_api.py` 覆盖 `/health`、`/chat`、`/chat/stream`（使用 FakeChain）。
  - `examples/sse_post_stream.html`（POST + ReadableStream）
  - `examples/sse_get_eventsource.html`（GET + EventSource）
- 安全与联调增强：
  - CORS（开发）：通过 `allowed_origins`/`allowed_methods` 启用白名单。
  - API Key 鉴权：`require_api_key` 开关 + `INTERNAL_API_KEY` 环境变量。
  - 基础限流：内存滑动窗口，`rate_limit_enabled`、`rate_limit_requests`、`rate_limit_window_s`，支持按 `ip`/`api_key` 维度。
  - 请求体大小限制：基于 `Content-Length` 拦截，默认 1MB（`request_max_body_bytes`）。
  - 日志脱敏：隐藏 `Authorization`、`X-API-Key`，掩码疑似 `sk-...` 格式密钥并截断超长日志。
  - 多密钥与签名 URL：支持多密钥平滑轮换（列表/映射），GET /chat/stream 可使用短期签名 URL（EventSource 友好）。

## 使用步骤
1) 生成自签名证书（开发用）：
   - `python scripts/generate_self_signed_cert.py`（可加 `--force` 重新生成）
   - `.env` 将追加/更新：
     - `SSL_CERTFILE=certs/cert.pem`
     - `SSL_KEYFILE=certs/key.pem`
2) 启动服务：
   - HTTP 开发：`uvicorn main:app --reload`
   - HTTPS：`python server.py`（读取 `.env` 证书）
3) 调用示例：
   - 常规：`curl -s -X POST http://localhost:8000/chat -H 'Content-Type: application/json' -d '{"message":"你好","session_id":"c1"}'`
   - 流式（POST）：`curl -N -X POST http://localhost:8000/chat/stream -H 'Content-Type: application/json' -d '{"message":"你好","session_id":"s1"}'`
   - 流式（GET/EventSource）：`curl -N 'http://localhost:8000/chat/stream?session_id=s2&message=你好'`
   - 浏览器：打开 `examples/sse_post_stream.html` 或 `examples/sse_get_eventsource.html`

## 安全与注意事项
- 自签名证书仅供本地开发；生产请使用受信任 CA 证书并在反向代理层终止 TLS。
- 请勿提交证书/私钥；`certs/` 已加入 `.gitignore`。
- 进一步建议：新增 日志脱敏、请求体大小限制、生产级限流/鉴权网关。

## 配置参考（.env / 环境变量）
- TLS：`SSL_CERTFILE`、`SSL_KEYFILE`、`SSL_KEYFILE_PASSWORD`
- CORS：`ALLOWED_ORIGINS`（可在 `config.py` 中通过环境解析为列表，或直接在代码中设置）
- 鉴权：`INTERNAL_API_KEY`，并在 `config.py` 中将 `require_api_key` 设为 `True`
- 限流：`rate_limit_enabled=True`，`rate_limit_requests=60`，`rate_limit_window_s=60`，`rate_limit_by=ip|api_key`
- 请求体限制：`request_max_body_bytes=1000000`
- 日志：`log_level=INFO`、`log_truncate_len=1000`
 - 多密钥与签名 URL：
   - 多密钥列表：`internal_api_keys=["k1","k2"]`（JSON 数组）
   - KID->KEY 映射：`api_keys={"kid1":"k1","kid2":"k2"}`（JSON 对象）
   - 签名 URL：`signed_url_enabled=True`、`signed_url_ttl_s=300`、`signed_url_clock_skew_s=30`

## GET 签名 URL 说明
- 适用场景：浏览器原生 EventSource 不支持自定义头，无法携带 `X-API-Key`。
- 计算方式：`HMAC_SHA256_HEX( method + "\n" + path + "\n" + session_id + "\n" + message + "\n" + exp + "\n" + nonce )`
- 参数：`session_id`、`message`、`exp`（秒级时间戳）、`nonce`（随机）、`sig`（签名）、可选 `kid`（多密钥时指定）。
- 生成工具：`python scripts/gen_signed_url.py --key <KEY> --kid <KID?> --session-id s1 --message 你好 --base https://localhost:8000 --ttl 300`
