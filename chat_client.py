"""聊天客户端模块 - 用于测试智能对话服务API"""

import requests
import json
import time


class ChatClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = f"test_user_{int(time.time())}"

    def send_message(self, message: str) -> dict:
        url = f"{self.base_url}/chat"
        payload = {"message": message, "session_id": self.session_id}
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"发送消息失败: {e}")
            return {"error": str(e)}

    def get_history(self) -> dict:
        """获取历史记录"""
        url = f"{self.base_url}/sessions/{self.session_id}/history"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"获取历史记录失败: {e}")
            return {"error": str(e)}

    def clear_session(self) -> dict:
        """清空会话"""
        url = f"{self.base_url}/sessions/{self.session_id}"
        try:
            response = requests.delete(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"清空会话失败: {e}")
            return {"error": str(e)}


def main():
    client = ChatClient()
    print(f"开始测试服务 (会话ID: {client.session_id})")
    print("=" * 50)

    test_messages = [
        "你好",
        "你能做什么？",
        "请介绍一下你自己",
        "请帮忙介绍下Rust语言?",
        "能否介绍下它的优略相比于Go和Java?",
        "Rust语言有哪些优点和缺点,适用场景?",
        "谢谢你的帮助",
        "再见",
    ]

    for msg in test_messages:
        print(f"发送消息: {msg}")
        response = client.send_message(msg)
        if "error" in response:
            print(f"发送消息失败: {response['error']}")
            continue
        else:
            print(f"收到回复: {response['reply']}")

        print("-" * 30)
        time.sleep(1)

    print("\n 获取会话历史")
    history = client.get_history()
    if "error" not in history:
        for i, record in enumerate(history.get("history", []), 1):
            print(f"{i}. 用户: {record['user_message']}")
            print(f"    AI: {record['bot_message']}")
            print(f"    时间: {record['timestamp']}")

    print("\n 清空会话")
    result = client.clear_session()
    if "error" not in result:
        print(f"清楚会话 {result}")


if __name__ == "__main__":
    main()
