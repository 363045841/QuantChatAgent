"""
聊天 API 路由
"""

import json
import logging
import re
from typing import Optional

from fastapi import APIRouter, Query, Header, Depends, Request, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.chat import ChatRequest
from app.agents.finance_agent import get_finance_agent
from app.api.deps import get_session_service, get_session_id
from app.utils.chat_utils import (
    validate_chart_configs,
    convert_to_langchain_messages,
    extract_stream_output,
)
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["聊天"])


@router.post("/chat-stream")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    x_session_id: Optional[str] = Header(None),
    session_service: SessionService = Depends(get_session_service),
):
    """流式聊天接口(POST)。"""
    session_id = await get_session_id(x_session_id)
    # 流式响应状态
    stream_state = {
        "completed": False,
        "full_reply": "",
        "output_tokens": 0,
    }

    async def event_generator():
        try:
            # 1. 保存用户消息
            await session_service.save_message(
                session_id, "user", body.message, tokens=0
            )

            # 2. 获取完整历史（已包含当前用户消息）并转换为LangChain格式
            history = await session_service.get_sliding_window(session_id)
            messages = convert_to_langchain_messages(history)

            # 3. 调用agent流式输出
            agent = get_finance_agent()
            logger.info("---")
            logger.info(f"messages: {messages}")
            async for chunk in agent.achat_stream(messages):
                output = extract_stream_output(chunk)
                content = output.get("content", "")
                if content:
                    stream_state["full_reply"] += content

                # 提取 usage_metadata 中的 output_tokens
                usage_metadata = output.get("usage_metadata")
                if usage_metadata and usage_metadata.get("output_tokens"):
                    logger.info(f"---")
                    logger.info(
                        f"input_tokens: {usage_metadata['input_tokens']} tokens"
                    )
                    logger.info(
                        f"output_tokens: {usage_metadata['output_tokens']} tokens"
                    )
                    logger.info(
                        f"total_tokens: {usage_metadata['total_tokens']} tokens"
                    )
                    stream_state["output_tokens"] = usage_metadata["output_tokens"]

                output["session_id"] = session_id
                yield {"data": json.dumps(output, ensure_ascii=False, default=str)}

            # 4. 流正常结束，标记完成
            stream_state["completed"] = True
            logger.info(f"full_reply: {stream_state['full_reply']}")
            logger.info(f"---")
            yield {"data": json.dumps({"content": "[DONE]", "session_id": session_id})}

        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            # 不向用户暴露内部错误详情
            yield {
                "data": json.dumps(
                    {
                        "content": "[ERROR]处理请求时发生错误，请稍后重试",
                        "session_id": session_id,
                    }
                )
            }

        finally:
            # 5. 只有流正常完成才保存完整回复
            if stream_state["completed"] and stream_state["full_reply"]:
                try:
                    # 验证并处理<chart>配置
                    reply_to_save, _ = validate_chart_configs(
                        stream_state["full_reply"]
                    )
                    await session_service.save_message(
                        session_id,
                        "assistant",
                        reply_to_save,
                        tokens=stream_state["output_tokens"],
                    )
                except Exception as save_error:
                    logger.error(f"Failed to save stream reply: {save_error}")
            elif stream_state["full_reply"] and not stream_state["completed"]:
                # 流中断，记录警告但不保存不完整的回复
                logger.warning(
                    f"Stream interrupted for session {session_id}, "
                    f"reply length: {len(stream_state['full_reply'])} chars, not saved"
                )

    return EventSourceResponse(event_generator())


@router.get("/health")
async def health_check():
    """健康检查。"""
    return {"status": "ok", "service": "QuantAgent Chat API"}


@router.post("/clear-session")
async def clear_session(
    request: Request,
    x_session_id: str = Header(...),
    session_service=Depends(get_session_service),
):
    """删除 x_session_id 会话。"""
    # 验证 session_id 格式
    if not re.match(r"^[a-zA-Z0-9_-]{8,64}$", x_session_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid session ID format. Use 8-64 alphanumeric characters, hyphens, or underscores.",
        )
    await session_service.clear_session(x_session_id)
    return {"status": "ok", "message": "Session cleared"}


@router.get("/sessions")
async def list_sessions(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    session_service=Depends(get_session_service),
):
    """获取会话列表。"""
    sessions = await session_service.list_sessions(limit=limit)
    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "message_count": s.message_count,
                "last_activity": s.last_activity.isoformat(),
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    request: Request, session_id: str, session_service=Depends(get_session_service)
):
    """获取会话历史消息。"""
    # 确保会话存在
    session = await session_service.get_session(session_id)
    if not session:
        return {"messages": []}

    # 获取消息
    messages = await session_service.get_sliding_window(session_id)
    return {
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in messages
        ]
    }
