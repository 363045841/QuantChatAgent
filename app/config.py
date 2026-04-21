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
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8001
    
    # 智谱 AI 配置（仅用于 Embedding）
    zhipu_embedding_api_url: str = "https://open.bigmodel.cn/api/paas/v4/embeddings"
    zhipu_embedding_model: str = "embedding-3"
    zhipu_embedding_dimensions: int = 1024
    zhipu_api_key: str = ""  # Embedding API 使用的密钥

    # 百度千帆 LLM 配置
    qianfan_api_key: str = ""
    qianfan_base_url: str = "https://qianfan.baidubce.com/v2/coding"
    qianfan_model: str = "kimi-k2.5"
    
    # RAG 配置
    rag_collection_name: str = "default"
    
    # 数据库配置
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "quantagent"
    db_user: str = "postgres"
    db_password: Optional[str] = None
    db_min_connections: int = 5
    db_max_connections: int = 20
    
    # Redis 配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_max_connections: int = 50

    # Token预算
    model_context_window: int = 128000
    max_output_tokens: int = 4096
    system_prompt_budget: int = 2000
    tool_schema_budget: int = 1000
    safety_margin: int = 1000
    
    # 消息限制
    max_message_length: int = 50000
    max_message_tokens: int = 16000
    
    # 会话配置
    session_idle_ttl: int = 7 * 24 * 3600  # 7天
    session_lock_ttl: int = 120
    session_lock_timeout: int = 10
    redis_max_messages: int = 100
    
    # 股票 API 配置
    stock_api_base_url: str = "http://localhost:8001"
    
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
        extra = "ignore"  # 忽略 .env 中未定义的字段


# 全局配置实例
settings = Settings()


def get_database_url() -> str:
    """获取数据库连接 URL（密码URL编码防止特殊字符问题）"""
    from urllib.parse import quote_plus
    password = quote_plus(settings.db_password, safe='') if settings.db_password else ''
    return f"postgresql://{settings.db_user}:{password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"


class SessionConfig:
    """会话配置"""
    
    @staticmethod
    def usable_history_budget() -> int:
        """可用历史token预算"""
        return (
            settings.model_context_window 
            - settings.max_output_tokens 
            - settings.system_prompt_budget 
            - settings.tool_schema_budget 
            - settings.safety_margin
        )