"""
财经新闻 API 路由
提供 7×24 财经快讯相关的 REST API 端点
"""

import logging
from datetime import datetime
from typing import TypedDict

from fastapi import APIRouter, Depends, Query

from src.datasources.manager import DataSourceManager

from ..dependencies import DataSourceDependency
from ..models import ErrorResponse

logger = logging.getLogger(__name__)


class NewsItem(TypedDict):
    """单条新闻数据结构"""

    title: str
    url: str
    time: str
    source: str


class NewsListData(TypedDict):
    """新闻列表响应数据结构"""

    news: list[NewsItem]
    timestamp: str
    category: str
    source: str


class NewsCategoriesResponse(TypedDict):
    """新闻分类响应"""

    categories: list[dict]
    timestamp: str


router = APIRouter(prefix="/api/news", tags=["财经新闻"])

# 支持的新闻分类
NEWS_CATEGORIES = [
    {"id": "finance", "name": "财经要闻", "icon": "📰"},
    {"id": "stock", "name": "股票新闻", "icon": "📈"},
    {"id": "fund", "name": "基金新闻", "icon": "💰"},
    {"id": "economy", "name": "宏观经济", "icon": "🏛️"},
    {"id": "global", "name": "全球市场", "icon": "🌍"},
    {"id": "commodity", "name": "大宗商品", "icon": "🛢️"},
]


@router.get(
    "",
    response_model=NewsListData,
    summary="获取财经新闻列表",
    description="获取 7×24 财经快讯，支持多分类筛选",
    responses={
        200: {"description": "成功获取新闻列表"},
        500: {"model": ErrorResponse, "description": "服务器错误"},
    },
)
async def get_news(
    category: str = Query(
        default="finance",
        description="新闻分类: finance(财经要闻), stock(股票), fund(基金), economy(宏观), global(全球), commodity(商品)",
    ),
    manager: DataSourceManager = Depends(DataSourceDependency()),
) -> NewsListData:
    """
    获取财经新闻列表

    Args:
        category: 新闻分类
        manager: 数据源管理器依赖

    Returns:
        NewsListData: 新闻列表数据
    """
    current_time = datetime.now().isoformat() + "Z"

    # 验证分类
    valid_categories = [c["id"] for c in NEWS_CATEGORIES]
    if category not in valid_categories:
        category = "finance"

    # 通过数据源管理器获取新闻
    # 优先使用东方财富新闻（更稳定），失败则使用新浪新闻
    try:
        result = await manager.fetch_with_source("eastmoney_news", category)
        
        # 如果东方财富失败，尝试新浪新闻
        if not result.success:
            result = await manager.fetch_with_source("sina_news", category)

        if not result.success:
            logger.warning(f"获取新闻失败: {result.error}")
            return {
                "news": [],
                "timestamp": current_time,
                "category": category,
                "source": "",
            }

        # 处理新闻数据
        news_list: list[NewsItem] = []
        raw_data = result.data or []

        for item in raw_data:
            if isinstance(item, dict):
                news_list.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "time": item.get("time", ""),
                        "source": item.get("source", result.source or "sina"),
                    }
                )

        return {
            "news": news_list,
            "timestamp": current_time,
            "category": category,
            "source": result.source,
        }

    except Exception as e:
        logger.error(f"获取新闻异常: {e}")
        return {
            "news": [],
            "timestamp": current_time,
            "category": category,
            "source": "",
        }


@router.get(
    "/categories",
    response_model=NewsCategoriesResponse,
    summary="获取新闻分类列表",
    description="获取支持的新闻分类",
)
async def get_categories() -> NewsCategoriesResponse:
    """
    获取新闻分类列表

    Returns:
        NewsCategoriesResponse: 分类列表
    """
    return {
        "categories": NEWS_CATEGORIES,
        "timestamp": datetime.now().isoformat() + "Z",
    }
