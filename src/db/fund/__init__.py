# -*- coding: UTF-8 -*-
"""基金数据库 DAO 模块

提供基金相关数据的数据库访问对象。
"""

from src.db.fund.cache_metadata_dao import CacheMetadataDAO
from src.db.fund.fund_basic_info_dao import FundBasicInfoDAO
from src.db.fund.fund_daily_dao import FundDailyCacheDAO
from src.db.fund.fund_history_dao import FundHistoryDAO
from src.db.fund.fund_industry_dao import FundIndustryDAO
from src.db.fund.fund_intraday_dao import FundIntradayCacheDAO

__all__ = [
    "CacheMetadataDAO",
    "FundHistoryDAO",
    "FundIntradayCacheDAO",
    "FundDailyCacheDAO",
    "FundBasicInfoDAO",
    "FundIndustryDAO",
]
