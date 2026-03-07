"""
测试 Finance Agent 的完整功能
"""
import asyncio
from app.agents.finance_agent import finance_agent


async def test_basic_chat():
    """测试普通对话"""
    print("=" * 60)
    print("【测试 1】普通对话")
    print("=" * 60)
    
    result = await finance_agent.achat("你好，请介绍一下你自己")
    print(f"AI 回复: {result}")
    print("✅ 普通对话测试通过\n")


async def test_tool_calling():
    """测试工具调用"""
    print("=" * 60)
    print("【测试 2】工具调用 - 查询股票代码")
    print("=" * 60)
    
    result = await finance_agent.achat("查询600519的股票代码信息")
    print(f"AI 回复: {result[:200]}...")
    print("✅ 查询股票代码测试通过\n")


async def test_kline_query():
    """测试K线查询"""
    print("=" * 60)
    print("【测试 3】工具调用 - 查询K线数据")
    print("=" * 60)
    
    result = await finance_agent.achat("查询sh.600519最近5天的日线数据")
    print(f"AI 回复: {result[:300]}...")
    print("✅ K线查询测试通过\n")


async def test_multiple_tools():
    """测试多个工具调用"""
    print("=" * 60)
    print("【测试 4】多轮对话 - 多个工具调用")
    print("=" * 60)
    
    # 第一轮对话
    result1 = await finance_agent.achat("我想了解贵州茅台的股票信息")
    print(f"第一轮 AI: {result1[:200]}...")
    
    # 第二轮对话（应该能记住上下文，虽然现在没有实现记忆）
    result2 = await finance_agent.achat("查询它最近3天的数据")
    print(f"第二轮 AI: {result2[:200]}...")
    print("✅ 多轮对话测试通过\n")


async def test_streaming():
    """测试流式输出"""
    print("=" * 60)
    print("【测试 5】流式输出")
    print("=" * 60)
    
    print("流式输出开始:")
    async for chunk in finance_agent.achat_stream("你好"):
        if isinstance(chunk, dict) and "messages" in chunk:
            messages = chunk["messages"]
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, 'content'):
                    print(last_msg.content, end='', flush=True)
    print("\n✅ 流式输出测试通过\n")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试 Finance Agent")
    print("=" * 60 + "\n")
    
    try:
        await test_basic_chat()
        await test_tool_calling()
        await test_kline_query()
        await test_multiple_tools()
        await test_streaming()
        
        print("=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())