"""
RAG 检索编排服务

职责：
- 编排向量检索和重排序流程
- 协调 VectorStoreManager 和 RerankerService
- 提供统一的检索接口

依赖关系：
    RAGService
         │
         ├── VectorStoreManager    → 连接管理、向量检索
         │
         ├── RerankerService       → 重排序
         │
         └── ResultFormatter       → 结果格式化
"""

import logging
from typing import List, Dict, Any

from app.config import settings
from app.services.vector_store import get_vector_store_manager, VectorStoreManager
from app.services.reranker_service import RerankerService
from app.services.result_formatter import get_result_formatter, ResultFormatter

# 配置日志
logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG 检索编排服务

    协调向量检索和重排序两个阶段，提供端到端的检索能力。

    检索流程：
    1. 向量检索阶段：使用 Embedding 将查询转为向量，在 Qdrant 中找相似文档
    2. 重排序阶段：使用 Reranker 对候选文档精排，提升相关性
    """

    def __init__(self):
        """初始化 RAG 服务"""
        # 延迟注入：通过函数获取单例，避免循环导入和启动时依赖
        self._vector_store = None
        self._formatter = None

    @property
    def vector_store(self) -> VectorStoreManager:
        """延迟获取向量存储管理器。"""
        if self._vector_store is None:
            self._vector_store = get_vector_store_manager()
        return self._vector_store

    @property
    def formatter(self) -> ResultFormatter:
        """延迟获取结果格式化器。"""
        if self._formatter is None:
            self._formatter = get_result_formatter()
        return self._formatter

    async def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
        use_reranker: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        执行向量相似度检索（可选重排序）

        两阶段检索流程：
        1. 向量检索：召回 top_k * 2 条候选（至少 20 条）
        2. 重排序：使用 Reranker 精排，返回 top_k 条最相关结果

        Args:
            query: 查询文本
            top_k: 最终返回结果数量
            score_threshold: 相似度阈值，向量检索阶段过滤低分结果
            use_reranker: 是否使用 Reranker 重排序

        Returns:
            检索结果列表，每个结果包含：
            - score: 相似度分数（向量检索分数或 Reranker 分数）
            - title: 新闻标题
            - abstract: 新闻摘要
            - timestamp: 发布时间（Unix 时间戳）
            - source: 来源
            - sentiment: 情感标签
            - url: 原始链接
        """
        try:
            # 1. 向量检索
            results = await self._vector_search(query, top_k, score_threshold)

            if not results:
                logger.info("向量检索未找到符合阈值的结果")
                return []

            # 2. Reranker
            if use_reranker and self._is_reranker_available():
                results = await self._rerank(query, results, top_k)
            else:
                # 无重排序，直接截取 top_k
                results = results[:top_k]
                logger.info(f"检索完成，返回 {len(results)} 条结果（无重排序）")

            return results

        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []

    async def _vector_search(
        self,
        query: str,
        top_k: int,
        score_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        执行向量相似度检索

        使用 Qdrant 进行 ANN（近似最近邻）搜索，返回候选结果集。
        候选数量设为 top_k * 2，为后续重排序提供足够的候选池。

        Args:
            query: 查询文本
            top_k: 最终需要的结果数量
            score_threshold: 相似度阈值

        Returns:
            格式化后的候选结果列表
        """
        # 候选数量：为重排序预留足够空间
        candidate_count = max(top_k * 2, 20)
        logger.info(f"向量检索: {query[:50]}... (候选 {candidate_count} 条)")

        # 生成查询向量
        query_vector = await self.vector_store.embed_query(query)

        # 执行向量检索
        scored_points = self.vector_store.search_similar(
            query_vector=query_vector,
            top_k=candidate_count,
            score_threshold=score_threshold
        )

        # 格式化检索结果
        results = [self._format_point(hit) for hit in scored_points]
        logger.info(f"向量检索返回 {len(results)} 条候选")

        return results

    def _format_point(self, hit) -> Dict[str, Any]:
        """
        将 Qdrant 返回的 ScoredPoint 格式化为标准字典

        Args:
            hit: Qdrant ScoredPoint 对象

        Returns:
            标准格式的结果字典
        """
        payload = hit.payload or {}
        return {
            "score": hit.score,
            "title": payload.get("title", ""),
            "abstract": payload.get("abstract", ""),
            "timestamp": payload.get("timestamp", 0),
            "source": payload.get("source", "未知"),
            "sentiment": payload.get("sentiment", "0"),
            "url": payload.get("url", ""),
            "stock_code": payload.get("stock_code", ""),
        }

    def _is_reranker_available(self) -> bool:
        """检查 Reranker 服务是否可用（配置了 API Key）。"""
        return bool(settings.baidu_reranker_api_key)

    async def _rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        使用 Reranker 对候选结果重排序

        Reranker 是 Cross-Encoder 模型，能更精确地计算 query-doc 相关性，
        但计算开销大，适合对小规模候选集精排。

        Args:
            query: 查询文本
            candidates: 候选结果列表
            top_k: 最终返回数量

        Returns:
            重排序后的结果列表（已截断至 top_k）
        """
        logger.info(f"Reranker 重排序 {len(candidates)} 条候选...")

        try:
            reranker = RerankerService()

            # 构造文档列表：使用 title + abstract 作为 Reranker 输入
            documents = [f"{r['title']}\n{r['abstract']}" for r in candidates]

            # 调用 Reranker API
            rerank_results = await reranker.rerank(query, documents, top_n=top_k)

            # 构建重排序映射：文档索引 -> 重排序分数
            score_map = self._build_rerank_score_map(rerank_results, documents)

            # 按重排序分数降序排列
            if score_map:
                sorted_indices = sorted(
                    score_map.keys(),
                    key=lambda x: score_map[x],
                    reverse=True
                )
                final_results = []
                for idx in sorted_indices[:top_k]:
                    result = candidates[idx].copy()
                    result["score"] = score_map[idx]  # 用 Reranker 分数覆盖原分数
                    final_results.append(result)

                self._log_rerank_results(final_results)
                return final_results

        except Exception as e:
            logger.warning(f"Reranker 调用失败，使用原始排序: {e}")

        # Reranker 失败时降级：返回原始候选的前 top_k 条
        return candidates[:top_k]

    def _build_rerank_score_map(
        self,
        rerank_results: List[Dict],
        documents: List[str]
    ) -> Dict[int, float]:
        """
        构建重排序分数映射表

        Reranker 返回结果包含原始文档文本，需要找到其在候选列表中的索引。

        Args:
            rerank_results: Reranker API 返回的结果列表
            documents: 原始文档列表

        Returns:
            文档索引到重排序分数的映射
        """
        score_map = {}
        for result in rerank_results:
            doc_text = result["document"]
            for i, doc in enumerate(documents):
                if doc == doc_text:
                    score_map[i] = result["relevance_score"]
                    break
        return score_map

    def _log_rerank_results(self, results: List[Dict[str, Any]]) -> None:
        """输出重排序结果摘要（用于调试和监控）。"""
        logger.info(f"重排序完成，返回 {len(results)} 条结果")
        summary = self.formatter.format_score_summary(results)
        for line in summary.split("\n"):
            logger.info(line)

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        格式化检索结果为可读文本

        Args:
            results: 检索结果列表

        Returns:
            格式化后的文本
        """
        return self.formatter.format_search_results(results)

    def check_collection(self) -> bool:
        """
        检查向量集合是否存在并输出诊断信息

        Returns:
            True 如果集合存在且可访问
        """
        return self.vector_store.check_collection_exists()


# 全局单例实例
_rag_service = None


def get_rag_service() -> RAGService:
    """
    获取 RAG 服务单例

    Returns:
        RAGService 单例实例
    """
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
