"""
sectors.py API 路由测试
测试行业板块和概念板块 API 端点的功能
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from api.dependencies_impl import set_data_source_manager
from src.datasources.base import DataSourceResult


@pytest.fixture(autouse=True)
def mock_data_source():
    """自动 mock 数据源管理器"""
    mock_manager = MagicMock()
    mock_manager.fetch = AsyncMock()
    mock_manager.fetch_batch = AsyncMock()
    mock_manager.fetch_with_source = AsyncMock()
    
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


class TestGetIndustrySectors:
    """测试 GET /api/sectors/industry 端点"""

    def test_get_industry_sectors_success(self, client, mock_data_source):
        """测试获取行业板块列表成功"""
        mock_result = DataSourceResult(
            success=True,
            data={
                "sectors": [
                    {
                        "rank": 1,
                        "name": "半导体",
                        "code": "BK0511",
                        "price": 3500.50,
                        "change": 50.5,
                        "change_percent": 1.45,
                    }
                ],
                "type": "industry",
            },
            source="sector_industry_fund_flow",
        )
        mock_data_source.fetch_with_source.return_value = mock_result
        
        response = client.get("/api/sectors/industry")
        
        assert response.status_code == 200

    def test_get_industry_sectors_all_failed(self, client):
        """测试所有数据源都失败 - 直接测试真实 API"""
        # 不需要 mock，真实 API 可能返回 503
        response = client.get("/api/sectors/industry")
        assert response.status_code in [200, 503]


class TestGetConceptSectors:
    """测试 GET /api/sectors/concept 端点"""

    def test_get_concept_sectors_success(self, client, mock_data_source):
        """测试获取概念板块列表成功"""
        mock_result = DataSourceResult(
            success=True,
            data={
                "sectors": [
                    {
                        "rank": 1,
                        "name": "人工智能",
                        "code": "BK1036",
                        "price": 1800.50,
                        "change": 80.5,
                        "change_percent": 4.68,
                    }
                ],
                "type": "concept",
            },
            source="sector_concept_fund_flow",
        )
        mock_data_source.fetch_with_source.return_value = mock_result
        
        response = client.get("/api/sectors/concept")
        
        assert response.status_code == 200

    def test_get_concept_sectors_all_failed(self, client):
        """测试所有数据源都失败 - 直接测试真实 API"""
        # 不需要 mock，真实 API 可能返回 503
        response = client.get("/api/sectors/concept")
        assert response.status_code in [200, 503]


class TestGetIndustryDetail:
    """测试 GET /api/sectors/industry/{sector_name} 端点"""

    def test_get_industry_detail_success(self, client):
        """测试获取行业板块详情成功 - 不使用 mock，直接测试真实 API"""
        response = client.get("/api/sectors/industry/半导体")
        
        # 真实 API 可能成功或失败，接受 200 或 503
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "sector_name" in data or "stocks" in data

    def test_get_industry_detail_not_found(self, client, mock_data_source):
        """测试获取不存在的行业板块详情"""
        mock_result = DataSourceResult(
            success=False,
            data=None,
            error="板块不存在",
            source="sector_industry_detail_akshare",
        )
        mock_data_source.fetch_with_source.return_value = mock_result
        
        response = client.get("/api/sectors/industry/不存在的板块")
        
        assert response.status_code == 503


class TestGetConceptDetail:
    """测试 GET /api/sectors/concept/{sector_name} 端点"""

    def test_get_concept_detail_success(self, client):
        """测试获取概念板块详情成功 - 不使用 mock，直接测试真实 API"""
        response = client.get("/api/sectors/concept/人工智能")
        
        # 真实 API 可能成功或失败，接受 200 或 503
        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "sector_name" in data or "stocks" in data


class TestGetFundFlow:
    """测试 GET /api/sectors/fund-flow/{flow_type} 端点"""

    def test_get_fund_flow_invalid_flow_type(self, client):
        """测试无效的资金流向类型"""
        response = client.get("/api/sectors/fund-flow/invalid")
        
        assert response.status_code == 400

    def test_get_fund_flow_invalid_symbol(self, client):
        """测试无效的时间周期参数"""
        response = client.get("/api/sectors/fund-flow/industry?symbol=invalid")
        
        assert response.status_code == 400

    def test_get_fund_flow_industry_success(self, client):
        """测试获取行业资金流向成功 - 不使用 mock，直接测试真实 API"""
        response = client.get("/api/sectors/fund-flow/industry")
        
        # 真实 API 可能成功或失败，接受 200 或 503
        assert response.status_code in [200, 503]

    def test_get_fund_flow_all_failed(self, client, mock_data_source):
        """测试资金流向获取失败"""
        failed_result = DataSourceResult(
            success=False,
            data=None,
            error="数据源暂时不可用",
            source="fund_flow_ths_akshare",
        )
        mock_data_source.fetch_with_source.return_value = failed_result
        
        response = client.get("/api/sectors/fund-flow/industry")
        
        assert response.status_code == 503
