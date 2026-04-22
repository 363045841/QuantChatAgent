"""
金融分析 Agent - 使用 LangGraph 构建的智能助手

该模块是金融智能助手的核心, 负责整合大语言模型(LLM)和各种专业金融工具(如K线获取、新闻检索等),
通过 Agent 架构实现理解用户意图并自动调用工具完成复杂的金融分析任务。
"""

from typing import List

# 导入 LangChain 的基础消息类型, 用于定义对话历史的结构
from langchain_core.messages import BaseMessage
from langgraph.graph.state import CompiledStateGraph

# 导入自定义的 LLM 服务, 用于获取配置好的模型和系统提示词
from app.services.llm_service import get_llm_service

# 导入自定义的金融数据工具
from app.tools.stock_tools import (
    get_kline_bao,  # 工具：获取股票K线数据
    query_recent_days_bao,  # 工具：查询近期交易日数据
    get_all_stocks_bao,  # 工具：获取所有股票列表
    get_stocks_by_date_bao,  # 工具：获取指定日期的股票数据
)

# 导入自定义的工具：通过股票代码查询公司信息
from app.tools.code_query import query_code_info

# 导入自定义的 RAG 工具：检索相关的金融新闻资讯
from app.tools.rag_tools import search_news


class FinanceAgent:
    """金融分析 Agent 类

    该类封装了 Agent 的创建和调用逻辑, 将 LLM 与具体的业务工具绑定,
    提供对外的流式对话接口。
    """

    def __init__(self):
        """初始化 Agent

        在实例化时, 会自动获取 LLM 服务、可用的工具列表、系统提示词,
        并驱动构建底层的 Agent 执行器。
        """
        # 1. 获取全局配置好的 LLM 服务实例
        llm_svc = get_llm_service()
        # 2. 从服务中提取聊天模型
        self.llm = llm_svc.get_chat_model()

        # 3. 定义该 Agent 可以调用的所有工具集合
        # LLM 会根据这些工具的描述(docstring)来决定何时调用哪个工具
        self.tools = [
            get_kline_bao,
            query_recent_days_bao,
            get_all_stocks_bao,
            get_stocks_by_date_bao,
            query_code_info,
            search_news,
        ]

        # 4. 获取系统提示词(定义了 Agent 的角色、行为规范和回答风格)
        self.system_prompt = llm_svc.get_system_prompt()

        # 5. 组装并创建 Agent 实例
        self.agent: CompiledStateGraph = self._create_agent()

    def _create_agent(self):
        """创建并组装 Agent 执行器

        将模型、工具和提示词组合成一个具备"思考-调用工具-观察结果-继续思考"能力的 Agent。

        Returns:
            构建好的 Agent 对象
        """
        from langchain.agents import create_agent

        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.system_prompt,
        )

    async def achat_stream(self, messages: List[BaseMessage]):
        """异步流式对话接口

        接收完整的对话上下文, 以流式的方式返回 Agent 的处理过程和最终结果。

        Args:
            messages: 完整的消息列表。
                      通常格式为 [SystemMessage, HumanMessage1, AIMessage1, ..., HumanMessageN]
                      必须包含当前的最新用户消息。

        Yields:
            chunk: 流式响应块。可能是 LLM 生成的文本片段, 也可能是工具调用的中间状态信息。
                   如果发生错误, 会返回包含 "error" 键的字典。
        """
        try:
            # 调用 Agent 的异步流式方法
            # stream_mode="messages" 表示逐个消息节点地流出(包括中间的 AIMessage、ToolMessage 等)
            async for chunk in self.agent.astream(
                {"messages": messages},
                stream_mode="messages",
            ):
                yield chunk
        except Exception as e:
            # 捕获异常并打印到后端控制台, 方便开发者调试
            print(f"流式对话失败: {e}")
            # 向前端抛出一个友好的错误提示, 避免直接暴露内部代码堆栈
            yield {"error": f"抱歉, 处理您的请求时出现了错误：{str(e)}"}


# ==========================================
# 单例模式实现
# ==========================================
# 使用模块级别的全局变量来保存 Agent 实例
_finance_agent = None


def get_finance_agent():
    """获取 FinanceAgent 的全局单例

    由于 Agent 的初始化可能涉及加载模型、解析工具等耗时操作,
    使用单例模式可以避免每次请求都重新创建 Agent, 节省资源并提高响应速度。

    Returns:
        全局唯一的 FinanceAgent 实例
    """
    global _finance_agent
    # 如果实例还未被创建, 则进行实例化
    if _finance_agent is None:
        _finance_agent = FinanceAgent()
    # 返回已有的实例
    return _finance_agent
