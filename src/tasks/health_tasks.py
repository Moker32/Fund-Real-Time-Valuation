"""
健康检查相关的 Celery 任务

提供定时健康检查和一次性健康检查任务。
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
    name="src.tasks.health_tasks.periodic_check",
)
def periodic_check(self):
    """
    定期健康检查任务

    每 1 分钟执行一次（通过 Celery Beat 配置）。
    检查所有已注册数据源的健康状态。
    """
    logger.info("开始执行定期健康检查任务")

    try:
        from src.datasources.health import DataSourceHealthChecker
        from src.datasources.manager import DataSourceManager

        manager = DataSourceManager()
        checker = DataSourceHealthChecker()

        # 获取所有已注册的数据源
        sources = []
        from src.datasources.base import DataSourceType

        for source_type in DataSourceType:
            type_sources = manager.get_sources_by_type(source_type)
            sources.extend(type_sources)

        if not sources:
            logger.warning("没有注册的数据源，跳过健康检查")
            return {
                "status": "success",
                "task": "periodic_check",
                "message": "no sources registered",
            }

        # 执行健康检查
        results = _run_async(checker.check_all_sources(sources))

        # 统计结果
        healthy_count = sum(1 for r in results.values() if r.status.value == "healthy")
        degraded_count = sum(1 for r in results.values() if r.status.value == "degraded")
        unhealthy_count = sum(1 for r in results.values() if r.status.value == "unhealthy")

        logger.info(
            f"定期健康检查任务完成: healthy={healthy_count}, "
            f"degraded={degraded_count}, unhealthy={unhealthy_count}"
        )

        return {
            "status": "success",
            "task": "periodic_check",
            "results": {name: result.to_dict() for name, result in results.items()},
            "summary": {
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
            },
        }

    except Exception as e:
        logger.error(f"定期健康检查任务失败: {e}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
    name="src.tasks.health_tasks.run_health_check",
)
def run_health_check(self, source_name: str | None = None):
    """
    运行一次性健康检查任务

    Args:
        source_name: 可选，指定要检查的数据源名称。如果为 None，则检查所有数据源。

    Returns:
        健康检查结果
    """
    logger.info(f"开始执行一次性健康检查任务 (source: {source_name})")

    try:
        from src.datasources.health import DataSourceHealthChecker
        from src.datasources.manager import DataSourceManager

        manager = DataSourceManager()
        checker = DataSourceHealthChecker()

        # 获取数据源
        if source_name:
            # 检查指定数据源
            from src.datasources.base import DataSourceType

            sources = []
            for source_type in DataSourceType:
                type_sources = manager.get_sources_by_type(source_type)
                for src in type_sources:
                    if src.name == source_name:
                        sources.append(src)
                        break

            if not sources:
                return {
                    "status": "error",
                    "task": "run_health_check",
                    "message": f"数据源 '{source_name}' 未找到",
                }

            result = _run_async(checker.check_source(sources[0]))
            results = {source_name: result}
        else:
            # 检查所有数据源
            sources = []
            from src.datasources.base import DataSourceType

            for source_type in DataSourceType:
                type_sources = manager.get_sources_by_type(source_type)
                sources.extend(type_sources)

            if not sources:
                return {
                    "status": "success",
                    "task": "run_health_check",
                    "message": "no sources registered",
                }

            results = _run_async(checker.check_all_sources(sources))

        # 统计结果
        healthy_count = sum(1 for r in results.values() if r.status.value == "healthy")
        degraded_count = sum(1 for r in results.values() if r.status.value == "degraded")
        unhealthy_count = sum(1 for r in results.values() if r.status.value == "unhealthy")

        logger.info(
            f"一次性健康检查任务完成: healthy={healthy_count}, "
            f"degraded={degraded_count}, unhealthy={unhealthy_count}"
        )

        return {
            "status": "success",
            "task": "run_health_check",
            "results": {name: result.to_dict() for name, result in results.items()},
            "summary": {
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
            },
        }

    except Exception as e:
        logger.error(f"一次性健康检查任务失败: {e}")
        raise
