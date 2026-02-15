"""
API 路由测试
测试 API 端点的基本功能
"""

import pytest


def test_routes_module_imports():
    """测试各个路由模块可以正确导入"""
    from api.routes import cache
    from api.routes import commodities
    from api.routes import datasource
    from api.routes import funds
    from api.routes import indices
    from api.routes import news
    from api.routes import overview
    from api.routes import sectors
    from api.routes import sentiment
    from api.routes import trading_calendar

    # 验证路由存在
    assert hasattr(cache, 'router')
    assert hasattr(commodities, 'router')
    assert hasattr(datasource, 'router')
    assert hasattr(funds, 'router')
    assert hasattr(indices, 'router')
    assert hasattr(news, 'router')
    assert hasattr(overview, 'router')
    assert hasattr(sectors, 'router')
    assert hasattr(sentiment, 'router')
    assert hasattr(trading_calendar, 'router')


def test_models_module_imports():
    """测试模型模块可以正确导入"""
    from api.models import (
        CommodityResponse,
        ErrorResponse,
        FundResponse,
        OverviewResponse,
    )

    # 验证模型存在
    assert CommodityResponse is not None
    assert ErrorResponse is not None
    assert FundResponse is not None
    assert OverviewResponse is not None


def test_dependencies_module_imports():
    """测试依赖模块可以正确导入"""
    from api.dependencies import DataSourceDependency
    assert DataSourceDependency is not None
