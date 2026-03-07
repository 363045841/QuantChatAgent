"""
股票工具测试脚本 - 使用真实 API 测试
"""
import asyncio
import sys
from app.tools.stock_tools import get_kline_bao, query_recent_days_bao, get_all_stocks_bao, get_stocks_by_date_bao
from app.tools.code_query import query_code_info


def print_separator(title: str):
    """打印分隔符"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60 + "\n")


async def test_get_kline():
    """测试 get_kline 工具"""
    print("【测试 1】测试 get_kline 工具")
    print("-" * 60)
    
    try:
        result = await get_kline_bao.ainvoke({
            "stock_code": "sh.600000",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "frequency": "d",
            "adjustflag": "3"
        })
        print("结果:")
        print(result)
        print("\n✅ get_kline 测试通过")
    except Exception as e:
        print(f"\n❌ get_kline 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()


async def test_query_recent_days():
    """测试 query_recent_days 工具"""
    print("【测试 2】测试 query_recent_days 工具")
    print("-" * 60)
    
    try:
        result = await query_recent_days_bao.ainvoke({
            "stock_code": "sh.600000",
            "days": 30
        })
        print("结果:")
        print(result)
        print("\n✅ query_recent_days 测试通过")
    except Exception as e:
        print(f"\n❌ query_recent_days 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()


async def test_get_all_stocks():
    """测试 get_all_stocks 工具"""
    print("【测试 3】测试 get_all_stocks 工具")
    print("-" * 60)
    
    try:
        result = await get_all_stocks_bao.ainvoke({"date": "2024-12-31"})
        print("结果:")
        print(result)
        print("\n✅ get_all_stocks 测试通过")
    except Exception as e:
        print(f"\n❌ get_all_stocks 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()


async def test_get_stocks_by_date():
    """测试 get_stocks_by_date 工具"""
    print("【测试 4】测试 get_stocks_by_date 工具")
    print("-" * 60)
    
    try:
        result = await get_stocks_by_date_bao.ainvoke({"date": "2024-12-31"})
        print("结果:")
        print(result)
        print("\n✅ get_stocks_by_date 测试通过")
    except Exception as e:
        print(f"\n❌ get_stocks_by_date 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()


async def test_query_code_info():
    """测试 query_code_info 工具"""
    print("【测试 5】测试 query_code_info 工具")
    print("-" * 60)
    
    try:
        result = await query_code_info.ainvoke({"code": "600000"})
        print("结果:")
        print(result)
        print("\n✅ query_code_info 测试通过")
    except Exception as e:
        print(f"\n❌ query_code_info 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()


async def run_all_tests():
    """运行所有测试"""
    print_separator("股票工具测试 - 使用真实 API")
    
    print("⚠️  注意: 此测试需要股票 API 服务运行在 http://localhost:8000")
    print("⚠️  如果 API 服务未运行，测试将失败\n")
    
    # 运行所有测试
    await test_get_kline()
    await test_query_recent_days()
    await test_get_all_stocks()
    await test_get_stocks_by_date()
    await test_query_code_info()
    
    print_separator("测试完成")


async def run_single_test(test_name: str):
    """运行单个测试"""
    print_separator(f"股票工具测试 - {test_name}")
    
    print("⚠️  注意: 此测试需要股票 API 服务运行在 http://localhost:8000")
    print("⚠️  如果 API 服务未运行，测试将失败\n")
    
    if test_name == "kline":
        await test_get_kline()
    elif test_name == "recent":
        await test_query_recent_days()
    elif test_name == "all":
        await test_get_all_stocks()
    elif test_name == "date":
        await test_get_stocks_by_date()
    elif test_name == "code":
        await test_query_code_info()
    else:
        print(f"❌ 未知的测试名称: {test_name}")
        print("可用的测试名称: kline, recent, all, date, code")
    
    print_separator("测试完成")


def print_help():
    """打印帮助信息"""
    print("""
股票工具测试脚本 - 使用真实 API

用法:
    python test_stock_tools.py              # 运行所有测试
    python test_stock_tools.py <test_name>  # 运行单个测试

可用的测试名称:
    kline   - 测试 get_kline 工具（K线数据查询）
    recent  - 测试 query_recent_days 工具（最近N天数据查询）
    all     - 测试 get_all_stocks 工具（获取所有股票列表）
    date    - 测试 get_stocks_by_date 工具（获取特定日期股票列表）
    code    - 测试 query_code_info 工具（查询股票代码信息）

注意:
    - 此测试需要股票 API 服务运行在 http://localhost:8000
    - 如果 API 服务未运行，测试将失败
    - 测试将直接调用真实 API，不使用 Mock 数据
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