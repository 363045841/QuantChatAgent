"""
股票基本信息数据模型
"""

from datetime import date
from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class StockBasicInfo(Base):
    """股票基本信息表模型"""

    __tablename__ = "stock_basic_info"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    a_share_code = Column(String, comment="A股代码")
    b_share_code = Column(String, comment="B股代码")
    security_abbreviation = Column(String, comment="证券简称")
    expanded_abbreviation = Column(String, comment="扩位证券简称")
    company_english_name = Column(String, comment="公司英文全称")
    listing_date = Column(Date, comment="上市日期")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "a_share_code": self.a_share_code,
            "b_share_code": self.b_share_code,
            "security_abbreviation": self.security_abbreviation,
            "expanded_abbreviation": self.expanded_abbreviation,
            "company_english_name": self.company_english_name,
            "listing_date": (
                self.listing_date.isoformat() if self.listing_date else None
            ),
        }
