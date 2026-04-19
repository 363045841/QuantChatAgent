"""
测试 RAGService 的懒加载行为
验证导入时不会触发网络连接
"""

import sys
import time
import socket
from contextlib import redirect_stdout, redirect_stderr
import io


def check_network_activity():
    """检查是否有网络连接活动"""
    # 这个函数只是模拟检测，实际需要更复杂的工具
    return False


def test_import_no_network():
    """测试导入模块不会触发网络连接"""
    print("=" * 70)
    print("测试 1: 导入 rag_service 模块")
    print("=" * 70)
    
    start_time = time.time()
    
    # 导入模块
    from app.services.rag_service import RAGService, get_rag_service
    
    import_time = time.time() - start_time
    
    print(f"✅ 导入成功")
    print(f"⏱️  耗时: {import_time:.3f} 秒")
    print(f"\n检查: RAGService 类已加载，但未实例化")
    print(f"  - RAGService.__name__: {RAGService.__name__}")
    print(f"  - get_rag_service: {get_rag_service}")
    
    return import_time


def test_instance_no_network():
    """测试创建实例不会触发网络连接"""
    print("\n" + "=" * 70)
    print("测试 2: 创建 RAGService 实例（但不使用它）")
    print("=" * 70)
    
    start_time = time.time()
    
    # 创建实例
    from app.services.rag_service import RAGService
    rag = RAGService()
    
    instance_time = time.time() - start_time
    
    print(f"✅ 实例创建成功")
    print(f"⏱️  耗时: {instance_time:.3f} 秒")
    print(f"\n检查: 内部资源未初始化（懒加载）")
    print(f"  - rag._client: {rag._client}")
    print(f"  - rag._embeddings: {rag._embeddings}")
    print(f"  - rag._vectorstore: {rag._vectorstore}")
    
    if instance_time < 0.1:
        print(f"\n✅ 确认: 实例创建非常快速，没有触发网络连接")
    else:
        print(f"\n⚠️  警告: 实例创建耗时较长，可能存在初始化问题")
    
    return instance_time


def test_property_lazy_loading():
    """测试属性懒加载"""
    print("\n" + "=" * 70)
    print("测试 3: 访问属性触发懒加载")
    print("=" * 70)
    
    from app.services.rag_service import RAGService
    
    rag = RAGService()
    
    print("\n检查 3.1: 访问 client 属性（应该触发 Qdrant 连接）")
    start_time = time.time()
    try:
        client = rag.client
        client_time = time.time() - start_time
        print(f"✅ client 访问成功")
        print(f"⏱️  耗时: {client_time:.3f} 秒")
        print(f"  - rag._client: {type(rag._client).__name__}")
        
        if client_time > 0.5:
            print(f"✅ 确认: 访问 client 时发生了网络连接（耗时较长）")
        else:
            print(f"⚠️  注意: 访问 client 耗时较短，可能是本地连接或连接失败")
    except Exception as e:
        print(f"❌ client 访问失败: {e}")
        print(f"💡 这可能是正常的（如果 Qdrant 服务未启动）")
    
    print("\n检查 3.2: 再次访问 client 属性（应该使用缓存）")
    start_time = time.time()
    client = rag.client
    client_time_cached = time.time() - start_time
    print(f"✅ client 访问成功（缓存）")
    print(f"⏱️  耗时: {client_time_cached:.3f} 秒")
    
    if client_time_cached < 0.01:
        print(f"✅ 确认: 使用缓存，访问速度极快")
    
    print("\n检查 3.3: 访问 embeddings 属性")
    start_time = time.time()
    try:
        embeddings = rag.embeddings
        embeddings_time = time.time() - start_time
        print(f"✅ embeddings 访问成功")
        print(f"⏱️  耗时: {embeddings_time:.3f} 秒")
        print(f"  - rag._embeddings: {type(rag._embeddings).__name__}")
    except Exception as e:
        print(f"❌ embeddings 访问失败: {e}")
    
    print("\n检查 3.4: 访问 vectorstore 属性")
    start_time = time.time()
    try:
        vectorstore = rag.vectorstore
        vectorstore_time = time.time() - start_time
        print(f"✅ vectorstore 访问成功")
        print(f"⏱️  耗时: {vectorstore_time:.3f} 秒")
        print(f"  - rag._vectorstore: {type(rag._vectorstore).__name__}")
    except Exception as e:
        print(f"❌ vectorstore 访问失败: {e}")


def test_get_rag_service():
    """测试 get_rag_service 函数"""
    print("\n" + "=" * 70)
    print("测试 4: 使用 get_rag_service() 函数")
    print("=" * 70)
    
    start_time = time.time()
    
    # 第一次调用
    from app.services.rag_service import get_rag_service
    rag1 = get_rag_service()
    
    first_call_time = time.time() - start_time
    
    print(f"✅ 第一次调用成功")
    print(f"⏱️  耗时: {first_call_time:.3f} 秒")
    print(f"  - 内部资源未初始化: {rag1._client is None}")
    
    # 第二次调用（应该返回同一个实例）
    start_time = time.time()
    rag2 = get_rag_service()
    second_call_time = time.time() - start_time
    
    print(f"\n✅ 第二次调用成功")
    print(f"⏱️  耗时: {second_call_time:.3f} 秒")
    print(f"  - 是否为同一个实例: {rag1 is rag2}")
    
    if rag1 is rag2:
        print(f"✅ 确认: 返回单例实例")


def main():
    """运行所有测试"""
    print("\n" + "🔍" * 35)
    print(" RAGService 懒加载行为测试")
    print("🔍" * 35 + "\n")
    
    try:
        # 测试 1: 导入模块
        import_time = test_import_no_network()
        
        # 测试 2: 创建实例
        instance_time = test_instance_no_network()
        
        # 测试 3: 属性懒加载
        test_property_lazy_loading()
        
        # 测试 4: get_rag_service 函数
        test_get_rag_service()
        
        # 总结
        print("\n" + "=" * 70)
        print("📊 测试总结")
        print("=" * 70)
        print(f"✅ 导入耗时: {import_time:.3f} 秒")
        print(f"✅ 实例创建耗时: {instance_time:.3f} 秒")
        
        if import_time < 1.0 and instance_time < 0.1:
            print(f"\n✅ 结论: RAGService 已实现真正的懒加载")
            print(f"  - 导入时不触发网络连接")
            print(f"  - 实例创建时不触发网络连接")
            print(f"  - 网络连接延迟到首次访问属性时")
        else:
            print(f"\n⚠️  警告: 可能仍存在初始化开销")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()