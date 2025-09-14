import asyncio
import json
import pytest
import httpx
import time
import hmac
import hashlib

import main
from session_manager import SessionManager


class FakeChain:
    async def initialize(self):
        return None

    async def process_message(self, message: str, history):
        return f"回声: {message}"

    async def stream_message(self, message: str, history):
        # 模拟分片输出
        for chunk in ["片段1", "片段2", "片段3"]:
            await asyncio.sleep(0)
            yield chunk


@pytest.fixture
async def async_client():
    # 关闭 lifespan，避免真实初始化外部 LLM
    transport = httpx.ASGITransport(app=main.app, lifespan="off")
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 注入假实现与独立会话管理器
        main.chat_chain = FakeChain()
        main.session_manager = SessionManager(max_history_length=5)
        yield client


@pytest.mark.asyncio
async def test_health(async_client: httpx.AsyncClient):
    r = await async_client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "healthy"


@pytest.mark.asyncio
async def test_chat_standard(async_client: httpx.AsyncClient):
    payload = {"message": "你好", "session_id": "s1"}
    r = await async_client.post("/chat", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["reply"].startswith("回声: ")
    assert data["session_id"] == "s1"


@pytest.mark.asyncio
async def test_chat_stream_sse(async_client: httpx.AsyncClient):
    payload = {"message": "流式测试", "session_id": "s2"}
    # 使用流式请求，验证 SSE 分片与结束事件
    async with async_client.stream("POST", "/chat/stream", json=payload) as r:
        assert r.status_code == 200
        text_chunks = []
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                text_chunks.append(line.removeprefix("data: "))
            if line.startswith("event: end"):
                break

    # 期望至少接收到多个分片
    assert any("片段" in c for c in text_chunks)

    # 校验会话历史已被写入完整合并内容
    history = main.session_manager.get_history("s2")
    assert len(history) == 1
    assert history[0]["bot_message"].endswith("片段3")


@pytest.mark.asyncio
async def test_chat_stream_get_signed_url(async_client: httpx.AsyncClient):
    # 启用鉴权并设置唯一密钥，允许使用签名 URL 访问 GET /chat/stream
    main.settings.require_api_key = True
    main.settings.signed_url_enabled = True
    main.settings.internal_api_key = "test-secret"

    session_id = "s3"
    message = "签名校验"
    exp = int(time.time()) + 60
    nonce = "n-1"
    to_sign = "\n".join(["GET", "/chat/stream", session_id, message, str(exp), nonce])
    sig = hmac.new(main.settings.internal_api_key.encode("utf-8"), to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    url = f"/chat/stream?session_id={session_id}&message={message}&exp={exp}&nonce={nonce}&sig={sig}"
    async with async_client.stream("GET", url) as r:
        assert r.status_code == 200
        lines = []
        async for line in r.aiter_lines():
            lines.append(line)
            if line.startswith("event: end"):
                break
        assert any(l.startswith("data: ") for l in lines)
