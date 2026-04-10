"""
基金 API 路由模块

提供基金相关的 REST API 端点：
- funds_data: 基金数据 (搜索、列表、详情、估值、历史、分时)
- funds_watchlist: 自选管理 (CRUD)
- funds_holdings: 持仓管理

向后兼容导出:
    from api.routes.funds import router  # 导出组合后的路由
    from api.routes.funds import _calculate_estimate_change  # 辅助函数
"""

from fastapi import APIRouter

# 先导入 get_basic_info_db，避免循环导入时找不到
from src.datasources.fund_source import get_basic_info_db

# 导入所有子模块路由
from . import funds_data, funds_holdings, funds_watchlist

# 导入辅助函数供测试使用
from .funds_data import (
    _calculate_estimate_change,
    _check_is_holding,
    _get_fund123_source,
    _get_fund_history_source,
    _is_qdii_fund,
    _is_trading_hours,
    build_fund_response,
)

# 创建组合路由（不含 prefix，由子路由提供）
router = APIRouter()

# 添加所有子路由（每个子路由自带 /api/funds prefix）
router.include_router(funds_data.router)
router.include_router(funds_watchlist.router)
router.include_router(funds_holdings.router)

__all__ = [
    "router",
    "funds_data",
    "funds_watchlist",
    "funds_holdings",
    # 辅助函数（向后兼容）
    "_calculate_estimate_change",
    "_check_is_holding",
    "_get_fund123_source",
    "_get_fund_history_source",
    "_is_qdii_fund",
    "_is_trading_hours",
    "build_fund_response",
    # get_basic_info_db 供测试 mock 使用
    "get_basic_info_db",
]
