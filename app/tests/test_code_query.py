"""
代码查询工具测试 - 使用 PostgreSQL 数据库
"""
import asyncio
import sys
from app.tools.code_query import query_code_info
from app.services.database_service import StockBasicInfoService


def print_separator(title: str):
    """打印分隔符"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60 + "\n")


async def test_query_code_info():
    """测试 query_code_info 工具"""
    print("【测试 1】测试 query_code_info 工具 - 查询浦发银行 (600000)")
    print("-" * 60)
    
    try:
        result = await query_code_info.ainvoke({"code": "600000"})
        print("查询结果:")
        print(result)
        print("\n✅ query_code_info(600000) 测试通过")
        return True
    except Exception as e:
        print(f"\n❌ query_code_info(600000) 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()


async def test_query_code_info_not_found():
    """测试查询不存在的股票代码"""
    print("【测试 2】测试 query_code_info 工具 - 查询不存在的代码 (999999)")
    print("-" * 60)
    
    try:
        result = await query_code_info.ainvoke({"code": "999999"})
        print("查询结果:")
        print(result)
        
        if "未找到" in result:
            print("\n✅ query_code_info(999999) 测试通过 - 正确返回未找到提示")
            return True
        else:
            print("\n❌ query_code_info(999999) 测试失败 - 应该返回未找到提示")
            return False
            
    except Exception as e:
        print(f"\n❌ query_code_info(999999) 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()


async def test_query_code_info_zero():
    """测试查询以 0 开头的股票代码"""
    print("【测试 3】测试 query_code_info 工具 - 查询深交所股票 (000001)")
    print("-" * 60)
    
    try:
        result = await query_code_info.ainvoke({"code": "000001"})
        print("查询结果:")
        print(result)
        print("\n✅ query_code_info(000001) 测试通过")
        return True
    except Exception as e:
        print(f"\n❌ query_code_info(000001) 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()


async def test_direct_db_service():
    """直接测试数据库服务层"""
    print("【测试 4】直接测试 StockBasicInfoService - 查询 600000")
    print("-" * 60)
    
    try:
        # 测试查询
        stock_info = await StockBasicInfoService.query_by_code("600000")
        
        if stock_info:
            print("数据库查询成功:")
            print(f"  ID: {stock_info.id}")
            print(f"  A股代码: {stock_info.a_share_code}")
            print(f"  证券简称: {stock_info.security_abbreviation}")
            print(f"  扩位证券简称: {stock_info.expanded_abbreviation}")
            print(f"  公司英文全称: {stock_info.company_english_name}")
            print(f"  上市日期: {stock_info.listing_date}")
            
            # 测试格式化
            formatted = await StockBasicInfoService.format_stock_info(stock_info)
            print("\n格式化结果:")
            print(formatted)
            
            print("\n✅ StockBasicInfoService 直接测试通过")
            return True
        else:
            print("❌ 数据库查询失败: 未找到股票代码 600000")
            return False
            
    except Exception as e:
        print(f"\n❌ StockBasicInfoService 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()


async def test_direct_db_service_not_found():
    """测试数据库服务层 - 查询不存在的代码"""
    print("【测试 5】直接测试 StockBasicInfoService - 查询不存在的代码 (999999)")
    print("-" * 60)
    
    try:
        stock_info = await StockBasicInfoService.query_by_code("999999")
        
        if stock_info is None:
            print("✅ 正确返回 None - 股票代码 999999 不存在")
            
            # 测试 query_and_format 方法
            result = await StockBasicInfoService.query_and_format("999999")
            print(f"格式化结果: {result}")
            
            if "未找到" in result:
                print("\n✅ StockBasicInfoService 未找到测试通过")
                return True
            else:
                print("\n❌ query_and_format 返回结果不符合预期")
                return False
        else:
            print(f"❌ 错误: 找到了不应该存在的股票数据: {stock_info}")
            return False
            
    except Exception as e:
        print(f"\n❌ StockBasicInfoService 未找到测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()


async def run_all_tests():
    """运行所有测试"""
    print_separator("代码查询工具测试 - PostgreSQL 数据库")
    
    print("⚠️  注意:")
    print("  - 此测试需要 PostgreSQL 数据库运行并可访问")
    print("  - 数据库中需要有 stock_basic_info 表和数据")
    print("  - 如果数据库配置不正确，测试将失败")
    print("  - 请确保 .env 文件中的 DB_PASSWORD 已正确配置\n")
    
    # 运行所有测试
    results = []
    results.append(await test_query_code_info())
    results.append(await test_query_code_info_not_found())
    results.append(await test_query_code_info_zero())
    results.append(await test_direct_db_service())
    results.append(await test_direct_db_service_not_found())
    
    # 统计结果
    passed = sum(results)
    total = len(results)
    
    print_separator("测试完成")
    print(f"\n📊 测试结果统计:")
    print(f"   通过: {passed}/{total}")
    print(f"   失败: {total - passed}/{total}")
    
    if passed == total:
        print("\n✅ 所有测试通过！")
    else:
        print(f"\n❌ 有 {total - passed} 个测试失败")


async def run_single_test(test_name: str):
    """运行单个测试"""
    print_separator(f"代码查询工具测试 - {test_name}")
    
    print("⚠️  注意:")
    print("  - 此测试需要 PostgreSQL 数据库运行并可访问")
    print("  - 数据库中需要有 stock_basic_info 表和数据\n")
    
    if test_name == "tool":
        await test_query_code_info()
    elif test_name == "not_found":
        await test_query_code_info_not_found()
    elif test_name == "zero":
        await test_query_code_info_zero()
    elif test_name == "db_service":
        await test_direct_db_service()
    elif test_name == "db_not_found":
        await test_direct_db_service_not_found()
    else:
        print(f"❌ 未知的测试名称: {test_name}")
        print("可用的测试名称: tool, not_found, zero, db_service, db_not_found")
    
    print_separator("测试完成")


def print_help():
    """打印帮助信息"""
    print("""
代码查询工具测试脚本 - PostgreSQL 数据库

用法:
    python test_code_query.py              # 运行所有测试
    python test_code_query.py <test_name>  # 运行单个测试

可用的测试名称:
    tool        - 测试 query_code_info 工具（查询浦发银行 600000）
    not_found   - 测试查询不存在的股票代码（999999）
    zero        - 测试查询以 0 开头的代码（000001）
    db_service  - 直接测试数据库服务层（StockBasicInfoService）
    db_not_found - 测试数据库服务层查询不存在的代码

注意:
    - 此测试需要 PostgreSQL 数据库运行并可访问
    - 数据库中需要有 stock_basic_info 表和数据
    - 请确保 .env 文件中的 DB_PASSWORD 已正确配置
    - 测试将直接查询真实数据库，不使用 Mock 数据
""")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ["-h", "--help", "help"]:
            print_help()
        else:
            asyncio.run(run_single_test(arg))
    else:
        asyncio.run(run_all_tests())