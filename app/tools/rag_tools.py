"""
RAG 工具 - 向量检索工具
将 RAG Service 包装为 LangChain 工具
"""

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from app.services.rag_service import rag_service
import logging

logger = logging.getLogger(__name__)


@tool
async def search_news(query: str, top_k: int = 5) -> str:
    """
    搜索相关新闻信息
    
    当用户询问关于某只股票或公司的新闻、资讯、消息时，使用此工具搜索相关信息。
    该工具会从向量数据库中检索与查询最相关的新闻内容。
    
    适用场景：
    - 用户询问某只股票的最新消息
    - 用户想了解某公司的新闻动态
    - 用户查询某股票的资讯、公告等
    - 用户询问关于某个公司的市场传闻
    
    Args:
        query: 搜索关键词，例如：
            - "601360 最新消息"
            - "阿里巴巴 财报"
            - "腾讯 新品发布"
            - "新能源汽车 政策"
        top_k: 返回结果数量，默认5条，范围1-10。数值越大返回结果越多，但可能相关性降低。
    
    Returns:
        相关新闻的摘要信息，每条包含：
        - 标题和摘要
        - 发布时间
        - 新闻来源
        - 情感倾向（利好/中性/利空）
        - 相似度评分
        - 原文链接
    
    Examples:
        >>> search_news("601360 最新消息")
        >>> search_news("阿里巴巴 财报", top_k=3)
        >>> search_news("新能源汽车 行业动态")
    
    Note:
        - 检索基于语义相似度，不限于完全匹配关键词
        - 结果按相似度从高到低排序
        - 如果未找到相关新闻，将返回"未找到相关新闻信息"
    """
    try:
        logger.info(f"开始搜索新闻: query='{query}', top_k={top_k}")
        
        # 调用 RAG Service 检索（异步）
        results = await rag_service.search(query, top_k=top_k)
        
        # 格式化结果
        formatted_results = rag_service.format_results(results)
        
        logger.info(f"搜索完成，返回 {len(results)} 条结果")
        return formatted_results
        
    except Exception as e:
        error_msg = f"搜索新闻时出错: {str(e)}"
        logger.error(error_msg)
        return error_msg


# 导出工具列表，方便其他模块使用
__all__ = ["search_news"]