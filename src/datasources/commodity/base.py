"""
商品数据源 - 基础模块

提供商品数据源的基类和共享配置：
- 三级缓存：内存 → 数据库 → 外部API
- LRU 缓存实现
- 指数退避重试机制
"""

import asyncio
import logging
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from typing_extensions import TypedDict

from src.db.commodity_repo import CommodityCacheDAO

from ..base import DataSource, DataSourceType

logger = logging.getLogger(__name__)

# 重试配置
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # 初始延迟1秒
RETRY_BACKOFF_FACTOR = 2.0  # 指数增长因子

# 内存缓存配置
MAX_CACHE_SIZE = 100  # 最大缓存条目数


class CommoditySearchResult(TypedDict):
    """商品搜索结果"""

    symbol: str
    name: str
    exchange: str
    currency: str
    category: str


class CommoditySearchResponse(TypedDict):
    """商品搜索响应"""

    query: str


class CommodityDataSource(DataSource):
    """商品数据源基类"""

    def __init__(self, name: str, timeout: float = 15.0):
        """
        初始化商品数据源

        Args:
            name: 数据源名称
            timeout: 请求超时时间(秒)
        """
        super().__init__(name=name, source_type=DataSourceType.COMMODITY, timeout=timeout)
        # 使用 OrderedDict 实现 LRU 缓存
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._cache_timeout = 60.0  # 内存缓存60秒
        self._db_dao: CommodityCacheDAO | None = None

    def set_db_dao(self, dao: CommodityCacheDAO) -> None:
        """设置数据库 DAO 用于缓存数据"""
        self._db_dao = dao

    async def _save_to_database(
        self, commodity_type: str, data: dict[str, Any], source: str
    ) -> None:
        """保存数据到数据库"""
        if self._db_dao:
            try:
                self._db_dao.save_from_api(commodity_type, data, source)
            except Exception as e:
                logger.error(f"保存商品数据到数据库失败: {e}")

    def _add_to_cache(self, cache_key: str, data: dict[str, Any]) -> None:
        """
        添加数据到LRU缓存

        如果缓存已满，移除最久未使用的条目
        """
        # 如果键已存在，先移除它（后面会重新添加以更新顺序）
        if cache_key in self._cache:
            del self._cache[cache_key]
        # 如果缓存已满，移除最久未使用的条目
        elif len(self._cache) >= MAX_CACHE_SIZE:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"LRU缓存已满，移除最久未使用的条目: {oldest_key}")

        # 添加新数据到末尾（最新使用）
        self._cache[cache_key] = data

    def _get_from_cache(self, cache_key: str) -> dict[str, Any] | None:
        """
        从LRU缓存获取数据

        访问数据时会将其移到末尾（标记为最新使用）
        """
        if cache_key not in self._cache:
            return None

        # 移动到末尾（标记为最新使用）
        data = self._cache.pop(cache_key)
        self._cache[cache_key] = data
        return data

    async def _fetch_with_retry(self, fetch_func: Callable, *args, **kwargs) -> Any:
        """
        带指数退避重试的获取方法

        Args:
            fetch_func: 实际获取数据的函数
            *args, **kwargs: 传递给 fetch_func 的参数

        Returns:
            获取的数据

        Raises:
            Exception: 所有重试都失败后的最后一个异常
        """
        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                return await fetch_func(*args, **kwargs)
            except asyncio.TimeoutError as e:
                last_exception = e
                # 超时错误需要重试
                if attempt < MAX_RETRIES - 1:
                    delay = INITIAL_RETRY_DELAY * (RETRY_BACKOFF_FACTOR**attempt)
                    logger.warning(
                        f"[{self.name}] 请求超时 (尝试 {attempt + 1}/{MAX_RETRIES}), "
                        f"{delay:.1f}秒后重试..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[{self.name}] 请求超时，已重试{MAX_RETRIES}次，放弃")
            except Exception as e:
                last_exception = e
                # 检查是否是网络相关错误
                error_str = str(e).lower()
                is_network_error = any(
                    keyword in error_str
                    for keyword in [
                        "network",
                        "connection",
                        "timeout",
                        "dns",
                        "unreachable",
                        "refused",
                        "reset",
                        "abort",
                        "ssl",
                        "certificate",
                        "handshake",
                    ]
                )

                if is_network_error and attempt < MAX_RETRIES - 1:
                    delay = INITIAL_RETRY_DELAY * (RETRY_BACKOFF_FACTOR**attempt)
                    logger.warning(
                        f"[{self.name}] 网络错误 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}, "
                        f"{delay:.1f}秒后重试..."
                    )
                    await asyncio.sleep(delay)
                else:
                    if is_network_error:
                        logger.error(f"[{self.name}] 网络错误，已重试{MAX_RETRIES}次，放弃: {e}")
                    else:
                        # 业务错误不重试
                        logger.warning(f"[{self.name}] 业务错误，不重试: {e}")
                    raise

        # 所有重试都失败了
        if last_exception:
            raise last_exception
        raise Exception("未知错误")

    async def close(self):
        """关闭数据源（子类应重写此方法）"""
        pass
