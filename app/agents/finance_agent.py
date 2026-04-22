"""
金融分析 Agent - 使用 LangGraph 构建的智能助手
"""

from typing import Optional, List, Dict, Any, Tuple

from langchain_core.messages import HumanMessage, AIMessage
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

    def chat(
        self, message: str, chat_history: Optional[List] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """同步对话

        Returns:
            (回复内容, usage信息)
        """
        messages = []
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=message))

        try:
            result = self.agent.invoke({"messages": messages})
            last_message = result["messages"][-1]
            usage = self._extract_usage(last_message)
            return last_message.content, usage
        except Exception as e:
            print(f"对话失败: {e}")
            return f"抱歉，处理您的请求时出现了错误：{str(e)}", {}

    async def achat(
        self, message: str, chat_history: Optional[List] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """异步对话

        Returns:
            (回复内容, usage信息)
        """
        messages = []
        if chat_history:
            messages.extend(chat_history)
        messages.append(HumanMessage(content=message))

        try:
            result = await self.agent.ainvoke({"messages": messages})
            last_message = result["messages"][-1]
            usage = self._extract_usage(last_message)
            return last_message.content, usage
        except Exception as e:
            print(f"对话失败: {e}")
            return f"抱歉，处理您的请求时出现了错误：{str(e)}", {}

    async def achat_stream(self, message: str, chat_history: Optional[List] = None):
        """流式对话

        Yields:
            chunk: 流式响应块
            最后会 yield 一个包含 usage 的特殊块
        """
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

    def _extract_usage(self, message: AIMessage) -> Dict[str, Any]:
        """从 AIMessage 中提取 usage 信息"""
        usage = {}

        # 尝试从 response_metadata 获取
        if hasattr(message, "response_metadata") and message.response_metadata:
            token_usage = message.response_metadata.get("token_usage", {})
            if token_usage:
                usage = {
                    "prompt_tokens": token_usage.get("prompt_tokens", 0),
                    "completion_tokens": token_usage.get("completion_tokens", 0),
                    "total_tokens": token_usage.get("total_tokens", 0),
                }

        # 尝试从 usage_metadata 获取（LangChain 新格式）
        if not usage and hasattr(message, "usage_metadata") and message.usage_metadata:
            usage = {
                "prompt_tokens": message.usage_metadata.get("input_tokens", 0),
                "completion_tokens": message.usage_metadata.get("output_tokens", 0),
                "total_tokens": message.usage_metadata.get("total_tokens", 0),
            }

        return usage


_finance_agent = None


def get_finance_agent():
    global _finance_agent
    if _finance_agent is None:
        _finance_agent = FinanceAgent()
    return _finance_agent
