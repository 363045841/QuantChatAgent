"""
QuantAgent 主应用入口
基于 FastAPI 和 LangChain 的智能金融数据分析助手
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.config import settings

# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于 FastAPI 和 LangChain 的智能金融数据分析助手",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "health": "/api/chat/health"
    }


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    print(f"""
    ========================================
    {settings.app_name} v{settings.app_version}
    ========================================
    应用已启动！
    API 文档: http://localhost:8000/docs
    健康检查: http://localhost:8000/api/chat/health
    ========================================
    """)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    print("应用正在关闭...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )