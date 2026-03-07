"""
聊天相关模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户输入的消息", min_length=1)
    session_id: Optional[str] = Field(None, description="会话 ID，用于上下文管理")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    reply: str = Field(..., description="AI 的回复")


class StreamChunk(BaseModel):
    """流式响应数据块"""
    content: str = Field(..., description="当前数据块的内容")