"""
聊天相关工具函数
"""

import json
import logging
import re
from typing import List, Dict, Any, Tuple

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    BaseMessage,
)

from app.models.chat_session import ChatMessage as ChatMessageModel

logger = logging.getLogger(__name__)

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
