"""
RAG 工具 - 向量检索工具
将 RAG Service 包装为 LangChain 工具
"""

import logging

from langchain.tools import tool
from app.services.rag_service import get_rag_service

logger = logging.getLogger(__name__)


@tool
async def search_news(query: str, top_k: int = 5) -> str:
    """
    搜索相关新闻信息
    """
    try:
        service = get_rag_service()
        results = await service.search(query, top_k=top_k)
        formatted_results = service.format_results(results)

        logger.info(f"搜索完成: '{query[:30]}...' -> {len(results)} 条结果")
        return formatted_results

    except Exception as e:
        error_msg = f"搜索新闻时出错: {str(e)}"
        logger.error(error_msg)
        return error_msg


__all__ = ["search_news"]