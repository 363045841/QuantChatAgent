"""
股票数据工具 - LangChain 工具定义
"""
from langchain.tools import tool
from app.services.stock_service import stock_data_service
from typing import Optional


@tool
async def get_kline(
    stock_code: str,
    start_date: str,
    end_date: str,
    frequency: Optional[str] = "d",
    adjustflag: Optional[str] = "3"
) -> str:
    """
    获取某只股票的K线数据信息
    
    Args:
        stock_code: 股票代码，如 sh.600000 或 sz.000001, 必须以sh.(沪市)或sz.(深市)开头
        start_date: 开始日期，格式 2024-07-01
        end_date: 结束日期，格式 2024-12-31
        frequency: 数据频率（可选，默认d=日线），可选值: d=日, w=周, m=月, 5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟
        adjustflag: 复权类型（可选，默认3=不复权），可选值: 1=后复权, 2=前复权, 3=不复权
    
    Returns:
        股票K线数据的JSON格式字符串
    """
    print(f"查询K线数据: stockCode={stock_code}, startDate={start_date}, endDate={end_date}, frequency={frequency}, adjustflag={adjustflag}")
    
    final_frequency = frequency if frequency else "d"
    final_adjustflag = adjustflag if adjustflag else "3"
    
    response = await stock_data_service.get_stock_k_data(
        stock_code, start_date, end_date, final_frequency, final_adjustflag
    )
    
    if response and response.success:
        print(f"查询K线数据成功: stockCode={stock_code}, 数据条数={response.data_count}")
        return build_kline_response_message(response, final_frequency, final_adjustflag)
    else:
        error_msg = response.error_msg if response else "查询股票K线数据失败"
        print(f"查询K线数据失败: stockCode={stock_code}, 错误={error_msg}")
        return f"查询失败: {error_msg}"


@tool
async def query_recent_days(stock_code: str, days: int = 30) -> str:
    """
    快捷查询最近N天的股票数据
    
    Args:
        stock_code: 股票代码，如 sh.600000 或 sz.000001,必须以sh.(沪市)或sz.(深市)开头
        days: 查询天数，默认30天
    
    Returns:
        股票数据的JSON格式字符串
    """
    final_days = days if days > 0 else 30
    print(f"查询近期股票数据: stockCode={stock_code}, days={final_days}")
    
    response = await stock_data_service.stock_query(stock_code, final_days)
    
    if response and response.success:
        print(f"查询近期股票数据成功: stockCode={stock_code}, 数据条数={response.data_count}")
        result = []
        result.append(f"股票代码: {response.stock_code}")
        result.append(f"查询近: {final_days}天的数据")
        result.append(f"数据条数: {response.data_count}")
        result.append(f"查询日期: {response.start_date} 至 {response.end_date}")
        result.append(f"数据详情: {response.data}")
        return "\n".join(result)
    else:
        error_msg = response.error_msg if response else "查询股票数据时发生错误"
        print(f"查询近期股票数据失败: stockCode={stock_code}, 错误={error_msg}")
        return f"查询失败: {error_msg}"


@tool
async def get_all_stocks(date: Optional[str] = None) -> str:
    """
    获取所有股票列表
    
    Args:
        date: 查询日期，格式 2024-07-01（可选，不传则查询最新数据）
    
    Returns:
        股票列表的JSON格式字符串
    """
    query_date = date if date else None
    print(f"查询股票列表: date={query_date if query_date else '最新'}")
    
    response = await stock_data_service.query_all_stocks(query_date)
    
    if response and response.success:
        print(f"查询股票列表成功: 股票数量={response.data_count}")
        result = []
        result.append(f"查询日期: {response.date if response.date else '最新'}")
        result.append(f"股票数量: {response.data_count}")
        result.append(f"数据详情: {response.data}")
        return "\n".join(result)
    else:
        error_msg = response.error_msg if response else "查询股票列表时发生错误"
        print(f"查询股票列表失败: 错误={error_msg}")
        return f"查询失败: {error_msg}"


@tool
async def get_stocks_by_date(date: str) -> str:
    """
    获取特定日期的股票列表
    
    Args:
        date: 查询日期，格式 2024-07-01
    
    Returns:
        股票列表的JSON格式字符串
    """
    # 直接调用底层服务，而不是通过工具包装
    response = await stock_data_service.query_all_stocks(date)
    
    if response and response.success:
        print(f"查询股票列表成功: 股票数量={response.data_count}")
        result = []
        result.append(f"查询日期: {response.date if response.date else date}")
        result.append(f"股票数量: {response.data_count}")
        result.append(f"数据详情: {response.data}")
        return "\n".join(result)
    else:
        error_msg = response.error_msg if response else "查询股票列表时发生错误"
        print(f"查询股票列表失败: 错误={error_msg}")
        return f"查询失败: {error_msg}"


def build_kline_response_message(response, frequency: str, adjustflag: str) -> str:
    """构建K线数据响应消息"""
    result = []
    result.append(f"股票代码: {response.stock_code}")
    result.append(f"查询日期: {response.start_date} 至 {response.end_date}")
    result.append(f"数据条数: {response.data_count}")
    result.append(f"数据频率: {get_frequency_desc(frequency)}")
    result.append(f"复权类型: {get_adjustflag_desc(adjustflag)}")
    result.append(f"数据详情: {response.data}")
    return "\n".join(result)


def get_frequency_desc(frequency: str) -> str:
    """获取频率描述"""
    freq_map = {
        "d": "日线",
        "w": "周线",
        "m": "月线",
        "5": "5分钟",
        "15": "15分钟",
        "30": "30分钟",
        "60": "60分钟"
    }
    return freq_map.get(frequency, "未知")


def get_adjustflag_desc(adjustflag: str) -> str:
    """获取复权类型描述"""
    adj_map = {
        "1": "后复权",
        "2": "前复权",
        "3": "不复权"
    }
    return adj_map.get(adjustflag, "未知")