"""
导入性能测试脚本 - 验证模块导入是否有副作用
"""
import time
import sys
import traceback

def test_import(module_path, description):
    """测试单个模块的导入性能和安全性"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"模块: {module_path}")
    print(f"{'='*60}")
    
    start = time.time()
    
    try:
        # 清除可能存在的模块缓存
        if module_path in sys.modules:
            del sys.modules[module_path]
        
        # 导入模块
        module = __import__(module_path, fromlist=[''])
        
        elapsed = time.time() - start
        
        print(f"✅ 导入成功")
        print(f"⏱️  耗时: {elapsed:.3f} 秒")
        
        # 检查是否有全局实例化
        global_vars = [name for name in dir(module) if not name.startswith('_')]
        instance_vars = []
        
        for var_name in global_vars:
            var = getattr(module, var_name)
            # 检查是否是服务实例（通过命名约定判断）
            if 'service' in var_name.lower() or var_name.endswith('_instance'):
                if hasattr(var, '__class__'):
                    instance_vars.append(f"  - {var_name}: {var.__class__.__name__}")
        
        if instance_vars:
            print(f"\n⚠️  发现可能的模块级实例:")
            for var in instance_vars:
                print(var)
        
        return elapsed, True, None
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ 导入失败")
        print(f"⏱️  耗时: {elapsed:.3f} 秒")
        print(f"错误: {str(e)}")
        
        if '--traceback' in sys.argv:
            print("\n详细堆栈:")
            traceback.print_exc()
        
        return elapsed, False, str(e)

def main():
    """运行所有测试"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║        导入安全性测试 - 检测模块级副作用                    ║
║                                                            ║
║  测试目标: 验证模块导入是否触发重型初始化、网络连接等         ║
║                                                            ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    tests = [
        ("app.services.llm_service", "LLM 服务（可能包含 ChatOpenAI 实例化）"),
        ("app.services.stock_service", "Stock 数据服务"),
        ("app.services.database_service", "数据库服务（可能创建引擎）"),
        ("app.services.rag_service", "RAG 服务（已修复懒加载）"),
        ("app.services.reranker_service", "Reranker 服务"),
        ("app.agents.finance_agent", "Finance Agent（已修复懒加载）"),
        ("app.tools.stock_tools", "股票工具"),
        ("app.tools.rag_tools", "RAG 工具"),
        ("app.tools.code_query", "代码查询工具"),
    ]
    
    results = []
    
    for module_path, description in tests:
        elapsed, success, error = test_import(module_path, description)
        results.append({
            'module': module_path,
            'description': description,
            'elapsed': elapsed,
            'success': success,
            'error': error
        })
    
    # 汇总报告
    print(f"\n{'='*60}")
    print("📊 测试汇总报告")
    print(f"{'='*60}")
    
    print(f"\n导入耗时排序:")
    sorted_results = sorted(results, key=lambda x: x['elapsed'], reverse=True)
    for i, r in enumerate(sorted_results, 1):
        status = "✅" if r['success'] else "❌"
        print(f"{i:2d}. {status} {r['elapsed']:6.3f}s - {r['module']}")
    
    # 识别潜在问题
    slow_imports = [r for r in results if r['elapsed'] > 0.5]
    failed_imports = [r for r in results if not r['success']]
    
    print(f"\n⚠️  潜在问题:")
    if slow_imports:
        print(f"  导入耗时超过 0.5 秒的模块:")
        for r in slow_imports:
            print(f"    - {r['module']}: {r['elapsed']:.3f}s")
    
    if failed_imports:
        print(f"  导入失败的模块:")
        for r in failed_imports:
            print(f"    - {r['module']}: {r['error']}")
    
    if not slow_imports and not failed_imports:
        print(f"  未发现明显的导入问题")
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()