"""
缓存清理任务模块

提供后台缓存清理功能：
1. 启动时清理过期数据
2. 定时任务定期清理
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CacheCleaner:
    """缓存清理器

    负责清理各类过期缓存数据：
    - 文件缓存 (DataCache)
    - 双层缓存 (DualLayerCache)
    - 数据库历史数据
    """

    def __init__(
        self,
        cleanup_interval: int = 3600,  # 默认每小时清理一次
        days_before_expired: int = 7,   # 默认清理 7 天前的数据
    ):
        """
        初始化缓存清理器

        Args:
            cleanup_interval: 清理任务执行间隔（秒），默认 1 小时
            days_before_expired: 清理多少天前的过期数据，默认 7 天
        """
        self.cleanup_interval = cleanup_interval
        self.days_before_expired = days_before_expired
        self._cleanup_task: asyncio.Task | None = None
        self._running = False

        # 缓存目录路径 (从环境变量或默认路径)
        config_dir = Path.home() / '.fund-tui'
        self._fund_cache_dir = config_dir / 'cache' / 'fund'
        self._commodity_cache_dir = config_dir / 'cache' / 'commodity'
        self._news_cache_dir = config_dir / 'cache' / 'news'

    async def cleanup_on_startup(self) -> dict[str, Any]:
        """
        启动时清理过期数据

        Returns:
            dict: 清理结果统计
        """
        logger.info("开始启动时缓存清理...")

        results = {
            "started_at": datetime.now().isoformat(),
            "fund_history_deleted": 0,
            "news_deleted": 0,
            "file_cache_cleaned": 0,
            "intraday_cache_cleaned": 0,
            "total_files_deleted": 0,
            "errors": []
        }

        try:
            # 1. 清理数据库中的旧历史数据
            deleted_history = await self._cleanup_database_history()
            results["fund_history_deleted"] = deleted_history
            logger.info(f"已清理 {deleted_history} 条基金历史记录")
        except Exception as e:
            error_msg = f"清理基金历史记录失败: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        try:
            # 2. 清理过期新闻
            deleted_news = await self._cleanup_news()
            results["news_deleted"] = deleted_news
            logger.info(f"已清理 {deleted_news} 条过期新闻")
        except Exception as e:
            error_msg = f"清理新闻缓存失败: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        try:
            # 3. 清理文件缓存
            files_deleted = await self._cleanup_file_cache()
            results["file_cache_cleaned"] = files_deleted
            logger.info(f"已清理 {files_deleted} 个文件缓存")
        except Exception as e:
            error_msg = f"清理文件缓存失败: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        try:
            # 4. 清理日内缓存
            intraday_deleted = await self._cleanup_intraday_cache()
            results["intraday_cache_cleaned"] = intraday_deleted
            logger.info(f"已清理 {intraday_deleted} 条日内缓存")
        except Exception as e:
            error_msg = f"清理日内缓存失败: {e}"
            logger.error(error_msg)
            results["errors"].append(error_msg)

        results["completed_at"] = datetime.now().isoformat()
        logger.info(f"启动时缓存清理完成: {results}")

        return results

    async def start_background_cleanup(self):
        """启动后台定时清理任务"""
        if self._running:
            logger.warning("清理任务已在运行中")
            return

        self._running = True
        logger.info(f"启动后台清理任务，间隔: {self.cleanup_interval}秒")

        async def periodic_cleanup():
            """定期执行清理任务"""
            while self._running:
                try:
                    # 清理过期文件缓存（不清理数据库，因为数据库已有 TTL 机制）
                    files_deleted = await self._cleanup_file_cache()
                    logger.info(f"定期清理: 已清理 {files_deleted} 个过期文件缓存")

                except Exception as e:
                    logger.error(f"定期清理任务错误: {e}")

                await asyncio.sleep(self.cleanup_interval)

        # 启动后台任务
        self._cleanup_task = asyncio.create_task(periodic_cleanup())

    def stop(self):
        """停止后台清理任务"""
        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                self._cleanup_task.result()
            except asyncio.CancelledError:
                pass

        logger.info("后台清理任务已停止")

    async def _cleanup_database_history(self) -> int:
        """清理数据库中的旧历史数据"""
        try:
            from src.db.database import DatabaseManager, FundHistoryDAO

            db = DatabaseManager()
            dao = FundHistoryDAO(db)

            # 清理 7 天前的历史数据
            deleted = dao.delete_old_history(days=self.days_before_expired)

            # 清理碎片
            db.vacuum()

            return deleted
        except Exception as e:
            logger.error(f"清理数据库历史记录失败: {e}")
            return 0

    async def _cleanup_news(self) -> int:
        """清理过期新闻（24小时前）"""
        try:
            from src.db.database import DatabaseManager, NewsDAO

            db = DatabaseManager()
            dao = NewsDAO(db)

            # 清理 24 小时前的新闻
            deleted = dao.cleanup_old_news(hours=24)

            return deleted
        except Exception as e:
            logger.error(f"清理过期新闻失败: {e}")
            return 0

    async def _cleanup_file_cache(self) -> int:
        """清理过期的文件缓存"""
        deleted_count = 0

        cache_dirs = [
            self._fund_cache_dir,
            self._commodity_cache_dir,
            self._news_cache_dir,
        ]

        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue

            try:
                for cache_file in cache_dir.glob('*.json'):
                    try:
                        # 检查文件是否过期（超过 7 天）
                        file_mtime = cache_file.stat().st_mtime
                        file_date = datetime.fromtimestamp(file_mtime)
                        cutoff_date = datetime.now() - timedelta(days=self.days_before_expired)

                        if file_date < cutoff_date:
                            cache_file.unlink(missing_ok=True)
                            deleted_count += 1
                    except (OSError, ValueError) as e:
                        logger.warning(f"检查缓存文件失败: {cache_file}, error: {e}")
            except Exception as e:
                logger.warning(f"清理缓存目录失败: {cache_dir}, error: {e}")

        return deleted_count

    async def _cleanup_intraday_cache(self) -> int:
        """清理过期的日内缓存"""
        try:
            from src.db.database import DatabaseManager, FundIntradayCacheDAO

            db = DatabaseManager()
            dao = FundIntradayCacheDAO(db)

            # 清理过期缓存（60秒前）
            deleted = dao.cleanup_expired_cache()

            return deleted
        except Exception as e:
            logger.error(f"清理日内缓存失败: {e}")
            return 0

    async def cleanup_all(self) -> dict[str, Any]:
        """
        执行完整清理（包括数据库）

        Returns:
            dict: 清理结果统计
        """
        return await self.cleanup_on_startup()

    def get_status(self) -> dict[str, Any]:
        """
        获取清理器状态

        Returns:
            dict: 状态信息
        """
        return {
            "running": self._running,
            "cleanup_interval": self.cleanup_interval,
            "days_before_expired": self.days_before_expired,
            "cache_dirs": {
                "fund": str(self._fund_cache_dir),
                "commodity": str(self._commodity_cache_dir),
                "news": str(self._news_cache_dir),
            }
        }


# 单例实例
_cache_cleaner: CacheCleaner | None = None


def get_cache_cleaner() -> CacheCleaner:
    """获取缓存清理器单例"""
    global _cache_cleaner
    if _cache_cleaner is None:
        _cache_cleaner = CacheCleaner()
    return _cache_cleaner


async def startup_cleanup() -> dict[str, Any]:
    """
    执行启动时清理

    Returns:
        dict: 清理结果统计
    """
    cleaner = get_cache_cleaner()
    return await cleaner.cleanup_on_startup()


def start_background_cleanup_task(interval: int = 3600):
    """
    启动后台清理任务

    Args:
        interval: 执行间隔（秒）
    """
    cleaner = get_cache_cleaner()
    cleaner.cleanup_interval = interval
    asyncio.create_task(cleaner.start_background_cleanup())
