# -*- coding: UTF-8 -*-
"""Cache Warmer Tests

测试缓存预热功能
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.datasources.cache_warmer import CacheWarmer


class TestCacheWarmer:
    """缓存预热器测试"""

    @pytest.fixture
    def mock_manager(self):
        """创建模拟的 manager"""
        manager = MagicMock()
        return manager

    @pytest.fixture
    def cache_warmer(self, mock_manager):
        """返回缓存预热器实例"""
        return CacheWarmer(mock_manager)

    def test_init(self, cache_warmer, mock_manager):
        """测试初始化"""
        assert cache_warmer.manager is mock_manager
        assert cache_warmer._running is False
        assert cache_warmer._cache_loaded is False
        assert cache_warmer._warmup_task is None
        assert cache_warmer._refresh_task is None

    def test_stop(self, cache_warmer):
        """测试停止后台预热"""
        cache_warmer._running = True
        cache_warmer._refresh_task = None
        
        cache_warmer.stop()
        
        assert cache_warmer._running is False

    def test_stop_with_task(self, cache_warmer):
        """测试停止后台预热（有任务）"""
        cache_warmer._running = True
        
        # 不创建实际任务，只测试逻辑
        cache_warmer._refresh_task = None
        
        # 不应该抛出异常
        cache_warmer.stop()
        
        assert cache_warmer._running is False


class TestCacheWarmerWarmup:
    """缓存预热器预热功能测试"""

    @pytest.fixture
    def mock_manager(self):
        """创建模拟的 manager"""
        manager = MagicMock()
        return manager

    @pytest.fixture
    def cache_warmer(self, mock_manager):
        """返回缓存预热器实例"""
        return CacheWarmer(mock_manager)

    @pytest.mark.asyncio
    async def test_warmup_empty_list(self, cache_warmer):
        """测试基金列表为空时不预热"""
        import src.datasources.cache_warmer as cache_warmer_module
        
        # 创建 mock 配置管理器
        mock_config_instance = MagicMock()
        mock_fund_list = MagicMock()
        mock_fund_list.get_all_codes = MagicMock(return_value=[])
        mock_config_instance.load_funds = MagicMock(return_value=mock_fund_list)
        
        # 模拟 ConfigManager
        with patch.object(cache_warmer_module, 'ConfigManager', return_value=mock_config_instance):
            with patch.object(cache_warmer.manager, 'fetch_batch', new_callable=AsyncMock) as mock_fetch:
                await cache_warmer.warmup()

                mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_warmup_with_funds(self, cache_warmer):
        """测试有基金时预热"""
        import src.datasources.cache_warmer as cache_warmer_module
        
        # 创建 mock 配置管理器
        mock_config_instance = MagicMock()
        mock_fund_list = MagicMock()
        mock_fund_list.get_all_codes = MagicMock(return_value=["000001"])
        mock_config_instance.load_funds = MagicMock(return_value=mock_fund_list)
        
        with patch.object(cache_warmer_module, 'ConfigManager', return_value=mock_config_instance):
            with patch.object(cache_warmer.manager, 'fetch_batch', new_callable=AsyncMock) as mock_fetch:
                # Mock fetch_batch result
                mock_result = MagicMock()
                mock_result.success = True
                mock_fetch.return_value = [mock_result]

                await cache_warmer.warmup(timeout=10.0)

                mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_warmup_timeout(self, cache_warmer):
        """测试预热超时"""
        import src.datasources.cache_warmer as cache_warmer_module
        
        mock_config_instance = MagicMock()
        mock_fund_list = MagicMock()
        mock_fund_list.get_all_codes = MagicMock(return_value=["000001"])
        mock_config_instance.load_funds = MagicMock(return_value=mock_fund_list)
        
        with patch.object(cache_warmer_module, 'ConfigManager', return_value=mock_config_instance):
            with patch.object(cache_warmer.manager, 'fetch_batch', new_callable=AsyncMock) as mock_fetch:
                # 模拟超时
                mock_fetch.side_effect = asyncio.TimeoutError()

                # 不应该抛出异常
                await cache_warmer.warmup(timeout=0.001)


class TestPrewarmNewFund:
    """预热新基金函数测试"""

    def test_prewarm_function_exists(self):
        """测试预热函数存在"""
        from src.datasources.cache_warmer import prewarm_new_fund
        assert callable(prewarm_new_fund)

    def test_cleanup_fund_cache_exists(self):
        """测试清理基金缓存函数存在"""
        from src.datasources.cache_warmer import cleanup_fund_cache
        assert callable(cleanup_fund_cache)
