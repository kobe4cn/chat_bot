from typing import List, Dict
from datetime import datetime
from collections import defaultdict

import time


class SessionManager:
    def __init__(self, max_history_length: int = 10):
        self.sessions: Dict[str, List[Dict]] = defaultdict(list)
        self.max_history_length = max_history_length
        self.last_activity: Dict[str, float] = {}

    def get_history(self, session_id: str) -> List[Dict]:
        """获取会话历史"""
        self._update_activity(session_id)
        return self.sessions.get(session_id, [])

    def add_message(self, session_id: str, user_message: str, bot_message: str):
        """添加消息"""
        self._update_activity(session_id)
        message_record = {
            "user_message": user_message,
            "bot_message": bot_message,
            "timestamp": datetime.now().isoformat(),
            "unix_timestamp": time.time(),
        }
        self.sessions[session_id].append(message_record)

        # 如果会话历史长度超过最大历史长度，则删除最早的消息
        if len(self.sessions[session_id]) > self.max_history_length:
            self.sessions[session_id] = self.sessions[session_id][
                -self.max_history_length :
            ]

    def clear_session(self, session_id: str):
        """清空会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.last_activity:
            del self.last_activity[session_id]

    def get_session_stats(self) -> Dict:
        """获取会话统计信息"""
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len(
                [s for s, t in self.last_activity.items() if t > time.time() - 3600]
            ),
            "total_messages": sum(len(messages) for messages in self.sessions.values()),
        }

    def _update_activity(self, session_id: str):
        """更新会话活跃时间"""
        self.last_activity[session_id] = time.time()

    def clean_inactive_sessions(self, timeout_hours: int = 24):
        """清理非活跃会话"""
        inactive_session = [
            session_id
            for session_id, last_activity in self.last_activity.items()
            if last_activity < time.time() - timeout_hours * 3600
        ]

        for session_id in inactive_session:
            self.clear_session(session_id)
        return len(inactive_session)
