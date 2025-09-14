from fastapi import FastAPI, HTTPException, Depends, Header, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from session_manager import SessionManager
from chat_chain import ChatChain
import uvicorn
from fastapi.responses import StreamingResponse
from config import settings
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import re
import hmac
import hashlib

# 全局对象
chat_chain = None
session_manager = SessionManager(max_history_length=settings.history_limit)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global chat_chain
    # 启动时初始化
    chat_chain = ChatChain()
    await chat_chain.initialize()
    yield
    # 关闭时清理（如果需要）


app = FastAPI(
    title="智能对话服务", 
    description="基于LangChain的智能对话服务", 
    version="1.0.0",
    lifespan=lifespan
)

# 条件性启用 CORS（开发联调用）
if settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=settings.allowed_methods,
        allow_headers=["*"],
        allow_credentials=False,
        max_age=600,
    )


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str


def _all_api_keys() -> list[str]:
    keys: list[str] = []
    if settings.internal_api_key:
        keys.append(settings.internal_api_key)
    if settings.internal_api_keys:
        keys.extend([k for k in settings.internal_api_keys if k])
    if settings.api_keys:
        keys.extend([v for v in settings.api_keys.values() if v])
    # 去重保持顺序
    out, seen = [], set()
    for k in keys:
        if k not in seen:
            out.append(k)
            seen.add(k)
    return out


def _is_valid_api_key(candidate: str | None) -> bool:
    if not candidate:
        return False
    return candidate in _all_api_keys()


def _get_key_for_kid(kid: str | None) -> str | None:
    if kid:
        return settings.api_keys.get(kid)
    # 未提供 kid，仅当唯一密钥时可使用
    keys = _all_api_keys()
    if len(keys) == 1:
        return keys[0]
    return None


def _verify_signed_url(request: Request) -> bool:
    if not settings.signed_url_enabled:
        return False
    q = request.query_params
    sig = q.get("sig")
    exp = q.get("exp")
    nonce = q.get("nonce")
    session_id = q.get("session_id")
    message = q.get("message")
    kid = q.get("kid")
    if not all([sig, exp, nonce, session_id, message]):
        return False
    try:
        exp_i = int(exp)
    except Exception:
        return False
    now = int(time.time())
    if not (now - settings.signed_url_clock_skew_s <= exp_i <= now + settings.signed_url_ttl_s + settings.signed_url_clock_skew_s):
        return False
    secret = _get_key_for_kid(kid)
    if not secret:
        return False
    to_sign = "\n".join([
        request.method,
        request.url.path,
        session_id,
        message,
        str(exp_i),
        nonce,
    ])
    digest = hmac.new(secret.encode("utf-8"), to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    # 时间常量比较
    try:
        return hmac.compare_digest(digest, sig)
    except Exception:
        return False


# 依赖：API 鉴权（支持 Header 与 GET 签名 URL）
def require_api_key(request: Request, x_api_key: str | None = Header(default=None)):
    if not settings.require_api_key:
        return
    if _is_valid_api_key(x_api_key):
        return
    # GET 请求允许使用签名 URL（EventSource 无法携带自定义头）
    if request.method == "GET" and _verify_signed_url(request):
        return
    raise HTTPException(status_code=401, detail="unauthorized")


# 轻量内存速率限制（滑动窗口）
class RateLimiter:
    def __init__(self, max_requests: int, window_s: int):
        self.max_requests = max_requests
        self.window_s = window_s
        self.buckets: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window_s
        q = self.buckets.setdefault(key, [])
        # 丢弃窗口外
        i = 0
        for ts in q:
            if ts >= window_start:
                break
            i += 1
        if i:
            del q[:i]
        if len(q) >= self.max_requests:
            return False
        q.append(now)
        return True


rate_limiter = RateLimiter(settings.rate_limit_requests, settings.rate_limit_window_s)


def require_rate_limit(request: Request, x_api_key: str | None = Header(default=None)):
    if not settings.rate_limit_enabled:
        return
    if settings.rate_limit_by == "api_key" and x_api_key:
        key = f"ak:{x_api_key}"
    else:
        client_ip = request.client.host if request.client else "0.0.0.0"
        key = f"ip:{client_ip}"
    if not rate_limiter.allow(key):
        raise HTTPException(status_code=429, detail="too many requests")


# ---------- 日志与脱敏 ----------
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("app")

_KEY_PAT = re.compile(r"sk-[A-Za-z0-9]+", re.IGNORECASE)


def sanitize_text(text: str) -> str:
    try:
        t = _KEY_PAT.sub("sk-***", text)
        if len(t) > settings.log_truncate_len:
            t = t[: settings.log_truncate_len] + "...<truncated>"
        return t
    except Exception:
        return "<unloggable>"


SENSITIVE_HEADERS = {"authorization", "x-api-key"}


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    red = {}
    for k, v in headers.items():
        if k.lower() in SENSITIVE_HEADERS:
            red[k] = "***"
        else:
            red[k] = v
    return red


# ---------- 中间件：请求体大小限制 + 基本访问日志 ----------
@app.middleware("http")
async def body_limit_and_logging(request: Request, call_next):
    # 限制请求体大小（基于 Content-Length）
    if request.method in ("POST", "PUT", "PATCH"):
        cl = request.headers.get("content-length")
        try:
            if cl is not None and int(cl) > settings.request_max_body_bytes:
                return StreamingResponse(
                    content=(c async for c in async_iter(["payload too large"])),
                    media_type="text/plain",
                    status_code=413,
                )
        except ValueError:
            pass

    # 访问日志（不记录请求体）
    client_ip = request.client.host if request.client else "-"
    logger.info(
        "req %s %s ip=%s headers=%s",
        request.method,
        request.url.path,
        client_ip,
        sanitize_headers(dict(request.headers)),
    )

    response = await call_next(request)
    logger.info("res %s %s status=%s", request.method, request.url.path, response.status_code)
    return response


async def async_iter(chunks):
    for c in chunks:
        yield c


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key), Depends(require_rate_limit)])
async def chat(request: ChatRequest):
    """聊天接口"""
    try:
        # 获取会话历史
        history = session_manager.get_history(request.session_id)

        # 调用会话链
        reply = await chat_chain.process_message(
            message=request.message, history=history
        )

        # 更新会话历史
        session_manager.add_message(
            session_id=request.session_id,
            user_message=request.message,
            bot_message=reply,
        )

        return ChatResponse(reply=reply, session_id=request.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@app.post("/chat/stream", dependencies=[Depends(require_api_key), Depends(require_rate_limit)])
async def chat_stream(request: ChatRequest):
    """流式聊天接口（SSE）。"""

    async def event_generator():
        history = session_manager.get_history(request.session_id)
        collected: list[str] = []
        try:
            async for chunk in chat_chain.stream_message(
                message=request.message, history=history
            ):
                text = str(chunk)
                collected.append(text)
                yield f"data: {text}\n\n"
            # 结束事件
            full_reply = "".join(collected).strip()
            session_manager.add_message(
                session_id=request.session_id,
                user_message=request.message,
                bot_message=full_reply,
            )
            yield "event: end\ndata: [DONE]\n\n"
        except Exception as e:
            # 错误事件（不暴露内部细节）
            yield "event: error\ndata: 服务器处理异常\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/chat/stream", dependencies=[Depends(require_api_key), Depends(require_rate_limit)])
async def chat_stream_get(message: str, session_id: str):
    """流式聊天接口（GET 版本，兼容原生 EventSource）。"""

    async def event_generator():
        history = session_manager.get_history(session_id)
        collected: list[str] = []
        try:
            async for chunk in chat_chain.stream_message(
                message=message, history=history
            ):
                text = str(chunk)
                collected.append(text)
                yield f"data: {text}\n\n"
            full_reply = "".join(collected).strip()
            session_manager.add_message(
                session_id=session_id,
                user_message=message,
                bot_message=full_reply,
            )
            yield "event: end\ndata: [DONE]\n\n"
        except Exception:
            yield "event: error\ndata: 服务器处理异常\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "version": "1.0.0"}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    session_manager.clear_session(session_id)
    return {"message": f"会话 {session_id} 删除成功"}


@app.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """获取会话历史"""
    history = session_manager.get_history(session_id)
    return {"session_id": session_id, "history": history}


if __name__ == "__main__":
    # 默认开发模式，未提供证书时以 HTTP 运行
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        ssl_certfile=settings.ssl_certfile,
        ssl_keyfile=settings.ssl_keyfile,
        ssl_keyfile_password=settings.ssl_keyfile_password,
    )
