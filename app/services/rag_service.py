"""
RAG 服务 - 向量检索服务
使用 Qdrant 向量数据库、智谱 AI Embedding API 和百度智能云 Reranker
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models
import httpx
import logging
from typing import List, Dict, Optional
from datetime import datetime
from qdrant_client.http import models
from app.config import settings
from app.services.reranker_service import RerankerService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGService:
    """RAG 服务类 - 提供向量检索功能"""

    def __init__(self):
        """初始化 RAG 服务"""
        # 初始化 Qdrant 客户端
        self.client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        # 配置信息
        self.collection_name = settings.rag_collection_name
        self.embedding_url = settings.zhipu_embedding_api_url
        self.embedding_model = settings.zhipu_embedding_model
        self.api_key = settings.zhipu_api_key or settings.zhipu_ai_api_key
        self.embedding_dimensions = settings.zhipu_embedding_dimensions

        logger.info(f"RAG Service 初始化完成 - Collection: {self.collection_name}")

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        调用智谱 AI Embedding API 生成向量

        Args:
            text: 要生成向量的文本

        Returns:
            向量列表，失败返回 None
        """
        if not self.api_key:
            logger.error("未配置 ZHIPU_API_KEY")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.embedding_model,
            "input": text,
            "dimensions": self.embedding_dimensions,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.embedding_url, headers=headers, json=data
                )

                if response.status_code == 200:
                    result = response.json()
                    embedding = result["data"][0]["embedding"]
                    return embedding
                else:
                    logger.error(
                        f"Embedding API 调用失败: {response.status_code} - {response.text}"
                    )
                    return None

        except Exception as e:
            logger.error(f"调用 Embedding API 异常: {e}")
            return None

    async def search(
        self, query: str, top_k: int = 5, score_threshold: float = 0.5, use_reranker: bool = True
    ) -> List[Dict]:
        """
        向量相似度检索（可选 Reranker 重排序）

        Args:
            query: 查询文本
            top_k: 返回结果数量
            score_threshold: 相似度阈值，低于此值的结果将被过滤
            use_reranker: 是否使用 Reranker 进行重排序

        Returns:
            检索结果列表，每个结果包含分数和 payload
        """
        try:
            # 生成查询向量
            logger.info(f"生成查询向量: {query[:50]}...")
            query_vector = await self._get_embedding(query)

            if query_vector is None:
                logger.error("查询向量生成失败")
                return []

            # 向量检索：获取更多候选结果用于 Reranker
            candidate_count = max(top_k * 2, 20)  # 获取更多候选
            logger.info(f"在 {self.collection_name} 中检索 top_{candidate_count}...")
            query_results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="default",
                limit=candidate_count,
                with_payload=True,
            )
            search_results = query_results.points

            # 格式化初步检索结果
            formatted_results = []
            for result in search_results:
                if result.score < score_threshold:
                    continue  # 过滤低分结果
                
                payload = result.payload
                formatted_result = {
                    "score": result.score,
                    "title": payload.get("title", ""),
                    "abstract": payload.get("abstract", ""),
                    "timestamp": payload.get("timestamp", 0),
                    "source": payload.get("source", "未知"),
                    "sentiment": payload.get("sentiment", "0"),
                    "url": payload.get("url", ""),
                    "stock_code": payload.get("stock_code", ""),
                }
                formatted_results.append(formatted_result)

            if not formatted_results:
                logger.info("未找到符合阈值的结果")
                return []

            # 使用 Reranker 重排序
            if use_reranker and settings.baidu_reranker_api_key:
                logger.info(f"使用 Reranker 重排序 {len(formatted_results)} 条候选结果...")
                try:
                    reranker_service = RerankerService()
                    
                    # 构造文档列表（使用摘要作为 Reranker 的输入）
                    documents = [f"{r['title']}\n{r['abstract']}" for r in formatted_results]
                    
                    # 调用 Reranker
                    rerank_results = await reranker_service.rerank(query, documents, top_n=top_k)
                    
                    # 根据重排序结果重新组织
                    reranked_dict = {}
                    for result in rerank_results:
                        doc_text = result["document"]
                        # 找到对应的结果
                        for i, doc in enumerate(documents):
                            if doc == doc_text:
                                reranked_dict[i] = result["relevance_score"]
                                break
                    
                    # 按重排序结果重新排列
                    if reranked_dict:
                        final_results = []
                        for idx in sorted(reranked_dict.keys(), key=lambda x: reranked_dict[x], reverse=True):
                            original_result = formatted_results[idx]
                            # 更新分数为 Reranker 的分数
                            original_result["score"] = reranked_dict[idx]
                            final_results.append(original_result)
                        
                        logger.info(f"Reranker 重排序完成，返回 {len(final_results)} 条结果")
                        return final_results[:top_k]
                    
                except Exception as e:
                    logger.warning(f"Reranker 调用失败，使用原始结果: {e}")
                    return formatted_results[:top_k]

            # 不使用 Reranker 或 Reranker 失败，返回原始结果
            logger.info(f"检索完成，返回 {min(len(formatted_results), top_k)} 条结果")
            return formatted_results[:top_k]

        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []

    def format_results(self, results: List[Dict]) -> str:
        """
        格式化检索结果为可读文本

        Args:
            results: 检索结果列表

        Returns:
            格式化后的文本
        """
        if not results:
            return "未找到相关新闻信息"

        formatted = []
        for idx, result in enumerate(results, 1):
            timestamp = result.get("timestamp", 0)
            if timestamp:
                date_str = datetime.fromtimestamp(timestamp).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            else:
                date_str = "未知时间"

            item = f"""
【新闻 {idx}】（相似度: {result['score']:.3f}）
标题: {result['title']}
摘要: {result['abstract']}
时间: {date_str}
来源: {result['source']}
情感: {self._get_sentiment_text(result['sentiment'])}
链接: {result['url']}
"""
            formatted.append(item)

        return "\n".join(formatted)

    def _get_sentiment_text(self, sentiment: str) -> str:
        """
        将情感标签转换为文本

        Args:
            sentiment: 情感标签 (0=中性, 1=利好, 2=利空)

        Returns:
            情感文本
        """
        sentiment_map = {"0": "中性", "1": "利好", "2": "利空"}
        return sentiment_map.get(sentiment, "未知")

    def check_collection(self) -> bool:
        """
        检查 Collection 是否存在

        Returns:
            Collection 是否存在
        """
        try:
            collections = self.client.get_collections()
            exists = any(
                c.name == self.collection_name for c in collections.collections
            )

            if exists:
                logger.info(f"Collection '{self.collection_name}' 存在")
                # 获取 Collection 信息
                try:
                    info = self.client.get_collection(self.collection_name)
                    # 处理不同的 Qdrant 版本 API
                    if hasattr(info.config, "params") and hasattr(
                        info.config.params, "vectors"
                    ):
                        vectors_config = info.config.params.vectors
                        if isinstance(vectors_config, dict):
                            size = vectors_config.get("size", "unknown")
                        else:
                            size = getattr(vectors_config, "size", "unknown")
                        logger.info(f"  - 向量维度: {size}")
                    else:
                        logger.info("  - 向量维度: 无法获取")

                    logger.info(
                        f"  - 文档数量: {info.points_count if hasattr(info, 'points_count') else 'unknown'}"
                    )
                except Exception as e:
                    logger.warning(f"获取 Collection 详情失败: {e}")
            else:
                logger.warning(f"Collection '{self.collection_name}' 不存在")

            return exists
        except Exception as e:
            logger.error(f"检查 Collection 失败: {e}")
            return False


# 全局 RAG Service 实例
rag_service = RAGService()
