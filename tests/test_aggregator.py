"""
数据聚合器测试
"""

from src.datasources.aggregator import (
    LoadBalancedAggregator,
    SameSourceAggregator,
)


class TestDataAggregator:
    """数据聚合器基类测试"""

    def test_aggregator_types(self):
        """测试聚合器类型"""
        # SameSourceAggregator - 相同数据源聚合
        assert SameSourceAggregator is not None
        # LoadBalancedAggregator - 负载均衡聚合
        assert LoadBalancedAggregator is not None


class TestSameSourceAggregator:
    """同源聚合器测试"""

    def test_aggregator_exists(self):
        """测试聚合器存在"""
        assert SameSourceAggregator is not None


class TestLoadBalancedAggregator:
    """负载均衡聚合器测试"""

    def test_aggregator_exists(self):
        """测试聚合器存在"""
        assert LoadBalancedAggregator is not None
