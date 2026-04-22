"""
会话数据模型
"""

from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from uuid import UUID, uuid4


class ChatSession(BaseModel):
    """会话模型"""

    id: str = Field(default_factory=lambda: str(uuid4()), description="会话ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    title: Optional[str] = Field(None, description="会话标题")
    message_count: int = Field(0, ge=0, description="消息数量")
    total_tokens: int = Field(0, ge=0, description="总token数")
    last_activity: datetime = Field(..., description="最后活动时间")
    created_at: datetime = Field(..., description="创建时间")


class ChatMessage(BaseModel):
    """消息模型"""

    id: int = Field(..., description="消息ID（数据库自增）")
    message_id: UUID = Field(default_factory=uuid4, description="消息唯一ID")
    session_id: str = Field(..., description="会话ID")
    seq_num: int = Field(..., ge=1, description="会话内序号")
    role: Literal["system", "user", "assistant", "tool"] = Field(
        ..., description="角色"
    )
    content: str = Field(..., description="消息内容")
    tokens: int = Field(..., ge=0, description="token数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外信息")
    created_at: datetime = Field(..., description="创建时间")


class MessageTooLongError(Exception):
    """消息过长异常"""

    pass


class SessionBusyError(Exception):
    """会话繁忙异常"""

    pass


class SessionNotFoundError(Exception):
    """会话不存在异常"""

    pass
