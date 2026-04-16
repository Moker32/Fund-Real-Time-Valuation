"""
overview.py API 路由测试
测试市场概览 API 端点的功能
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from api.dependencies_impl import set_data_source_manager
from api.main import app
from src.config.models import Fund, FundList, Holding
from src.datasources.base import DataSourceResult


@pytest.fixture(autouse=True)
def mock_data_source():
    """自动 mock 数据源管理器"""
    mock_manager = MagicMock()
    mock_manager.fetch = AsyncMock()
    mock_manager.fetch_batch = AsyncMock()

    # 设置全局 mock
    set_data_source_manager(mock_manager)
    yield mock_manager
    # 清理
    set_data_source_manager(None)


@pytest.fixture
def client():
    """创建测试客户端"""
    with TestClient(app) as client:
        yield client


class TestGetOverview:
    """测试 GET /api/overview 端点"""

    def test_get_overview_returns_200(self, client, mock_data_source):
        """测试获取市场概览返回 200"""
        mock_result = DataSourceResult(
            success=True,
            data={
                "fund_code": "000001",
                "name": "测试基金",
                "estimated_net_value": 1.5234,
                "unit_net_value": 1.5000,
                "estimate_time": "2024-01-15 15:00:00",
            },
            source="eastmoney",
        )
        mock_data_source.fetch_batch.return_value = [mock_result]

        response = client.get("/api/overview")

        assert response.status_code == 200

    def test_get_overview_response_structure(self, client):
        """测试响应结构"""
        response = client.get("/api/overview")

        assert response.status_code == 200
        data = response.json()
        assert "totalValue" in data
        assert "totalChange" in data
        assert "totalChangePercent" in data
        assert "fundCount" in data
        assert "lastUpdated" in data


class TestGetSimpleOverview:
    """测试 GET /api/overview/simple 端点"""

    def test_get_simple_overview_success(self, client, mock_data_source):
        """测试获取简版市场概览成功"""
        mock_result = DataSourceResult(
            success=True,
            data={
                "fund_code": "000001",
                "name": "测试基金",
                "estimated_net_value": 1.5234,
                "unit_net_value": 1.5000,
            },
            source="eastmoney",
        )
        mock_data_source.fetch_batch.return_value = [mock_result]

        response = client.get("/api/overview/simple")

        assert response.status_code == 200
        data = response.json()
        # 应该与完整的 overview 返回相同结构
        assert "totalValue" in data
        assert "fundCount" in data


class TestLoadDefaultFundCodes:
    """测试 load_default_fund_codes 辅助函数"""

    def test_load_default_fund_codes_with_funds(self):
        """测试加载有基金的情况"""
        from api.routes.overview import load_default_fund_codes

        mock_config_manager = MagicMock()
        mock_fund_list = FundList(
            watchlist=[Fund(code="000001", name="基金1")],
            holdings=[Holding(code="000002", name="基金2")],
        )
        mock_config_manager.load_funds.return_value = mock_fund_list

        result = load_default_fund_codes(mock_config_manager)

        assert "000001" in result
        assert "000002" in result

    def test_load_default_fund_codes_empty(self):
        """测试加载空基金列表返回默认值"""
        from api.routes.overview import load_default_fund_codes

        mock_config_manager = MagicMock()
        mock_config_manager.load_funds.side_effect = Exception("加载失败")

        result = load_default_fund_codes(mock_config_manager)

        # 应该返回默认基金列表
        assert isinstance(result, list)
        assert len(result) > 0


class TestOverviewEdgeCases:
    """测试边界情况"""

    def test_overview_timestamp_format(self, client):
        """测试时间戳格式"""
        response = client.get("/api/overview")

        assert response.status_code == 200
        data = response.json()
        # 检查时间戳格式
        assert "lastUpdated" in data
        assert data["lastUpdated"]
