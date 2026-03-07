"""
LLM 服务 - 智谱 AI 集成
"""

from langchain_openai import ChatOpenAI
from app.config import settings


class LLMService:
    """LLM 服务类"""

    def __init__(self):
        """初始化 LLM 服务"""
        self.chat_model = self._create_chat_model()
        self.streaming_model = self._create_streaming_model()

    def _create_chat_model(self) -> ChatOpenAI:
        """创建普通聊天模型"""
        return ChatOpenAI(
            model=settings.zhipu_ai_model,
            api_key=settings.zhipu_ai_api_key,
            base_url=settings.zhipu_ai_base_url,
            temperature=0.7,
            max_tokens=2048,
            timeout=60,
        )

    def _create_streaming_model(self) -> ChatOpenAI:
        """创建流式聊天模型"""
        return ChatOpenAI(
            model=settings.zhipu_ai_model,
            api_key=settings.zhipu_ai_api_key,
            base_url=settings.zhipu_ai_base_url,
            temperature=0.7,
            max_tokens=2048,
            streaming=True,
            timeout=60,
        )

    def get_chat_model(self) -> ChatOpenAI:
        """获取普通聊天模型"""
        return self.chat_model

    def get_streaming_model(self) -> ChatOpenAI:
        """获取流式聊天模型"""
        return self.streaming_model

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        from datetime import datetime

        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")

        return f"""你是一个专业金融数据分析师。你叫小财。
当前的日期是：{current_date}
当前的时间是：{current_time}
如果工具调用结果、用户提示词中没有明确给出股票代码对应的公司挂牌名称，请你调用工具查询正确的公司名称信息再回答。
"""


# 全局 LLM 服务实例
llm_service = LLMService()
