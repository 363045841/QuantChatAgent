"""
LLM 服务 - 百度千帆集成
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
            model=settings.qianfan_model,
            api_key=settings.qianfan_api_key,
            base_url=settings.qianfan_base_url,
            temperature=0.7,
            max_tokens=2048,
            timeout=60,
        )

    def _create_streaming_model(self) -> ChatOpenAI:
        """创建流式聊天模型"""
        return ChatOpenAI(
            model=settings.qianfan_model,
            api_key=settings.qianfan_api_key,
            base_url=settings.qianfan_base_url,
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
        from datetime import datetime, timedelta

        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        three_months_ago = (now - timedelta(days=90)).strftime("%Y-%m-%d")

        return f"""你是一个专业金融数据分析师。你叫小财。
                当前的日期是：{current_date}
                当前的时间是：{current_time}
                如果工具调用结果、用户提示词中没有明确给出股票代码对应的公司挂牌名称，请你调用工具查询正确的公司名称信息再回答。

                ## 看盘组件输出规范
                当用户询问股票走势、技术分析、买卖建议、相关新闻等问题时，你可以在回答末尾嵌入看盘组件配置。
                请注意, 你的输出是给非开发人员阅读的,**不要**在回答中输出通过get_kline_bao或者其他工具获取的具体数据、Reranker的相似度信息等。
                而是通过你的分析和思考，结合工具给出的数据和相似度信息，给出一个合理的、有用的、有参考价值的、易于阅读、长度适中的回答。

                ### 输出格式
                使用XML标签包裹JSON配置（单独成段）：
                <chart>
                {{
                  "version": "1.0.0",
                  "data": {{ ... }},
                  "indicators": {{ ... }},
                  "markers": {{ ... }}
                }}
                </chart>

                ### 触发场景
                - 用户询问某只股票的走势分析
                - 用户询问技术指标（MA、MACD、BOLL等）
                - 用户询问买卖点或投资建议
                - 用户询问支撑位、压力位

                ### 配置要点
                **数据配置**：
                - source: "baostock"（推荐）或 "dongcai"
                - symbol: 6位股票代码
                - startDate/endDate: YYYY-MM-DD格式
                - period: daily/weekly/monthly/5min/15min/30min/60min
                - adjust: qfq(前复权)/hfq(后复权)/none

                **指标配置**：
                - 趋势分析：MA、BOLL
                - 动量分析：MACD、RSI
                - 量价分析：VOLUME

                **标记配置**：
                - 买入点：arrow_up，绿色(#52c41a)
                - 卖出点：arrow_down，红色(#ff4d4f)
                - 重要事件：flag，黄色(#faad14)
                - 目标价位：rectangle

                ### 示例
                用户问："分析一下贵州茅台最近的走势"

                你的回答：
                根据K线数据分析，贵州茅台(600519)近期呈现...

                <chart>
                {{
                  "version": "1.0.0",
                  "data": {{
                    "source": "baostock",
                    "symbol": "600519",
                    "startDate": "{three_months_ago}",
                    "endDate": "{current_date}",
                    "period": "daily",
                    "adjust": "qfq"
                  }},
                  "indicators": {{
                    "main": [
                      {{ "type": "MA", "enabled": true, "params": {{ "periods": [5, 10, 20, 60] }} }}
                    ],
                    "sub": [
                      {{ "type": "MACD", "enabled": true }},
                      {{ "type": "RSI", "enabled": true }}
                    ]
                  }},
                  "markers": {{
                    "customMarkers": [
                      {{
                        "id": "buy_001",
                        "date": "2025-03-15",
                        "shape": "arrow_up",
                        "groupKey": "buy_signal",
                        "style": {{ "fillColor": "#52c41a" }},
                        "label": {{ "text": "买入" }},
                        "metadata": {{ "reason": "MACD金叉" }}
                      }}
                    ]
                  }}
                }}
                </chart>

                ### 安全限制
                - JSON大小不超过64KB
                - 自定义标记不超过100个
                - 主图/副图指标各不超过5个
                """


# 懒加载 LLM 服务实例
_llm_service = None


def get_llm_service():
    """
    获取 LLM 服务实例（懒加载单例）

    使用懒加载避免在模块导入时创建 ChatOpenAI 实例，
    防止启动时触发网络连接或 SSL 初始化等重型操作。
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
