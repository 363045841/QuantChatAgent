"""
金融分析 Agent - 使用 LangGraph 构建的智能助手
"""

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent
from app.services.llm_service import llm_service
from app.tools.stock_tools import (
    get_kline,
    query_recent_days,
    get_all_stocks,
    get_stocks_by_date,
)
from app.tools.code_query import query_code_info
from typing import Optional, List


class FinanceAgent:
    """金融分析 Agent 类"""

    def __init__(self):
        """初始化金融 Agent"""
        self.llm = llm_service.get_chat_model()
        self.streaming_llm = llm_service.get_streaming_model()
        self.tools = [
            get_kline,
            query_recent_days,
            get_all_stocks,
            get_stocks_by_date,
            query_code_info,
        ]

        # 获取系统提示词
        self.system_prompt = llm_service.get_system_prompt()

        # 创建 Agent
        self.agent = self._create_agent()

    def _create_agent(self):
        """
        使用 LangGraph 创建 ReAct Agent

        Returns:
            LangGraph CompiledGraph 实例
        """
        """ return create_react_agent(
            self.llm,
            self.tools,
            prompt=self.system_prompt
        ) """
        return create_agent(
            model=self.llm, tools=self.tools, system_prompt=self.system_prompt
        )

    def chat(self, message: str, chat_history: Optional[List] = None) -> str:
        """
        普通对话

        Args:
            message: 用户消息
            chat_history: 聊天历史（可选）

        Returns:
            AI 的回复
        """
        messages = []

        # 添加聊天历史
        if chat_history:
            messages.extend(chat_history)

        # 添加当前用户消息
        messages.append(HumanMessage(content=message))

        try:
            result = self.agent.invoke({"messages": messages})
            # 获取最后一条 AI 消息
            last_message = result["messages"][-1]
            return last_message.content
        except Exception as e:
            print(f"对话失败: {e}")
            return f"抱歉，处理您的请求时出现了错误：{str(e)}"

    async def achat(self, message: str, chat_history: Optional[List] = None) -> str:
        """
        异步普通对话

        Args:
            message: 用户消息
            chat_history: 聊天历史（可选）

        Returns:
            AI 的回复
        """
        messages = []

        # 添加聊天历史
        if chat_history:
            messages.extend(chat_history)

        # 添加当前用户消息
        messages.append(HumanMessage(content=message))

        try:
            result = await self.agent.ainvoke({"messages": messages})
            # 获取最后一条 AI 消息
            last_message = result["messages"][-1]
            return last_message.content
        except Exception as e:
            print(f"对话失败: {e}")
            return f"抱歉，处理您的请求时出现了错误：{str(e)}"

    async def achat_stream(self, message: str, chat_history: Optional[List] = None):
        """
        异步流式对话

        Args:
            message: 用户消息
            chat_history: 聊天历史（可选）

        Yields:
            流式输出的内容块
        """
        messages = []

        # 添加聊天历史
        if chat_history:
            messages.extend(chat_history)

        # 添加当前用户消息
        messages.append(HumanMessage(content=message))

        try:
            async for chunk in self.agent.astream({"messages": messages}, stream_mode="messages"):
                yield chunk
        except Exception as e:
            print(f"流式对话失败: {e}")
            yield {"error": f"抱歉，处理您的请求时出现了错误：{str(e)}"}


# 全局 Agent 实例
finance_agent = FinanceAgent()
