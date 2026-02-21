"""
基金 API 路由
提供基金相关的 REST API 端点
"""

import asyncio
import logging
from datetime import datetime
from typing import TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query

from src.config.manager import ConfigManager
from src.config.models import Fund, FundList, Holding
from src.datasources.base import DataSourceType
from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency
from ..models import (
    AddFundRequest,
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
    progress: int | None  # 加载进度 0-100


router = APIRouter(prefix="/api/funds", tags=["基金"])

logger = logging.getLogger(__name__)


def _check_is_holding(code: str) -> bool:
    """检查基金是否为持仓

    Args:
        code: 基金代码

    Returns:
        bool: 是否持有
    """
    try:
        config_manager = ConfigManager()
        fund_list = config_manager.load_funds()
        return code in {h.code for h in fund_list.holdings}
    except Exception:
        logger.warning(f"加载持仓信息失败: {code}")
        return False


def get_default_fund_codes() -> list[str]:
    """获取默认基金代码列表"""
    default_funds = [
        "161039",  # 易方达消费行业股票
        "161725",  # 招商中证白酒指数
        "110022",  # 易方达消费行业
        "000015",  # 华夏策略精选混合
        "161032",  # 富国中证新能源汽车指数
    ]

    try:
        config_manager = ConfigManager()
        fund_list: FundList = config_manager.load_funds()
        codes = fund_list.get_all_codes()
        if codes:
            return codes
    except Exception:
        pass

    return default_funds


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
    """构建基金响应数据"""
    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = _calculate_estimate_change(unit_net, estimate_net)

    # 使用 model_construct 绕过 mypy 对 alias 字段的类型检查
    return FundResponse.model_construct(
        code=data.get("fund_code", ""),
        name=data.get("name", ""),
        type=data.get("type"),
        netValue=data.get("unit_net_value"),
        netValueDate=data.get("net_value_date"),
        prevNetValue=data.get("prev_net_value"),
        prevNetValueDate=data.get("prev_net_value_date"),
        estimateValue=data.get("estimated_net_value"),
        estimateChangePercent=data.get("estimated_growth_rate"),
        estimateTime=data.get("estimate_time"),
        estimateChange=estimate_change,
        source=source,
        isHolding=is_holding,
        hasRealTimeEstimate=data.get("has_real_time_estimate", True),
    ).model_dump()


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
) -> FundListData:
    """
    获取基金列表

    Args:
        codes: 可选的基金代码列表，逗号分隔
        manager: 数据源管理器依赖

    Returns:
        FundListData: 包含基金列表、总数量和时间戳的字典
    """
    from src.config.manager import ConfigManager

    current_time = datetime.now().isoformat() + "Z"

    # 加载持仓信息
    config_manager = ConfigManager()
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
    fund_codes = get_default_fund_codes()

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


@router.get(
    "/{code}",
    response_model=FundDetailResponse,
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
    is_holding = _check_is_holding(code)

    # 使用 model_construct 绕过 mypy 对 alias 字段的类型检查
    return FundDetailResponse.model_construct(
        code=data.get("fund_code", ""),
        name=data.get("name", ""),
        type=data.get("type"),
        netValue=data.get("unit_net_value"),
        netValueDate=data.get("net_value_date"),
        estimateValue=data.get("estimated_net_value"),
        estimateChangePercent=data.get("estimated_growth_rate"),
        estimateTime=data.get("estimate_time"),
        estimateChange=estimate_change,
        source=result.source,
        isHolding=is_holding,
        hasRealTimeEstimate=data.get("has_real_time_estimate", True),
    ).model_dump()


@router.get(
    "/{code}/estimate",
    response_model=FundEstimateResponse,
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
) -> dict:
    """
    获取基金估值

    Args:
        code: 基金代码 (6位数字)
        manager: 数据源管理器依赖

    Returns:
        FundEstimateResponse: 基金估值信息
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
    is_holding = _check_is_holding(code)

    # 使用 model_construct 绕过 mypy 对 alias 字段的类型检查
    return FundEstimateResponse.model_construct(
        code=data.get("fund_code", ""),
        name=data.get("name", ""),
        type=data.get("type"),
        estimateValue=data.get("estimated_net_value"),
        estimateChangePercent=data.get("estimated_growth_rate"),
        estimateTime=data.get("estimate_time"),
        netValue=data.get("unit_net_value"),
        netValueDate=data.get("net_value_date"),
        estimateChange=estimate_change,
        isHolding=is_holding,
        hasRealTimeEstimate=data.get("has_real_time_estimate", True),
    ).model_dump()


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
    period: str = "近一年",
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> dict:
    """
    获取基金历史净值

    Args:
        code: 基金代码 (6位数字)
        period: 时间周期，可选值: "近一周", "近一月", "近三月", "近六月", "近一年", "近三年", "近五年", "成立以来"
        manager: 数据源管理器依赖

    Returns:
        dict: 包含历史净值数据的字典
    """
    from src.datasources.fund_source import FundHistorySource

    history_source = FundHistorySource()
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
    """
    获取基金日内分时数据

    Args:
        code: 基金代码 (6位数字)
        manager: 数据源管理器依赖

    Returns:
        FundIntradayResponse: 基金日内分时数据
    """
    from src.datasources.fund_source import Fund123DataSource

    fund123_source = Fund123DataSource()
    result = await fund123_source.fetch_intraday(code)

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
    "/watchlist",
    response_model=dict,
    summary="获取自选基金列表",
    description="获取当前用户的自选基金列表",
    responses={
        200: {"description": "获取成功"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_watchlist() -> dict:
    """
    获取自选基金列表

    Returns:
        dict: 自选基金列表
    """
    config_manager = ConfigManager()
    fund_list = config_manager.load_funds()

    watchlist_data = [
        {"code": f.code, "name": f.name, "isHolding": fund_list.is_holding(f.code)}
        for f in fund_list.watchlist
    ]

    return {
        "success": True,
        "watchlist": watchlist_data,
        "total": len(watchlist_data),
    }


@router.post(
    "/watchlist",
    response_model=dict,
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
) -> dict:
    """
    添加基金到自选列表

    Args:
        request: 添加基金请求
        manager: 数据源管理器依赖

    Returns:
        dict: 添加结果
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
    config_manager = ConfigManager()
    fund = Fund(code=request.code, name=fund_name)
    config_manager.add_watchlist(fund)

    # 添加成功后，触发新基金数据预热（非阻塞）
    asyncio.create_task(_prewarm_added_fund(request.code))

    return {
        "success": True,
        "message": f"基金 {request.code} 已添加到自选",
        "fund": {"code": request.code, "name": fund_name},
    }


@router.put(
    "/{code}/holding",
    response_model=dict,
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
) -> dict:
    """
    标记/取消持有基金

    Args:
        code: 基金代码
        holding: 是否持有
        manager: 数据源管理器依赖

    Returns:
        dict: 操作结果
    """
    from src.config.manager import ConfigManager

    config_manager = ConfigManager()
    fund_list = config_manager.load_funds()

    if holding:
        # 标记为持有
        if fund_list.is_holding(code):
            return {
                "success": True,
                "message": f"基金 {code} 已是持有状态",
            }

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

        return {
            "success": True,
            "message": f"基金 {code} 已标记为持有",
        }
    else:
        # 取消持有
        if not fund_list.is_holding(code):
            return {
                "success": True,
                "message": f"基金 {code} 不在持有列表中",
            }

        config_manager.remove_holding(code)

        # 取消持有后，清理相关缓存
        asyncio.create_task(_cleanup_removed_fund(code))

        return {
            "success": True,
            "message": f"基金 {code} 已取消持有",
        }


@router.delete(
    "/watchlist/{code}",
    response_model=dict,
    summary="删除自选基金",
    description="从自选列表中移除基金",
    responses={
        200: {"description": "删除成功"},
        404: {"model": ErrorResponse, "description": "基金不在自选列表中"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def remove_from_watchlist(code: str) -> dict:
    """
    从自选列表中移除基金

    Args:
        code: 基金代码 (6位数字)

    Returns:
        dict: 删除结果
    """
    config_manager = ConfigManager()

    # 检查是否在自选列表中
    fund_list = config_manager.load_funds()
    if not fund_list.is_watching(code):
        raise HTTPException(
            status_code=404,
            detail=f"基金 {code} 不在自选列表中",
        )

    # 从自选列表中移除
    config_manager.remove_watchlist(code)

    # 移除成功后，清理相关缓存
    asyncio.create_task(_cleanup_removed_fund(code))

    return {
        "success": True,
        "message": f"基金 {code} 已从自选移除",
    }


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
