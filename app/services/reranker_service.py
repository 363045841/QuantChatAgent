"""
百度智能云 Reranker 服务
"""
import httpx
from typing import List, Optional
from app.config import settings


class RerankerService:
    """百度智能云 Reranker 服务"""
    
    def __init__(self):
        self.api_key = settings.baidu_reranker_api_key
        self.model = settings.baidu_reranker_model
        self.base_url = settings.baidu_reranker_base_url
        self.default_top_n = settings.baidu_reranker_top_n
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None
    ) -> List[dict]:
        """
        对文档列表进行重排序
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_n: 返回的最相关文档数量，默认使用配置中的值
        
        Returns:
            重排序后的文档列表，按相关性降序排列
            格式: [{"document": "...", "relevance_score": 0.68, "index": 0}, ...]
        """
        if not documents:
            return []
        
        # 构造请求体
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents
        }
        
        if top_n is not None:
            payload["top_n"] = top_n
        
        # 构造请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                
                # 返回结果（已经按 relevance_score 降序排列）
                return result.get("results", [])
                
        except httpx.HTTPStatusError as e:
            raise Exception(f"Reranker API 请求失败: {e.response.status_code} - {e.response.text}")
        except httpx.TimeoutException:
            raise Exception("Reranker API 请求超时")
        except Exception as e:
            raise Exception(f"Reranker API 调用异常: {str(e)}")
    
    async def rerank_documents_only(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None
    ) -> List[str]:
        """
        对文档列表进行重排序，只返回文档内容
        
        Args:
            query: 查询文本
            documents: 待排序的文档列表
            top_n: 返回的最相关文档数量
        
        Returns:
            重排序后的文档内容列表
        """
        results = await self.rerank(query, documents, top_n)
        return [r["document"] for r in results]