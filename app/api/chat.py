"""
聊天 API 路由
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4

from fastapi import APIRouter, Query, Header, Depends, Request, HTTPException
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage

from app.models.chat import ChatRequest, ChatResponse
from app.models.chat_session import ChatMessage as ChatMessageModel
from app.agents.finance_agent import get_finance_agent
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["聊天"])

# 消息角色到LangChain消息类型的映射
_MESSAGE_CLASS_MAP = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


def validate_chart_configs(response: str) -> Tuple[str, List[Dict]]:
    """验证回答中的<chart>标签内JSON格式有效性。

    Args:
        response: Agent返回的响应文本，可能包含多个<chart>标签。

    Returns:
        tuple: (processed, valid_configs)
            - processed (str): 移除无效<chart>标签后的清理文本。
            - valid_configs (List[Dict]): 成功解析的JSON配置列表。
    """
    # 防御性处理 None 输入
    if response is None:
        return "", []

    pattern = r"<chart>\s*([\s\S]*?)\s*</chart>"
    valid_configs = []
    invalid_spans = []  # 记录无效标签的位置

    # 遍历验证所有匹配的 <chart> 标签对
    for match in re.finditer(pattern, response):
        json_str = match.group(1).strip()
        try:
            config = json.loads(json_str)
            valid_configs.append(config)
            logger.debug(
                f"Valid chart config found: {config.get('data', {}).get('symbol', 'unknown')}"
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid chart config JSON: {e}")
            invalid_spans.append((match.start(), match.end()))

    # 从后往前删除无效标签，避免位置偏移
    processed = list(response)
    for start, end in reversed(invalid_spans):
        del processed[start:end]

    return "".join(processed), valid_configs


def convert_to_langchain_messages(history: List[ChatMessageModel]) -> List[BaseMessage]:
    """将历史消息转换为LangChain消息格式。

    Args:
        history: 历史消息列表，每条消息包含 role 和 content 字段。

    Returns:
        LangChain消息对象列表。
    """
    messages = []
    for msg in history:
        msg_class = _MESSAGE_CLASS_MAP.get(msg.role)
        if msg_class:
            messages.append(msg_class(content=msg.content))
    return messages


def extract_stream_output(chunk) -> dict:
    """从流式响应chunk中提取结构化数据。

    Args:
        chunk: 流式响应的chunk对象，可能是 (message, metadata) tuple。

    Returns:
        dict: 包含所有字段(content, metadata, tool_calls等)。
    """
    # 处理 (message, metadata) tuple 格式
    if isinstance(chunk, tuple) and len(chunk) == 2:
        message, metadata = chunk
        result = {}

        # 提取消息内容
        if hasattr(message, "model_dump"):
            result = message.model_dump()
        elif hasattr(message, "content"):
            result = {"content": message.content}
            for attr in [
                "additional_kwargs",
                "response_metadata",
                "id",
                "tool_calls",
                "invalid_tool_calls",
                "tool_call_chunks",
            ]:
                if hasattr(message, attr):
                    result[attr] = getattr(message, attr)
        else:
            result = {"content": str(message)}

        # 添加 metadata
        if metadata:
            result["metadata"] = metadata

        return result

    # 处理字典格式
    elif isinstance(chunk, dict):
        if "error" in chunk:
            return {"content": chunk["error"]}
        if "output" in chunk:
            return {"content": chunk["output"]}
        if "messages" in chunk:
            msgs = chunk["messages"]
            if msgs:
                return extract_stream_output(msgs[-1])
            return {"content": ""}
        return {"content": str(chunk)}

    # 处理单个消息对象
    elif hasattr(chunk, "model_dump"):
        return chunk.model_dump()

    elif hasattr(chunk, "content"):
        result = {"content": chunk.content}
        for attr in [
            "additional_kwargs",
            "response_metadata",
            "id",
            "tool_calls",
            "invalid_tool_calls",
            "tool_call_chunks",
        ]:
            if hasattr(chunk, attr):
                result[attr] = getattr(chunk, attr)
        return result

    else:
        return {"content": str(chunk)}


async def get_session_service(request: Request):
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


async def _handle_chat(
    message: str,
    session_id: str,
    session_service: SessionService,
) -> ChatResponse:
    """处理聊天请求的公共逻辑。"""
    try:
        # 1. 保存用户消息(token 数未知，存 0)
        await session_service.save_message(session_id, "user", message, tokens=0)

        # 2. 获取历史消息并转换为LangChain格式
        history = await session_service.get_sliding_window(session_id)
        chat_history = convert_to_langchain_messages(history)

        # 3. 调用 agent，获取回复和 usage 信息
        agent = get_finance_agent()
        reply, usage = await agent.achat(message, chat_history)

        # 4. 验证并处理 <chart> 块
        reply, chart_configs = validate_chart_configs(reply)

        # 5. 保存助手回复(使用 API 返回的 completion_tokens)
        logger.info(f"reply: {reply}")
        completion_tokens = usage.get("completion_tokens", 0)
        logger.info(f"completion_tokens: {completion_tokens}")
        await session_service.save_message(
            session_id, "assistant", reply, tokens=completion_tokens
        )

        return ChatResponse(
            reply=reply, session_id=session_id, charts=chart_configs or None
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        # 不向用户暴露内部错误详情
        return ChatResponse(
            reply="处理请求时发生错误，请稍后重试", session_id=session_id, charts=None
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_post(
    request: Request,
    body: ChatRequest,
    x_session_id: Optional[str] = Header(None),
    session_service=Depends(get_session_service),
):
    """聊天接口(POST)。"""
    session_id = await get_session_id(x_session_id)
    return await _handle_chat(body.message, session_id, session_service)


@router.post("/chat-stream")
async def chat_stream(
    request: Request,
    body: ChatRequest,
    x_session_id: Optional[str] = Header(None),
    session_service=Depends(get_session_service),
):
    """流式聊天接口(POST)。"""
    session_id = await get_session_id(x_session_id)
    # 用于追踪流式响应状态
    stream_state = {
        "completed": False,
        "full_reply": "",
        "output_tokens": 0,  # 存储 output_tokens
    }

    async def event_generator():
        try:
            # 1. 保存用户消息
            await session_service.save_message(
                session_id, "user", body.message, tokens=0
            )

            # 2. 获取历史消息并转换为LangChain格式
            history = await session_service.get_sliding_window(session_id)
            chat_history = convert_to_langchain_messages(history)

            # 3. 调用agent流式输出
            agent = get_finance_agent()
            async for chunk in agent.achat_stream(body.message, chat_history):
                output = extract_stream_output(chunk)
                content = output.get("content", "")
                if content:
                    stream_state["full_reply"] += content

                # 提取 usage_metadata 中的 output_tokens
                usage_metadata = output.get("usage_metadata")
                if usage_metadata and usage_metadata.get("output_tokens"):
                    stream_state["output_tokens"] = usage_metadata["output_tokens"]

                output["session_id"] = session_id
                yield {"data": json.dumps(output, ensure_ascii=False, default=str)}

            # 4. 流正常结束，标记完成
            stream_state["completed"] = True
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
