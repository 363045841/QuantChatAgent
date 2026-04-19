"""
股票数据服务 - 调用外部股票 API
"""
import httpx
from typing import Optional
from app.config import settings
from app.models.stock import StockDataResponse, StockListResponse


class StockDataService:
    """股票数据服务类"""
    
    def __init__(self):
        """初始化股票数据服务"""
        self.base_url = settings.stock_api_base_url
        self.timeout = 30
    
    async def get_stock_k_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d",
        adjustflag: str = "3"
    ) -> Optional[StockDataResponse]:
        """
        获取股票历史 K 线数据
        
        Args:
            stock_code: 股票代码，如 sh.600000
            start_date: 开始日期，格式 2024-07-01
            end_date: 结束日期，格式 2024-12-31
            frequency: 数据频率: d=日, w=周, m=月, 5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟
            adjustflag: 复权类型: 1=后复权, 2=前复权, 3=不复权
        
        Returns:
            StockDataResponse 对象，失败返回 None
        """
        url = f"{self.base_url}/api/stock/kdata"
        params = {
            "stock_code": stock_code,
            "start_date": start_date,
            "end_date": end_date,
            "frequency": frequency,
            "adjustflag": adjustflag
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return StockDataResponse(**data)
        except Exception as e:
            print(f"获取股票 K 线数据失败: {e}")
            return None
    
    async def query_all_stocks(self, date: Optional[str] = None) -> Optional[StockListResponse]:
        """
        获取所有股票列表
        
        Args:
            date: 查询日期，格式 2024-07-01（可选）
        
        Returns:
            StockListResponse 对象，失败返回 None
        """
        url = f"{self.base_url}/api/stock/list"
        params = {"date": date} if date else {}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return StockListResponse(**data)
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return None
    
    async def stock_query(self, stock_code: str, days: int = 30) -> Optional[StockDataResponse]:
        """
        快捷查询最近 N 天的股票数据
        
        Args:
            stock_code: 股票代码，如 sh.600000
            days: 查询天数
        
        Returns:
            StockDataResponse 对象，失败返回 None
        """
        url = f"{self.base_url}/api/stock/query"
        params = {
            "stock_code": stock_code,
            "days": days
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return StockDataResponse(**data)
        except Exception as e:
            print(f"查询股票数据失败: {e}")
            return None


# 懒加载股票数据服务实例
_stock_data_service = None

def get_stock_data_service():
    """
    获取股票数据服务实例（懒加载单例）
    
    使用懒加载避免在模块导入时创建服务实例，
    保持架构一致性和更好的资源管理。
    """
    global _stock_data_service
    if _stock_data_service is None:
        _stock_data_service = StockDataService()
    return _stock_data_service
