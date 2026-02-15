"""
双层缓存测试
"""

import asyncio

import pytest

from src.datasources.dual_cache import DualLayerCache, MemoryCache


class TestMemoryCache:
    """内存缓存测试"""

    @pytest.fixture
    def cache(self):
        return MemoryCache(max_size=10, ttl_seconds=1)

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache):
        """测试缓存设置和获取"""
        await cache.set("key1", {"value": "test"})
        result = await cache.get("key1")
        assert result == {"value": "test"}

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        """测试缓存未命中"""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_ttl(self, cache):
        """测试 TTL 过期"""
        await cache.set("key1", "value1", ttl_seconds=1)
        # 立即获取应该命中
        result = await cache.get("key1")
        assert result == "value1"
        # 等待过期
        await asyncio.sleep(1.1)
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self, cache):
        """测试 LRU 淘汰"""
        # 设置 max_size=2
        small_cache = MemoryCache(max_size=2, ttl_seconds=60)
        await small_cache.set("key1", "value1")
        await small_cache.set("key2", "value2")
        # 这应该淘汰 key1
        await small_cache.set("key3", "value3")
        
        # key1 应该被淘汰
        result = await small_cache.get("key1")
        assert result is None
        # key2 和 key3 应该还在
        assert await small_cache.get("key2") == "value2"
        assert await small_cache.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache):
        """测试缓存清空"""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        cache.clear()  # MemoryCache.clear() 是同步方法
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None


class TestDualLayerCache:
    """双层缓存测试"""

    @pytest.fixture
    def cache(self, tmp_path):
        return DualLayerCache(
            cache_dir=tmp_path / "cache",
            memory_ttl=1,
            file_ttl=60,
            max_memory_items=10,
        )

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache):
        """测试缓存设置和获取"""
        await cache.set("key1", {"data": "test"})
        result, cache_type = await cache.get("key1")
        assert result == {"data": "test"}
        assert cache_type in ("memory", "file")

    @pytest.mark.asyncio
    async def test_cache_file_fallback_after_memory_expired(self, cache, tmp_path):
        """测试内存缓存过期后回退到文件缓存"""
        # 先设置缓存
        await cache.set("key1", "value1")
        # 验证内存缓存有数据
        result, cache_type = await cache.get("key1")
        assert result == "value1"
        
        # 等待内存缓存过期
        await asyncio.sleep(1.1)
        
        # 内存缓存应该过期，但文件缓存还有
        result, cache_type = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache):
        """测试缓存清空"""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        result1, _ = await cache.get("key1")
        result2, _ = await cache.get("key2")
        assert result1 is None
        assert result2 is None
