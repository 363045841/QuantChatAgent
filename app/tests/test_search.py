"""
测试 RAGService.search() 函数
"""
import asyncio


from app.services.rag_service import rag_service

async def main():
    """简单测试 search 函数"""
    query = "三六零 财务"
    print(f"查询: {query}")
    print("-" * 60)
    
    # 调用 search 函数
    results = await rag_service.search(query, top_k=3)
    
    # 打印结果
    if results:
        print(f"✅ 检索成功，返回 {len(results)} 条结果")
        for idx, result in enumerate(results, 1):
            print(f"\n【{idx}】{result['title']}")
            print(f"   相似度: {result['score']:.3f}")
            print(f"   摘要: {result['abstract'][:50]}...")
    else:
        print("❌ 未检索到结果")

if __name__ == "__main__":
    asyncio.run(main())