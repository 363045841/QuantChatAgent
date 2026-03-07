"""
测试百度智能云 Reranker 功能
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.reranker_service import RerankerService
from app.services.rag_service import RAGService


async def test_reranker_basic():
    """测试 Reranker 基本功能"""
    print("=" * 60)
    print("测试 1: Reranker 基本功能")
    print("=" * 60)
    
    reranker = RerankerService()
    
    query = "上海天气"
    documents = [
        "上海气候",
        "北京美食",
        "上海旅游景点",
        "北京交通",
        "上海房价"
    ]
    
    print(f"\n查询: {query}")
    print(f"\n候选文档 ({len(documents)} 条):")
    for i, doc in enumerate(documents, 1):
        print(f"  {i}. {doc}")
    
    try:
        results = await reranker.rerank(query, documents, top_n=3)
        
        print(f"\n重排序结果 ({len(results)} 条):")
        for i, result in enumerate(results, 1):
            print(f"\n  结果 {i}:")
            print(f"    文档: {result['document']}")
            print(f"    相关性分数: {result['relevance_score']:.4f}")
            print(f"    原始索引: {result['index']}")
        
        print("\n✅ Reranker 基本功能测试通过")
        return True
    except Exception as e:
        print(f"\n❌ Reranker 基本功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_reranker_with_real_news():
    """测试 Reranker 处理真实新闻"""
    print("\n" + "=" * 60)
    print("测试 2: Reranker 处理真实新闻")
    print("=" * 60)
    
    reranker = RerankerService()
    
    query = "茅台股价上涨"
    documents = [
        "贵州茅台今日发布财报，营收同比增长15%",
        "五粮液股价今日下跌2%",
        "贵州茅台宣布分红方案，每股派息2元",
        "白酒板块整体表现疲软",
        "贵州茅台董事长更换，新任领导强调创新",
        "A股今日大涨，创业板涨幅超过3%"
    ]
    
    print(f"\n查询: {query}")
    print(f"\n候选文档 ({len(documents)} 条):")
    for i, doc in enumerate(documents, 1):
        print(f"  {i}. {doc}")
    
    try:
        results = await reranker.rerank(query, documents, top_n=3)
        
        print(f"\n重排序结果 ({len(results)} 条):")
        for i, result in enumerate(results, 1):
            print(f"\n  结果 {i}:")
            print(f"    文档: {result['document']}")
            print(f"    相关性分数: {result['relevance_score']:.4f}")
        
        print("\n✅ Reranker 真实新闻测试通过")
        return True
    except Exception as e:
        print(f"\n❌ Reranker 真实新闻测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_rag_with_reranker():
    """测试 RAG Service 集成 Reranker"""
    print("\n" + "=" * 60)
    print("测试 3: RAG Service 集成 Reranker")
    print("=" * 60)
    
    rag_service = RAGService()
    
    # 检查 Collection 是否存在
    if not rag_service.check_collection():
        print("\n❌ Collection 不存在，跳过此测试")
        return False
    
    query = "茅台股价"
    
    print(f"\n查询: {query}")
    print("\n使用 Reranker 进行检索...")
    
    try:
        results = await rag_service.search(query, top_k=3, use_reranker=True)
        
        print(f"\n检索结果 ({len(results)} 条):")
        for i, result in enumerate(results, 1):
            print(f"\n  结果 {i}:")
            print(f"    标题: {result['title']}")
            print(f"    相似度: {result['score']:.4f}")
            print(f"    摘要: {result['abstract'][:80]}...")
        
        print("\n✅ RAG Service 集成 Reranker 测试通过")
        return True
    except Exception as e:
        print(f"\n❌ RAG Service 集成 Reranker 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_rag_without_reranker():
    """测试 RAG Service 不使用 Reranker"""
    print("\n" + "=" * 60)
    print("测试 4: RAG Service 不使用 Reranker（对比）")
    print("=" * 60)
    
    rag_service = RAGService()
    
    # 检查 Collection 是否存在
    if not rag_service.check_collection():
        print("\n❌ Collection 不存在，跳过此测试")
        return False
    
    query = "茅台股价"
    
    print(f"\n查询: {query}")
    print("\n不使用 Reranker 进行检索...")
    
    try:
        results = await rag_service.search(query, top_k=3, use_reranker=False)
        
        print(f"\n检索结果 ({len(results)} 条):")
        for i, result in enumerate(results, 1):
            print(f"\n  结果 {i}:")
            print(f"    标题: {result['title']}")
            print(f"    相似度: {result['score']:.4f}")
            print(f"    摘要: {result['abstract'][:80]}...")
        
        print("\n✅ RAG Service 不使用 Reranker 测试通过")
        return True
    except Exception as e:
        print(f"\n❌ RAG Service 不使用 Reranker 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试百度智能云 Reranker 功能")
    print("=" * 60)
    
    results = []
    
    # 测试 1: Reranker 基本功能
    results.append(await test_reranker_basic())
    
    # 测试 2: Reranker 处理真实新闻
    results.append(await test_reranker_with_real_news())
    
    # 测试 3: RAG Service 集成 Reranker
    results.append(await test_rag_with_reranker())
    
    # 测试 4: RAG Service 不使用 Reranker（对比）
    results.append(await test_rag_without_reranker())
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"\n通过: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)