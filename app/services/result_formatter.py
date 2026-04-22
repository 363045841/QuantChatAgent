"""
检索结果格式化服务

职责：
- 将原始检索结果格式化为可读的文本输出
- 处理时间戳转换、情感标签映射等字段格式化
- 提供统一的结果展示格式

设计原则：
- 与检索逻辑分离：纯格式化，无业务逻辑
- 可复用：不同检索服务可共用同一格式化器
- 可扩展：支持多种输出格式（文本、JSON、Markdown 等）
"""

from datetime import datetime
from typing import List, Dict, Any


class ResultFormatter:
    """
    检索结果格式化器

    负责将结构化检索结果转换为人类可读的文本格式，
    支持字段映射、时间格式化、分数展示等功能。

    Attributes:
        sentiment_map: 情感标签到文本的映射表
    """

    def __init__(self):
        """初始化格式化器，配置字段映射规则。"""
        # 情感标签映射：0=中性，1=利好，2=利空
        self.sentiment_map = {
            "0": "中性",
            "1": "利好",
            "2": "利空",
        }

    def format_search_results(
        self,
        results: List[Dict[str, Any]],
        empty_message: str = "未找到相关新闻信息"
    ) -> str:
        """
        格式化检索结果为可读文本

        将检索结果列表格式化为带编号的文本块，每个结果包含：
        - 序号和相似度分数
        - 标题、摘要、时间、来源
        - 情感倾向
        - 原始链接

        Args:
            results: 检索结果列表，每个结果为包含以下字段的字典：
                - score: 相似度分数 (float)
                - title: 标题 (str)
                - abstract: 摘要 (str)
                - timestamp: Unix 时间戳 (int, 可选)
                - source: 来源 (str, 可选)
                - sentiment: 情感标签 (str, 可选)
                - url: 链接 (str, 可选)
            empty_message: 结果为空时的提示信息

        Returns:
            格式化后的多行文本

        Example:
            >>> formatter = ResultFormatter()
            >>> results = [{
            ...     "score": 0.85,
            ...     "title": "测试新闻",
            ...     "abstract": "这是一个测试",
            ...     "timestamp": 1704067200,
            ...     "source": "测试源",
            ...     "sentiment": "1",
            ...     "url": "http://example.com"
            ... }]
            >>> print(formatter.format_search_results(results))
        """
        if not results:
            return empty_message

        formatted_items = []
        for idx, result in enumerate(results, 1):
            item = self._format_single_result(idx, result)
            formatted_items.append(item)

        return "\n".join(formatted_items)

    def _format_single_result(self, index: int, result: Dict[str, Any]) -> str:
        """
        格式化单个检索结果

        Args:
            index: 结果序号（用于展示）
            result: 单个结果字典

        Returns:
            格式化的单条结果文本
        """
        # 提取字段（使用 .get() 提供默认值防止 KeyError）
        score = result.get("score", 0.0)
        title = result.get("title", "无标题")
        abstract = result.get("abstract", "")
        timestamp = result.get("timestamp", 0)
        source = result.get("source", "未知")
        sentiment = result.get("sentiment", "0")
        url = result.get("url", "")

        # 格式化时间戳
        date_str = self._format_timestamp(timestamp)

        # 转换情感标签
        sentiment_text = self._get_sentiment_text(sentiment)

        # 构建格式化文本块
        return f"""
【新闻 {index}】（相似度: {score:.3f}）
标题: {title}
摘要: {abstract}
时间: {date_str}
来源: {source}
情感: {sentiment_text}
链接: {url}"""

    def _format_timestamp(self, timestamp: int) -> str:
        """
        将 Unix 时间戳格式化为可读字符串

        Args:
            timestamp: Unix 时间戳（秒）

        Returns:
            格式化的日期时间字符串，无效时间戳返回 "未知时间"
        """
        if not timestamp:
            return "未知时间"

        try:
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError, OverflowError):
            # 处理无效时间戳（如负数、过大值等）
            return "无效时间"

    def _get_sentiment_text(self, sentiment: str) -> str:
        """
        将情感标签转换为可读文本

        Args:
            sentiment: 情感标签字符串（"0"/"1"/"2" 或其他）

        Returns:
            对应的情感描述文本
        """
        return self.sentiment_map.get(sentiment, "未知")

    def format_score_summary(self, results: List[Dict[str, Any]]) -> str:
        """
        生成检索结果的分数摘要（用于日志记录）

        Args:
            results: 检索结果列表

        Returns:
            包含每条结果标题预览和分数的摘要文本
        """
        if not results:
            return "无结果"

        lines = []
        for idx, result in enumerate(results, 1):
            score = result.get("score", 0.0)
            title = result.get("title", "无标题")
            # 标题预览：过长时截断
            title_preview = title[:30] + "..." if len(title) > 30 else title
            lines.append(f"  {idx}. [{score:.3f}] {title_preview}")

        return "\n".join(lines)


# 全局单例
_formatter: ResultFormatter = ResultFormatter()


def get_result_formatter() -> ResultFormatter:
    """
    获取结果格式化器单例

    Returns:
        ResultFormatter 单例实例
    """
    return _formatter
