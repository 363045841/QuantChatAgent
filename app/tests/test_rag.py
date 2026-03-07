"""
RAG 功能测试
测试 RAG Service 和 Agent 集成
"""

import asyncio
import sys
from app.services.rag_service import rag_service
from app.agents.finance_agent import finance_agent


async def test_rag_service():
    """测试 RAG Service"""
    print("=" * 80)
    print("测试 1: 检查 Qdrant Collection")
    print("=" * 80)
    
    exists = rag_service.check_collection()
    if not exists:
        print("❌ Collection 不存在，请先运行 baidu.py 抓取数据")
        return False
    
    print()
    print("=" * 80)
    print("测试 2: 向量检索")
    print("=" * 80)
    
    query = "601360 最新消息"
    print(f"查询: {query}")
    print()
    
    results = await rag_service.search(query, top_k=5)
    
    if results:
        print(f"✅ 检索成功，返回 {len(results)} 条结果")
        print()
        print(rag_service.format_results(results))
    else:
        print("❌ 未检索到结果")
        return False
    
    print()
    return True


async def test_rag_tool():
    """测试 RAG Tool"""
    print("=" * 80)
    print("测试 3: RAG Tool 调用")
    print("=" * 80)
    
    from app.tools.rag_tools import search_news
    
    query = "601360 最新消息"
    print(f"查询: {query}")
    print()
    
    # LangChain Tool 通过 ainvoke 调用（异步）
    result = await search_news.ainvoke({"query": query, "top_k": 3})
    print(result)
    print()
    
    if "未找到相关新闻信息" in result:
        print("⚠️ 未找到相关新闻")
        return False
    
    return True


async def test_agent_with_rag():
    """测试 Agent 调用 RAG 工具"""
    print("=" * 80)
    print("测试 4: Agent 调用 RAG 工具")
    print("=" * 80)
    
    message = "帮我查一下 601360 的最新消息"
    print(f"用户提问: {message}")
    print()
    print("AI 回复:")
    print("-" * 80)
    
    try:
        reply = await finance_agent.achat(message)
        print(reply)
        print("-" * 80)
        print()
        
        if "未找到" in reply or "没有找到" in reply:
            print("⚠️ Agent 可能未能正确使用 RAG 工具")
            return False
        
        print("✅ Agent 成功调用 RAG 工具")
        return True
        
    except Exception as e:
        print(f"❌ Agent 调用失败: {e}")
        return False


async def main():
    """主测试函数"""
    print()
    print("🚀 开始 RAG 功能测试")
    print()
    
    # 测试 1: RAG Service
    success1 = await test_rag_service()
    print()
    
    # 测试 2: RAG Tool
    success2 = await test_rag_tool()
    print()
    
    # 测试 3: Agent 集成
    success3 = await test_agent_with_rag()
    print()
    
    # 测试总结
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"RAG Service: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"RAG Tool:    {'✅ 通过' if success2 else '❌ 失败'}")
    print(f"Agent 集成:  {'✅ 通过' if success3 else '❌ 失败'}")
    print()
    
    if success1 and success2 and success3:
        print("🎉 所有测试通过！RAG 功能已成功集成。")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)