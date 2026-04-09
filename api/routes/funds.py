"""
基金 API 路由
提供基金相关的 REST API 端点
"""

import asyncio
import logging
from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from typing_extensions import TypedDict

from src.config.manager import ConfigManager
from src.config.models import Fund, FundList, Holding
from src.datasources.base import DataSourceType
from src.datasources.fund_source import TiantianFundDataSource, get_basic_info_db
from src.datasources.manager import DataSourceManager
from src.datasources.trading_calendar_source import Market, TradingCalendarSource

if TYPE_CHECKING:
    from src.datasources.fund_source import FundHistorySource

from ..dependencies import ConfigManagerDependency, DataSourceDependency
from ..models import (
    AddFundRequest,
    ErrorResponse,
    FundDetailResponse,
    FundEstimateResponse,
    FundIntradayResponse,
    FundResponse,
    OperationResponse,
    WatchlistItem,
    WatchlistResponse,
)


class FundListData(TypedDict):
    """基金列表响应数据结构"""

    funds: list[dict]
    total: int
    timestamp: str
    progress: int | None  # 加载进度 0-100


router = APIRouter(prefix="/api/funds", tags=["基金"])

logger = logging.getLogger(__name__)


@router.get(
    "/search",
    summary="搜索基金",
    description="本地搜索基金，搜索不到时返回空列表（前端可选择是否降级到外部API）",
    responses={
        200: {"description": "搜索成功"},
    },
)
async def search_funds(
    q: str | None = Query(
        None, min_length=1, max_length=20, description="搜索关键词（基金代码或名称）"
    ),
    limit: int = Query(20, ge=1, le=100, description="返回结果数量"),
) -> dict:
    """
    本地搜索基金

    优先从本地数据库搜索，响应速度快。
    """
    if not q:
        return {"funds": [], "total": 0, "source": "local"}

    from src.db.database import DatabaseManager, FundBasicInfoDAO

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

    return {
        "funds": funds,
        "total": len(funds),
        "source": "local",
    }


# 交易日历源单例（用于判断是否交易时段）
_trading_calendar_source: TradingCalendarSource | None = None


def _get_trading_calendar_source() -> TradingCalendarSource:
    """获取交易日历源单例"""
    global _trading_calendar_source
    if _trading_calendar_source is None:
        _trading_calendar_source = TradingCalendarSource()
    return _trading_calendar_source


def _is_trading_hours() -> bool:
    """检查当前是否为交易时段

    先检查是否是交易日（节假日检查），再检查是否在交易时段内。
    如果获取交易日历失败，默认返回 False（非交易时段）。
    """
    try:
        calendar = _get_trading_calendar_source()

        # 首先检查是否是交易日
        if not calendar.is_trading_day(Market.CHINA):
            return False

        # 再检查是否在交易时段内
        result = calendar.is_within_trading_hours(Market.CHINA)
        return result.get("status") == "open"
    except Exception as e:
        logger.warning(f"检查交易时段失败: {e}")
        return False


@lru_cache
def _get_fund_history_source() -> "FundHistorySource":
    """获取基金历史数据源实例（缓存）"""
    from src.datasources.fund_source import FundHistorySource

    return FundHistorySource()


@lru_cache
def _get_tiantian_source() -> TiantianFundDataSource:
    """获取天天基金数据源实例（缓存）"""
    return TiantianFundDataSource()


def _is_qdii_fund(code: str) -> bool:
    """检查基金是否为 QDII 基金或投资海外的 FOF

    QDII 基金和投资海外的 FOF 基金不支持日内分时数据，
    因为它们投资海外市场，净值更新延迟。

    判断逻辑与 src/datasources/fund_source.py 中的 _has_real_time_estimate() 保持一致。

    Args:
        code: 基金代码

    Returns:
        bool: 是否为 QDII 基金或投资海外的 FOF
    """
    try:
        basic_info = get_basic_info_db(code)
        if not basic_info:
            logger.debug(f"基金 {code} 基本信息不存在，无法判断是否为 QDII")
            return False

        # 统一转换为大写进行比较，确保大小写不一致时也能正确识别
        fund_type = (basic_info.get("type") or "").upper()
        fund_name = basic_info.get("name") or ""

        # QDII 基金不支持日内分时数据（包括 QDII-商品、QDII-股票等子类型）
        if fund_type.startswith("QDII"):
            return True

        # FOF 基金需要进一步判断是否投资海外（精确匹配类型）
        if fund_type == "FOF":
            name_upper = fund_name.upper()
            # QDII-FOF 或投资海外的 FOF 不支持日内分时数据
            if "QDII" in name_upper or "海外" in fund_name or "全球" in fund_name:
                return True

        return False
    except Exception as e:
        logger.warning(f"检查基金类型失败: {code} - {e}")
        return False


def _check_is_holding(code: str, config_manager: ConfigManager) -> bool:
    """检查基金是否为持仓

    Args:
        code: 基金代码

    Returns:
        bool: 是否持有
    """
    try:
        fund_list = config_manager.load_funds()
        return code in {h.code for h in fund_list.holdings}
    except Exception as e:
        logger.warning(f"加载持仓信息失败: {code} - {e}")
        return False


def get_default_fund_codes(config_manager: ConfigManager) -> list[str]:
    """获取默认基金代码列表"""
    fund_list: FundList = config_manager.load_funds()
    codes = fund_list.get_all_codes()
    if codes:
        return codes
    return []


def _calculate_estimate_change(unit_net: float | None, estimate_net: float | None) -> float | None:
    """计算估算涨跌额

    Args:
        unit_net: 单位净值
        estimate_net: 估算净值

    Returns:
        估算涨跌额，如果无法计算则返回 None
    """
    if unit_net is not None and estimate_net is not None and unit_net != 0:
        return round(estimate_net - unit_net, 4)
    return None


def build_fund_response(data: dict, source: str = "", is_holding: bool = False) -> dict:
    """构建基金响应数据

    使用 model_validate 进行数据验证，确保数据完整性
    """
    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = _calculate_estimate_change(unit_net, estimate_net)

    # 使用 model_validate 进行验证 (修复: 不再绕过验证)
    # 数据使用 alias 名称 (snake_case) 以匹配字段定义
    validated = FundResponse.model_validate(
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
            "qdii_estimate_change_percent": data.get("qdii_estimate_change_percent"),
            "market_status": data.get("market_status"),
            "underlying_index": data.get("underlying_index", []),
            "interval_returns": data.get("interval_returns"),
            "peer_rank": data.get("peer_rank"),
            "manager": data.get("manager"),
        }
    )

    # 设置计算属性和额外字段
    validated.estimateChange = estimate_change
    validated.source = source
    validated.isHolding = is_holding

    return validated.model_dump()


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
    """
    获取基金列表

    Args:
        codes: 可选的基金代码列表，逗号分隔
        manager: 数据源管理器依赖

    Returns:
        FundListData: 包含基金列表、总数量和时间戳的字典
    """
    current_time = datetime.now().isoformat() + "Z"

    # 加载持仓信息
    fund_list = config_manager.load_funds()
    holding_codes = {h.code for h in fund_list.holdings}

    # 如果指定了基金代码
    if codes:
        fund_codes = [c.strip() for c in codes.split(",") if c.strip()]
        if not fund_codes:
            return {"funds": [], "total": 0, "timestamp": current_time, "progress": 0}

        # 构建参数列表，每个元素是字典格式
        params_list = [{"args": [code]} for code in fund_codes]
        results = await manager.fetch_batch(DataSourceType.FUND, params_list)
        funds = []
        failed_count = 0
        for result in results:
            if result.success and result.data:
                is_holding = result.data.get("fund_code") in holding_codes
                funds.append(build_fund_response(result.data, result.source, is_holding))
            else:
                # 记录失败的基金代码
                fund_code = (
                    result.metadata.get("fund_code", "unknown") if result.metadata else "unknown"
                )
                logger.warning(f"基金获取失败: {fund_code} - {result.error}")
                failed_count += 1

        if failed_count > 0:
            logger.info(f"批量获取基金完成: 成功 {len(funds)}, 失败 {failed_count}")

        return {"funds": funds, "total": len(funds), "timestamp": current_time, "progress": 100}

    # 没有指定 codes 时，使用默认基金代码获取真实数据
    fund_codes = get_default_fund_codes(config_manager)

    # 构建参数列表
    params_list = [{"args": [code]} for code in fund_codes]
    results = await manager.fetch_batch(DataSourceType.FUND, params_list)
    funds = []
    failed_count = 0
    for result in results:
        if result.success and result.data:
            is_holding = result.data.get("fund_code") in holding_codes
            funds.append(build_fund_response(result.data, result.source, is_holding))
        else:
            # 记录失败的基金代码
            fund_code = (
                result.metadata.get("fund_code", "unknown") if result.metadata else "unknown"
            )
            logger.warning(f"基金获取失败: {fund_code} - {result.error}")
            failed_count += 1

    if failed_count > 0:
        logger.info(f"批量获取基金完成: 成功 {len(funds)}, 失败 {failed_count}")

    return {"funds": funds, "total": len(funds), "timestamp": current_time, "progress": 100}


# ==================== 自选相关路由 ====================
# 注意：这些路由必须在 /{code} 之前定义，否则会被 /{code} 路由匹配


@router.get(
    "/watchlist",
    response_model=WatchlistResponse,
    summary="获取自选基金列表",
    description="获取当前用户的自选基金列表",
    responses={
        200: {"description": "获取成功"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_watchlist(
    config_manager: ConfigManager = Depends(ConfigManagerDependency()),
) -> WatchlistResponse:
    """
    获取自选基金列表

    Returns:
        WatchlistResponse: 自选基金列表
    """
    fund_list = config_manager.load_funds()

    watchlist_data = [
        WatchlistItem(code=f.code, name=f.name, isHolding=fund_list.is_holding(f.code))
        for f in fund_list.watchlist
    ]

    return WatchlistResponse(
        success=True,
        watchlist=watchlist_data,
        total=len(watchlist_data),
    )


@router.post(
    "/watchlist",
    response_model=OperationResponse,
    summary="添加自选基金",
    description="将基金添加到自选列表",
    responses={
        200: {"description": "添加成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def add_to_watchlist(
    request: AddFundRequest,
    manager: DataSourceManager = Depends(DataSourceDependency()),
    config_manager: ConfigManager = Depends(ConfigManagerDependency()),
) -> OperationResponse:
    """
    添加基金到自选列表

    Args:
        request: 添加基金请求
        manager: 数据源管理器依赖

    Returns:
        OperationResponse: 添加结果
    """
    # 验证基金是否存在
    result = await manager.fetch(DataSourceType.FUND, request.code)
    if not result.success:
        error_msg = result.error or "未知错误"
        raise HTTPException(
            status_code=404 if "不存在" in error_msg else 400,
            detail=error_msg,
        )

    # 获取基金名称（如果请求中没有提供）
    fund_name = request.name
    if not fund_name and result.data:
        fund_name = result.data.get("name", "")

    # 添加到自选列表
    fund = Fund(code=request.code, name=fund_name)
    config_manager.add_watchlist(fund)

    # 添加成功后，触发新基金数据预热（非阻塞）
    asyncio.create_task(_prewarm_added_fund(request.code))

    return OperationResponse(
        success=True,
        message=f"基金 {request.code} 已添加到自选",
    )


@router.delete(
    "/watchlist/{code}",
    response_model=OperationResponse,
    summary="删除自选基金",
    description="从自选列表中移除基金",
    responses={
        200: {"description": "删除成功"},
        404: {"model": ErrorResponse, "description": "基金不在自选列表中"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def remove_from_watchlist(
    code: str, config_manager: ConfigManager = Depends(ConfigManagerDependency())
) -> OperationResponse:
    """
    从自选列表中移除基金

    Args:
        code: 基金代码 (6位数字)

    Returns:
        OperationResponse: 删除结果
    """
    # config_manager provided via DI

    # 检查是否在自选列表中
    fund_list = config_manager.load_funds()
    if not fund_list.is_watching(code):
        raise HTTPException(
            status_code=404,
            detail=f"基金 {code} 不在自选列表中",
        )

    # 从自选列表中移除
    config_manager.remove_watchlist(code)

    # 如果该基金也在持有列表中，同时从持有列表中移除
    if fund_list.is_holding(code):
        config_manager.remove_holding(code)

    # 移除成功后，清理相关缓存
    asyncio.create_task(_cleanup_removed_fund(code))

    return OperationResponse(
        success=True,
        message=f"基金 {code} 已从自选移除",
    )


# ==================== 基金详情路由 ====================


@router.get(
    "/{code}",
    # response_model=FundDetailResponse,  # 移除 response_model，使用手动序列化
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
    """
    获取基金详情

    Args:
        code: 基金代码 (6位数字)
        manager: 数据源管理器依赖

    Returns:
        FundDetailResponse: 基金详情
    """

    result = await manager.fetch(DataSourceType.FUND, code)

    if not result.success or not result.data:
        error_msg = result.error or "未知错误"
        raise HTTPException(
            status_code=404 if "不存在" in error_msg else 500,
            detail=error_msg,
        )

    data = result.data

    # 计算 estimateChange (估算涨跌额)
    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = _calculate_estimate_change(unit_net, estimate_net)

    # 检查是否持仓
    is_holding = _check_is_holding(code, config_manager)

    # 使用 model_validate 进行验证
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

    # 设置计算属性和额外字段
    validated.estimateChange = estimate_change
    validated.source = result.source
    validated.isHolding = is_holding

    return validated.model_dump()


@router.get(
    "/{code}/estimate",
    # response_model=FundEstimateResponse,  # 移除 response_model，使用手动序列化
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
    """
    获取基金估值

    交易时段不使用缓存，直接从数据源获取实时数据。
    非交易时段使用缓存以减少 API 调用。

    Args:
        code: 基金代码 (6位数字)
        manager: 数据源管理器依赖

    Returns:
        FundEstimateResponse: 基金估值信息
    """
    # 交易时段不使用缓存，确保获取实时数据
    use_cache = not _is_trading_hours()
    result = await manager.fetch(DataSourceType.FUND, code, use_cache=use_cache)

    if not result.success or not result.data:
        error_msg = result.error or "未知错误"
        raise HTTPException(
            status_code=404 if "不存在" in error_msg else 500,
            detail=error_msg,
        )

    data = result.data

    # 计算 estimateChange (估算涨跌额)
    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = _calculate_estimate_change(unit_net, estimate_net)

    # 检查是否持仓
    is_holding = _check_is_holding(code, config_manager)

    # 使用 model_validate 进行验证
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

    # 设置计算属性和额外字段
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
    days: int = Query(
        365, ge=7, le=1825, description="时间周期（天数），可选值: 7, 30, 90, 180, 365, 1095, 1825"
    ),
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """
    获取基金历史净值

    Args:
        code: 基金代码 (6位数字)
        days: 时间周期（天数），可选值: 7, 30, 90, 180, 365, 1095(近三年), 1825(近五年)
        manager: 数据源管理器依赖

    Returns:
        dict: 包含历史净值数据的字典
    """
    # Map days to period string
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
        raise HTTPException(
            status_code=404 if "不存在" in error_msg else 500,
            detail=error_msg,
        )

    return result.data


@router.get(
    "/{code}/intraday",
    response_model=FundIntradayResponse,
    summary="获取基金日内分时数据",
    description="根据基金代码获取天天基金接口的完整日内分时数据",
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
    """
    获取基金日内分时数据

    交易时段不使用缓存，直接从数据源获取实时数据。
    非交易时段使用缓存以减少 API 调用。

    Args:
        code: 基金代码 (6位数字)
        manager: 数据源管理器依赖

    Returns:
        FundIntradayResponse: 基金日内分时数据
    """
    # 交易时段不使用缓存，确保获取实时数据
    use_cache = not _is_trading_hours()
    tiantian_source = _get_tiantian_source()
    result = await tiantian_source.fetch_intraday(code, use_cache=use_cache)

    if not result.success or result.data is None:
        error_msg = result.error or "未知错误"
        raise HTTPException(
            status_code=404 if "不存在" in error_msg else 500,
            detail=error_msg,
        )

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
    """
    获取指定日期的基金日内分时数据（从缓存）

    Args:
        code: 基金代码 (6位数字)
        date: 日期 (YYYY-MM-DD 格式)
        manager: 数据源管理器依赖

    Returns:
        FundIntradayResponse: 基金日内分时数据
    """
    # 首先检查是否为 QDII 基金或投资海外的 FOF
    # 这类基金不支持日内分时数据，因为投资海外市场，净值更新延迟
    if _is_qdii_fund(code):
        raise HTTPException(
            status_code=400,
            detail="QDII 基金不支持日内分时数据，因其投资海外市场，净值更新延迟",
        )

    fund123_source = _get_tiantian_source()
    result = await fund123_source.fetch_intraday_by_date(code, date)

    if not result.success or result.data is None:
        error_msg = result.error or "数据不存在"
        raise HTTPException(
            status_code=404 if "不存在" in error_msg else 500,
            detail=error_msg,
        )

    return FundIntradayResponse(
        fund_code=result.data.get("fund_code", code),
        name=result.data.get("name", ""),
        date=result.data.get("date", ""),
        data=result.data.get("data", []),
        count=result.data.get("count", 0),
        source=result.source,
    ).model_dump()


@router.put(
    "/{code}/holding",
    response_model=OperationResponse,
    summary="标记/取消持有基金",
    description="将基金标记为持有或取消持有",
    responses={
        200: {"description": "操作成功"},
        400: {"model": ErrorResponse, "description": "请求参数错误"},
        404: {"model": ErrorResponse, "description": "基金不存在"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def toggle_holding(
    code: str,
    holding: bool = Query(..., description="True 表示标记为持有，False 表示取消持有"),
    manager: DataSourceManager = Depends(DataSourceDependency()),
    config_manager: ConfigManager = Depends(ConfigManagerDependency()),
) -> OperationResponse:
    """
    标记/取消持有基金

    Args:
        code: 基金代码
        holding: 是否持有
        manager: 数据源管理器依赖

    Returns:
        OperationResponse: 操作结果
    """
    fund_list = config_manager.load_funds()

    if holding:
        # 标记为持有
        if fund_list.is_holding(code):
            return OperationResponse(
                success=True,
                message=f"基金 {code} 已是持有状态",
            )

        # 验证基金是否存在
        result = await manager.fetch(DataSourceType.FUND, code)
        if not result.success:
            error_msg = result.error or "未知错误"
            raise HTTPException(
                status_code=404 if "不存在" in error_msg else 400,
                detail=error_msg,
            )

        fund_name = result.data.get("name", "") if result.data else ""

        # 如果在自选列表中，获取名称
        if not fund_name:
            for f in fund_list.watchlist:
                if f.code == code:
                    fund_name = f.name
                    break

        new_holding = Holding(code=code, name=fund_name)
        config_manager.add_holding(new_holding)

        # 标记为持有后，触发基金数据预热（非阻塞）
        asyncio.create_task(_prewarm_added_fund(code))

        return OperationResponse(
            success=True,
            message=f"基金 {code} 已标记为持有",
        )
    else:
        # 取消持有
        if not fund_list.is_holding(code):
            return OperationResponse(
                success=True,
                message=f"基金 {code} 不在持有列表中",
            )

        config_manager.remove_holding(code)

        # 取消持有后，清理相关缓存
        asyncio.create_task(_cleanup_removed_fund(code))

        return OperationResponse(
            success=True,
            message=f"基金 {code} 已取消持有",
        )


async def _prewarm_added_fund(fund_code: str):
    """
    预热新添加的基金数据

    在添加基金到自选后触发预热，将数据写入缓存供后续请求使用。
    这是非阻塞操作，在后台执行。

    Args:
        fund_code: 基金代码
    """
    try:
        from src.datasources.cache_warmer import prewarm_new_fund

        await prewarm_new_fund(fund_code, timeout=30.0)
    except Exception as e:
        logger.warning(f"预热基金数据失败: {fund_code} - {e}")


async def _cleanup_removed_fund(fund_code: str):
    """
    清理移除的基金缓存

    在从自选移除基金后清理相关缓存条目。
    这是非阻塞操作，在后台执行。

    Args:
        fund_code: 基金代码
    """
    try:
        from src.datasources.cache_warmer import cleanup_fund_cache

        await cleanup_fund_cache(fund_code)
    except Exception as e:
        logger.warning(f"清理基金缓存失败: {fund_code} - {e}")
