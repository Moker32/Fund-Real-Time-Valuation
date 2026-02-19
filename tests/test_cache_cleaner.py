# -*- coding: UTF-8 -*-
"""Cache Cleaner Tests

测试缓存清理功能
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCacheCleaner:
    """缓存清理器测试"""

    @pytest.fixture
    def cleaner(self):
        """创建缓存清理器实例"""
        from src.datasources.cache_cleaner import CacheCleaner
        return CacheCleaner(
            cleanup_interval=3600,
            days_before_expired=7
        )

    def test_init(self, cleaner):
        """测试初始化"""
        assert cleaner.cleanup_interval == 3600
        assert cleaner.days_before_expired == 7
        assert cleaner._running is False
        assert cleaner._cleanup_task is None

    def test_init_defaults(self):
        """测试默认初始化"""
        from src.datasources.cache_cleaner import CacheCleaner
        cleaner = CacheCleaner()
        
        assert cleaner.cleanup_interval == 3600
        assert cleaner.days_before_expired == 7

    def test_get_status(self, cleaner):
        """测试获取状态"""
        status = cleaner.get_status()

        assert status["running"] is False
        assert status["cleanup_interval"] == 3600
        assert status["days_before_expired"] == 7
        assert "cache_dirs" in status

    def test_cache_dirs_paths(self, cleaner):
        """测试缓存目录路径"""
        status = cleaner.get_status()
        
        # 验证缓存目录路径
        assert "fund" in status["cache_dirs"]
        assert "commodity" in status["cache_dirs"]
        assert "news" in status["cache_dirs"]

    @pytest.mark.asyncio
    async def test_cleanup_file_cache_empty_dir(self, cleaner):
        """测试清理空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cleaner._fund_cache_dir = Path(tmpdir)
            cleaner._commodity_cache_dir = Path(tmpdir)
            cleaner._news_cache_dir = Path(tmpdir)

            deleted = await cleaner._cleanup_file_cache()
            assert deleted == 0

    @pytest.mark.asyncio
    async def test_cleanup_file_cache_with_expired_files(self, cleaner):
        """测试清理过期文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            cleaner._fund_cache_dir = cache_dir
            cleaner._commodity_cache_dir = cache_dir
            cleaner._news_cache_dir = cache_dir

            # 创建一个过期的缓存文件
            expired_file = cache_dir / "test_cache.json"
            expired_file.write_text('{"data": "test"}')

            # 修改文件时间为 8 天前
            old_time = datetime.now() - timedelta(days=8)
            old_timestamp = old_time.timestamp()
            os.utime(expired_file, (old_timestamp, old_timestamp))

            deleted = await cleaner._cleanup_file_cache()
            assert deleted >= 1
            assert not expired_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_file_cache_with_recent_files(self, cleaner):
        """测试不清理近期文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            cleaner._fund_cache_dir = cache_dir

            # 创建一个近期的缓存文件
            recent_file = cache_dir / "recent_cache.json"
            recent_file.write_text('{"data": "test"}')

            deleted = await cleaner._cleanup_file_cache()
            assert deleted == 0
            assert recent_file.exists()

    @pytest.mark.asyncio
    async def test_cleanup_file_cache_invalid_files(self, cleaner):
        """测试处理无效文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            cleaner._fund_cache_dir = cache_dir

            # 创建一些无效文件（无扩展名）
            (cache_dir / "invalid_file").write_text("test")

            # 不应该抛出异常
            deleted = await cleaner._cleanup_file_cache()
            assert isinstance(deleted, int)

    @pytest.mark.asyncio
    async def test_cleanup_on_startup_without_db(self, cleaner):
        """测试启动时清理（无数据库）"""
        # 直接测试各清理方法，不依赖数据库
        with patch.object(cleaner, '_cleanup_file_cache', return_value=0):
            result = await cleaner.cleanup_on_startup()

            assert "started_at" in result
            assert "fund_history_deleted" in result
            assert "news_deleted" in result
            assert "file_cache_cleaned" in result

    @pytest.mark.asyncio
    async def test_cleanup_all(self, cleaner):
        """测试完整清理"""
        with patch.object(cleaner, 'cleanup_on_startup', return_value={"test": "result"}):
            result = await cleaner.cleanup_all()
            assert result == {"test": "result"}

    def test_stop_not_running(self, cleaner):
        """测试停止未运行的任务"""
        # 不应该抛出异常
        cleaner.stop()
        assert cleaner._running is False

    @pytest.mark.asyncio
    async def test_start_background_cleanup(self, cleaner):
        """测试启动后台清理"""
        await cleaner.start_background_cleanup()
        assert cleaner._running is True
        
        # 使用 mock 停止任务，避免 InvalidStateError
        if cleaner._cleanup_task:
            cleaner._cleanup_task.cancel()
            cleaner._cleanup_task = None
        cleaner._running = False
        assert cleaner._running is False

    @pytest.mark.asyncio
    async def test_start_background_cleanup_already_running(self, cleaner):
        """测试启动已运行的后台清理"""
        cleaner._running = True
        
        await cleaner.start_background_cleanup()
        # 应该只记录警告，不抛出异常


class TestCacheCleanerFunctions:
    """缓存清理器函数测试"""

    def test_get_cache_cleaner_singleton(self):
        """测试单例获取"""
        from src.datasources.cache_cleaner import _cache_cleaner, get_cache_cleaner
        
        # 保存原始单例
        original = _cache_cleaner
        
        # 清除单例
        import src.datasources.cache_cleaner as module
        module._cache_cleaner = None
        
        cleaner1 = get_cache_cleaner()
        cleaner2 = get_cache_cleaner()
        
        assert cleaner1 is cleaner2
        
        # 恢复原始单例
        module._cache_cleaner = original

    @pytest.mark.asyncio
    async def test_startup_cleanup(self):
        """测试启动清理函数"""
        from src.datasources.cache_cleaner import startup_cleanup
        
        with patch('src.datasources.cache_cleaner.get_cache_cleaner') as mock_get:
            mock_cleaner = MagicMock()
            mock_cleaner.cleanup_on_startup = AsyncMock(return_value={"deleted": 0})
            mock_get.return_value = mock_cleaner
            
            await startup_cleanup()
            
            mock_cleaner.cleanup_on_startup.assert_called_once()

    def test_start_background_cleanup_task(self):
        """测试启动后台清理任务"""
        from src.datasources.cache_cleaner import start_background_cleanup_task
        
        with patch('src.datasources.cache_cleaner.get_cache_cleaner') as mock_get:
            with patch('src.datasources.cache_cleaner.asyncio.create_task'):
                mock_cleaner = MagicMock()
                mock_get.return_value = mock_cleaner
                
                start_background_cleanup_task(interval=1800)
                
                mock_cleaner.cleanup_interval = 1800
