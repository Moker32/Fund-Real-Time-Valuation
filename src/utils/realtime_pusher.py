"""
实时数据推送器模块

定时获取数据并通过 WebSocket 推送到前端。
支持智能 Diff 只推送变化数据。
支持交易时段检测，在非交易时段降低推送频率。
"""

import asyncio
import logging

from src.datasources.manager import DataSourceManager, DataSourceType
from src.datasources.trading_calendar_source import Market, TradingCalendarSource
from src.utils.websocket_manager import (
    WebSocketManager,
    _convert_dict_to_camel_case,
    get_websocket_manager,
)
from typing import TypedDict

logger = logging.getLogger(__name__)


class DiffResult(TypedDict):
    """_diff_data 返回类型：有变化时返回变化项列表，无变化时返回 None"""
    added: list[dict]
    updated: list[dict]
    removed: list[dict]
    unchanged: list[dict]

# 交易时段推送间隔（秒）
# 注意：基金推送间隔设为 30 秒是为了平衡实时性和 API 压力
# 基金估值数据通常不需要秒级更新，30 秒间隔足够满足用户需求
# 同时避免过于频繁调用外部数据源导致被限流
TRADING_FUND_INTERVAL = 30  # 基金估值更新频率（每30秒从数据源获取一次）
TRADING_COMMODITY_INTERVAL = 10
TRADING_INDEX_INTERVAL = 10
TRADING_SECTOR_INTERVAL = 10

# 非交易时段推送间隔（秒）
NON_TRADING_FUND_INTERVAL = 60  # 非交易时段降低频率
NON_TRADING_COMMODITY_INTERVAL = 30
NON_TRADING_INDEX_INTERVAL = 30
NON_TRADING_SECTOR_INTERVAL = 30


class RealtimePusher:
    """实时数据推送器"""

    def __init__(
        self,
        data_source_manager: DataSourceManager | None = None,
        websocket_manager: WebSocketManager | None = None,
    ):
        self._data_manager = data_source_manager
        self._ws_manager = websocket_manager
        self._running = False
        self._tasks: list[asyncio.Task] = []

        self._last_fund_data: list[dict] | None = None
        self._last_commodity_data: list[dict] | None = None
        self._last_index_data: list[dict] | None = None
        self._last_sector_data: dict | None = None

        self._trading_calendar = TradingCalendarSource()
        self._trading_hours_cache: dict[str, tuple[bool, float]] = {}

    @property
    def data_manager(self) -> DataSourceManager:
        if self._data_manager is None:
            from api.dependencies import get_data_source_manager

            self._data_manager = get_data_source_manager()
        return self._data_manager

    @property
    def ws_manager(self) -> WebSocketManager:
        if self._ws_manager is None:
            self._ws_manager = get_websocket_manager()
        return self._ws_manager

    def _has_subscribers(self, subscription: str) -> bool:
        subscriptions = self.ws_manager.get_subscriptions_info()
        return subscriptions.get(subscription, 0) > 0

    def _is_trading_hours(self, market: Market = Market.CHINA) -> bool:
        # 缓存检查结果，避免频繁调用阻塞的 is_within_trading_hours
        # 缓存1分钟，避免阻塞事件循环
        import time

        now = time.time()
        cache_key = f"_is_trading_hours_{market.value}"
        if hasattr(self, "_trading_hours_cache") and cache_key in self._trading_hours_cache:
            cached_result, cached_time = self._trading_hours_cache[cache_key]
            if now - cached_time < 60:
                return cached_result

        try:
            result = self._trading_calendar.is_within_trading_hours(market)
            is_open = result.get("status") == "open"
            logger.debug(f"交易时段检查: market={market.value}, result={result}, is_open={is_open}")
            # 缓存结果
            if not hasattr(self, "_trading_hours_cache"):
                self._trading_hours_cache = {}
            self._trading_hours_cache[cache_key] = (is_open, now)
            return is_open
        except Exception as e:
            logger.warning(f"检查交易时段失败: {e}")
            return False

    def _get_intervals(self) -> tuple[int, int, int, int]:
        is_trading = self._is_trading_hours(Market.CHINA)
        if is_trading:
            return (
                TRADING_FUND_INTERVAL,
                TRADING_COMMODITY_INTERVAL,
                TRADING_INDEX_INTERVAL,
                TRADING_SECTOR_INTERVAL,
            )
        return (
            NON_TRADING_FUND_INTERVAL,
            NON_TRADING_COMMODITY_INTERVAL,
            NON_TRADING_INDEX_INTERVAL,
            NON_TRADING_SECTOR_INTERVAL,
        )

    def _diff_data(
        self, data_type: str, old_data: list[dict], new_data: list[dict]
    ) -> list[dict] | None:
        """
        对比新旧数据，返回有变化的项列表。

        - old_data 为空时，返回 new_data（全量）
        - keys 有新增/删除时，返回 new_data（全量）
        - fields 有变化时，返回变化项列表
        - 完全无变化时，返回 None
        """
        if not old_data:
            return new_data

        def _get_item_key(item: dict) -> str | None:
            """获取数据项的唯一键，支持 code/symbol/fund_code 字段"""
            return item.get("code") or item.get("symbol") or item.get("fund_code")

        old_dict = {_get_item_key(item): item for item in old_data if _get_item_key(item)}
        new_dict = {_get_item_key(item): item for item in new_data if _get_item_key(item)}

        old_keys = set(old_dict.keys())
        new_keys = set(new_dict.keys())

        if old_keys != new_keys:
            return new_data

        changed_items = []
        for key in new_keys:
            old_item = old_dict[key]
            new_item = new_dict[key]
            for field, value in new_item.items():
                if field not in old_item or old_item[field] != value:
                    changed_items.append(new_item)
                    break

        return changed_items if changed_items else None

    def _get_fund_codes(self) -> list[str]:
        """获取自选基金代码列表"""
        try:
            from src.config import get_config_manager

            config_manager = get_config_manager()
            fund_list = config_manager.load_funds()
            codes = fund_list.get_all_codes()
            return codes if codes else []
        except Exception as e:
            logger.warning(f"获取基金代码列表失败: {e}")
            return []

    async def _push_funds_loop(self):
        fund_interval, _, _ = self._get_intervals()
        logger.info(
            "基金推送循环启动",
            extra={"interval_seconds": fund_interval},
        )
        while self._running:
            try:
                if not self._has_subscribers("funds"):
                    logger.debug("基金推送: 无订阅者，等待...")
                    await asyncio.sleep(5)
                    continue

                # 获取自选基金代码
                fund_codes = self._get_fund_codes()
                if not fund_codes:
                    logger.debug("基金推送: 无自选基金，等待...")
                    await asyncio.sleep(fund_interval)
                    continue

                logger.debug(f"基金推送: 开始获取 {len(fund_codes)} 只基金数据...")

                # 交易时段不使用缓存，直接从数据源获取实时数据
                # 非交易时段使用缓存以减少 API 调用
                is_trading = self._is_trading_hours(Market.CHINA)
                params_list = [
                    {"args": [code], "kwargs": {"use_cache": not is_trading}} for code in fund_codes
                ]
                results = await self.data_manager.fetch_batch(DataSourceType.FUND, params_list)

                # 汇总成功的基金数据
                new_data = []
                failed_count = 0
                for result in results:
                    if result.success and result.data:
                        new_data.append(result.data)
                    else:
                        failed_count += 1

                if failed_count > 0:
                    logger.warning(
                        "基金推送部分失败",
                        extra={
                            "failed_count": failed_count,
                            "total_count": len(fund_codes),
                            "is_trading": is_trading,
                        },
                    )

                if new_data:
                    # 每次都推送完整数据（不使用差量更新）
                    camel_data = [_convert_dict_to_camel_case(item) for item in new_data]
                    sent = await self.ws_manager.broadcast_to_subscription(
                        subscription="funds",
                        message_type="fund_update",
                        data={"funds": camel_data},
                    )
                    logger.info(
                        "基金数据推送完成",
                        extra={
                            "fund_count": len(new_data),
                            "sent_count": sent,
                            "is_trading": is_trading,
                        },
                    )
                    self._last_fund_data = new_data
                else:
                    logger.warning(
                        "基金推送全部失败",
                        extra={
                            "fund_count": len(fund_codes),
                            "is_trading": is_trading,
                        },
                    )

            except Exception as e:
                logger.error(f"基金推送循环异常: {e}")

            await asyncio.sleep(fund_interval)

    async def _push_commodities_loop(self):
        _, commodity_interval, _ = self._get_intervals()
        while self._running:
            try:
                if not self._has_subscribers("commodities"):
                    await asyncio.sleep(5)
                    continue

                result = await self.data_manager.fetch(DataSourceType.COMMODITY)
                if result.success and result.data:
                    new_data = result.data if isinstance(result.data, list) else [result.data]

                    if self._last_commodity_data is not None:
                        diff_data = self._diff_data(
                            "commodities", self._last_commodity_data, new_data
                        )
                        if diff_data is None:
                            logger.debug("商品数据无变化，跳过推送")
                            self._last_commodity_data = new_data
                            await asyncio.sleep(commodity_interval)
                            continue

                        # 转换为 camelCase 格式
                        camel_data = [_convert_dict_to_camel_case(item) for item in diff_data]
                        sent = await self.ws_manager.broadcast_to_subscription(
                            subscription="commodities",
                            message_type="commodity_update",
                            data={"commodities": camel_data},  # 包装为对象
                        )
                        logger.info(f"推送 {len(diff_data)} 条变化商品数据，发送到 {sent} 个客户端")
                    else:
                        # 转换为 camelCase 格式
                        camel_data = [_convert_dict_to_camel_case(item) for item in new_data]
                        sent = await self.ws_manager.broadcast_to_subscription(
                            subscription="commodities",
                            message_type="commodity_update",
                            data={"commodities": camel_data},  # 包装为对象
                        )
                        logger.info(f"首次推送 {len(new_data)} 条商品数据，发送到 {sent} 个客户端")

                    self._last_commodity_data = new_data
                else:
                    logger.warning(f"获取商品数据失败: {result.error}")

            except Exception as e:
                logger.error(f"商品推送循环异常: {e}")

            await asyncio.sleep(commodity_interval)

    # 支持的指数类型列表
    # 注意：这里使用的是内部指数类型标识符，不是数据源特定的代码
    SUPPORTED_INDICES = [
        "shanghai",  # 上证指数
        "shenzhen",  # 深证成指
        "chi_next",  # 创业板指
        "hs300",  # 沪深300
        "shanghai50",  # 上证50
        "csi500",  # 中证500
        "hang_seng",  # 恒生指数
        "hang_seng_tech",  # 恒生科技
        "nikkei225",  # 日经225 - 新增
        "dow_jones",  # 道琼斯
        "nasdaq",  # 纳斯达克
        "sp500",  # 标普500
        "dax",  # 德国DAX - 新增
        "ftse",  # 富时100 - 新增
        "cac40",  # CAC40 - 新增
    ]

    async def _push_indices_loop(self):
        _, _, index_interval = self._get_intervals()
        logger.info(f"指数推送循环启动，间隔: {index_interval}s")
        while self._running:
            try:
                if not self._has_subscribers("indices"):
                    logger.debug("指数推送: 无订阅者，等待...")
                    await asyncio.sleep(5)
                    continue

                # 使用 fetch_batch 批量获取指数数据
                params_list = [{"args": [it]} for it in self.SUPPORTED_INDICES]
                results = await self.data_manager.fetch_batch(DataSourceType.STOCK, params_list)

                # 汇总成功的指数数据
                new_data = []
                failed_count = 0
                for result in results:
                    if result.success and result.data:
                        new_data.append(result.data)
                    else:
                        failed_count += 1

                if failed_count > 0:
                    logger.debug(
                        f"指数推送: {failed_count}/{len(self.SUPPORTED_INDICES)} 个指数获取失败"
                    )

                if new_data:
                    if self._last_index_data is not None:
                        diff_data = self._diff_data("indices", self._last_index_data, new_data)
                        if diff_data is None:
                            logger.debug("指数数据无变化，跳过推送")
                            self._last_index_data = new_data
                            await asyncio.sleep(index_interval)
                            continue

                        # 转换为 camelCase 格式
                        camel_data = [_convert_dict_to_camel_case(item) for item in diff_data]
                        sent = await self.ws_manager.broadcast_to_subscription(
                            subscription="indices",
                            message_type="index_update",
                            data={"indices": camel_data},  # 包装为对象
                        )
                        logger.info(f"推送 {len(diff_data)} 条变化指数数据，发送到 {sent} 个客户端")
                    else:
                        # 转换为 camelCase 格式
                        camel_data = [_convert_dict_to_camel_case(item) for item in new_data]
                        sent = await self.ws_manager.broadcast_to_subscription(
                            subscription="indices",
                            message_type="index_update",
                            data={"indices": camel_data},  # 包装为对象
                        )
                        logger.info(f"首次推送 {len(new_data)} 条指数数据，发送到 {sent} 个客户端")

                    self._last_index_data = new_data
                else:
                    logger.warning("指数推送: 所有指数数据获取失败")

            except Exception as e:
                logger.error(f"指数推送循环异常: {e}")

            await asyncio.sleep(index_interval)

    async def _push_sectors_loop(self):
        _, _, _, sector_interval = self._get_intervals()
        logger.info(f"板块推送循环启动，间隔: {sector_interval}s")
        while self._running:
            try:
                if not self._has_subscribers("sectors"):
                    logger.debug("板块推送: 无订阅者，等待...")
                    await asyncio.sleep(5)
                    continue

                # 获取行业板块数据（ths_sector）和概念板块数据（sina_sector）
                ths_result = await self.data_manager.fetch_with_source("sector_ths_akshare")
                sina_result = await self.data_manager.fetch_with_source("sina_sector")

                industry_sectors = []
                if ths_result.success and ths_result.data:
                    data = ths_result.data
                    if isinstance(data, dict) and "sectors" in data:
                        industry_sectors = data.get("sectors", [])
                    elif isinstance(data, list):
                        industry_sectors = data

                concept_sectors = []
                if sina_result.success and sina_result.data:
                    sina_data = sina_result.data
                    if isinstance(sina_data, list):
                        concept_sectors = sina_data
                    elif isinstance(sina_data, dict) and "sectors" in sina_data:
                        concept_sectors = sina_data.get("sectors", [])

                new_data = {
                    "industry": industry_sectors,
                    "concept": concept_sectors,
                    "industry_count": len(industry_sectors),
                    "concept_count": len(concept_sectors),
                }

                # 与 commodity/index loop 保持一致：diff 只决定是否推送，推送时发完整数据
                should_push = False
                if self._last_sector_data is None:
                    should_push = True
                else:
                    old_industry = self._last_sector_data.get("industry", [])
                    old_concept = self._last_sector_data.get("concept", [])
                    industry_diff = self._diff_data("industry", old_industry, industry_sectors)
                    concept_diff = self._diff_data("concept", old_concept, concept_sectors)
                    if industry_diff is not None or concept_diff is not None:
                        should_push = True

                if should_push:
                    push_data = {
                        "industry": industry_sectors,
                        "concept": concept_sectors,
                    }
                    camel_data = _convert_dict_to_camel_case(push_data)
                    sent = await self.ws_manager.broadcast_to_subscription(
                        subscription="sectors",
                        message_type="sector_update",
                        data=camel_data,
                    )
                    logger.info(
                        f"推送板块数据，发送到 {sent} 个客户端: "
                        f"{len(industry_sectors)} 个行业，{len(concept_sectors)} 个概念"
                    )

                self._last_sector_data = new_data

            except Exception as e:
                logger.error(f"板块推送循环异常: {e}")

            await asyncio.sleep(sector_interval)

    async def start(self):
        if self._running:
            logger.warning("推送器已在运行中")
            return

        self._running = True
        logger.info("启动实时数据推送器")

        self._tasks = [
            asyncio.create_task(self._push_funds_loop()),
            asyncio.create_task(self._push_commodities_loop()),
            asyncio.create_task(self._push_indices_loop()),
            asyncio.create_task(self._push_sectors_loop()),
        ]

        logger.info(f"已启动 {len(self._tasks)} 个推送任务")

    async def stop(self):
        if not self._running:
            logger.warning("推送器未在运行")
            return

        self._running = False
        logger.info("停止实时数据推送器")

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks = []
        logger.info("实时数据推送器已停止")


_pusher: RealtimePusher | None = None


def get_realtime_pusher() -> RealtimePusher:
    global _pusher
    if _pusher is None:
        _pusher = RealtimePusher()
    return _pusher


async def start_realtime_pusher():
    pusher = get_realtime_pusher()
    await pusher.start()


async def stop_realtime_pusher():
    if _pusher is not None:
        await _pusher.stop()
