#!/usr/bin/env python3
"""
FastAPI 集成多维数组会话管理的示例
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from session_manager import SessionManager

app = FastAPI(title="AI API with Multidimensional Array Session Management", version="2.0.0")

# 全局会话管理器
session_manager = SessionManager(max_history_length=100, session_timeout_minutes=30)


class ChatRequest(BaseModel):
    message: str
    session_index: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    session_index: int


class SessionStatsResponse(BaseModel):
    session_index: int
    session_id: Any
    total_messages: int
    user_messages: int
    ai_messages: int
    created_at: str
    last_activity: str
    is_active: bool


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    # 如果没有提供会话索引，创建新会话
    if request.session_index is None:
        session_index = session_manager.create_session()
    else:
        session_index = request.session_index
        # 检查会话是否存在且有效
        if session_index < 0 or session_index >= len(session_manager.sessions):
            raise HTTPException(status_code=404, detail="会话不存在")

    # 添加用户消息
    success = session_manager.add_user_message(session_index, request.message)
    if not success:
        raise HTTPException(status_code=400, detail="添加用户消息失败")

    # 模拟AI回复（在实际应用中，这里会调用LLM）
    ai_response = f"我理解您说的是: {request.message}。这是一个模拟回复。"

    # 添加AI消息
    success = session_manager.add_ai_message(session_index, ai_response)
    if not success:
        raise HTTPException(status_code=400, detail="添加AI消息失败")

    return ChatResponse(response=ai_response, session_index=session_index)


@app.get("/sessions", response_model=List[int])
async def list_sessions():
    """获取所有会话索引列表"""
    return session_manager.list_all_sessions()


@app.get("/sessions/active", response_model=List[int])
async def list_active_sessions():
    """获取活跃会话索引列表"""
    return session_manager.list_active_sessions()


@app.get("/sessions/{session_index}/history")
async def get_session_history(session_index: int):
    """获取会话历史"""
    history = session_manager.get_session_history(session_index)
    if not history and (session_index < 0 or session_index >= len(session_manager.sessions)):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"session_index": session_index, "history": history}


@app.get("/sessions/{session_index}/langchain-messages")
async def get_langchain_messages(session_index: int):
    """获取LangChain格式的消息"""
    messages = session_manager.get_langchain_messages(session_index)
    if not messages and (session_index < 0 or session_index >= len(session_manager.sessions)):
        raise HTTPException(status_code=404, detail="会话不存在")

    # 转换为可序列化的格式
    serialized_messages = []
    for msg in messages:
        serialized_messages.append({
            "type": type(msg).__name__,
            "content": msg.content
        })

    return {"session_index": session_index, "messages": serialized_messages}


@app.get("/sessions/{session_index}/stats", response_model=SessionStatsResponse)
async def get_session_stats(session_index: int):
    """获取会话统计信息"""
    stats = session_manager.get_session_stats(session_index)
    if not stats:
        raise HTTPException(status_code=404, detail="会话不存在")
    return SessionStatsResponse(**stats)


@app.get("/sessions/stats")
async def get_all_sessions_stats():
    """获取全局会话统计"""
    return session_manager.get_all_sessions_stats()


@app.delete("/sessions/{session_index}")
async def delete_session(session_index: int):
    """删除会话"""
    success = session_manager.delete_session(session_index)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "会话删除成功"}


@app.post("/sessions/{session_index}/clear")
async def clear_session(session_index: int):
    """清空会话内容"""
    success = session_manager.clear_session(session_index)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "会话内容清空成功"}


@app.post("/sessions/cleanup")
async def cleanup_inactive_sessions():
    """清理非活跃会话"""
    cleaned_count = session_manager.cleanup_inactive_sessions()
    return {"message": f"清理了 {cleaned_count} 个非活跃会话"}


@app.post("/sessions/{session_index}/update-activity")
async def update_session_activity(session_index: int):
    """更新会话活跃时间"""
    success = session_manager.update_session_activity(session_index)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"message": "会话活跃时间更新成功"}


@app.get("/sessions/{session_index}/export")
async def export_session(session_index: int):
    """导出会话数据"""
    data = session_manager.export_session_data(session_index)
    if not data:
        raise HTTPException(status_code=404, detail="会话不存在")
    return data


@app.post("/sessions/import")
async def import_session(session_data: Dict[str, Any]):
    """导入会话数据"""
    session_index = session_manager.import_session_data(session_data)
    if session_index is None:
        raise HTTPException(status_code=400, detail="导入会话数据失败")
    return {"message": "会话数据导入成功", "session_index": session_index}


@app.get("/sessions/arrays/sessions")
async def get_sessions_array():
    """获取sessions多维数组"""
    return {"sessions": session_manager.get_sessions_array()}


@app.get("/sessions/arrays/activity")
async def get_activity_array():
    """获取last_activity多维数组"""
    return {"last_activity": session_manager.get_last_activity_array()}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "total_sessions": len(session_manager.list_all_sessions()),
        "active_sessions": len(session_manager.list_active_sessions())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)