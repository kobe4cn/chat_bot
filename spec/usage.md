% 使用与启动手册（AI API Example）

## 简介
基于 FastAPI + LangChain（Tongyi/DashScope）的对话服务，提供标准与流式（SSE）接口，支持 TLS、会话历史、可配置化、开发用 CORS、可选 API Key 鉴权与基础限流，并包含最小集成测试与前端流式示例。

## 功能亮点
- 流式响应：`POST/GET /chat/stream` 基于 SSE，低延迟增量输出。
- TLS 支持：读取 `.env` 证书或使用脚本生成自签名证书。
- 可配置：集中 `config.py`（模型、温度、历史上限、CORS、鉴权、限流、日志、请求体大小）。
- 会话管理：内存历史裁剪，可获取与清理会话。
- 安全增强：开发 CORS 白名单、可选 `X-API-Key`、基础限流、请求体大小限制、日志脱敏。
- 测试与示例：pytest 集成测试；POST/GET 两种前端流式示例页面。

## 环境准备
- Python 3.10+，建议使用虚拟环境。
- fish 用户激活命令：`source .venv/bin/activate.fish`（bash/zsh：`source .venv/bin/activate`）。
- 可选：安装 openssl 以生成自签证书（macOS：`brew install openssl`）。

## 安装与依赖
- 创建并激活虚拟环境：
  - `python -m venv .venv && source .venv/bin/activate`
- 安装依赖：
  - `pip install -r requirements.txt`

## 证书生成（开发用）
- 一键生成并写入 `.env`：
  - `python scripts/generate_self_signed_cert.py`（覆盖：加 `--force`）
- 生成文件：`certs/cert.pem`、`certs/key.pem`（已在 `.gitignore` 忽略）。

## 启动方式
- HTTP（开发）：`uvicorn main:app --reload`
- HTTPS（读取 .env 证书）：`python server.py`
- 强制以 HTTP（忽略证书）：`python server.py --http`

## 配置说明（.env / 环境变量）
- TLS：`SSL_CERTFILE`、`SSL_KEYFILE`、`SSL_KEYFILE_PASSWORD`
- 模型：`model_name`（如 `qwen-turbo`）、`temperature`
- 会话：`history_limit`
- CORS：`allowed_origins`、`allowed_methods`（在 `config.py` 中数组配置，或通过环境解析）
- 鉴权：`require_api_key=True` 与 `INTERNAL_API_KEY=your-secret`（请求头 `X-API-Key`）
- 限流：`rate_limit_enabled=True`、`rate_limit_requests`、`rate_limit_window_s`、`rate_limit_by=ip|api_key`
- 请求体与日志：`request_max_body_bytes`、`log_level`、`log_truncate_len`
 - 多密钥与签名 URL：
   - 多密钥列表：`internal_api_keys=["k1","k2"]`（JSON 数组）
   - KID->KEY：`api_keys={"kid1":"k1","kid2":"k2"}`（JSON 对象）
   - 启用签名 URL：`signed_url_enabled=True`、有效期 `signed_url_ttl_s=300`、时钟偏移 `signed_url_clock_skew_s=30`

## API 概览
- `GET /health`：健康检查
- `POST /chat`：标准回复（请求体：`{message, session_id}`）
- `POST /chat/stream`：SSE 流式（请求体）
- `GET /chat/stream`：SSE 流式（query：`message`、`session_id`；适配 EventSource）
- `GET /sessions/{session_id}/history`：获取会话历史
- `DELETE /sessions/{session_id}`：删除会话

## 使用与验证
- 常规：
  - `curl -s -X POST http://localhost:8000/chat -H 'Content-Type: application/json' -d '{"message":"你好","session_id":"c1"}'`
- 流式（POST）：
  - `curl -N -X POST http://localhost:8000/chat/stream -H 'Content-Type: application/json' -d '{"message":"你好","session_id":"s1"}'`
- 流式（GET/EventSource）：
  - `curl -N 'http://localhost:8000/chat/stream?session_id=s2&message=你好'`
- HTTPS（自签证书）：在 curl 中加 `-k`（忽略校验）。
- 前端示例：
  - `examples/sse_post_stream.html`（POST + ReadableStream）
  - `examples/sse_get_eventsource.html`（GET + EventSource）
- 鉴权开启后：为上述请求添加头 `X-API-Key: your-secret`。

### GET /chat/stream 的签名 URL（EventSource）
- 目的：EventSource 不支持自定义头；通过短期签名 URL 安全访问。
- 签名规则：`HMAC_SHA256_HEX(method, path, session_id, message, exp, nonce)`，按行拼接后签名。
- 生成工具：
  - `python scripts/gen_signed_url.py --key <KEY> --kid <KID?> --session-id s1 --message 你好 --base https://localhost:8000 --ttl 300`
  - 输出 URL 可直接用于 EventSource：`new EventSource(url)`。
  - 如配置了 `api_keys={"kid1":"<KEY>"}`，请在生成时提供 `--kid kid1`。

## 基于 HTTPS 的测试
- 启动 HTTPS：`python server.py`（需 `.env` 配置证书，见“证书生成”）。
- 健康检查：`curl -k https://localhost:8000/health`
- 常规聊天（HTTPS）：
  - `curl -k -s -X POST https://localhost:8000/chat -H 'Content-Type: application/json' -d '{"message":"你好","session_id":"c1"}'`
- 流式（POST/SSE + HTTPS）：
  - `curl -k -N -X POST https://localhost:8000/chat/stream -H 'Content-Type: application/json' -d '{"message":"你好","session_id":"s1"}'`
- 流式（GET/EventSource + HTTPS）：
  - `curl -k -N 'https://localhost:8000/chat/stream?session_id=s2&message=你好'`
- 若启用 API Key 鉴权：为 curl 增加 `-H 'X-API-Key: your-secret'`。
- 浏览器首次访问 HTTPS 需手动信任自签证书：先打开 `https://localhost:8000/health` 并选择信任/继续访问。

## 示例页面使用
1) 启动 API：HTTP（`uvicorn main:app --reload`）或 HTTPS（`python server.py`）。
2) 启动静态文件服务（推荐，避免 file:// 跨域问题）：
   - `python -m http.server 8080 --directory examples`
   - 将 `config.py` 中 `allowed_origins` 设置为 `["http://localhost:8080"]`（开发时期），以通过 CORS。
3) 访问示例页面：
   - 打开 `http://localhost:8080/sse_post_stream.html`（POST 流式，ReadableStream）
   - 打开 `http://localhost:8080/sse_get_eventsource.html`（GET 流式，EventSource）
4) 页面使用说明：
   - 将“服务地址”改为 API 的地址（HTTP 或 HTTPS），例如 `https://localhost:8000`。
   - 输入 `Session ID` 与消息后点击“发送/开始流式”，输出区域会实时追加服务端 `data:` 片段，结束时出现 `[END]`。
5) 若启用 API Key：
   - curl 已示例 `-H 'X-API-Key: ...'`。
   - 浏览器 POST 示例可在 `fetch` 头中加入：`'X-API-Key': 'your-secret'`（修改 `examples/sse_post_stream.html` 中 headers）。
   - GET/EventSource 不支持自定义头；如需鉴权，请临时关闭 `require_api_key` 或改用 POST 示例。

## 运行测试
- 激活虚拟环境后执行：`pytest -q`
- 覆盖：`/health`、`/chat`、`/chat/stream`；使用 FakeChain 避免外部 LLM 依赖。

## 故障排查
- CORS：设置 `allowed_origins`（如 `http://localhost:3000`），浏览器跨域联调需白名单。
- 429 限流：调大 `rate_limit_requests` 或关闭 `rate_limit_enabled`。
- 413 过大：调大 `request_max_body_bytes`；反代（如 Nginx）同步放宽。
- 自签证书告警：curl 使用 `-k`；浏览器需手动信任或使用受信任证书/反向代理。

## 下一步优化方向
- 生产化鉴权与限流：接入网关（如 Kong/Traefik）或 Redis 限流，细化租户维度。
- 会话持久化：抽象 `SessionStore` 到 Redis/数据库，支持 TTL 与横向扩展。
- 结构化日志与追踪：JSON 日志 + Trace/Span（OpenTelemetry），完善脱敏策略。
- 更严格的请求大小控制：基于接收流实时截断（不依赖 Content-Length）。
- Token/成本控制：基于近似 Token 的上下文裁剪与配额管理。
- 前端示例完善：加入重连、错误提示与超时处理的完整 DEMO。
