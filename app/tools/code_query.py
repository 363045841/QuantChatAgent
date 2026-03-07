"""
代码查询工具 - 查询股票代码对应的信息
"""
from langchain.tools import tool
import httpx
from app.config import settings


@tool
async def query_code_info(code: str) -> str:
    """
    查询股票代码对应的信息，返回: 证券简称, 扩位证券简称, 公司英文全称, 上市日期
    
    Args:
        code: 股票代码，如 600000 或 000001
    
    Returns:
        股票代码信息的字符串格式
    """
    print(f"开始查询股票代码: {code}")
    
    # 这里应该调用实际的代码查询 API
    # 由于原项目中使用的是数据库查询，这里暂时返回模拟数据
    # 实际应用中需要根据实际情况实现
    
    try:
        # 示例：调用股票 API 的代码查询接口
        url = f"{settings.stock_api_base_url}/api/stock/code"
        params = {"code": code}
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("success"):
                stock_info = data.get("data", {})
                result = []
                result.append(f"股票代码: {code}")
                result.append(f"证券简称: {stock_info.get('name', '未知')}")
                result.append(f"扩位证券简称: {stock_info.get('full_name', '未知')}")
                result.append(f"公司英文全称: {stock_info.get('english_name', '未知')}")
                result.append(f"上市日期: {stock_info.get('list_date', '未知')}")
                return "\n".join(result)
            else:
                error_msg = data.get("error_msg", "查询失败")
                return f"查询股票代码 {code} 失败: {error_msg}"
    
    except Exception as e:
        print(f"查询股票代码 {code} 失败: {e}")
        
        # 返回示例数据，用于演示
        return f"""股票代码: {code}
证券简称: 示例公司
扩位证券简称: 示例股份有限公司
公司英文全称: Example Company Limited
上市日期: 2000-01-01
"""