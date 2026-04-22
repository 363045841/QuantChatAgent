"""
API 依赖注入函数
"""

import re
from typing import Optional
from uuid import uuid4

from fastapi import Header, HTTPException, Request

from app.services.session_service import SessionService


async def get_session_service(request: Request) -> SessionService:
    """获取session_service依赖(从app.state获取)。"""
    service = getattr(request.app.state, "session_service", None)
    if service is None:
        raise RuntimeError("Session service not initialized")
    return service


async def get_session_id(x_session_id: Optional[str] = Header(None)) -> str:
    """获取或生成会话ID，验证格式。"""
    if x_session_id:
        # 验证session_id格式(UUID或自定义安全格式)
        # 允许字母数字、连字符、下划线，长度8-64
        if not re.match(r"^[a-zA-Z0-9_-]{8,64}$", x_session_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid session ID format. Use 8-64 alphanumeric characters, hyphens, or underscores.",
            )
        return x_session_id
    return str(uuid4())
