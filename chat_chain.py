from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_community.llms import Tongyi
from typing import List, Dict, Any, AsyncIterator
import dotenv
from config import settings

dotenv.load_dotenv()

class ChatChain:
    def __init__(self):
        self.llms = None
        self.chain = None
        self.parser = StrOutputParser()

    async def initialize(self):
        # 使用集中配置
        self.llm = Tongyi(model=settings.model_name, temperature=settings.temperature)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """你是一个专业的智能客服助手，请遵循以下规则：
            1. 友好，专业地回答客户问题
            2. 如果不知道答案，请礼貌地告知客户不知道
            3. 保持回答简洁明了
            4. 根据对话历史提供连贯回复
            5. 用中文回答""",
                ),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{message}"),
            ]
        )
        self.chain = (
            RunnablePassthrough.assign(history=RunnableLambda(self._format_history))
            | self.prompt
            | self.llm
            | self.parser
        )

    async def process_message(self, message: str, history: List[Dict]) -> str:
        """处理消息"""
        try:
            input_data = {
                "message": message,
                "raw_history": history,
            }
            response = await self.chain.ainvoke(input_data)
            return response.strip()
        except Exception as e:
            print(f"处理消息失败: {e}")
            return "抱歉无法处理你的消息，请稍后再试"

    def _format_history(self, input_data: Dict[str, Any]) -> List[BaseMessage]:
        """格式化对话历史 为langchain 消息格式"""

        history = input_data.get("raw_history", [])
        if not history:
            return []

        messages: List[BaseMessage] = []
        recent_history = history[-10:] if len(history) > 10 else history
        for msg in recent_history:
            if msg["user_message"]:
                messages.append(HumanMessage(content=msg["user_message"]))
            if msg["bot_message"]:
                messages.append(AIMessage(content=msg["bot_message"]))
        return messages

    async def stream_message(self, message: str, history: List[Dict]) -> AsyncIterator[str]:
        """流式处理消息，逐块产出文本片段。

        说明：依赖 LangChain 的 astream 能力，将解析后字符串片段逐步返回。
        """
        input_data = {"message": message, "raw_history": history}
        try:
            async for chunk in self.chain.astream(input_data):
                # chunk 通常为 str 片段
                if chunk:
                    yield str(chunk)
        except Exception as e:
            # 发生错误时，向上抛出，由上层统一处理
            raise e
