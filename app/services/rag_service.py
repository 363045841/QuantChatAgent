"""
RAG 服务 - 向量检索服务
使用 Qdrant 向量数据库、LangChain Embeddings 和百度智能云 Reranker
"""

from qdrant_client import QdrantClient
from qdrant_client.http import models
import logging
import threading
from typing import List, Dict, Optional
from datetime import datetime

from langchain_community.embeddings import ZhipuAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.runnables import RunnableConfig

from app.config import settings
from app.services.reranker_service import RerankerService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGService:
    """RAG 服务类 - 提供向量检索功能"""

    def __init__(self):
        """初始化 RAG 服务 - 只保存配置，不建立连接（真·懒加载）"""
        # 配置信息
        self.collection_name = settings.qdrant_collection_name
        self.embedding_model = settings.zhipu_embedding_model
        self.api_key = settings.zhipu_api_key or settings.zhipu_ai_api_key
        self.embedding_dimensions = settings.zhipu_embedding_dimensions

        # 延迟初始化的资源（只有在真正需要时才创建）
        self._client = None
        self._embeddings = None
        self._vectorstore = None
        self._lock = threading.RLock()  # 使用可重入锁，防止嵌套调用死锁

        logger.info(f"RAG Service 初始化 - Collection: {self.collection_name}")

    @property
    def client(self):
        """懒加载 Qdrant 客户端（线程安全）"""
        if self._client is None:
            with self._lock:
                if self._client is None:
                    url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"
                    logger.info(f"初始化 Qdrant 客户端: {url}")
                    try:
                        self._client = QdrantClient(url=url, timeout=5)
                    except Exception as e:
                        logger.error(f"QdrantClient 创建失败: {e}")
                        raise
        return self._client

    @property
    def embeddings(self):
        """懒加载 Embeddings（线程安全）"""
        if self._embeddings is None:
            with self._lock:
                if self._embeddings is None:
                    logger.info(f"初始化 Embeddings: {self.embedding_model}")
                    self._embeddings = ZhipuAIEmbeddings(
                        model=self.embedding_model,
                        api_key=self.api_key,
                        dimensions=self.embedding_dimensions,
                    )
        return self._embeddings

    @property
    def vectorstore(self):
        """懒加载 VectorStore（线程安全）"""
        if self._vectorstore is None:
            with self._lock:
                if self._vectorstore is None:
                    logger.info(f"初始化 QdrantVectorStore")
                    # 数据存储在 payload 根级别：abstract 作为内容，其他字段作为元数据
                    self._vectorstore = QdrantVectorStore(
                        client=self.client,
                        collection_name=self.collection_name,
                        embedding=self.embeddings,
                        vector_name="default",
                        content_payload_key="abstract",
                        metadata_payload_key=None,
                    )
        return self._vectorstore

    @property
    def retriever(self):
        """懒加载 Retriever"""
        return self.vectorstore.as_retriever(search_type="similarity")

    async def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
        use_reranker: bool = True,
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
            # 直接使用 Qdrant 客户端进行检索，以获取完整 payload
            candidate_count = max(top_k * 2, 20)
            logger.info(f"使用 Qdrant 检索: {query[:50]}... (top_{candidate_count})")

            # 生成查询向量
            query_vector = await self.embeddings.aembed_query(query)

            # 使用 query_points API
            search_response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="default",  # 使用名为 default 的向量
                limit=candidate_count,
                score_threshold=score_threshold,
                with_payload=True,
            )

            # 格式化检索结果
            formatted_results = []
            for hit in search_response.points:
                payload = hit.payload or {}
                formatted_result = {
                    "score": hit.score,
                    "title": payload.get("title", ""),
                    "abstract": payload.get("abstract", ""),
                    "timestamp": payload.get("timestamp", 0),
                    "source": payload.get("source", "未知"),
                    "sentiment": payload.get("sentiment", "0"),
                    "url": payload.get("url", ""),
                    "stock_code": payload.get("stock_code", ""),
                }
                formatted_results.append(formatted_result)

            logger.info(f"检索到 {len(formatted_results)} 条候选结果")

            if not formatted_results:
                logger.info("未找到符合阈值的结果")
                return []

            # 使用 Reranker 重排序
            if use_reranker and settings.baidu_reranker_api_key:
                logger.info(
                    f"使用 Reranker 重排序 {len(formatted_results)} 条候选结果..."
                )
                try:
                    reranker_service = RerankerService()

                    # 构造文档列表（使用摘要作为 Reranker 的输入）
                    documents = [
                        f"{r['title']}\n{r['abstract']}" for r in formatted_results
                    ]

                    # 调用 Reranker
                    rerank_results = await reranker_service.rerank(
                        query, documents, top_n=top_k
                    )

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
                        for idx in sorted(
                            reranked_dict.keys(),
                            key=lambda x: reranked_dict[x],
                            reverse=True,
                        ):
                            original_result = formatted_results[idx]
                            # 更新分数为 Reranker 的分数
                            original_result["score"] = reranked_dict[idx]
                            final_results.append(original_result)

                        # 输出重排序后的结果摘要
                        logger.info(
                            f"重排序完成，返回 {min(len(final_results), top_k)} 条结果"
                        )
                        for idx, result in enumerate(final_results[:top_k], 1):
                            title_preview = (
                                result["title"][:30] + "..."
                                if len(result["title"]) > 30
                                else result["title"]
                            )
                            logger.info(
                                f"  {idx}. [{result['score']:.3f}] {title_preview}"
                            )

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


_rag_service = None
_rag_lock = threading.RLock()


def get_rag_service():
    """获取 RAG 服务单例（线程安全）"""
    global _rag_service
    if _rag_service is None:
        with _rag_lock:
            if _rag_service is None:
                _rag_service = RAGService()
    return _rag_service
