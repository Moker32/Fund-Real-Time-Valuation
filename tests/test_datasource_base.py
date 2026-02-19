# -*- coding: UTF-8 -*-
"""Data Source Base Tests

测试数据源基类
"""

import time

import pytest

from src.datasources.base import (
    DataParseError,
    DataSource,
    DataSourceError,
    DataSourceResult,
    DataSourceType,
    DataSourceUnavailableError,
    NetworkError,
    TimeoutError,
)


class TestDataSourceType:
    """数据源类型枚举测试"""

    def test_data_source_type_values(self):
        """测试数据源类型值"""
        assert DataSourceType.FUND.value == "fund"
        assert DataSourceType.COMMODITY.value == "commodity"
        assert DataSourceType.NEWS.value == "news"
        assert DataSourceType.SECTOR.value == "sector"
        assert DataSourceType.STOCK.value == "stock"
        assert DataSourceType.BOND.value == "bond"
        assert DataSourceType.CRYPTO.value == "crypto"


class TestDataSourceError:
    """数据源错误测试"""

    def test_data_source_error_creation(self):
        """测试数据源错误创建"""
        error = DataSourceError(
            message="Test error",
            source_type=DataSourceType.FUND,
            details={"key": "value"}
        )

        assert error.message == "Test error"
        assert error.source_type == DataSourceType.FUND
        assert error.details == {"key": "value"}

    def test_network_error(self):
        """测试网络错误"""
        error = NetworkError(
            message="Network failed",
            source_type=DataSourceType.FUND
        )
        
        assert isinstance(error, DataSourceError)
        assert error.message == "Network failed"

    def test_data_parse_error(self):
        """测试数据解析错误"""
        error = DataParseError(
            message="Parse failed",
            source_type=DataSourceType.FUND
        )
        
        assert isinstance(error, DataSourceError)
        assert error.message == "Parse failed"

    def test_data_source_unavailable_error(self):
        """测试数据源不可用错误"""
        error = DataSourceUnavailableError(
            message="Source unavailable",
            source_type=DataSourceType.FUND
        )
        
        assert isinstance(error, DataSourceError)
        assert error.message == "Source unavailable"

    def test_timeout_error(self):
        """测试超时错误"""
        error = TimeoutError(
            message="Request timeout",
            source_type=DataSourceType.FUND
        )
        
        assert isinstance(error, DataSourceError)
        assert error.message == "Request timeout"


class TestDataSourceResult:
    """数据源结果测试"""

    def test_data_source_result_creation(self):
        """测试数据源结果创建"""
        result = DataSourceResult(
            success=True,
            data={"key": "value"},
            error=None,
            timestamp=time.time(),
            source="test_source",
            metadata={"category": "test"}
        )

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.source == "test_source"
        assert result.metadata == {"category": "test"}

    def test_data_source_result_default_timestamp(self):
        """测试默认时间戳"""
        result = DataSourceResult(success=True)
        
        assert result.timestamp > 0

    def test_data_source_result_failure(self):
        """测试失败结果"""
        result = DataSourceResult(
            success=False,
            error="Error message",
            source="test_source"
        )

        assert result.success is False
        assert result.error == "Error message"


class MockDataSource(DataSource):
    """用于测试的模拟数据源"""

    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        """模拟获取数据"""
        return DataSourceResult(
            success=True,
            data={"mock": "data"},
            source=self.name
        )

    async def fetch_batch(self, *args, **kwargs) -> list[DataSourceResult]:
        """模拟批量获取数据"""
        return [await self.fetch()]


class TestDataSource:
    """数据源基类测试"""

    @pytest.fixture
    def mock_source(self):
        """返回模拟数据源实例"""
        return MockDataSource(
            name="mock_source",
            source_type=DataSourceType.FUND,
            timeout=10.0
        )

    def test_init(self, mock_source):
        """测试初始化"""
        assert mock_source.name == "mock_source"
        assert mock_source.source_type == DataSourceType.FUND
        assert mock_source.timeout == 10.0
        assert mock_source._request_count == 0
        assert mock_source._error_count == 0

    def test_error_rate(self, mock_source):
        """测试错误率计算"""
        # 无请求时错误率为0
        assert mock_source.error_rate == 0.0

        # 有请求无错误
        mock_source._request_count = 10
        assert mock_source.error_rate == 0.0

        # 有错误
        mock_source._error_count = 2
        assert mock_source.error_rate == 0.2

    def test_handle_error(self, mock_source):
        """测试错误处理"""
        error = ValueError("Test error")
        
        result = mock_source._handle_error(error, "test_source")

        assert result.success is False
        assert "Test error" in result.error
        assert result.source == "test_source"
        assert mock_source._request_count == 1
        assert mock_source._error_count == 1
        assert mock_source._last_error is not None

    def test_handle_data_source_error(self, mock_source):
        """测试处理 DataSourceError"""
        error = DataSourceError(
            message="Custom error",
            source_type=DataSourceType.FUND,
            details={"key": "value"}
        )

        result = mock_source._handle_error(error, "test_source")

        assert result.success is False
        assert result.error == "Custom error"
        assert result.metadata.get("source_type") == DataSourceType.FUND

    def test_record_success(self, mock_source):
        """测试记录成功"""
        result = mock_source._record_success()

        assert result.success is True
        assert mock_source._request_count == 1
        assert mock_source._error_count == 0

    def test_get_status(self, mock_source):
        """测试获取状态"""
        mock_source._request_count = 10
        mock_source._error_count = 2

        status = mock_source.get_status()

        assert status["name"] == "mock_source"
        assert status["type"] == "fund"
        assert status["timeout"] == 10.0
        assert status["request_count"] == 10
        assert status["error_count"] == 2
        assert status["error_rate"] == 0.2

    @pytest.mark.asyncio
    async def test_fetch_success(self, mock_source):
        """测试获取数据成功"""
        result = await mock_source.fetch()

        assert result.success is True
        assert result.data == {"mock": "data"}
        assert result.source == "mock_source"

    @pytest.mark.asyncio
    async def test_fetch_batch(self, mock_source):
        """测试批量获取数据"""
        results = await mock_source.fetch_batch()

        assert len(results) == 1
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_source):
        """测试健康检查成功"""
        result = await mock_source.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_source):
        """测试健康检查失败"""
        # 创建一个总是失败的数据源
        class FailingSource(DataSource):
            async def fetch(self, *args, **kwargs) -> DataSourceResult:
                return DataSourceResult(success=False, error="Failed")

            async def fetch_batch(self, *args, **kwargs) -> list[DataSourceResult]:
                return []

        failing_source = FailingSource(
            name="failing",
            source_type=DataSourceType.FUND
        )

        result = await failing_source.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_close(self, mock_source):
        """测试关闭连接"""
        await mock_source.close()  # 默认实现不做任何事


class TestDataSourceAbstract:
    """测试抽象方法"""

    def test_cannot_instantiate_abstract_class(self):
        """测试不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            DataSource(name="test", source_type=DataSourceType.FUND)

    def test_can_instantiate_concrete_class(self):
        """测试可以实例化实现类"""
        # 应该可以正常创建
        source = MockDataSource(name="test", source_type=DataSourceType.FUND)
        assert source.name == "test"
