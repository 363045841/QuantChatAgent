"""
向量存储连接管理模块

职责：
- 管理 Qdrant 客户端连接（线程安全懒加载）
- 管理智谱 AI Embedding 服务（线程安全懒加载）
- 管理 QdrantVectorStore 封装（线程安全懒加载）
- 提供统一的数据访问接口

设计原则：
- 单一职责：只负责连接管理和基础数据访问
- 懒加载：首次使用时才建立连接，避免启动时依赖
- 线程安全：使用可重入锁防止并发初始化问题
"""

import logging
import threading
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_community.embeddings import ZhipuAIEmbeddings
from langchain_qdrant import QdrantVectorStore

from app.config import settings

# 配置日志
logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    向量存储管理器

    封装 Qdrant 向量数据库的所有连接操作，提供线程安全的懒加载机制。
    分离连接管理与业务逻辑，使上层服务专注于检索策略而非连接细节。

    Attributes:
        collection_name: Qdrant 集合名称
        embedding_dimensions: 向量维度（由 Embedding 模型决定）
        _client: Qdrant 客户端实例（懒加载）
        _embeddings: 智谱 AI Embedding 实例（懒加载）
        _vectorstore: LangChain QdrantVectorStore 封装（懒加载）
        _lock: 线程锁，防止并发初始化
    """

    def __init__(self):
        """
        初始化管理器配置

        注意：此方法仅保存配置，不建立任何连接。
        真正的连接在首次访问对应属性时通过懒加载机制建立。
        """
        # 基础配置
        self.collection_name = settings.qdrant_collection_name
        self.embedding_dimensions = settings.zhipu_embedding_dimensions

        # 延迟初始化的资源（None 表示尚未初始化）
        self._client: Optional[QdrantClient] = None
        self._embeddings: Optional[ZhipuAIEmbeddings] = None
        self._vectorstore: Optional[QdrantVectorStore] = None

        # 可重入锁：防止嵌套调用时死锁，同时保证线程安全
        self._lock = threading.RLock()

        logger.info(f"VectorStoreManager 初始化完成 - Collection: {self.collection_name}")

    @property
    def client(self) -> QdrantClient:
        """
        懒加载 Qdrant 客户端（线程安全）

        QdrantClient 是 HTTP/gRPC 客户端，负责与 Qdrant 服务器通信。
        使用双检锁模式确保多线程环境下只初始化一次。

        Returns:
            QdrantClient 实例

        Raises:
            Exception: 连接建立失败时抛出
        """
        if self._client is None:
            with self._lock:
                # 双重检查：获取锁后再次确认
                if self._client is None:
                    url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"
                    logger.info(f"[懒加载] 初始化 Qdrant 客户端: {url}")
                    try:
                        self._client = QdrantClient(url=url, timeout=5)
                    except Exception as e:
                        logger.error(f"QdrantClient 创建失败: {e}")
                        raise
        return self._client

    @property
    def embeddings(self) -> ZhipuAIEmbeddings:
        """
        懒加载智谱 AI Embedding 服务（线程安全）

        Embedding 服务将文本转换为向量表示，是语义检索的基础。
        使用智谱 AI 的 embedding-3 模型，支持 1024 维向量。

        Returns:
            ZhipuAIEmbeddings 实例
        """
        if self._embeddings is None:
            with self._lock:
                if self._embeddings is None:
                    logger.info(f"[懒加载] 初始化 Embedding: {settings.zhipu_embedding_model}")
                    self._embeddings = ZhipuAIEmbeddings(
                        model=settings.zhipu_embedding_model,
                        api_key=settings.zhipu_api_key,
                        dimensions=self.embedding_dimensions,
                    )
        return self._embeddings

    @property
    def vectorstore(self) -> QdrantVectorStore:
        """
        懒加载 LangChain VectorStore 封装（线程安全）

        QdrantVectorStore 是 LangChain 对 Qdrant 的封装，提供标准化接口。
        配置说明：
        - vector_name="default": 使用名为 default 的向量字段
        - content_payload_key="abstract": 摘要字段作为文档内容
        - metadata_payload_key=None: 元数据直接存储在 payload 根级

        Returns:
            QdrantVectorStore 实例
        """
        if self._vectorstore is None:
            with self._lock:
                if self._vectorstore is None:
                    logger.info("[懒加载] 初始化 QdrantVectorStore")
                    self._vectorstore = QdrantVectorStore(
                        client=self.client,                    # 使用懒加载的客户端
                        collection_name=self.collection_name,
                        embedding=self.embeddings,            # 使用懒加载的 Embedding
                        vector_name="default",
                        content_payload_key="abstract",
                        metadata_payload_key=None,
                    )
        return self._vectorstore

    async def embed_query(self, query: str) -> List[float]:
        """
        异步生成查询向量

        Args:
            query: 查询文本

        Returns:
            查询文本的向量表示
        """
        return await self.embeddings.aembed_query(query)

    def search_similar(
        self,
        query_vector: List[float],
        top_k: int,
        score_threshold: float
    ) -> List[models.ScoredPoint]:
        """
        执行向量相似度检索

        使用 Qdrant 的 query_points API 进行最近邻搜索，
        返回按相似度排序的候选结果。

        Args:
            query_vector: 查询向量
            top_k: 返回结果数量上限
            score_threshold: 相似度阈值，低于此值的结果被过滤

        Returns:
            ScoredPoint 列表，包含相似度分数和 payload 数据
        """
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            using="default",              # 使用名为 default 的向量字段
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,            # 返回完整 payload
        )
        return response.points

    def check_collection_exists(self) -> bool:
        """
        检查集合是否存在并输出诊断信息

        Returns:
            True 如果集合存在，False  otherwise
        """
        try:
            collections = self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)

            if exists:
                logger.info(f"集合 '{self.collection_name}' 存在")
                self._log_collection_info()
            else:
                logger.warning(f"集合 '{self.collection_name}' 不存在")

            return exists
        except Exception as e:
            logger.error(f"检查集合失败: {e}")
            return False

    def _log_collection_info(self) -> None:
        """
        输出集合详细诊断信息（内部方法）

        包括向量维度和文档数量，用于调试和监控。
        """
        try:
            info = self.client.get_collection(self.collection_name)

            # 适配不同 Qdrant 版本的 API 差异
            if hasattr(info.config, "params") and hasattr(info.config.params, "vectors"):
                vectors_config = info.config.params.vectors
                size = vectors_config.get("size", "unknown") if isinstance(vectors_config, dict) else getattr(vectors_config, "size", "unknown")
                logger.info(f"  - 向量维度: {size}")

            points_count = info.points_count if hasattr(info, "points_count") else "unknown"
            logger.info(f"  - 文档数量: {points_count}")

        except Exception as e:
            logger.warning(f"获取集合详情失败: {e}")


# 全局单例实例（线程安全）
_vector_store_manager: Optional[VectorStoreManager] = None
_vector_store_lock = threading.RLock()


def get_vector_store_manager() -> VectorStoreManager:
    """
    获取向量存储管理器单例（线程安全）

    使用双检锁确保全局只有一个实例，避免重复建立连接。

    Returns:
        VectorStoreManager 单例
    """
    global _vector_store_manager
    if _vector_store_manager is None:
        with _vector_store_lock:
            if _vector_store_manager is None:
                _vector_store_manager = VectorStoreManager()
    return _vector_store_manager
