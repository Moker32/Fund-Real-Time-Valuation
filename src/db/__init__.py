# -*- coding: UTF-8 -*-
"""数据库模块初始化

提供 SQLite 数据库支持，包括：
- 基金配置存储（自选、持仓）
- 商品配置存储
- 基金净值历史数据
- 新闻缓存
- 基金日内分时数据缓存

使用示例：
    from src.db.database import DatabaseManager

    db = DatabaseManager()
    db.add_fund_to_watchlist("161039", "富国中证新能源汽车指数")
    holdings = db.get_holdings()
"""

from src.db.calendar import ExchangeHolidayDAO, TradingCalendarDAO
from src.db.commodity_intraday_dao import CommodityIntradayCacheDAO
from src.db.config_dao import ConfigDAO
from src.db.database import DatabaseManager
from src.db.fund import (
    CacheMetadataDAO,
    FundBasicInfoDAO,
    FundConceptTagsDAO,
    FundDailyCacheDAO,
    FundHistoryDAO,
    FundIndustryDAO,
    FundIntradayCacheDAO,
    StockConceptDAO,
)
from src.db.index_intraday_dao import IndexIntradayCacheDAO
from src.db.models import (
    ApiCallStats,
    CacheMetadata,
    CommodityConfig,
    CommodityIntradayRecord,
    ExchangeHoliday,
    FundBasicInfo,
    FundConfig,
    FundDailyRecord,
    FundHistoryRecord,
    FundIndustryRecord,
    FundIntradayRecord,
    IndexIntradayRecord,
    NewsRecord,
    StockConceptRecord,
    TradingCalendarRecord,
)
from src.db.news_dao import NewsDAO

__all__ = [
    # DatabaseManager
    "DatabaseManager",
    # Models
    "FundConfig",
    "CommodityConfig",
    "CommodityIntradayRecord",
    "FundHistoryRecord",
    "FundIndustryRecord",
    "NewsRecord",
    "FundIntradayRecord",
    "IndexIntradayRecord",
    "FundDailyRecord",
    "FundBasicInfo",
    "StockConceptRecord",
    "CacheMetadata",
    "ApiCallStats",
    "TradingCalendarRecord",
    "ExchangeHoliday",
    # DAOs
    "ConfigDAO",
    "FundHistoryDAO",
    "NewsDAO",
    "FundIntradayCacheDAO",
    "IndexIntradayCacheDAO",
    "FundDailyCacheDAO",
    "FundBasicInfoDAO",
    "FundIndustryDAO",
    "StockConceptDAO",
    "FundConceptTagsDAO",
    "TradingCalendarDAO",
    "ExchangeHolidayDAO",
    "CacheMetadataDAO",
    "CommodityIntradayCacheDAO",
]
