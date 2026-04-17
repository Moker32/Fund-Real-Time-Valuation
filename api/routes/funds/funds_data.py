"""
基金数据 API 路由
提供基金数据相关的 REST API 端点
"""

import logging
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from typing_extensions import TypedDict

from src.config.manager import ConfigManager
from src.datasources.base import DataSourceType
from src.datasources.fund_source import Fund123DataSource
from src.datasources.manager import DataSourceManager
from src.datasources.trading_calendar_source import Market, TradingCalendarSource

if TYPE_CHECKING:
    from src.datasources.fund_source import FundHistorySource

from ...dependencies import (
    ConfigManagerDependency,
    DataSourceDependency,
)
from ...models import (
    ErrorResponse,
    FundDetailResponse,
    FundEstimateResponse,
    FundIntradayResponse,
    FundResponse,
)


class FundListData(TypedDict):
    """基金列表响应数据结构"""

    funds: list[dict]
    total: int
    timestamp: str
    progress: int | None


router = APIRouter(prefix="/api/funds", tags=["基金"])

logger = logging.getLogger(__name__)


# ==================== 辅助函数 ====================


def _get_trading_calendar_source() -> TradingCalendarSource:
    """获取交易日历源实例（通过依赖注入）"""
    from ...dependencies import get_trading_calendar_source as get_calendar

    return get_calendar()


@lru_cache
def _is_trading_hours_cached() -> bool:
    """检查当前是否为交易时段（带缓存）"""
    try:
        calendar = _get_trading_calendar_source()
        if not calendar.is_trading_day(Market.CHINA):
            return False
        result = calendar.is_within_trading_hours(Market.CHINA)
        return result.get("status") == "open"
    except Exception as e:
        logger.warning(f"检查交易时段失败: {e}")
        return False


def _is_trading_hours() -> bool:
    """检查当前是否为交易时段（使用缓存）"""
    return _is_trading_hours_cached()


@lru_cache
def _get_fund_history_source() -> "FundHistorySource":
    """获取基金历史数据源实例（缓存）"""
    from src.datasources.fund_source import FundHistorySource

    return FundHistorySource()


@lru_cache
def _get_fund123_source() -> Fund123DataSource:
    """获取 Fund123 数据源实例（缓存）"""
    return Fund123DataSource()


def _is_qdii_fund(code: str) -> bool:
    """检查基金是否为 QDII 基金或投资海外的 FOF"""
    try:
        # Import from api.routes.funds to support mocking in tests
        from api.routes.funds import get_basic_info_db

        basic_info = get_basic_info_db(code)
        if not basic_info:
            logger.debug(f"基金 {code} 基本信息不存在，无法判断是否为 QDII")
            return False

        fund_type = (basic_info.get("type") or "").upper()
        fund_name = basic_info.get("name") or ""

        if fund_type.startswith("QDII"):
            return True

        if fund_type == "FOF":
            name_upper = fund_name.upper()
            if "QDII" in name_upper or "海外" in fund_name or "全球" in fund_name:
                return True

        return False
    except Exception as e:
        logger.warning(f"检查基金类型失败: {code} - {e}")
        return False


def _check_is_holding(code: str, config_manager: ConfigManager) -> bool:
    """检查基金是否为持仓"""
    try:
        fund_list = config_manager.load_funds()
        return code in {h.code for h in fund_list.holdings}
    except Exception as e:
        logger.warning(f"加载持仓信息失败: {code} - {e}")
        return False


def _get_default_fund_codes(config_manager: ConfigManager) -> list[str]:
    """获取默认基金代码列表"""
    from src.config.models import FundList

    fund_list: FundList = config_manager.load_funds()
    codes = fund_list.get_all_codes()
    if codes:
        return codes
    return []


def _calculate_estimate_change(unit_net: float | None, estimate_net: float | None) -> float | None:
    """计算估算涨跌额"""
    if unit_net is not None and estimate_net is not None and unit_net != 0:
        return round(estimate_net - unit_net, 4)
    return None


def _validate_estimate_change_percent(
    unit_net: float | None,
    estimate_net: float | None,
    provided_percent: float | None,
    fund_code: str = "",
    fund_type: str | None = None,
    logger=None,
) -> float | None:
    """
    校验数据源提供的估算增长率是否与计算值一致
    如果不一致，返回计算值（修正）
    如果一致，返回原值
    容许 0.01% 的浮点数误差

    注意：QDII 基金使用 prev_net_value 而非 unit_net_value 计算，
    校验时需要跳过。
    """
    # QDII 基金使用 prev_net_value 估算，校验时跳过
    if fund_type == "QDII":
        return provided_percent

    if unit_net is None or estimate_net is None or unit_net == 0 or provided_percent is None:
        return provided_percent

    calculated_percent = (estimate_net - unit_net) / unit_net * 100
    diff = abs(calculated_percent - provided_percent)

    if diff > 0.01:  # 误差超过 0.01% 认为有问题
        if logger:
            logger.warning(
                "基金 %s 估算增长率不一致: 数据源=%.4f%%, 计算值=%.4f%%, 差异=%.4f%%",
                fund_code,
                provided_percent,
                calculated_percent,
                diff,
                extra={
                    "fund_code": fund_code,
                    "provided_percent": provided_percent,
                    "calculated_percent": calculated_percent,
                    "diff_percent": diff,
                    "event": "estimate_change_mismatch",
                },
            )
        return round(calculated_percent, 4)

    return provided_percent


def build_fund_response(
    data: dict, source: str = "", is_holding: bool = False, logger=None
) -> dict:
    """构建基金响应数据"""
    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = _calculate_estimate_change(unit_net, estimate_net)

    # 校验估算增长率是否与计算值一致
    provided_percent = data.get("estimated_growth_rate")
    fund_code = data.get("fund_code", "")
    validated_percent = _validate_estimate_change_percent(
        unit_net, estimate_net, provided_percent, fund_code, data.get("type"), logger
    )

    validated = FundResponse.model_validate(
        {
            "fund_code": fund_code,
            "name": data.get("name", ""),
            "type": data.get("type"),
            "unit_net_value": unit_net,
            "net_value_date": data.get("net_value_date"),
            "prev_net_value": data.get("prev_net_value"),
            "prev_net_value_date": data.get("prev_net_value_date"),
            "estimated_net_value": estimate_net,
            "estimated_growth_rate": validated_percent,
            "estimate_time": data.get("estimate_time"),
            "has_real_time_estimate": data.get("has_real_time_estimate", True),
        }
    )

    validated.estimateChange = estimate_change
    validated.source = source
    validated.isHolding = is_holding

    return validated.model_dump()


# ==================== 搜索和列表 ====================


@router.get(
    "/search",
    summary="搜索基金",
    description="本地搜索基金，搜索不到时返回空列表（前端可选择是否降级到外部API）",
    responses={200: {"description": "搜索成功"}},
)
async def search_funds(
    q: str | None = Query(
        None, min_length=1, max_length=20, description="搜索关键词（基金代码或名称）"
    ),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量"),
) -> dict:
    """本地搜索基金"""
    if not q:
        return {"funds": [], "total": 0, "source": "local"}

    from src.db.database import DatabaseManager
    from src.db.fund import FundBasicInfoDAO

    dao = FundBasicInfoDAO(DatabaseManager())
    results = dao.search(q, limit=limit)

    funds = [
        {
            "code": f.code,
            "name": f.short_name or f.name,
            "type": f.type,
        }
        for f in results
    ]

    return {"funds": funds, "total": len(funds), "source": "local"}


@router.get(
    "",
    response_model=FundListData,
    summary="获取基金列表",
    description="获取所有已注册基金数据源的基金信息",
    responses={
        200: {"description": "成功获取基金列表"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_funds_list(
    codes: str | None = None,
    manager: DataSourceManager = Depends(DataSourceDependency()),
    config_manager: ConfigManager = Depends(ConfigManagerDependency()),
) -> FundListData:
    """获取基金列表"""
    current_time = datetime.now().isoformat() + "Z"

    fund_list = config_manager.load_funds()
    holding_codes = {h.code for h in fund_list.holdings}

    if codes:
        fund_codes = [c.strip() for c in codes.split(",") if c.strip()]
        if not fund_codes:
            return {"funds": [], "total": 0, "timestamp": current_time, "progress": 0}

        params_list = [{"args": [code]} for code in fund_codes]
        results = await manager.fetch_batch(DataSourceType.FUND, params_list)
        funds = []
        failed_count = 0
        for result in results:
            if result.success and result.data:
                is_holding = result.data.get("fund_code") in holding_codes
                funds.append(build_fund_response(result.data, result.source, is_holding))
            else:
                fund_code = (
                    result.metadata.get("fund_code", "unknown") if result.metadata else "unknown"
                )
                logger.warning(f"基金获取失败: {fund_code} - {result.error}")
                failed_count += 1

        if failed_count > 0:
            logger.info(f"批量获取基金完成: 成功 {len(funds)}, 失败 {failed_count}")

        return {"funds": funds, "total": len(funds), "timestamp": current_time, "progress": 100}

    fund_codes = _get_default_fund_codes(config_manager)

    params_list = [{"args": [code]} for code in fund_codes]
    results = await manager.fetch_batch(DataSourceType.FUND, params_list)
    funds = []
    failed_count = 0
    for result in results:
        if result.success and result.data:
            is_holding = result.data.get("fund_code") in holding_codes
            funds.append(build_fund_response(result.data, result.source, is_holding))
        else:
            fund_code = (
                result.metadata.get("fund_code", "unknown") if result.metadata else "unknown"
            )
            logger.warning(f"基金获取失败: {fund_code} - {result.error}")
            failed_count += 1

    if failed_count > 0:
        logger.info(f"批量获取基金完成: 成功 {len(funds)}, 失败 {failed_count}")

    return {"funds": funds, "total": len(funds), "timestamp": current_time, "progress": 100}


# ==================== 基金详情 ====================


@router.get(
    "/{code}",
    summary="获取基金详情",
    description="根据基金代码获取单个基金的详细信息",
    responses={
        200: {"description": "成功获取基金详情"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_fund_detail(
    code: str,
    manager: DataSourceManager = Depends(DataSourceDependency()),
    config_manager: ConfigManager = Depends(ConfigManagerDependency()),
) -> dict:
    """获取基金详情"""
    from fastapi import HTTPException

    result = await manager.fetch(DataSourceType.FUND, code)

    if not result.success or not result.data:
        error_msg = result.error or "未知错误"
        raise HTTPException(status_code=404 if "不存在" in error_msg else 500, detail=error_msg)

    data = result.data

    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = _calculate_estimate_change(unit_net, estimate_net)
    is_holding = _check_is_holding(code, config_manager)

    validated = FundDetailResponse.model_validate(
        {
            "fund_code": data.get("fund_code", ""),
            "name": data.get("name", ""),
            "type": data.get("type"),
            "unit_net_value": data.get("unit_net_value"),
            "net_value_date": data.get("net_value_date"),
            "prev_net_value": data.get("prev_net_value"),
            "prev_net_value_date": data.get("prev_net_value_date"),
            "estimated_net_value": data.get("estimated_net_value"),
            "estimated_growth_rate": data.get("estimated_growth_rate"),
            "estimate_time": data.get("estimate_time"),
            "has_real_time_estimate": data.get("has_real_time_estimate", True),
        }
    )

    validated.estimateChange = estimate_change
    validated.source = result.source
    validated.isHolding = is_holding

    return validated.model_dump()


@router.get(
    "/{code}/estimate",
    summary="获取基金估值",
    description="根据基金代码获取基金的实时估值信息",
    responses={
        200: {"description": "成功获取基金估值"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_fund_estimate(
    code: str,
    manager: DataSourceManager = Depends(DataSourceDependency()),
    config_manager: ConfigManager = Depends(ConfigManagerDependency()),
) -> dict:
    """获取基金估值"""
    from fastapi import HTTPException

    use_cache = not _is_trading_hours()
    result = await manager.fetch(DataSourceType.FUND, code, use_cache=use_cache)

    if not result.success or not result.data:
        error_msg = result.error or "未知错误"
        raise HTTPException(status_code=404 if "不存在" in error_msg else 500, detail=error_msg)

    data = result.data

    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = _calculate_estimate_change(unit_net, estimate_net)
    is_holding = _check_is_holding(code, config_manager)

    validated = FundEstimateResponse.model_validate(
        {
            "fund_code": data.get("fund_code", ""),
            "name": data.get("name", ""),
            "type": data.get("type"),
            "unit_net_value": data.get("unit_net_value"),
            "net_value_date": data.get("net_value_date"),
            "estimated_net_value": data.get("estimated_net_value"),
            "estimated_growth_rate": data.get("estimated_growth_rate"),
            "estimate_time": data.get("estimate_time"),
            "has_real_time_estimate": data.get("has_real_time_estimate", True),
        }
    )

    validated.estimateChange = estimate_change
    validated.isHolding = is_holding

    return validated.model_dump()


@router.get(
    "/{code}/history",
    response_model=dict,
    summary="获取基金历史净值",
    description="根据基金代码获取基金的历史净值数据",
    responses={
        200: {"description": "成功获取基金历史净值"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_fund_history(
    code: str,
    days: int = Query(365, ge=7, le=1825, description="时间周期（天数）"),
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """获取基金历史净值"""
    from fastapi import HTTPException

    days_to_period = {
        7: "近一周",
        30: "近一月",
        90: "近三月",
        180: "近六月",
        365: "近一年",
        1095: "近三年",
        1825: "近五年",
    }
    period = days_to_period.get(days, "近一年")

    history_source = _get_fund_history_source()
    result = await history_source.fetch(code, period)

    if not result.success or result.data is None:
        error_msg = result.error or "未知错误"
        raise HTTPException(status_code=404 if "不存在" in error_msg else 500, detail=error_msg)

    return result.data


@router.get(
    "/{code}/intraday",
    response_model=FundIntradayResponse,
    summary="获取基金日内分时数据",
    description="根据基金代码获取 fund123.cn 的完整日内分时数据",
    responses={
        200: {"description": "成功获取日内分时数据"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_fund_intraday(
    code: str,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """获取基金日内分时数据"""
    from fastapi import HTTPException

    use_cache = not _is_trading_hours()
    fund123_source = _get_fund123_source()
    result = await fund123_source.fetch_intraday(code, use_cache=use_cache)

    if not result.success or result.data is None:
        error_msg = result.error or "未知错误"
        raise HTTPException(status_code=404 if "不存在" in error_msg else 500, detail=error_msg)

    return FundIntradayResponse(
        fund_code=result.data.get("fund_code", code),
        name=result.data.get("name", ""),
        date=result.data.get("date", ""),
        data=result.data.get("data", []),
        count=result.data.get("count", 0),
        source=result.source,
    ).model_dump()


@router.get(
    "/{code}/intraday/{date}",
    response_model=FundIntradayResponse,
    summary="获取指定日期的基金日内分时数据",
    description="根据基金代码和日期获取历史日内分时数据",
    responses={
        200: {"description": "成功获取日内分时数据"},
        404: {"model": ErrorResponse, "description": "数据不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_fund_intraday_by_date(
    code: str,
    date: str,
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """获取指定日期的基金日内分时数据"""
    from fastapi import HTTPException

    if _is_qdii_fund(code):
        raise HTTPException(
            status_code=400,
            detail="QDII 基金不支持日内分时数据，因其投资海外市场，净值更新延迟",
        )

    fund123_source = _get_fund123_source()
    result = await fund123_source.fetch_intraday_by_date(code, date)

    if not result.success or result.data is None:
        error_msg = result.error or "数据不存在"
        raise HTTPException(status_code=404 if "不存在" in error_msg else 500, detail=error_msg)

    return FundIntradayResponse(
        fund_code=result.data.get("fund_code", code),
        name=result.data.get("name", ""),
        date=result.data.get("date", ""),
        data=result.data.get("data", []),
        count=result.data.get("count", 0),
        source=result.source,
    ).model_dump()


# 导出辅助函数供其他模块使用
__all__ = [
    "router",
    "_is_trading_hours",
    "_get_fund_history_source",
    "_get_fund123_source",
    "_is_qdii_fund",
    "_check_is_holding",
    "_calculate_estimate_change",
    "build_fund_response",
]
