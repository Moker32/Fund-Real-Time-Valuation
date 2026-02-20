"""
基金相关的 Celery 任务

提供基金数据预热和缓存清理任务。
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
    name="src.tasks.fund_tasks.prewarm_fund",
)
def prewarm_fund(self, fund_code: str):
    """
    预热单个基金数据

    在添加基金到自选后立即触发数据预热，将数据写入缓存供后续请求使用。

    Args:
        fund_code: 基金代码
    """
    logger.info(f"开始预热基金数据: {fund_code}")

    try:
        from src.datasources.cache_warmer import prewarm_new_fund

        _run_async(prewarm_new_fund(fund_code))

        logger.info(f"基金数据预热完成: {fund_code}")
        return {"status": "success", "task": "prewarm_fund", "fund_code": fund_code}

    except Exception as e:
        logger.error(f"预热基金数据失败: {fund_code} - {e}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
    name="src.tasks.fund_tasks.cleanup_fund_cache",
)
def cleanup_fund_cache(self, fund_code: str):
    """
    清理基金缓存

    在从自选移除基金后清理相关缓存条目。

    Args:
        fund_code: 基金代码
    """
    logger.info(f"开始清理基金缓存: {fund_code}")

    try:
        from src.datasources.cache_warmer import cleanup_fund_cache as _cleanup

        _run_async(_cleanup(fund_code))

        logger.info(f"基金缓存清理完成: {fund_code}")
        return {"status": "success", "task": "cleanup_fund_cache", "fund_code": fund_code}

    except Exception as e:
        logger.error(f"清理基金缓存失败: {fund_code} - {e}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    max_retries=3,
    name="src.tasks.fund_tasks.prewarm_all_funds",
)
def prewarm_all_funds(self):
    """
    预热所有配置的基金数据

    在服务启动时获取所有自选基金数据并写入缓存。
    """
    logger.info("开始预热所有基金数据")

    try:
        from src.datasources.cache_warmer import CacheWarmer
        from src.datasources.manager import DataSourceManager

        manager = DataSourceManager()
        warmer = CacheWarmer(manager)

        _run_async(warmer.warmup(timeout=120.0))

        logger.info("所有基金数据预热完成")
        return {"status": "success", "task": "prewarm_all_funds"}

    except Exception as e:
        logger.error(f"预热所有基金数据失败: {e}")
        raise
