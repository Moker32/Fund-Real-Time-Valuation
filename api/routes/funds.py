"""
基金 API 路由
提供基金相关的 REST API 端点
"""

from datetime import datetime
from typing import Optional, TypedDict

from fastapi import APIRouter, Depends, HTTPException

from src.config.manager import ConfigManager
from src.config.models import Fund, FundList
from src.datasources.base import DataSourceType
from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency
from ..models import (
    ErrorResponse,
    FundDetailResponse,
    FundEstimateResponse,
    FundListResponse,
    FundResponse,
    AddFundRequest,
)


class FundListData(TypedDict):
    """基金列表响应数据结构"""
    funds: list[dict]
    total: int
    timestamp: str
    progress: Optional[int]  # 加载进度 0-100


router = APIRouter(prefix="/api/funds", tags=["基金"])


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


def build_fund_response(data: dict, source: str = "", is_holding: bool = False) -> dict:
    """构建基金响应数据"""
    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = None
    if unit_net is not None and estimate_net is not None and unit_net != 0:
        estimate_change = round(estimate_net - unit_net, 4)

    return FundResponse(
        code=data.get("fund_code", ""),
        name=data.get("name", ""),
        type=data.get("type"),
        netValue=data.get("unit_net_value"),
        netValueDate=data.get("net_value_date"),
        estimateValue=data.get("estimated_net_value"),
        estimateChangePercent=data.get("estimated_growth_rate"),
        estimateTime=data.get("estimate_time"),
        estimateChange=estimate_change,
        source=source,
        isHolding=is_holding,
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
    codes: Optional[str] = None,
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
        for result in results:
            if result.success:
                is_holding = result.data.get("fund_code") in holding_codes
                funds.append(build_fund_response(result.data, result.source, is_holding))
            else:
                # 如果单个基金获取失败，记录错误但不中断
                pass
        return {"funds": funds, "total": len(funds), "timestamp": current_time}

    # 没有指定 codes 时，使用默认基金代码获取真实数据
    fund_codes = get_default_fund_codes()

    # 构建参数列表
    params_list = [{"args": [code]} for code in fund_codes]
    results = await manager.fetch_batch(DataSourceType.FUND, params_list)
    funds = []
    for result in results:
        if result.success:
            is_holding = result.data.get("fund_code") in holding_codes
            funds.append(build_fund_response(result.data, result.source, is_holding))
        else:
            # 如果单个基金获取失败，记录错误但不中断
            pass

    return {"funds": funds, "total": len(funds), "timestamp": current_time}


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
    from src.config.manager import ConfigManager

    result = await manager.fetch(DataSourceType.FUND, code)

    if not result.success:
        raise HTTPException(
            status_code=404 if "不存在" in result.error else 500,
            detail=result.error,
        )

    data = result.data

    # 计算 estimateChange (估算涨跌额)
    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = None
    if unit_net is not None and estimate_net is not None and unit_net != 0:
        estimate_change = round(estimate_net - unit_net, 4)

    # 检查是否持仓
    config_manager = ConfigManager()
    fund_list = config_manager.load_funds()
    is_holding = code in {h.code for h in fund_list.holdings}

    return FundDetailResponse(
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
    from src.config.manager import ConfigManager

    result = await manager.fetch(DataSourceType.FUND, code)

    if not result.success:
        raise HTTPException(
            status_code=404 if "不存在" in result.error else 500,
            detail=result.error,
        )

    data = result.data

    # 计算 estimateChange (估算涨跌额)
    unit_net = data.get("unit_net_value")
    estimate_net = data.get("estimated_net_value")
    estimate_change = None
    if unit_net is not None and estimate_net is not None and unit_net != 0:
        estimate_change = round(estimate_net - unit_net, 4)

    # 检查是否持仓
    config_manager = ConfigManager()
    fund_list = config_manager.load_funds()
    is_holding = code in {h.code for h in fund_list.holdings}

    return FundEstimateResponse(
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

    if not result.success:
        raise HTTPException(
            status_code=404 if "不存在" in result.error else 500,
            detail=result.error,
        )

    return result.data


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
        raise HTTPException(
            status_code=404 if "不存在" in result.error else 400,
            detail=result.error,
        )

    # 获取基金名称（如果请求中没有提供）
    fund_name = request.name
    if not fund_name and result.data:
        fund_name = result.data.get("name", "")

    # 添加到自选列表
    config_manager = ConfigManager()
    fund = Fund(code=request.code, name=fund_name)
    config_manager.add_watchlist(fund)

    return {
        "success": True,
        "message": f"基金 {request.code} 已添加到自选",
        "fund": {"code": request.code, "name": fund_name},
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

    return {
        "success": True,
        "message": f"基金 {code} 已从自选移除",
    }
