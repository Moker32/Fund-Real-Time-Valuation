"""
基金 API 路由 - 向后兼容垫片

此文件是 api/routes/funds/ 子包的向后兼容垫片。
新代码请直接从子包导入：
    from api.routes.funds import router

旧导入路径（此文件）仍然可用：
    from api.routes.funds import router
"""

# 重新导出所有内容，保持旧导入路径兼容
from api.routes.funds import (
    _calculate_estimate_change,
    _check_is_holding,
    _get_fund123_source,
    _get_fund_history_source,
    _is_qdii_fund,
    _is_trading_hours,
    build_fund_response,
    funds_data,
    funds_holdings,
    funds_watchlist,
    get_basic_info_db,
    router,
)

__all__ = [
    "router",
    "funds_data",
    "funds_watchlist",
    "funds_holdings",
    "build_fund_response",
    "get_basic_info_db",
    "_calculate_estimate_change",
    "_check_is_holding",
    "_get_fund123_source",
    "_get_fund_history_source",
    "_is_qdii_fund",
    "_is_trading_hours",
]
