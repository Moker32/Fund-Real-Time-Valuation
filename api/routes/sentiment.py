"""
舆情数据 API 路由
提供全球宏观事件（财经日历）和微博舆情相关的 REST API 端点
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from typing_extensions import TypedDict

from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency
from ..models import ErrorResponse

logger = logging.getLogger(__name__)


def _clean_float(val):
    """清理 NaN 和 Inf 值"""
    import math

    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


class EconomicEventItem(TypedDict):
    """单条财经事件数据结构"""

    日期: str
    时间: str
    地区: str
    事件: str
    公布: float | None
    预期: float | None
    前值: float | None
    重要性: int


class EconomicEventsData(TypedDict):
    """财经事件列表响应数据结构"""

    events: list[EconomicEventItem]
    timestamp: str
    date: str
    source: str


class WeiboSentimentItem(TypedDict):
    """单条微博舆情数据结构"""

    name: str
    rate: float


class WeiboSentimentData(TypedDict):
    """微博舆情响应数据结构"""

    sentiment: list[WeiboSentimentItem]
    timestamp: str
    period: str
    source: str


class SentimentAllData(TypedDict):
    """舆情汇总响应数据结构"""

    economic: list[EconomicEventItem] | None
    weibo: list[WeiboSentimentItem] | None
    timestamp: str
    source: str
    errors: list[str] | None


class SentimentCategoriesResponse(TypedDict):
    """舆情分类响应"""

    categories: list[dict]
    timestamp: str


router = APIRouter(prefix="/api/sentiment", tags=["舆情数据"])


@router.get(
    "/economic",
    response_model=EconomicEventsData,
    summary="获取全球宏观事件",
    description="获取全球宏观经济事件发布日程（财经日历）",
    responses={
        200: {"description": "成功获取财经事件列表"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_economic_events(
    date: str = Query(
        default="",
        description="日期，格式 YYYYMMDD，默认今天",
    ),
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> EconomicEventsData:
    """
    获取全球宏观事件（财经日历）

    Args:
        date: 日期，格式 YYYYMMDD，默认今天
        manager: 数据源管理器依赖

    Returns:
        EconomicEventsData: 财经事件数据
    """
    current_time = datetime.now().isoformat() + "Z"

    target_date = date if date else datetime.now().strftime("%Y%m%d")

    try:
        result = await manager.fetch_with_source("akshare_economic_news", target_date)

        if not result.success:
            logger.warning(f"获取财经事件失败: {result.error}")
            return {
                "events": [],
                "timestamp": current_time,
                "date": target_date,
                "source": "",
            }

        events: list[EconomicEventItem] = []
        raw_data = result.data or []

        for item in raw_data:
            if isinstance(item, dict):
                date_val = item.get("日期", "")
                if date_val and hasattr(date_val, "isoformat"):
                    date_val = date_val.isoformat()

                # 处理 NaN 值
                events.append(
                    {
                        "日期": str(date_val) if date_val else "",
                        "时间": item.get("时间", ""),
                        "地区": item.get("地区", ""),
                        "事件": item.get("事件", ""),
                        "公布": _clean_float(item.get("公布")),
                        "预期": _clean_float(item.get("预期")),
                        "前值": _clean_float(item.get("前值")),
                        "重要性": item.get("重要性", 0),
                    }
                )

        return {
            "events": events,
            "timestamp": current_time,
            "date": target_date,
            "source": result.source,
        }

    except Exception as e:
        logger.error(f"获取财经事件异常: {e}")
        return {
            "events": [],
            "timestamp": current_time,
            "date": target_date,
            "source": "",
        }


@router.get(
    "/weibo",
    response_model=WeiboSentimentData,
    summary="获取微博舆情",
    description="获取微博舆情报告中近期受关注的股票",
    responses={
        200: {"description": "成功获取微博舆情列表"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_weibo_sentiment(
    period: str = Query(
        default="12h",
        description="时间周期: 2h, 6h, 12h, 24h, 7d, 30d",
    ),
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> WeiboSentimentData:
    """
    获取微博舆情报告

    Args:
        period: 时间周期
        manager: 数据源管理器依赖

    Returns:
        WeiboSentimentData: 微博舆情数据
    """
    current_time = datetime.now().isoformat() + "Z"

    try:
        result = await manager.fetch_with_source("akshare_weibo_sentiment", period)

        if not result.success:
            logger.warning(f"获取微博舆情失败: {result.error}")
            return {
                "sentiment": [],
                "timestamp": current_time,
                "period": period,
                "source": "",
            }

        sentiment: list[WeiboSentimentItem] = []
        raw_data = result.data or []

        for item in raw_data:
            if isinstance(item, dict):
                sentiment.append(
                    {
                        "name": item.get("name", ""),
                        "rate": item.get("rate", 0.0),
                    }
                )

        return {
            "sentiment": sentiment,
            "timestamp": current_time,
            "period": period,
            "source": result.source,
        }

    except Exception as e:
        logger.error(f"获取微博舆情异常: {e}")
        return {
            "sentiment": [],
            "timestamp": current_time,
            "period": period,
            "source": "",
        }


@router.get(
    "/all",
    response_model=SentimentAllData,
    summary="获取全部舆情数据",
    description="同时获取财经事件和微博舆情数据",
    responses={
        200: {"description": "成功获取舆情数据"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_all_sentiment(
    date: str = Query(
        default="",
        description="财经事件日期，格式 YYYYMMDD，默认今天",
    ),
    period: str = Query(
        default="12h",
        description="微博舆情时间周期: 2h, 6h, 12h, 24h, 7d, 30d",
    ),
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> SentimentAllData:
    """
    获取全部舆情数据

    Args:
        date: 财经事件日期
        period: 微博舆情时间周期
        manager: 数据源管理器依赖

    Returns:
        SentimentAllData: 舆情汇总数据
    """
    current_time = datetime.now().isoformat() + "Z"
    target_date = date if date else datetime.now().strftime("%Y%m%d")

    try:
        result = await manager.fetch_with_source(
            "akshare_sentiment_aggregator", "all", date=target_date, period=period
        )

        if not result.success:
            logger.warning(f"获取舆情数据失败: {result.error}")
            return {
                "economic": None,
                "weibo": None,
                "timestamp": current_time,
                "source": "",
                "errors": [result.error] if result.error else [],
            }

        combined_data = result.data or {}
        errors = combined_data.get("errors", [])

        economic_data = combined_data.get("economic")
        weibo_data = combined_data.get("weibo")

        economic: list[EconomicEventItem] | None = None
        if economic_data:
            economic = []
            for item in economic_data:
                if isinstance(item, dict):
                    date_val = item.get("日期", "")
                    if date_val and hasattr(date_val, "isoformat"):
                        date_val = date_val.isoformat()

                    # 处理 NaN 值
                    economic.append(
                        {
                            "日期": str(date_val) if date_val else "",
                            "时间": item.get("时间", ""),
                            "地区": item.get("地区", ""),
                            "事件": item.get("事件", ""),
                            "公布": _clean_float(item.get("公布")),
                            "预期": _clean_float(item.get("预期")),
                            "前值": _clean_float(item.get("前值")),
                            "重要性": item.get("重要性", 0),
                        }
                    )

        weibo: list[WeiboSentimentItem] | None = None
        if weibo_data:
            weibo = []
            for item in weibo_data:
                if isinstance(item, dict):
                    weibo.append(
                        {
                            "name": item.get("name", ""),
                            "rate": item.get("rate", 0.0),
                        }
                    )

        return {
            "economic": economic,
            "weibo": weibo,
            "timestamp": current_time,
            "source": result.source,
            "errors": errors if errors else None,
        }

    except Exception as e:
        logger.error(f"获取舆情数据异常: {e}")
        return {
            "economic": None,
            "weibo": None,
            "timestamp": current_time,
            "source": "",
            "errors": [str(e)],
        }


@router.get(
    "/categories",
    response_model=SentimentCategoriesResponse,
    summary="获取舆情分类列表",
    description="获取支持的舆情数据类型",
)
async def get_sentiment_categories() -> SentimentCategoriesResponse:
    """
    获取舆情分类列表

    Returns:
        SentimentCategoriesResponse: 分类列表
    """
    return {
        "categories": [
            {"id": "economic", "name": "全球宏观事件", "icon": "📅"},
            {"id": "weibo", "name": "微博舆情", "icon": "📱"},
            {"id": "all", "name": "全部", "icon": "📊"},
        ],
        "timestamp": datetime.now().isoformat() + "Z",
    }
