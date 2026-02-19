"""
数据源管理器测试
"""

import asyncio

import pytest

from src.datasources.base import DataSource, DataSourceResult, DataSourceType
from src.datasources.manager import DataSourceConfig, DataSourceManager, create_default_manager


class MockDataSource(DataSource):
    """用于测试的模拟数据源"""
    
    def __init__(self, name: str, source_type: DataSourceType = DataSourceType.FUND, should_fail: bool = False):
        super().__init__(name=name, source_type=source_type, timeout=5.0)
        self.should_fail = should_fail
        self.fetch_count = 0
    
    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        self.fetch_count += 1
        if self.should_fail:
            return DataSourceResult(
                success=False,
                error=f"Mock failure for {self.name}",
                timestamp=0,
                source=self.name
            )
        return DataSourceResult(
            success=True,
            data={"name": self.name, "args": args, "kwargs": kwargs},
            timestamp=0,
            source=self.name
        )
    
    async def fetch_batch(self, items: list) -> list[DataSourceResult]:
        results = []
        for item in items:
            result = await self.fetch(item)
            results.append(result)
        return results
    
    async def close(self):
        pass


class TestDataSourceConfig:
    """数据源配置测试"""
    
    def test_config_creation(self):
        """测试配置创建"""
        config = DataSourceConfig(
            source_class=MockDataSource,
            name="test_source",
            source_type=DataSourceType.FUND,
            enabled=True,
            priority=1,
            config={"timeout": 10}
        )
        
        assert config.source_class == MockDataSource
        assert config.name == "test_source"
        assert config.source_type == DataSourceType.FUND
        assert config.enabled is True
        assert config.priority == 1
        assert config.config["timeout"] == 10
    
    def test_default_values(self):
        """测试默认值"""
        config = DataSourceConfig(
            source_class=MockDataSource,
            name="test",
            source_type=DataSourceType.FUND
        )
        
        assert config.enabled is True
        assert config.priority == 0
        assert config.config == {}


class TestDataSourceManager:
    """数据源管理器测试"""
    
    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return DataSourceManager(max_concurrent=5, enable_load_balancing=False)
    
    @pytest.fixture
    def mock_source1(self):
        return MockDataSource("source1", DataSourceType.FUND)
    
    @pytest.fixture
    def mock_source2(self):
        return MockDataSource("source2", DataSourceType.FUND)
    
    @pytest.fixture
    def mock_source3(self):
        return MockDataSource("source3", DataSourceType.COMMODITY)
    
    def test_init(self):
        """测试初始化"""
        manager = DataSourceManager()
        
        assert manager._max_concurrent == 10
        assert manager._enable_load_balancing is False
        assert len(manager._sources) == 0
    
    def test_register(self, manager, mock_source1):
        """测试注册数据源"""
        manager.register(mock_source1)
        
        assert "source1" in manager._sources
        assert mock_source1.source_type in manager._type_sources
        assert "source1" in manager._type_sources[DataSourceType.FUND]
    
    def test_register_duplicate(self, manager, mock_source1):
        """测试重复注册"""
        manager.register(mock_source1)
        
        with pytest.raises(ValueError, match="已注册"):
            manager.register(mock_source1)
    
    def test_unregister(self, manager, mock_source1):
        """测试注销数据源"""
        manager.register(mock_source1)
        manager.unregister("source1")
        
        assert "source1" not in manager._sources
        assert "source1" not in manager._type_sources[DataSourceType.FUND]
    
    def test_unregister_not_found(self, manager):
        """测试注销不存在的数据源"""
        with pytest.raises(ValueError, match="未注册"):
            manager.unregister("nonexistent")
    
    def test_get_source(self, manager, mock_source1):
        """测试获取数据源"""
        manager.register(mock_source1)
        
        source = manager.get_source("source1")
        assert source == mock_source1
        
        source = manager.get_source("nonexistent")
        assert source is None
    
    def test_get_sources_by_type(self, manager, mock_source1, mock_source3):
        """测试按类型获取数据源"""
        manager.register(mock_source1)
        manager.register(mock_source3)
        
        fund_sources = manager.get_sources_by_type(DataSourceType.FUND)
        assert len(fund_sources) == 1
        assert fund_sources[0].name == "source1"
        
        commodity_sources = manager.get_sources_by_type(DataSourceType.COMMODITY)
        assert len(commodity_sources) == 1
        assert commodity_sources[0].name == "source3"
    
    def test_get_ordered_sources_default(self, manager, mock_source1, mock_source2):
        """测试默认排序（按优先级）"""
        manager.register(mock_source1)
        manager.register(mock_source2, DataSourceConfig(
            source_class=MockDataSource,
            name="source2",
            source_type=DataSourceType.FUND,
            priority=1  # 高优先级
        ))
        
        sources = manager._get_ordered_sources(DataSourceType.FUND)
        
        # source1 优先级为 0（默认），source2 优先级为 1
        # priority 越小越高，所以 source1 应该在前面
        assert sources[0].name == "source1"
    
    def test_get_ordered_sources_load_balancing(self, manager, mock_source1, mock_source2):
        """测试负载均衡模式"""
        manager_load_balanced = DataSourceManager(enable_load_balancing=True)
        manager_load_balanced.register(mock_source1)
        manager_load_balanced.register(mock_source2)
        
        # 多次调用应该轮询
        results = []
        for _ in range(4):
            sources = manager_load_balanced._get_ordered_sources(DataSourceType.FUND)
            results.append(sources[0].name)
        
        # 应该轮换选择
        assert results[0] != results[1] or results[1] != results[2]
    
    @pytest.mark.asyncio
    async def test_fetch_success(self, manager, mock_source1):
        """测试成功获取数据"""
        manager.register(mock_source1)
        
        result = await manager.fetch(DataSourceType.FUND, "test_arg", key="value")
        
        assert result.success is True
        assert result.data["name"] == "source1"
        assert result.data["kwargs"]["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_fetch_failover(self, manager):
        """测试故障切换"""
        source1 = MockDataSource("source1", DataSourceType.FUND, should_fail=True)
        source2 = MockDataSource("source2", DataSourceType.FUND)
        
        manager.register(source1)
        manager.register(source2)
        
        result = await manager.fetch(DataSourceType.FUND)
        
        # 应该成功，因为 source2 会成功
        assert result.success is True
        assert result.source == "source2"
    
    @pytest.mark.asyncio
    async def test_fetch_all_failed(self, manager):
        """测试所有数据源都失败"""
        source1 = MockDataSource("source1", DataSourceType.FUND, should_fail=True)
        source2 = MockDataSource("source2", DataSourceType.FUND, should_fail=True)
        
        manager.register(source1)
        manager.register(source2)
        
        result = await manager.fetch(DataSourceType.FUND)
        
        assert result.success is False
        assert "所有数据源均失败" in result.error
    
    @pytest.mark.asyncio
    async def test_fetch_no_sources(self, manager):
        """测试没有数据源"""
        result = await manager.fetch(DataSourceType.FUND)
        
        assert result.success is False
        assert "没有可用的数据源" in result.error
    
    @pytest.mark.asyncio
    async def test_fetch_with_source(self, manager, mock_source1):
        """测试指定数据源获取"""
        manager.register(mock_source1)
        
        result = await manager.fetch_with_source("source1", "arg1", key="value")
        
        assert result.success is True
        assert result.source == "source1"
    
    @pytest.mark.asyncio
    async def test_fetch_with_source_not_found(self, manager):
        """测试指定不存在的数据源"""
        result = await manager.fetch_with_source("nonexistent")
        
        assert result.success is False
        assert "不存在" in result.error
    
    @pytest.mark.asyncio
    async def test_fetch_batch(self, manager):
        """测试批量获取"""
        source1 = MockDataSource("source1", DataSourceType.FUND)
        
        manager.register(source1)
        
        params_list = [
            {"args": ("code1",), "kwargs": {}},
            {"args": ("code2",), "kwargs": {}},
            {"args": ("code3",), "kwargs": {}},
        ]
        
        results = await manager.fetch_batch(DataSourceType.FUND, params_list)
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_fetch_batch_parallel(self, manager):
        """测试并行批量获取"""
        source1 = MockDataSource("source1", DataSourceType.FUND)
        
        manager.register(source1)
        
        params_list = [{"args": (f"code{i}",), "kwargs": {}} for i in range(5)]
        
        results = await manager.fetch_batch(DataSourceType.FUND, params_list, parallel=True)
        
        assert len(results) == 5
    
    def test_set_source_enabled(self, manager, mock_source1):
        """测试设置数据源启用/禁用"""
        manager.register(mock_source1)
        
        manager.set_source_enabled("source1", False)
        
        config = manager._source_configs["source1"]
        assert config.enabled is False
        
        manager.set_source_enabled("source1", True)
        
        config = manager._source_configs["source1"]
        assert config.enabled is True
    
    def test_set_source_priority(self, manager, mock_source1):
        """测试设置数据源优先级"""
        manager.register(mock_source1)
        
        manager.set_source_priority("source1", 5)
        
        config = manager._source_configs["source1"]
        assert config.priority == 5
    
    def test_list_sources(self, manager, mock_source1, mock_source3):
        """测试列出数据源"""
        manager.register(mock_source1)
        manager.register(mock_source3)
        
        sources = manager.list_sources()
        
        assert len(sources) == 2
        source_names = [s["name"] for s in sources]
        assert "source1" in source_names
        assert "source3" in source_names
    
    def test_get_statistics(self, manager, mock_source1):
        """测试获取统计数据"""
        manager.register(mock_source1)
        
        # 执行一些请求
        loop = asyncio.new_event_loop()
        loop.run_until_complete(manager.fetch(DataSourceType.FUND))
        
        stats = manager.get_statistics()
        
        assert "total_requests" in stats
        assert "registered_sources" in stats
        assert "source1" in stats["registered_sources"]
    
    @pytest.mark.asyncio
    async def test_close_all(self, manager, mock_source1):
        """测试关闭所有数据源"""
        manager.register(mock_source1)
        
        await manager.close_all()
        
        # 应该正常关闭，不会抛出异常


class TestCreateDefaultManager:
    """默认管理器工厂测试"""
    
    @pytest.mark.asyncio
    async def test_create_default_manager(self):
        """测试创建默认管理器"""
        manager = create_default_manager()
        
        assert manager is not None
        assert isinstance(manager, DataSourceManager)
    
    @pytest.mark.asyncio
    async def test_default_manager_sources(self):
        """测试默认管理器的数据源"""
        manager = create_default_manager()
        
        # 列出所有数据源
        manager.list_sources()
        
        # 获取基金数据源
        manager.get_sources_by_type(DataSourceType.FUND)
    
    def test_create_with_load_balancing(self):
        """测试创建带负载均衡的管理器"""
        manager = create_default_manager(enable_load_balancing=True)
        
        assert manager._enable_load_balancing is True
