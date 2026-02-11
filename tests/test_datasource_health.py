"""
数据源健康检查模块测试

覆盖:
1. 单元测试 - HealthStatus, HealthCheckResult
2. 单元测试 - DataSourceHealthChecker
3. 服务测试 - HealthCheckInterceptor
4. 集成测试 - DataSourceManager 健康检查集成
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.datasources.base import (
    DataSource,
    DataSourceResult,
    DataSourceType,
)
from src.datasources.health import (
    DataSourceHealthChecker,
    HealthCheckInterceptor,
    HealthCheckResult,
    HealthStatus,
)
from src.datasources.manager import DataSourceManager

# ============================================================================
# 1. 单元测试 - HealthStatus 枚举
# ============================================================================

class TestHealthStatus:
    """健康状态枚举测试"""

    def test_healthy_status(self):
        """测试健康状态"""
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_degraded_status(self):
        """测试降级状态"""
        assert HealthStatus.DEGRADED.value == "degraded"

    def test_unhealthy_status(self):
        """测试不健康状态"""
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_unknown_status(self):
        """测试未知状态"""
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_all_statuses_count(self):
        """测试所有状态数量"""
        assert len(HealthStatus) == 4

    def test_status_comparison(self):
        """测试状态比较"""
        assert HealthStatus.HEALTHY != HealthStatus.DEGRADED
        assert HealthStatus.HEALTHY == HealthStatus.HEALTHY


# ============================================================================
# 2. 单元测试 - HealthCheckResult
# ============================================================================

class TestHealthCheckResult:
    """HealthCheckResult 测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = HealthCheckResult(
            source_name="test_source",
            status=HealthStatus.HEALTHY,
            response_time_ms=100.5,
            error_count=0,
            last_check=datetime.now()
        )
        assert result.source_name == "test_source"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms == 100.5
        assert result.error_count == 0
        assert result.message == ""

    def test_result_with_message(self):
        """测试带消息的结果"""
        result = HealthCheckResult(
            source_name="test_source",
            status=HealthStatus.DEGRADED,
            response_time_ms=6000.0,
            error_count=2,
            last_check=datetime.now(),
            message="响应时间过长"
        )
        assert result.message == "响应时间过长"

    def test_result_with_details(self):
        """测试带详情的结果"""
        result = HealthCheckResult(
            source_name="test_source",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0,
            error_count=3,
            last_check=datetime.now(),
            message="连接失败",
            details={"error_type": "ConnectionError", "endpoint": "http://test.com"}
        )
        assert result.details["error_type"] == "ConnectionError"
        assert result.details["endpoint"] == "http://test.com"

    def test_to_dict(self):
        """测试转换为字典"""
        now = datetime.now()
        result = HealthCheckResult(
            source_name="test_source",
            status=HealthStatus.HEALTHY,
            response_time_ms=50.0,
            error_count=0,
            last_check=now,
            message="OK"
        )

        result_dict = result.to_dict()
        assert result_dict["source_name"] == "test_source"
        assert result_dict["status"] == "healthy"
        assert result_dict["response_time_ms"] == 50.0
        assert result_dict["error_count"] == 0
        assert result_dict["message"] == "OK"
        assert result_dict["last_check"] == now.isoformat()


# ============================================================================
# 3. 单元测试 - DataSourceHealthChecker
# ============================================================================

class TestDataSourceHealthChecker:
    """数据源健康检查器测试"""

    @pytest.fixture
    def checker(self):
        """创建健康检查器"""
        return DataSourceHealthChecker(
            check_interval=60,
            timeout=10.0,
            max_response_time_ms=5000.0,
            consecutive_failure_threshold=3
        )

    @pytest.fixture
    def mock_source_healthy(self):
        """创建健康的数据源 Mock"""
        source = MagicMock(spec=DataSource)
        source.name = "healthy_source"
        source.source_type = DataSourceType.STOCK
        source.health_check = AsyncMock(return_value=True)
        return source

    @pytest.fixture
    def mock_source_unhealthy(self):
        """创建不健康的数据源 Mock"""
        source = MagicMock(spec=DataSource)
        source.name = "unhealthy_source"
        source.source_type = DataSourceType.STOCK
        source.health_check = AsyncMock(return_value=False)
        return source

    @pytest.fixture
    def mock_source_slow(self):
        """创建响应慢的数据源 Mock"""
        source = MagicMock(spec=DataSource)
        source.name = "slow_source"
        source.source_type = DataSourceType.STOCK
        source.health_check = AsyncMock(return_value=True)
        return source

    def test_init(self, checker):
        """测试初始化"""
        assert checker.check_interval == 60
        assert checker.timeout == 10.0
        assert checker.max_response_time_ms == 5000.0
        assert checker.consecutive_failure_threshold == 3
        assert checker.health_history == {}
        assert checker._running is False

    @pytest.mark.asyncio
    async def test_check_healthy_source(self, checker, mock_source_healthy):
        """测试检查健康的数据源"""
        result = await checker.check_source(mock_source_healthy)

        assert result.source_name == "healthy_source"
        assert result.status == HealthStatus.HEALTHY
        assert result.error_count == 0
        assert result.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_check_unhealthy_source(self, checker, mock_source_unhealthy):
        """测试检查不健康的数据源"""
        result = await checker.check_source(mock_source_unhealthy)

        assert result.source_name == "unhealthy_source"
        assert result.status == HealthStatus.DEGRADED
        assert result.error_count >= 1

    @pytest.mark.asyncio
    async def test_check_source_timeout(self, checker, mock_source_healthy):
        """测试检查超时"""
        mock_source_healthy.health_check = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )

        result = await checker.check_source(mock_source_healthy)

        assert result.source_name == "healthy_source"
        assert result.status == HealthStatus.UNHEALTHY
        assert "超时" in result.message

    @pytest.mark.asyncio
    async def test_check_source_exception(self, checker, mock_source_healthy):
        """测试检查异常"""
        mock_source_healthy.health_check = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        result = await checker.check_source(mock_source_healthy)

        assert result.source_name == "healthy_source"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection failed" in result.message

    @pytest.mark.asyncio
    async def test_check_all_sources(self, checker, mock_source_healthy, mock_source_unhealthy):
        """测试并行检查所有数据源"""
        sources = [mock_source_healthy, mock_source_unhealthy]
        results = await checker.check_all_sources(sources)

        assert len(results) == 2
        assert results["healthy_source"].status == HealthStatus.HEALTHY
        assert results["unhealthy_source"].status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)

    @pytest.mark.asyncio
    async def test_check_all_sources_empty(self, checker):
        """测试检查空数据源列表"""
        results = await checker.check_all_sources([])
        assert results == {}

    def test_get_source_health_no_history(self, checker):
        """测试获取无历史记录的数据源状态"""
        result = checker.get_source_health("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_source_health_with_history(self, checker):
        """测试获取有历史记录的数据源状态"""
        # 创建新的 mock source
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = "healthy_source"
        mock_source.source_type = DataSourceType.STOCK
        mock_source.health_check = AsyncMock(return_value=True)

        await checker.check_source(mock_source)
        result = checker.get_source_health("healthy_source")

        assert result is not None
        assert result.source_name == "healthy_source"
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_get_health_history(self, checker):
        """测试获取健康历史"""
        # 创建新的 mock source
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = "history_source"
        mock_source.source_type = DataSourceType.STOCK
        mock_source.health_check = AsyncMock(return_value=True)

        # 执行多次检查
        for _ in range(5):
            await checker.check_source(mock_source)

        history = checker.get_health_history("history_source", limit=3)
        assert len(history) == 3  # 限制为3条

    def test_get_statistics(self, checker):
        """测试获取统计数据"""
        stats = checker.get_statistics()
        assert "total_sources_checked" in stats
        assert "sources" in stats
        assert stats["total_sources_checked"] == 0

    @pytest.mark.asyncio
    async def test_get_statistics_with_data(self, checker):
        """测试获取统计数据（有数据时）"""
        # 创建新的 mock sources
        healthy_source = MagicMock(spec=DataSource)
        healthy_source.name = "healthy_source"
        healthy_source.source_type = DataSourceType.STOCK
        healthy_source.health_check = AsyncMock(return_value=True)

        unhealthy_source = MagicMock(spec=DataSource)
        unhealthy_source.name = "unhealthy_source"
        unhealthy_source.source_type = DataSourceType.STOCK
        unhealthy_source.health_check = AsyncMock(return_value=False)

        await checker.check_source(healthy_source)
        await checker.check_source(unhealthy_source)

        stats = checker.get_statistics()
        assert stats["total_sources_checked"] == 2
        assert "healthy_source" in stats["sources"]
        assert "unhealthy_source" in stats["sources"]

    def test_get_unhealthy_sources_empty(self, checker):
        """测试获取不健康的数据源（空）"""
        sources = checker.get_unhealthy_sources()
        assert sources == []

    def test_get_healthy_sources_empty(self, checker):
        """测试获取健康的数据源（空）"""
        sources = checker.get_healthy_sources()
        assert sources == []

    @pytest.mark.asyncio
    async def test_get_unhealthy_sources_with_data(self, checker):
        """测试获取不健康的数据源（有数据时）"""
        # 创建健康的数据源
        healthy_source = MagicMock(spec=DataSource)
        healthy_source.name = "healthy_source"
        healthy_source.source_type = DataSourceType.STOCK
        healthy_source.health_check = AsyncMock(return_value=True)

        # 创建不健康的数据源
        unhealthy_source = MagicMock(spec=DataSource)
        unhealthy_source.name = "unhealthy_source"
        unhealthy_source.source_type = DataSourceType.STOCK
        unhealthy_source.health_check = AsyncMock(return_value=False)

        await checker.check_source(healthy_source)

        # 多次检查不健康的数据源，使其达到 UNHEALTHY 状态
        for _ in range(3):
            await checker.check_source(unhealthy_source)

        unhealthy = checker.get_unhealthy_sources()
        assert "unhealthy_source" in unhealthy

    @pytest.mark.asyncio
    async def test_get_healthy_sources_with_data(self, checker):
        """测试获取健康的数据源（有数据时）"""
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = "healthy_source"
        mock_source.source_type = DataSourceType.STOCK
        mock_source.health_check = AsyncMock(return_value=True)

        await checker.check_source(mock_source)

        healthy = checker.get_healthy_sources()
        assert "healthy_source" in healthy

    def test_reset(self, checker, mock_source_healthy):
        """测试重置"""
        checker.health_history["test"] = []
        checker._consecutive_failures["test"] = 5
        checker._running = True

        checker.reset()

        assert checker.health_history == {}
        assert checker._consecutive_failures == {}
        assert checker._running is False


# ============================================================================
# 4. 服务测试 - HealthCheckInterceptor
# ============================================================================

class TestHealthCheckInterceptor:
    """健康检查拦截器测试"""

    @pytest.fixture
    def checker(self):
        """创建健康检查器"""
        return DataSourceHealthChecker(
            check_interval=60,
            timeout=10.0,
            consecutive_failure_threshold=2
        )

    @pytest.fixture
    def interceptor(self, checker):
        """创建拦截器"""
        return HealthCheckInterceptor(checker)

    @pytest.fixture
    def mock_source_1(self):
        """创建数据源 Mock 1"""
        source = MagicMock(spec=DataSource)
        source.name = "source1"
        source.source_type = DataSourceType.STOCK
        source.health_check = AsyncMock(return_value=True)
        return source

    @pytest.fixture
    def mock_source_2(self):
        """创建数据源 Mock 2"""
        source = MagicMock(spec=DataSource)
        source.name = "source2"
        source.source_type = DataSourceType.STOCK
        source.health_check = AsyncMock(return_value=True)
        return source

    def test_init(self, interceptor):
        """测试初始化"""
        assert interceptor.checker is not None

    @pytest.mark.asyncio
    async def test_get_healthy_source_empty(self, interceptor):
        """测试获取健康的数据源（空列表）"""
        result = await interceptor.get_healthy_source([])
        assert result is None

    @pytest.mark.asyncio
    async def test_get_healthy_source_prefer_healthy(self, interceptor, mock_source_1, mock_source_2):
        """测试优先获取健康的数据源"""
        sources = [mock_source_1, mock_source_2]
        result = await interceptor.get_healthy_source(sources, prefer_healthy=True)

        assert result is not None
        assert result.name in ["source1", "source2"]

    @pytest.mark.asyncio
    async def test_get_healthy_source_not_prefer(self, interceptor, mock_source_1):
        """测试不优先获取健康的数据源"""
        sources = [mock_source_1]
        result = await interceptor.get_healthy_source(sources, prefer_healthy=False)

        assert result == mock_source_1

    def test_should_skip_source_no_history(self, interceptor):
        """测试跳过无历史记录的数据源"""
        result = interceptor.should_skip_source("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_should_skip_source_healthy(self, interceptor, mock_source_1):
        """测试不应跳过健康的数据源"""
        await interceptor.checker.check_source(mock_source_1)

        result = interceptor.should_skip_source("source1")
        assert result is False

    @pytest.mark.asyncio
    async def test_should_skip_source_unhealthy(self, interceptor):
        """测试应跳过不健康的数据源"""
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = "unhealthy"
        mock_source.source_type = DataSourceType.STOCK
        mock_source.health_check = AsyncMock(return_value=False)

        # 多次检查使其达到不健康状态
        for _ in range(3):
            await interceptor.checker.check_source(mock_source)

        result = interceptor.should_skip_source("unhealthy")
        assert result is True


# ============================================================================
# 5. 集成测试 - DataSourceManager 健康检查集成
# ============================================================================

class TestDataSourceManagerHealthCheck:
    """DataSourceManager 健康检查集成测试"""

    @pytest.fixture
    def manager(self):
        """创建数据源管理器"""
        return DataSourceManager(
            max_concurrent=10,
            enable_load_balancing=False,
            health_check_interval=60
        )

    @pytest.fixture
    def mock_source(self):
        """创建 Mock 数据源"""
        source = MagicMock(spec=DataSource)
        source.name = "test_source"
        source.source_type = DataSourceType.STOCK
        source.fetch = AsyncMock(return_value=DataSourceResult(
            success=True,
            data={"price": 100},
            source="test_source"
        ))
        source.health_check = AsyncMock(return_value=True)
        return source

    def test_manager_init_with_health_checker(self, manager):
        """测试管理器初始化（带健康检查器）"""
        assert manager._health_checker is not None
        assert manager._health_interceptor is not None

    @pytest.mark.asyncio
    async def test_health_check_single_source(self, manager, mock_source):
        """测试单数据源健康检查"""
        manager.register(mock_source)

        result = await manager.health_check("test_source")

        assert result["source"] == "test_source"
        assert result["status"] == "healthy"
        assert "response_time_ms" in result

    @pytest.mark.asyncio
    async def test_health_check_all_sources(self, manager, mock_source):
        """测试所有数据源健康检查"""
        manager.register(mock_source)

        result = await manager.health_check()

        assert result["total_sources"] == 1
        assert result["healthy_count"] == 1
        assert result["degraded_count"] == 0
        assert result["unhealthy_count"] == 0

    @pytest.mark.asyncio
    async def test_get_source_health(self, manager):
        """测试获取数据源健康状态"""
        # 创建 mock source
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = "test_source"
        mock_source.source_type = DataSourceType.STOCK
        mock_source.fetch = AsyncMock(return_value=DataSourceResult(
            success=True,
            data={"price": 100},
            source="test_source"
        ))
        mock_source.health_check = AsyncMock(return_value=True)

        manager.register(mock_source)
        await manager.health_check("test_source")

        result = manager.get_source_health("test_source")

        assert result is not None
        assert result.source_name == "test_source"
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_get_health_history(self, manager):
        """测试获取健康历史"""
        # 创建 mock source
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = "test_source"
        mock_source.source_type = DataSourceType.STOCK
        mock_source.fetch = AsyncMock(return_value=DataSourceResult(
            success=True,
            data={"price": 100},
            source="test_source"
        ))
        mock_source.health_check = AsyncMock(return_value=True)

        manager.register(mock_source)
        await manager.health_check("test_source")
        await manager.health_check("test_source")

        history = manager.get_health_history("test_source", limit=1)
        assert len(history) == 1

    def test_get_health_statistics(self, manager, mock_source):
        """测试获取健康统计"""
        stats = manager.get_health_statistics()
        assert "total_sources_checked" in stats
        assert "sources" in stats

    @pytest.mark.asyncio
    async def test_get_unhealthy_sources(self, manager):
        """测试获取不健康的数据源"""
        # 创建 mock source
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = "test_source"
        mock_source.source_type = DataSourceType.STOCK
        mock_source.fetch = AsyncMock(return_value=DataSourceResult(
            success=True,
            data={"price": 100},
            source="test_source"
        ))
        mock_source.health_check = AsyncMock(return_value=True)

        manager.register(mock_source)

        unhealthy = manager.get_unhealthy_sources()
        assert unhealthy == []

    @pytest.mark.asyncio
    async def test_get_healthy_sources(self, manager):
        """测试获取健康的数据源"""
        # 创建 mock source
        mock_source = MagicMock(spec=DataSource)
        mock_source.name = "test_source"
        mock_source.source_type = DataSourceType.STOCK
        mock_source.fetch = AsyncMock(return_value=DataSourceResult(
            success=True,
            data={"price": 100},
            source="test_source"
        ))
        mock_source.health_check = AsyncMock(return_value=True)

        manager.register(mock_source)
        await manager.health_check("test_source")

        healthy = manager.get_healthy_sources()
        assert "test_source" in healthy

    @pytest.mark.asyncio
    async def test_fetch_with_health_aware(self, manager, mock_source):
        """测试健康感知的获取"""
        manager.register(mock_source)

        result = await manager.fetch(
            DataSourceType.STOCK,
            health_aware=True
        )

        assert result.success is True
        assert result.data["price"] == 100

    @pytest.mark.asyncio
    async def test_fetch_health_aware_failover(self, manager, mock_source):
        """测试健康感知故障切换"""
        # 创建两个数据源，一个健康一个不健康
        healthy_source = MagicMock(spec=DataSource)
        healthy_source.name = "healthy"
        healthy_source.source_type = DataSourceType.STOCK
        healthy_source.fetch = AsyncMock(return_value=DataSourceResult(
            success=True,
            data={"price": 100},
            source="healthy"
        ))
        healthy_source.health_check = AsyncMock(return_value=True)

        unhealthy_source = MagicMock(spec=DataSource)
        unhealthy_source.name = "unhealthy"
        unhealthy_source.source_type = DataSourceType.STOCK
        unhealthy_source.fetch = AsyncMock(return_value=DataSourceResult(
            success=False,
            error="Source down",
            source="unhealthy"
        ))
        unhealthy_source.health_check = AsyncMock(return_value=False)

        manager.register(healthy_source)
        manager.register(unhealthy_source)

        # 先执行健康检查
        await manager.health_check_all_sources()

        # 获取数据时应优先选择健康的数据源
        result = await manager.fetch(
            DataSourceType.STOCK,
            health_aware=True
        )

        assert result.success is True
        assert result.source == "healthy"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
