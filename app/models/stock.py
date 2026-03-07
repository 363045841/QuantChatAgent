"""
股票数据模型
"""
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class StockDataResponse(BaseModel):
    """股票数据响应模型"""
    success: bool
    stock_code: str = Field(alias="stock_code")
    start_date: str = Field(alias="start_date")
    end_date: str = Field(alias="end_date")
    data_count: int = Field(alias="data_count")
    data: List[Any]
    error_code: Optional[str] = Field(None, alias="error_code")
    error_msg: Optional[str] = Field(None, alias="error_msg")

    class Config:
        populate_by_name = True


class StockListResponse(BaseModel):
    """股票列表响应模型"""
    success: bool
    date: Optional[str] = None
    data_count: int = Field(alias="data_count")
    data: List[Any]
    error_code: Optional[str] = Field(None, alias="error_code")
    error_msg: Optional[str] = Field(None, alias="error_msg")

    class Config:
        populate_by_name = True


class StockInfo(BaseModel):
    """股票基本信息模型"""
    code: str
    name: str
    english_name: Optional[str] = None
    list_date: Optional[str] = None