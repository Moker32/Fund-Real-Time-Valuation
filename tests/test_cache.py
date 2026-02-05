# -*- coding: UTF-8 -*-
"""数据缓存模块测试用例

使用 TDD 流程开发：
1. 先编写测试（预期失败）
2. 运行测试（验证失败）
3. 实现功能
4. 运行测试（验证通过）
"""

import pytest
import tempfile
import os
import time
from pathlib import Path
import sys

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.cache import DataCache


@pytest.fixture
def temp_cache_dir():
    """创建临时缓存目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def cache(temp_cache_dir):
    """创建 DataCache 实例"""
    return DataCache(cache_dir=Path(temp_cache_dir))


class TestDataCache:
    """DataCache 测试类"""

    def test_cache_set_and_get(self, cache):
        """测试设置和获取缓存"""
        cache.set("test_key", {"name": "test", "value": 123}, ttl_seconds=300)
        result = cache.get("test_key")

        assert result is not None
        assert result["name"] == "test"
        assert result["value"] == 123

    def test_cache_expiration(self, cache):
        """测试缓存过期"""
        # 设置 1 秒过期的缓存
        cache.set("expire_key", "expire_value", ttl_seconds=1)

        # 立即获取应该存在
        assert cache.get("expire_key") == "expire_value"

        # 等待过期
        time.sleep(1.5)

        # 过期后应该返回 None
        assert cache.get("expire_key") is None

    def test_cache_miss(self, cache):
        """测试缓存未命中返回 None"""
        result = cache.get("nonexistent_key")
        assert result is None

    def test_cache_clear_single_key(self, cache):
        """测试清除单个缓存"""
        cache.set("key_to_clear", "value", ttl_seconds=300)
        assert cache.get("key_to_clear") == "value"

        cache.clear("key_to_clear")
        assert cache.get("key_to_clear") is None

    def test_cache_clear_all(self, cache):
        """测试清除所有缓存"""
        cache.set("key1", "value1", ttl_seconds=300)
        cache.set("key2", "value2", ttl_seconds=300)

        cache.clear()  # 不传参数清除所有

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_update_existing(self, cache):
        """测试更新已存在的缓存"""
        cache.set("update_key", "old_value", ttl_seconds=300)
        cache.set("update_key", "new_value", ttl_seconds=300)

        result = cache.get("update_key")
        assert result == "new_value"

    def test_cache_with_complex_data(self, cache):
        """测试缓存复杂数据"""
        complex_data = {
            "funds": [
                {"code": "161039", "name": "富国中证新能源汽车指数", "value": 1.234},
                {"code": "161725", "name": "招商中证白酒指数", "value": 2.345},
            ],
            "timestamp": "2024-01-15T10:00:00",
            "metadata": {"source": "akshare", "version": "1.0"},
        }

        cache.set("complex_data", complex_data, ttl_seconds=300)
        result = cache.get("complex_data")

        assert result == complex_data
        assert len(result["funds"]) == 2
        assert result["metadata"]["source"] == "akshare"

    def test_cache_default_ttl(self, cache):
        """测试默认 TTL（5分钟）"""
        cache.set("default_ttl", "value")

        # 4分钟内应该有效
        time.sleep(0.1)
        assert cache.get("default_ttl") == "value"

    def test_cache_persistent_directory(self, temp_cache_dir):
        """测试缓存目录持久化"""
        cache_dir = Path(temp_cache_dir) / "persistent_cache"
        cache = DataCache(cache_dir=cache_dir)

        # 设置缓存
        cache.set("persistent_key", "persistent_value", ttl_seconds=300)

        # 创建新的缓存实例（模拟重启）
        cache2 = DataCache(cache_dir=cache_dir)

        # 应该能从持久化存储中读取
        assert cache2.get("persistent_key") == "persistent_value"
