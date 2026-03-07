"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 环境配置
    env: str = "development"
    
    # 应用基本信息
    app_name: str = "QuantAgent"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # 智谱 AI 配置
    zhipu_ai_api_key: str = ""
    zhipu_ai_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_ai_model: str = "glm-4.5-air"
    zhipu_embedding_api_url: str = "https://open.bigmodel.cn/api/paas/v4/embeddings"
    zhipu_embedding_model: str = "embedding-3"
    zhipu_embedding_dimensions: int = 1024
    zhipu_api_key: str = ""  # Embedding API 使用的密钥
    
    # RAG 配置
    rag_collection_name: str = "default"
    
    # 数据库配置
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "quantagent"
    db_user: str = "postgres"
    db_password: Optional[str] = None
    
    # 股票 API 配置
    stock_api_base_url: str = "http://localhost:8000"
    
    # Qdrant 向量数据库配置
    qdrant_host: str = "localhost"
    qdrant_port: int = 6334
    qdrant_collection_name: str = "QuantAgent"
    qdrant_use_grpc: bool = True
    
    # 百度智能云 Reranker 配置
    baidu_reranker_api_key: str = ""
    baidu_reranker_model: str = "qwen3-reranker-8b"
    baidu_reranker_base_url: str = "https://qianfan.baidubce.com/v2/rerank"
    baidu_reranker_top_n: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
settings = Settings()


def get_database_url() -> str:
    """获取数据库连接 URL"""
    return f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"