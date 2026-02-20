"""
缓存相关的 Celery 任务

提供定时缓存预热和清理任务。
"""

import asyncio
import logging

from src.tasks import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """
    在同步 Celery 任务中运行异步函数

    Args:
        coro: 协程函数

    Returns:
        协程的返回值
    """
    return asyncio.run(coro)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
    name="src.tasks.cache_tasks.preload_all",
)
def preload_all(self):
    """
    预加载所有文件缓存到内存

    服务启动时立即执行，让首次请求就能使用缓存数据。
    """
    logger.info("开始执行预加载所有缓存任务")

    try:
        from src.datasources.cache_warmer import CacheWarmer
        from src.datasources.manager import DataSourceManager

        manager = DataSourceManager()
        warmer = CacheWarmer(manager)

        _run_async(warmer.preload_all_cache())

        logger.info("预加载所有缓存任务完成")
        return {"status": "success", "task": "preload_all"}

    except Exception as e:
        logger.error(f"预加载所有缓存任务失败: {e}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
    name="src.tasks.cache_tasks.preload_funds",
)
def preload_funds(self):
    """
    预热基金信息缓存（名称、类型等）

    在服务启动时并行获取所有基金的名称和类型，缓存起来供后续请求使用。
    """
    logger.info("开始执行预热基金信息缓存任务")

    try:
        from src.datasources.cache_warmer import CacheWarmer
        from src.datasources.manager import DataSourceManager

        manager = DataSourceManager()
        warmer = CacheWarmer(manager)

        _run_async(warmer.preload_fund_info_cache())

        logger.info("预热基金信息缓存任务完成")
        return {"status": "success", "task": "preload_funds"}

    except Exception as e:
        logger.error(f"预热基金信息缓存任务失败: {e}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    max_retries=3,
    name="src.tasks.cache_tasks.periodic_warmup",
)
def periodic_warmup(self):
    """
    定期预热缓存 - 获取所有自选基金数据

    每 5 分钟执行一次（通过 Celery Beat 配置）。
    """
    logger.info("开始执行定期缓存预热任务")

    try:
        from src.datasources.cache_warmer import CacheWarmer
        from src.datasources.manager import DataSourceManager

        manager = DataSourceManager()
        warmer = CacheWarmer(manager)

        _run_async(warmer.warmup(timeout=60.0))

        logger.info("定期缓存预热任务完成")
        return {"status": "success", "task": "periodic_warmup"}

    except Exception as e:
        logger.error(f"定期缓存预热任务失败: {e}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    max_retries=3,
    name="src.tasks.cache_tasks.periodic_cleanup",
)
def periodic_cleanup(self):
    """
    定期清理过期缓存

    每小时执行一次（通过 Celery Beat 配置）。
    """
    logger.info("开始执行定期缓存清理任务")

    try:
        from src.datasources.cache_cleaner import CacheCleaner

        cleaner = CacheCleaner()

        result = _run_async(cleaner.cleanup_on_startup())

        logger.info(f"定期缓存清理任务完成: {result}")
        return {"status": "success", "task": "periodic_cleanup", "result": result}

    except Exception as e:
        logger.error(f"定期缓存清理任务失败: {e}")
        raise
