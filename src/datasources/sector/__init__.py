"""
板块数据源模块

提供多种板块数据源:
- 新浪财经行业板块 (SinaSectorDataSource)
- 东方财富直连 API (EastMoneyDirectSource)
- 东方财富板块 akshare 接口 (EastMoneySectorSource, EastMoneySectorDataSource)
- 板块详情/成份股 (EastMoneyIndustryDetailSource, EastMoneyConceptDetailSource)
- 资金流向 (FundFlowConceptSource, FundFlowIndustrySource)
- 板块聚合器 (SectorDataAggregator)

工具函数:
- get_last_trading_day() - 获取最近交易日
- is_trading_day() - 判断是否为交易日
"""

from .aggregator import SectorDataAggregator
from .akshare_em_source import EastMoneySectorDataSource, EastMoneySectorSource, ThsSectorSource
from .detail_source import EastMoneyConceptDetailSource, EastMoneyIndustryDetailSource
from .eastmoney_source import EastMoneyDirectSource
from .fund_flow_source import FundFlowConceptSource, FundFlowIndustrySource
from .sector_helpers import get_last_trading_day, is_trading_day
from .sina_source import SinaSectorDataSource

__all__ = [
    # 新浪板块
    "SinaSectorDataSource",
    # 东方财富直连
    "EastMoneyDirectSource",
    # 东方财富 akshare
    "EastMoneySectorSource",
    "EastMoneySectorDataSource",
    # 同花顺
    "ThsSectorSource",
    # 板块详情
    "EastMoneyIndustryDetailSource",
    "EastMoneyConceptDetailSource",
    # 资金流向
    "FundFlowConceptSource",
    "FundFlowIndustrySource",
    # 聚合器
    "SectorDataAggregator",
    # 工具函数
    "get_last_trading_day",
    "is_trading_day",
]
