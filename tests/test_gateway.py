"""
数据网关 (DataGateway) 测试

测试 DataGateway 类的功能:
1. 请求方法
2. 统计和监控
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.datasources.base import DataSourceType
from src.datasources.gateway import (
    DataGateway,
    GatewayStats,
)
from src.datasources.unified_models import (
    BatchDataRequest,
    BatchDataResponse,
    DataRequest,
    DataResponse,
    ResponseStatus,
)


class TestGatewayStats:
    """测试网关统计数据类"""

    def test_init(self):
        """测试初始化"""
        stats = GatewayStats()
        
        assert stats.total_requests == 0
        assert stats.success_count == 0
        assert stats.failure_count == 0
        assert stats.fallback_count == 0
        assert stats.total_latency_ms == 0.0
        assert stats.request_latencies == []

    def test_record_success_request(self):
        """测试记录成功请求"""
        stats = GatewayStats()
        
        stats.record_request(latency_ms=100.0, success=True)
        
        assert stats.total_requests == 1
        assert stats.success_count == 1
        assert stats.failure_count == 0
        assert 100.0 in stats.request_latencies

    def test_record_failure_request(self):
        """测试记录失败请求"""
        stats = GatewayStats()
        
        stats.record_request(latency_ms=200.0, success=False)
        
        assert stats.total_requests == 1
        assert stats.success_count == 0
        assert stats.failure_count == 1

    def test_record_fallback_request(self):
        """测试记录回退请求"""
        stats = GatewayStats()
        
        stats.record_request(latency_ms=150.0, success=True, fallback=True)
        
        assert stats.fallback_count == 1

    def test_success_rate(self):
        """测试成功率计算"""
        stats = GatewayStats()
        
        # 无请求
        assert stats.success_rate == 0.0
        
        # 全部成功
        stats.record_request(100.0, True)
        stats.record_request(100.0, True)
        assert stats.success_rate == 1.0
        
        # 部分成功
        stats.record_request(100.0, False)
        assert stats.success_rate == 2/3

    def test_average_latency_ms(self):
        """测试平均延迟计算"""
        stats = GatewayStats()
        
        assert stats.average_latency_ms == 0.0
        
        stats.record_request(100.0, True)
        stats.record_request(200.0, True)
        
        assert stats.average_latency_ms == 150.0

    def test_p95_latency_ms(self):
        """测试 P95 延迟计算"""
        stats = GatewayStats()
        
        assert stats.p95_latency_ms == 0.0
        
        # 添加100个样本
        for i in range(100):
            stats.record_request(float(i + 1), True)
        
        # P95 应该约为95
        p95 = stats.p95_latency_ms
        assert 90 <= p95 <= 100

    def test_p99_latency_ms(self):
        """测试 P99 延迟计算"""
        stats = GatewayStats()
        
        assert stats.p99_latency_ms == 0.0
        
        # 添加100个样本
        for i in range(100):
            stats.record_request(float(i + 1), True)
        
        # P99 应该约为99
        p99 = stats.p99_latency_ms
        assert 95 <= p99 <= 100

    def test_max_latencies_limit(self):
        """测试延迟记录数量限制"""
        stats = GatewayStats(max_latencies=10)
        
        # 添加超过限制的请求
        for i in range(20):
            stats.record_request(float(i), True)
        
        assert len(stats.request_latencies) == 10

    def test_to_dict(self):
        """测试转换为字典"""
        stats = GatewayStats()
        stats.record_request(100.0, True)
        
        d = stats.to_dict()
        
        assert "total_requests" in d
        assert "success_count" in d
        assert "success_rate" in d
        assert "average_latency_ms" in d


class TestDataGateway:
    """测试数据网关"""

    @pytest.fixture
    def mock_manager(self):
        """创建模拟的 DataSourceManager"""
        # 延迟导入避免顶层导入错误
        from src.datasources.manager import DataSourceManager
        manager = MagicMock(spec=DataSourceManager)
        return manager

    def test_init(self, mock_manager):
        """测试初始化"""
        gateway = DataGateway(manager=mock_manager)
        
        assert gateway._manager == mock_manager
        assert gateway._stats is not None

    def test_init_default_stats(self, mock_manager):
        """测试默认统计"""
        gateway = DataGateway(manager=mock_manager)
        
        # 默认应该有空的统计
        assert gateway._stats.total_requests == 0

    @pytest.mark.asyncio
    async def test_request_single(self, mock_manager):
        """测试单个请求"""
        gateway = DataGateway(manager=mock_manager)
        
        # 模拟 manager 返回
        mock_response = MagicMock()
        mock_response.success = True
        
        mock_manager.fetch = AsyncMock(return_value=mock_response)
        
        req = DataRequest(symbol="001000", source_type=DataSourceType.FUND)
        result = await gateway.request(req)
        
        assert result is not None
        mock_manager.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_batch(self, mock_manager):
        """测试批量请求"""
        gateway = DataGateway(manager=mock_manager)
        
        # 模拟批量返回
        mock_response1 = DataResponse(
            request_id="test_001",
            success=True,
            status=ResponseStatus.SUCCESS,
            data={"value": 100},
            source="source1",
            timestamp=1000.0
        )
        mock_response2 = DataResponse(
            request_id="test_002",
            success=True,
            status=ResponseStatus.SUCCESS,
            data={"value": 200},
            source="source2",
            timestamp=1000.0
        )
        
        mock_batch_response = BatchDataResponse(
            request_id="batch_001",
            responses=[mock_response1, mock_response2],
            total_count=2,
            success_count=2,
            failed_count=0,
            total_latency_ms=100.0
        )
        mock_manager.request_batch = AsyncMock(return_value=mock_batch_response)
        
        batch = BatchDataRequest(requests=[
            DataRequest(symbol="001", source_type=DataSourceType.FUND),
            DataRequest(symbol="002", source_type=DataSourceType.FUND),
        ])
        
        result = await gateway.request_batch(batch)
        
        assert len(result.responses) == 2

    @pytest.mark.asyncio
    async def test_get_fund(self, mock_manager):
        """测试获取基金数据"""
        gateway = DataGateway(manager=mock_manager)
        
        mock_response = DataResponse(
            request_id="test_001",
            success=True,
            status=ResponseStatus.SUCCESS,
            data={"nav": 1.234},
            source="fund_source",
            timestamp=1000.0
        )
        mock_manager.request = AsyncMock(return_value=mock_response)
        
        result = await gateway.get_fund("001000")
        
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_stock(self, mock_manager):
        """测试获取股票数据"""
        gateway = DataGateway(manager=mock_manager)
        
        mock_response = DataResponse(
            request_id="test_001",
            success=True,
            status=ResponseStatus.SUCCESS,
            data={"price": 100.0},
            source="stock_source",
            timestamp=1000.0
        )
        mock_manager.request = AsyncMock(return_value=mock_response)
        
        result = await gateway.get_stock("600000")
        
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_commodity(self, mock_manager):
        """测试获取大宗商品数据"""
        gateway = DataGateway(manager=mock_manager)
        
        mock_response = DataResponse(
            request_id="test_001",
            success=True,
            status=ResponseStatus.SUCCESS,
            data={"price": 2000.0},
            source="commodity_source",
            timestamp=1000.0
        )
        mock_manager.request = AsyncMock(return_value=mock_response)
        
        result = await gateway.get_commodity("黄金")
        
        assert result.success is True

    def test_get_stats(self, mock_manager):
        """测试获取统计信息"""
        gateway = DataGateway(manager=mock_manager)
        
        # 记录一些请求
        gateway._stats.record_request(100.0, True)
        gateway._stats.record_request(200.0, False)
        
        stats = gateway.get_stats()
        
        assert stats["total_requests"] == 2
        assert stats["success_count"] == 1

    def test_reset_stats(self, mock_manager):
        """测试重置统计"""
        gateway = DataGateway(manager=mock_manager)
        
        gateway._stats.record_request(100.0, True)
        gateway.reset_stats()
        
        assert gateway._stats.total_requests == 0
