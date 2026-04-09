"""
基金数据源模块 - 兼容性别名

WARNING: 此模块已弃用，请从 src.datasources.fund 导入。

此文件仅用于向后兼容，所有功能已移至 src.datasources.fund 模块。
"""

# 从新的模块重新导出所有公开 API
from src.datasources.fund import (
    TiantianFundDataSource,
    SinaFundDataSource,
    EastMoneyFundDataSource,
    FundHistorySource,
    FundHistoryYFinanceSource,
    Fund123DataSource,
    get_fund_cache,
    get_fund_cache_stats,
    get_intraday_cache_dao,
    get_daily_cache_dao,
    get_basic_info_dao,
    get_basic_info_db,
    save_basic_info_to_db,
    get_full_fund_info,
    get_fund_basic_info,
    _get_fund_type_from_fund_name_em,
    _infer_fund_type_from_name,
    _has_real_time_estimate,
    _get_net_value_date_from_akshare,
    _get_china_market_date,
    _is_after_market_close,
    _get_latest_trading_day,
    _is_net_value_cache_valid,
    _update_net_value_cache,
    CacheLockManager,
    CacheLockTimeoutError,
    CacheResult,
    FundCacheStrategy,
    get_cache_strategy,
    get_fund_data_with_cache,
)

__all__ = [
    "TiantianFundDataSource",
    "SinaFundDataSource",
    "EastMoneyFundDataSource",
    "FundHistorySource",
    "FundHistoryYFinanceSource",
    "Fund123DataSource",
    "get_fund_cache",
    "get_fund_cache_stats",
    "get_intraday_cache_dao",
    "get_daily_cache_dao",
    "get_basic_info_dao",
    "get_basic_info_db",
    "save_basic_info_to_db",
    "get_full_fund_info",
    "get_fund_basic_info",
    "_get_fund_type_from_fund_name_em",
    "_infer_fund_type_from_name",
    "_has_real_time_estimate",
    "_get_net_value_date_from_akshare",
    "_get_china_market_date",
    "_is_after_market_close",
    "_get_latest_trading_day",
    "_is_net_value_cache_valid",
    "_update_net_value_cache",
    "CacheLockManager",
    "CacheLockTimeoutError",
    "CacheResult",
    "FundCacheStrategy",
    "get_cache_strategy",
    "get_fund_data_with_cache",
]
