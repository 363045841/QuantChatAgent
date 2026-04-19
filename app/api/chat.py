"""
聊天 API 路由
"""
import logging
import json
from typing import List, Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Query, Header, Depends, Request
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage

from app.models.chat import ChatRequest, ChatResponse
from app.agents.finance_agent import get_finance_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["聊天"])

# 消息角色到LangChain消息类型的映射
_MESSAGE_CLASS_MAP = {
    'system': SystemMessage,
    'user': HumanMessage,
    'assistant': AIMessage,
}


def convert_to_langchain_messages(history: List[Dict[str, Any]]) -> List[BaseMessage]:
    """
    将历史消息转换为LangChain消息格式

    Args:
        history: 历史消息列表，每条消息包含 role 和 content 字段

    Returns:
        LangChain消息对象列表
    """
    messages = []
    for msg in history:
        msg_class = _MESSAGE_CLASS_MAP.get(msg['role'])
        if msg_class:
            messages.append(msg_class(content=msg['content']))
    return messages


def extract_stream_output(chunk) -> str:
    """
    从流式响应chunk中提取输出文本

    Args:
        chunk: 流式响应的chunk对象

    Returns:
        提取的输出文本
    """
    if isinstance(chunk, dict):
        if "output" in chunk:
            return chunk["output"]
        elif "messages" in chunk:
            messages = chunk["messages"]
            if messages:
                return str(messages[-1])
        return str(chunk)
    return str(chunk)


async def get_session_service(request: Request):
    """获取session_service依赖（从app.state获取）"""
    service = getattr(request.app.state, 'session_service', None)
    if service is None:
        raise RuntimeError("Session service not initialized")
    return service


async def get_session_id(x_session_id: Optional[str] = Header(None)) -> str:
    """获取或生成会话ID，验证格式"""
    if x_session_id:
        # 验证session_id格式（UUID或自定义安全格式）
        # 允许字母数字、连字符、下划线，长度8-64
        import re
        if not re.match(r'^[a-zA-Z0-9_-]{8,64}$', x_session_id):
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="Invalid session ID format. Use 8-64 alphanumeric characters, hyphens, or underscores."
            )
        return x_session_id
    return str(uuid4())


@router.get("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    message: str = Query(..., description="用户消息"),
    x_session_id: Optional[str] = Header(None),
    session_service=Depends(get_session_service)
):
    """聊天接口（GET）"""
    session_id = await get_session_id(x_session_id)

    try:
        # 1. 保存用户消息
        await session_service.save_message(session_id, "user", message)

        # 2. 获取历史消息并转换为LangChain格式
        history = await session_service.get_sliding_window(session_id)
        chat_history = convert_to_langchain_messages(history)

        # 3. 调用agent
        agent = get_finance_agent()
        reply = await agent.achat(message, chat_history)

        # 4. 保存助手回复
        await session_service.save_message(session_id, "assistant", reply)

        return ChatResponse(reply=reply, session_id=session_id)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        # 不向用户暴露内部错误详情
        return ChatResponse(
            reply="处理请求时发生错误，请稍后重试",
            session_id=session_id
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_post(
    request: Request,
    body: ChatRequest,
    x_session_id: Optional[str] = Header(None),
    session_service=Depends(get_session_service)
):
    """聊天接口（POST）"""
    session_id = await get_session_id(x_session_id)

    try:
        # 1. 保存用户消息
        await session_service.save_message(session_id, "user", body.message)

        # 2. 获取历史消息并转换为LangChain格式
        history = await session_service.get_sliding_window(session_id)
        chat_history = convert_to_langchain_messages(history)

        # 3. 调用agent
        agent = get_finance_agent()
        reply = await agent.achat(body.message, chat_history)

        # 4. 保存助手回复
        await session_service.save_message(session_id, "assistant", reply)

        return ChatResponse(reply=reply, session_id=session_id)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        # 不向用户暴露内部错误详情
        return ChatResponse(
            reply="处理请求时发生错误，请稍后重试",
            session_id=session_id
        )


@router.get("/chat-stream")
async def chat_stream(
    request: Request,
    message: str = Query(..., description="用户消息"),
    x_session_id: Optional[str] = Header(None),
    session_service=Depends(get_session_service)
):
    """流式聊天接口（GET）"""
    session_id = await get_session_id(x_session_id)
    # 用于追踪流式响应状态
    stream_state = {"completed": False, "full_reply": ""}

    async def event_generator():
        try:
            # 1. 保存用户消息
            await session_service.save_message(session_id, "user", message)

            # 2. 获取历史消息并转换为LangChain格式
            history = await session_service.get_sliding_window(session_id)
            chat_history = convert_to_langchain_messages(history)

            # 3. 调用agent流式输出
            agent = get_finance_agent()
            async for chunk in agent.achat_stream(message, chat_history):
                output = extract_stream_output(chunk)
                if output:
                    stream_state["full_reply"] += output
                    yield {"data": json.dumps({"text": output, "session_id": session_id})}

            # 4. 流正常结束，标记完成
            stream_state["completed"] = True
            yield {"data": json.dumps({"text": "[DONE]", "session_id": session_id})}

        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            # 不向用户暴露内部错误详情
            yield {"data": json.dumps({"text": "[ERROR]处理请求时发生错误，请稍后重试", "session_id": session_id})}

        finally:
            # 5. 只有流正常完成才保存完整回复
            if stream_state["completed"] and stream_state["full_reply"]:
                try:
                    await session_service.save_message(
                        session_id, "assistant", stream_state["full_reply"]
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


@router.post("/chat-stream")
async def chat_stream_post(
    request: Request,
    body: ChatRequest,
    x_session_id: Optional[str] = Header(None),
    session_service=Depends(get_session_service)
):
    """流式聊天接口（POST）"""
    session_id = await get_session_id(x_session_id)
    # 用于追踪流式响应状态
    stream_state = {"completed": False, "full_reply": ""}

    async def event_generator():
        try:
            # 1. 保存用户消息
            await session_service.save_message(session_id, "user", body.message)

            # 2. 获取历史消息并转换为LangChain格式
            history = await session_service.get_sliding_window(session_id)
            chat_history = convert_to_langchain_messages(history)

            # 3. 调用agent流式输出
            agent = get_finance_agent()
            async for chunk in agent.achat_stream(body.message, chat_history):
                output = extract_stream_output(chunk)
                if output:
                    stream_state["full_reply"] += output
                    yield {"data": json.dumps({"text": output, "session_id": session_id})}

            # 4. 流正常结束，标记完成
            stream_state["completed"] = True
            yield {"data": json.dumps({"text": "[DONE]", "session_id": session_id})}

        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            # 不向用户暴露内部错误详情
            yield {"data": json.dumps({"text": "[ERROR]处理请求时发生错误，请稍后重试", "session_id": session_id})}

        finally:
            # 5. 只有流正常完成才保存完整回复
            if stream_state["completed"] and stream_state["full_reply"]:
                try:
                    await session_service.save_message(
                        session_id, "assistant", stream_state["full_reply"]
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
    """健康检查"""
    return {"status": "ok", "service": "QuantAgent Chat API"}


@router.post("/clear-session")
async def clear_session(
    request: Request,
    x_session_id: str = Header(...),
    session_service=Depends(get_session_service)
):
    """清空会话"""
    await session_service.clear_session(x_session_id)
    return {"status": "ok", "message": "Session cleared"}
