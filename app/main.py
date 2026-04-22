"""
QuantAgent 主应用入口
基于 FastAPI 和 LangChain 的智能金融数据分析助手
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.chat import router as chat_router
from app.config import settings
from app.services.redis_client import get_redis_client, close_redis_client
from app.services.session_service import create_session_service
from app.services.database_service import get_pool
from app.models.chat_session import (
    MessageTooLongError,
    SessionBusyError,
    SessionNotFoundError,
)

# 配置日志级别 - 抑制第三方库的冗余日志
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# 使用 lifespan 替代已弃用的 @app.on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""

    # 启动事件
    try:
        # 初始化PostgreSQL连接池
        logger.info("Initializing PostgreSQL connection pool...")
        app.state.pg_pool = await get_pool()
        logger.info("PostgreSQL connection pool initialized")

        # 初始化Redis客户端
        logger.info("Initializing Redis client...")
        app.state.redis_client = await get_redis_client()
        logger.info("Redis client initialized")

        # 初始化会话服务
        logger.info("Initializing session service...")
        app.state.session_service = create_session_service(
            app.state.redis_client, app.state.pg_pool
        )
        logger.info("Session service initialized")

        logger.info(
            f"""
    ========================================
    {settings.app_name} v{settings.app_version}
    ========================================
    应用已启动！
    API 文档: http://localhost:{settings.port}/docs
    健康检查: http://localhost:{settings.port}/api/chat/health
    ========================================
    """
        )

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    yield

    # 关闭事件
    logger.info("应用正在关闭...")
    try:
        if hasattr(app.state, "redis_client") and app.state.redis_client:
            await close_redis_client()
        if hasattr(app.state, "pg_pool") and app.state.pg_pool:
            await app.state.pg_pool.close()
        logger.info("All services closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# 创建 FastAPI 应用实例，使用 lifespan
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于 FastAPI 和 LangChain 的智能金融数据分析助手",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === 全局异常处理器 ===


@app.exception_handler(MessageTooLongError)
async def message_too_long_handler(request: Request, exc: MessageTooLongError):
    """消息过长异常处理"""
    logger.warning(f"Message too long: {exc}")
    return JSONResponse(
        status_code=400, content={"error": "message_too_long", "message": str(exc)}
    )


@app.exception_handler(SessionBusyError)
async def session_busy_handler(request: Request, exc: SessionBusyError):
    """会话繁忙异常处理"""
    logger.warning(f"Session busy: {exc}")
    return JSONResponse(
        status_code=429, content={"error": "session_busy", "message": str(exc)}
    )


@app.exception_handler(SessionNotFoundError)
async def session_not_found_handler(request: Request, exc: SessionNotFoundError):
    """会话不存在异常处理"""
    logger.warning(f"Session not found: {exc}")
    return JSONResponse(
        status_code=404, content={"error": "session_not_found", "message": str(exc)}
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """请求参数验证错误处理"""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422, content={"error": "validation_error", "message": str(exc)}
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "服务器内部错误"},
    )


# 注册路由
app.include_router(chat_router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用 QuantAgent - 智能金融数据分析助手",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/chat/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
