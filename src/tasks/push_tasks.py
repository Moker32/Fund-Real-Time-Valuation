"""
WebSocket 推送相关的 Celery 任务

提供定时推送基金、商品、指数数据到 WebSocket 客户端。
"""

import asyncio
import logging

from src.tasks import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """在同步 Celery 任务中运行异步函数"""
    return asyncio.run(coro)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=30,
    max_retries=3,
    name="src.tasks.push_tasks.push_fund_update",
)
def push_fund_update_task(self):
    """定时推送基金数据到 WebSocket 客户端"""
    logger.info("开始推送基金数据")

    try:
        from api.routes.websocket import push_fund_update
        from src.datasources import FundDataSource
        from src.db.database import DatabaseManager

        # 获取自选基金列表
        db = DatabaseManager()
        dao = db.get_config_dao()
        watchlist = dao.get_watchlist()

        if not watchlist:
            logger.info("自选基金列表为空，跳过推送")
            return {"status": "success", "message": "no watchlist"}

        # 获取基金数据
        fund_source = FundDataSource()
        fund_data_list = []

        for fund in watchlist:
            try:
                result = _run_async(fund_source.fetch(fund.code, use_cache=False))
                if result.success and result.data:
                    fund_data_list.append(result.data)
            except Exception as e:
                logger.warning(f"获取基金数据失败: {fund.code} - {e}")
                continue

        if fund_data_list:
            _run_async(push_fund_update({"funds": fund_data_list}))

        logger.info(f"基金数据推送完成: {len(fund_data_list)} 条")
        return {"status": "success", "count": len(fund_data_list)}

    except Exception as e:
        logger.error(f"推送基金数据失败: {e}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=30,
    max_retries=3,
    name="src.tasks.push_tasks.push_commodity_update",
)
def push_commodity_update_task(self):
    """定时推送商品数据到 WebSocket 客户端"""
    logger.info("开始推送商品数据")

    try:
        from api.routes.websocket import push_commodity_update
        from src.datasources import CommodityDataAggregator

        # 商品类型列表
        commodity_types = ["gold", "silver", "wti", "brent"]

        aggregator = CommodityDataAggregator()
        commodity_data_list = []

        for commodity_type in commodity_types:
            try:
                result = _run_async(aggregator.fetch(commodity_type))
                if result.success and result.data:
                    commodity_data_list.append(result.data)
            except Exception as e:
                logger.warning(f"获取商品数据失败: {commodity_type} - {e}")
                continue

        if commodity_data_list:
            _run_async(push_commodity_update({"commodities": commodity_data_list}))

        logger.info(f"商品数据推送完成: {len(commodity_data_list)} 条")
        return {"status": "success", "count": len(commodity_data_list)}

    except Exception as e:
        logger.error(f"推送商品数据失败: {e}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=30,
    max_retries=3,
    name="src.tasks.push_tasks.push_index_update",
)
def push_index_update_task(self):
    """定时推送指数数据到 WebSocket 客户端"""
    logger.info("开始推送指数数据")

    try:
        from api.routes.websocket import push_index_update
        from src.datasources.base import DataSourceType
        from src.datasources.manager import DataSourceManager

        manager = DataSourceManager()
        index_data_list = []

        # 指数类型列表
        index_types = [
            "shanghai",
            "shenzhen",
            "hs300",
            "chi_next",
            "hang_seng",
            "dow_jones",
            "nasdaq",
        ]

        for index_type in index_types:
            try:
                result = _run_async(manager.fetch(DataSourceType.INDEX, index_type))
                if result.success and result.data:
                    index_data_list.append(result.data)
            except Exception as e:
                logger.warning(f"获取指数数据失败: {index_type} - {e}")
                continue

        if index_data_list:
            _run_async(push_index_update({"indices": index_data_list}))

        logger.info(f"指数数据推送完成: {len(index_data_list)} 条")
        return {"status": "success", "count": len(index_data_list)}

    except Exception as e:
        logger.error(f"推送指数数据失败: {e}")
        raise


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
    name="src.tasks.push_tasks.push_all_data",
)
def push_all_data_task(self):
    """定时推送所有数据（基金+商品+指数）"""
    logger.info("开始推送所有数据")

    results = {
        "funds": 0,
        "commodities": 0,
        "indices": 0,
    }

    # Push funds
    try:
        push_fund_update_task.apply()
        results["funds"] = 1
    except Exception as e:
        logger.warning(f"推送基金数据失败: {e}")

    # Push commodities
    try:
        push_commodity_update_task.apply()
        results["commodities"] = 1
    except Exception as e:
        logger.warning(f"推送商品数据失败: {e}")

    # Push indices
    try:
        push_index_update_task.apply()
        results["indices"] = 1
    except Exception as e:
        logger.warning(f"推送指数数据失败: {e}")

    logger.info(f"所有数据推送完成: {results}")
    return {"status": "success", "results": results}
