"""基金缓存助手模块

包含全局缓存实例和 DAO 单例获取器。
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from src.db.database import (
    DatabaseManager,
    FundBasicInfoDAO,
    FundDailyCacheDAO,
    FundIntradayCacheDAO,
    IndexIntradayCacheDAO,
)

from ..dual_cache import DualLayerCache

if TYPE_CHECKING:
    from src.datasources.trading_calendar_source import TradingCalendarSource

logger = logging.getLogger(__name__)

# 全局缓存实例（单例模式）
_fund_cache: DualLayerCache | None = None
# 基金基本信息缓存（全局 akshare 调用结果）
_fund_info_cache: dict[str, tuple[dict, float]] = {}  # {code: (info, timestamp)}
_fund_info_cache_ttl = 3600  # 1小时缓存
# 基金信息缓存命中率统计
_fund_info_hit_count = 0
_fund_info_miss_count = 0
# 日内分时缓存 DAO 单例
_intraday_cache_dao: FundIntradayCacheDAO | None = None
# 每日缓存 DAO 单例
_daily_cache_dao: FundDailyCacheDAO | None = None
# 基金基本信息缓存 DAO 单例
_basic_info_dao: FundBasicInfoDAO | None = None
# 指数日内分时缓存 DAO 单例
_index_intraday_cache_dao: IndexIntradayCacheDAO | None = None
# 交易日历源单例（用于净值缓存有效性判断）
_trading_calendar_source: "TradingCalendarSource | None" = None


def get_fund_cache() -> DualLayerCache:
    """获取基金缓存单例"""
    global _fund_cache
    if _fund_cache is None:
        cache_dir = Path.home() / ".fund-tui" / "cache" / "funds"
        _fund_cache = DualLayerCache(
            cache_dir=cache_dir,
            memory_ttl=0,  # 禁用内存缓存
            file_ttl=0,  # 禁用文件缓存
            max_memory_items=100,
        )
    return _fund_cache


def get_intraday_cache_dao() -> FundIntradayCacheDAO:
    """获取日内分时缓存 DAO 单例"""
    global _intraday_cache_dao
    if _intraday_cache_dao is None:
        db_manager = DatabaseManager()
        _intraday_cache_dao = FundIntradayCacheDAO(db_manager)
    return _intraday_cache_dao


def get_daily_cache_dao() -> FundDailyCacheDAO:
    """获取每日缓存 DAO 单例"""
    global _daily_cache_dao
    if _daily_cache_dao is None:
        db_manager = DatabaseManager()
        # 设置 1 小时缓存过期时间（3600秒）
        # 延长缓存时间以减少 API 调用，提高性能
        # 历史净值数据不会频繁变化，较长的缓存时间是安全的
        _daily_cache_dao = FundDailyCacheDAO(db_manager, cache_ttl=3600)
    return _daily_cache_dao


def get_basic_info_dao() -> FundBasicInfoDAO:
    """获取基金基本信息 DAO 单例"""
    global _basic_info_dao
    if _basic_info_dao is None:
        db_manager = DatabaseManager()
        _basic_info_dao = FundBasicInfoDAO(db_manager)
    return _basic_info_dao


def get_index_intraday_cache_dao() -> IndexIntradayCacheDAO:
    """获取指数日内分时缓存 DAO 单例"""
    global _index_intraday_cache_dao
    if _index_intraday_cache_dao is None:
        db_manager = DatabaseManager()
        _index_intraday_cache_dao = IndexIntradayCacheDAO(db_manager, cache_ttl=60)
    return _index_intraday_cache_dao
