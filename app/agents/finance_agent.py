"""
金融分析 Agent - 使用 LangGraph 构建的智能助手
"""

from typing import Optional, List

from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

from app.services.llm_service import get_llm_service
from app.tools.stock_tools import (
    get_kline_bao,
    query_recent_days_bao,
    get_all_stocks_bao,
    get_stocks_by_date_bao,
)
from app.tools.code_query import query_code_info
from app.tools.rag_tools import search_news


class FinanceAgent:
    """金融分析 Agent 类"""

    def __init__(self):
        llm_svc = get_llm_service()
        self.llm = llm_svc.get_chat_model()
        self.streaming_llm = llm_svc.get_streaming_model()
        self.tools = [
            get_kline_bao,
            query_recent_days_bao,
            get_all_stocks_bao,
            get_stocks_by_date_bao,
            query_code_info,
            search_news,
        ]
        self.system_prompt = llm_svc.get_system_prompt()
        self.agent = self._create_agent()

    def _create_agent(self):
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
        )

    def chat(self, message: str, chat_history: Optional[List] = None) -> str:
        messages = []
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=message))

        try:
            result = self.agent.invoke({"messages": messages})
            last_message = result["messages"][-1]
            return last_message.content
        except Exception as e:
            print(f"对话失败: {e}")
            return f"抱歉，处理您的请求时出现了错误：{str(e)}"

    async def achat(self, message: str, chat_history: Optional[List] = None) -> str:
        messages = []
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=message))

        try:
            result = await self.agent.ainvoke({"messages": messages})
            last_message = result["messages"][-1]
            return last_message.content
        except Exception as e:
            print(f"对话失败: {e}")
            return f"抱歉，处理您的请求时出现了错误：{str(e)}"

    async def achat_stream(self, message: str, chat_history: Optional[List] = None):
        messages = []
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=message))

        try:
            async for chunk in self.agent.astream(
                {"messages": messages},
                stream_mode="messages",
            ):
                yield chunk
        except Exception as e:
            print(f"流式对话失败: {e}")
            yield {"error": f"抱歉，处理您的请求时出现了错误：{str(e)}"}


_finance_agent = None


def get_finance_agent():
    global _finance_agent
    if _finance_agent is None:
        _finance_agent = FinanceAgent()
    return _finance_agent