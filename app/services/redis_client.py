"""
Redis客户端管理
"""
import logging
import threading
from typing import Optional
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis客户端"""

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._init_lock = threading.Lock()

    async def initialize(self):
        """初始化Redis连接池（线程安全）"""
        with self._init_lock:
            if self._pool is not None:
                return

            try:
                self._pool = ConnectionPool(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    password=settings.redis_password,
                    max_connections=settings.redis_max_connections,
                    decode_responses=True,  # 自动解码为str
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )

                self._client = Redis(connection_pool=self._pool)

                # 测试连接
                await self._client.ping()
                logger.info(f"Redis connected: {settings.redis_host}:{settings.redis_port}")

            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    async def close(self):
        """关闭Redis连接"""
        if self._pool:
            await self._pool.aclose()
            self._pool = None
            self._client = None
            logger.info("Redis connection closed")

    @property
    def client(self) -> Redis:
        """获取Redis客户端"""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")
        return self._client

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if self._client is None:
                return False
            await self._client.ping()
            return True
        except RedisError as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# 全局Redis客户端实例
_redis_client: Optional[RedisClient] = None
_redis_lock = threading.Lock()


async def get_redis_client() -> RedisClient:
    """获取Redis客户端单例（线程安全）"""
    global _redis_client
    if _redis_client is None:
        with _redis_lock:
            if _redis_client is None:
                _redis_client = RedisClient()
                await _redis_client.initialize()
    return _redis_client


async def close_redis_client():
    """关闭Redis客户端"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
