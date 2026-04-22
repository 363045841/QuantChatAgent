"""
数据库服务层 - 提供异步数据库访问
"""

from typing import Optional, List
import threading
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import asyncpg
import logging

from app.config import settings, get_database_url
from app.models.stock_basic_info import StockBasicInfo, Base

logger = logging.getLogger(__name__)


# 延迟初始化引擎和会话工厂
_engine = None
_AsyncSessionLocal = None

# asyncpg连接池（用于SessionService）
_pg_pool = None

# 线程安全锁（使用RLock防止嵌套调用死锁）
_engine_lock = threading.RLock()
_pool_lock = threading.RLock()


def get_engine():
    """
    获取数据库引擎（延迟初始化，线程安全）

    使用延迟初始化避免在模块导入时创建引擎和连接池，
    防止在数据库不可用时导致应用启动失败。
    """
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = create_async_engine(
                    get_database_url().replace(
                        "postgresql://", "postgresql+asyncpg://"
                    ),
                    echo=False,
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20,
                )
    return _engine


def get_async_session_local():
    """
    获取异步会话工厂（延迟初始化）

    会话工厂依赖引擎，因此也采用延迟初始化。
    """
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        with _engine_lock:
            if _AsyncSessionLocal is None:
                _AsyncSessionLocal = async_sessionmaker(
                    get_engine(),
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autoflush=False,
                )
    return _AsyncSessionLocal


async def get_pool():
    """
    获取asyncpg连接池（用于SessionService，线程安全）

    Returns:
        asyncpg.pool.Pool: asyncpg连接池实例
    """
    global _pg_pool
    if _pg_pool is None:
        with _pool_lock:
            if _pg_pool is None:
                # 从配置获取连接参数
                import re

                db_url = get_database_url()
                # 解析postgresql://user:pass@host:port/db
                match = re.match(
                    r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url
                )
                if match:
                    user, password, host, port, database = match.groups()
                    _pg_pool = await asyncpg.create_pool(
                        host=host,
                        port=int(port),
                        user=user,
                        password=password,
                        database=database,
                        min_size=settings.db_min_connections,
                        max_size=settings.db_max_connections,
                        command_timeout=60,
                    )
                else:
                    # 不在错误信息中暴露完整URL
                    raise ValueError("Invalid database URL format")
    return _pg_pool


async def get_db_session() -> AsyncSession:
    """
    获取数据库会话（依赖注入使用）

    Yields:
        AsyncSession: 数据库会话
    """
    async with get_async_session_local()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class StockBasicInfoService:
    """股票基本信息服务"""

    @staticmethod
    async def query_by_code(code: str) -> Optional[StockBasicInfo]:
        """
        根据 A 股代码查询股票基本信息

        Args:
            code: A 股代码（如 600000）

        Returns:
            StockBasicInfo: 股票基本信息，未找到返回 None
        """
        async with get_async_session_local()() as session:
            try:
                stmt = select(StockBasicInfo).where(StockBasicInfo.a_share_code == code)
                result = await session.execute(stmt)
                stock_info = result.scalar_one_or_none()

                if stock_info:
                    logger.info(f"成功查询到股票代码 {code} 的信息")
                else:
                    logger.warning(f"未找到股票代码 {code} 的信息")

                return stock_info

            except Exception as e:
                logger.error(f"查询股票代码 {code} 失败: {e}")
                raise

    @staticmethod
    async def format_stock_info(stock_info: StockBasicInfo) -> str:
        """
        格式化股票信息为字符串

        Args:
            stock_info: 股票基本信息对象

        Returns:
            str: 格式化后的股票信息字符串
        """
        listing_date_str = (
            stock_info.listing_date.isoformat() if stock_info.listing_date else "未知"
        )

        return (
            f"证券简称: {stock_info.security_abbreviation or '未知'}\n"
            f"扩位证券简称: {stock_info.expanded_abbreviation or '未知'}\n"
            f"公司英文全称: {stock_info.company_english_name or '未知'}\n"
            f"上市日期: {listing_date_str}"
        )

    @staticmethod
    async def query_and_format(code: str) -> str:
        """
        查询股票代码并返回格式化信息

        Args:
            code: A 股代码

        Returns:
            str: 格式化后的股票信息，未找到返回提示信息
        """
        stock_info = await StockBasicInfoService.query_by_code(code)

        if stock_info:
            return await StockBasicInfoService.format_stock_info(stock_info)
        else:
            return f"未找到股票代码: {code}"


# 初始化数据库表（仅在开发环境使用）
async def init_db():
    """初始化数据库表（谨慎使用）"""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表初始化完成")
