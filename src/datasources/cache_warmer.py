"""
缓存预热模块

在服务启动时后台预加载数据到缓存，提升首次访问速度。
"""

import asyncio
import json
import logging
from typing import Any

from src.config.manager import ConfigManager
from src.config.models import FundList
from src.datasources.base import DataSourceType

logger = logging.getLogger(__name__)


class CacheWarmer:
    """缓存预热器"""

    def __init__(self, manager: Any):
        """
        初始化预热器

        Args:
            manager: DataSourceManager 实例
        """
        self.manager = manager
        self._warmup_task: asyncio.Task | None = None
        self._refresh_task: asyncio.Task | None = None
        self._running = False
        self._cache_loaded = False  # 标记缓存是否已加载

    async def preload_all_cache(self, timeout: float = 10.0):
        """
        预加载所有文件缓存到内存（同步读取，不触发数据源请求）

        服务启动时立即执行，让首次请求就能使用缓存数据。

        Args:
            timeout: 超时时间（秒）
        """
        try:
            from src.datasources.fund_source import get_fund_cache

            cache = get_fund_cache()
            cache_dir = cache.cache_dir

            if not cache_dir.exists():
                logger.info(f"缓存目录不存在: {cache_dir}")
                self._cache_loaded = True
                return

            logger.info(f"开始预加载缓存目录: {cache_dir}")

            loaded_count = 0
            cache_files = list(cache_dir.glob('*.json'))

            for cache_file in cache_files:
                try:
                    with open(cache_file, encoding='utf-8') as f:
                        cache_data = json.load(f)
                        value = cache_data.get('value')

                    if value is not None:
                        # 解析 key
                        cache_key = cache_data.get('key', cache_file.stem)
                        # 直接设置到内存缓存
                        await cache.memory_cache.set(cache_key, value, cache.file_ttl)
                        loaded_count += 1

                except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                    logger.warning(f"加载缓存文件失败: {cache_file}, error: {e}")

            self._cache_loaded = True
            logger.info(f"缓存预加载完成: {loaded_count}/{len(cache_files)} 个缓存文件")

        except Exception as e:
            logger.error(f"缓存预加载失败: {e}")
            self._cache_loaded = True  # 标记已尝试加载，避免重复

    async def warmup(self, timeout: float = 120.0):
        """
        预热缓存 - 获取所有自选基金数据

        Args:
            timeout: 预热超时时间（秒）
        """
        try:
            # 加载基金列表
            config_manager = ConfigManager()
            fund_list: FundList = config_manager.load_funds()
            fund_codes = fund_list.get_all_codes()

            if not fund_codes:
                logger.info("没有基金需要预热")
                return

            logger.info(f"开始缓存预热，共 {len(fund_codes)} 个基金...")

            # 构建参数列表
            params_list = [{"args": [code]} for code in fund_codes]

            # 使用较长的超时执行预热
            async def fetch_with_timeout():
                return await asyncio.wait_for(
                    self.manager.fetch_batch(DataSourceType.FUND, params_list),
                    timeout=timeout
                )

            results = await fetch_with_timeout()

            # 统计结果
            success_count = sum(1 for r in results if r.success)
            fail_count = len(results) - success_count

            logger.info(f"缓存预热完成: 成功 {success_count}，失败 {fail_count}")

        except asyncio.TimeoutError:
            logger.warning("缓存预热超时")
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")

    async def start_background_warmup(self, interval: int = 300):
        """
        启动后台定时预热任务

        Args:
            interval: 刷新间隔（秒），默认 5 分钟
        """
        if self._running:
            return

        self._running = True

        async def periodic_warmup():
            """定期刷新缓存"""
            while self._running:
                try:
                    await self.warmup(timeout=60.0)
                except Exception as e:
                    logger.error(f"后台预热任务错误: {e}")

                await asyncio.sleep(interval)

        # 先执行一次预热
        await self.warmup(timeout=60.0)

        # 启动后台任务
        self._refresh_task = asyncio.create_task(periodic_warmup())
        logger.info("后台缓存预热任务已启动")

    def stop(self):
        """停止后台预热任务"""
        self._running = False

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                self._refresh_task.result()
            except asyncio.CancelledError:
                pass

        logger.info("后台缓存预热任务已停止")
