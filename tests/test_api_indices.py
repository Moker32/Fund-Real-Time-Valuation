"""
indices.py API 路由测试
测试全球市场指数 API 端点的功能
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.dependencies_impl import set_data_source_manager
from api.main import app
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


class TestGetIndices:
    """测试 GET /api/indices 端点"""

    def test_get_indices_returns_200(self, client, mock_data_source):
        """测试获取指数列表返回 200"""
        mock_data_source.fetch_batch.return_value = []
        
        response = client.get("/api/indices")
        
        assert response.status_code == 200

    def test_get_indices_response_structure(self, client):
        """测试响应结构"""
        response = client.get("/api/indices")
        
        assert response.status_code == 200
        data = response.json()
        assert "indices" in data
        assert "timestamp" in data


class TestGetIndex:
    """测试 GET /api/indices/{index_type} 端点"""

    def test_get_single_index_success(self, client):
        """测试获取单个指数成功 - 不使用 mock，直接测试真实 API"""
        response = client.get("/api/indices/shanghai")
        
        assert response.status_code == 200
        data = response.json()
        # 验证返回的数据结构
        assert "index" in data
        assert "name" in data
        assert "price" in data
        assert data["price"] is not None

    def test_get_single_index_fetch_failure(self, client):
        """测试获取单个指数失败 - 使用不存在的指数类型"""
        # 不存在的指数类型会抛出 ValueError，返回 500 或 422
        try:
            response = client.get("/api/indices/invalid_index_type_12345")
            # 如果没有抛出异常，检查状态码
            assert response.status_code in [400, 422, 500]
        except ValueError:
            # ValueError 也会被 FastAPI 转换为错误响应
            pass


class TestGetRegions:
    """测试 GET /api/indices/regions 端点"""

    def test_get_regions_success(self, client):
        """测试获取支持的区域列表"""
        response = client.get("/api/indices/regions")
        
        assert response.status_code == 200
        data = response.json()
        assert "regions" in data
        assert "supported_indices" in data
        assert isinstance(data["regions"], list)
        assert isinstance(data["supported_indices"], list)


class TestGetIndexHistory:
    """测试 GET /api/indices/{index_type}/history 端点"""

    def test_get_index_history_with_period(self, client):
        """测试获取历史数据"""
        with patch("api.routes.indices._get_index_history_source") as mock_get_source:
            mock_history_source = MagicMock()
            mock_history_source.fetch_history = AsyncMock()
            mock_history_source.fetch_history.return_value = DataSourceResult(
                success=True,
                data={
                    "index": "shanghai",
                    "history": [
                        {"date": "2024-01-01", "close": 3000.0},
                        {"date": "2024-01-02", "close": 3050.0},
                    ],
                },
                source="eastmoney",
            )
            mock_get_source.return_value = mock_history_source
            
            response = client.get("/api/indices/shanghai/history?period=1mo")
            
            assert response.status_code == 200

    def test_get_index_history_fetch_failure(self, client):
        """测试历史数据获取失败"""
        with patch("api.routes.indices._get_index_history_source") as mock_get_source:
            mock_history_source = MagicMock()
            mock_history_source.fetch_history = AsyncMock()
            mock_history_source.fetch_history.return_value = DataSourceResult(
                success=False,
                data=None,
                error="历史数据不可用",
                source="eastmoney",
            )
            mock_get_source.return_value = mock_history_source
            
            response = client.get("/api/indices/shanghai/history")
            
            assert response.status_code == 400


class TestGetTradingStatus:
    """测试 get_trading_status 辅助函数"""

    def test_get_trading_status_unknown_index(self):
        """测试未知指数的交易状态"""
        from api.routes.indices import get_trading_status

        result = get_trading_status(None)

        assert result["status"] == "unknown"
        assert result["market_time"] is None

    def test_get_trading_status_with_valid_state(self):
        """测试有效的 market_state"""
        from api.routes.indices import get_trading_status

        result = get_trading_status("CLOSED")

        assert "status" in result
        assert "market_time" in result
        assert result["status"] == "closed"

    def test_get_trading_status_with_pre_state(self):
        """测试 pre market_state"""
        from api.routes.indices import get_trading_status

        result = get_trading_status("PRE")

        assert "status" in result
        assert result["status"] == "pre"


class TestValidatePeriod:
    """测试 _validate_period 辅助函数"""

    def test_validate_period_valid(self):
        """测试有效的周期参数"""
        from api.routes.indices import _validate_period
        
        assert _validate_period("1d") == "1d"
        assert _validate_period("1mo") == "1mo"
        assert _validate_period("1y") == "1y"
        assert _validate_period("max") == "max"

    def test_validate_period_invalid(self):
        """测试无效的周期参数，应返回默认值 1y"""
        from api.routes.indices import _validate_period
        
        assert _validate_period("invalid") == "1y"
        assert _validate_period("") == "1y"
