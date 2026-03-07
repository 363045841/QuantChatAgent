"""
聊天 API 路由
"""
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from app.models.chat import ChatRequest, ChatResponse
from app.agents.finance_agent import finance_agent
from typing import Optional

router = APIRouter(prefix="/api/chat", tags=["聊天"])


@router.get("/chat", response_model=ChatResponse)
async def chat(message: str = Query(..., description="用户消息")):
    """
    普通对话接口
    
    Args:
        message: 用户输入的消息
    
    Returns:
        AI 的回复
    """
    try:
        reply = await finance_agent.achat(message)
        return ChatResponse(reply=reply)
    except Exception as e:
        return ChatResponse(reply=f"处理请求时出错: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat_post(request: ChatRequest):
    """
    普通对话接口 (POST)
    
    Args:
        request: 聊天请求
    
    Returns:
        AI 的回复
    """
    try:
        reply = await finance_agent.achat(request.message)
        return ChatResponse(reply=reply)
    except Exception as e:
        return ChatResponse(reply=f"处理请求时出错: {str(e)}")


@router.get("/chat-stream")
async def chat_stream(message: str = Query(..., description="用户消息")):
    """
    流式对话接口 (SSE)
    
    Args:
        message: 用户输入的消息
    
    Returns:
        流式输出的 SSE 响应
    """
    
    async def event_generator():
        """生成 SSE 事件"""
        try:
            async for chunk in finance_agent.achat_stream(message):
                # 提取输出内容
                output = ""
                if isinstance(chunk, dict):
                    # 处理不同类型的输出
                    if "output" in chunk:
                        output = chunk["output"]
                    elif "messages" in chunk:
                        messages = chunk["messages"]
                        if messages:
                            output = str(messages[-1])
                    else:
                        output = str(chunk)
                else:
                    output = str(chunk)
                
                if output:
                    yield {"data": output}
            
        except Exception as e:
            yield {"data": f"错误: {str(e)}"}
    
    return EventSourceResponse(event_generator())


@router.post("/chat-stream")
async def chat_stream_post(request: ChatRequest):
    """
    流式对话接口 (POST, SSE)
    
    Args:
        request: 聊天请求
    
    Returns:
        流式输出的 SSE 响应
    """
    
    async def event_generator():
        """生成 SSE 事件"""
        try:
            async for chunk in finance_agent.achat_stream(request.message):
                # 提取输出内容
                output = ""
                if isinstance(chunk, dict):
                    # 处理不同类型的输出
                    if "output" in chunk:
                        output = chunk["output"]
                    elif "messages" in chunk:
                        messages = chunk["messages"]
                        if messages:
                            output = str(messages[-1])
                    else:
                        output = str(chunk)
                else:
                    output = str(chunk)
                
                if output:
                    yield {"data": output}
            
        except Exception as e:
            yield {"data": f"错误: {str(e)}"}
    
    return EventSourceResponse(event_generator())


@router.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "QuantAgent Chat API"}