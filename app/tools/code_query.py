"""
代码查询工具 - 查询股票代码对应的信息
"""
from langchain.tools import tool
import logging
from app.services.database_service import StockBasicInfoService

logger = logging.getLogger(__name__)


@tool
async def query_code_info(code: str) -> str:
    """
    查询股票代码对应的信息，返回: 证券简称, 扩位证券简称, 公司英文全称, 上市日期
    
    Args:
        code: 股票代码，如 600000 或 000001
    
    Returns:
        股票代码信息的字符串格式
    """
    logger.info(f"开始查询股票代码: {code}")
    
    try:
        # 使用数据库服务查询股票信息
        result = await StockBasicInfoService.query_and_format(code)
        
        if "未找到" in result:
            logger.warning(f"股票代码 {code} 查询结果: {result}")
        else:
            logger.info(f"股票代码 {code} 查询成功")
            
        return result
        
    except Exception as e:
        error_msg = f"查询股票代码 {code} 失败: {str(e)}"
        logger.error(error_msg)
        return error_msg
