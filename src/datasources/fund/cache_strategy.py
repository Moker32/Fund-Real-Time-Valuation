# -*- coding: UTF-8 -*-
"""基金数据缓存策略模块

实现数据库优先、API回源的缓存策略，支持：
- 按TTL分层缓存（静态/中频/高频数据）
- 缓存状态机管理
- 防止缓存击穿的锁机制
- 降级策略（过期缓存可用）
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from src.db.database import CacheMetadata, DatabaseManager, FundBasicInfoDAO
from src.db.fund.cache_metadata_dao import CacheMetadataDAO

logger = logging.getLogger(__name__)


@dataclass
class CacheResult:
    """缓存获取结果"""

    data: dict[str, Any] | None
    from_cache: bool
    is_stale: bool = False
    error: str | None = None


class CacheLockTimeoutError(Exception):
    """缓存锁超时异常"""

    pass


class CacheLockManager:
    """缓存锁管理器，防止缓存击穿"""

    _locks: dict[str, asyncio.Lock] = {}
    _lock = asyncio.Lock()  # 保护 _locks 字典的锁

    @classmethod
    @asynccontextmanager
    async def acquire(cls, key: str, timeout: float = 30.0):
        """
        获取缓存锁

        Args:
            key: 缓存键（如基金代码）
            timeout: 锁超时时间

        Yields:
            None

        Raises:
            CacheLockTimeoutError: 获取锁超时
        """
        # 获取或创建锁
        async with cls._lock:
            if key not in cls._locks:
                cls._locks[key] = asyncio.Lock()
            lock = cls._locks[key]

        # 尝试获取锁
        acquired = False
        try:
            acquired = await asyncio.wait_for(lock.acquire(), timeout=timeout)
            if not acquired:
                raise CacheLockTimeoutError(f"获取缓存锁超时: {key}")
            yield
        finally:
            if acquired:
                lock.release()
                # 清理不再使用的锁
                async with cls._lock:
                    if not lock.locked() and key in cls._locks:
                        del cls._locks[key]


class FundCacheStrategy:
    """基金数据缓存策略

    实现数据库优先、API回源的获取策略：

    1. 查询本地数据库
    2. 检查缓存状态和TTL
    3. 如有效则直接返回
    4. 如过期则尝试获取刷新锁
    5. 获取锁成功则回源API并更新
    6. 获取锁失败则返回旧数据（降级）
    """

    # TTL 配置
    STATIC_TTL = timedelta(days=30)  # 静态数据：name, type, manager等
    MID_TTL = timedelta(days=7)  # 中频数据：fund_scale
    HIGH_TTL = timedelta(days=1)  # 高频数据：net_value, net_value_date

    # 字段分类
    STATIC_FIELDS = {"name", "short_name", "type", "establishment_date", "manager", "custodian", "risk_level"}
    MID_FIELDS = {"fund_scale", "scale_date"}
    HIGH_FIELDS = {"net_value", "net_value_date", "fund_key"}

    # 按数据类型定义TTL配置（包含过期容忍度）
    TTL_CONFIG = {
        "static": {
            "fields": STATIC_FIELDS,
            "ttl": timedelta(days=30),
            "stale_threshold": timedelta(days=90),  # 静态数据可容忍更长的过期时间
        },
        "mid": {
            "fields": MID_FIELDS,
            "ttl": timedelta(days=7),
            "stale_threshold": timedelta(days=30),
        },
        "high": {
            "fields": HIGH_FIELDS,
            "ttl": timedelta(days=1),
            "stale_threshold": timedelta(days=7),  # 高频数据过期容忍度较低
        },
    }

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化缓存策略

        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager
        self.basic_info_dao = FundBasicInfoDAO(db_manager)
        self.cache_metadata_dao = CacheMetadataDAO(db_manager)

    def _get_ttl_for_field(self, field: str) -> timedelta:
        """
        根据字段获取对应的TTL

        Args:
            field: 字段名

        Returns:
            timedelta: TTL时间
        """
        if field in self.STATIC_FIELDS:
            return self.STATIC_TTL
        elif field in self.MID_FIELDS:
            return self.MID_TTL
        elif field in self.HIGH_FIELDS:
            return self.HIGH_TTL
        else:
            return self.MID_TTL  # 默认中频

    def _get_max_ttl(self, fields: list[str]) -> timedelta:
        """
        获取字段列表中的最大TTL

        Args:
            fields: 字段列表

        Returns:
            timedelta: 最大TTL
        """
        if not fields:
            return self.MID_TTL
        return max(self._get_ttl_for_field(f) for f in fields)

    def _get_field_category(self, field: str) -> str:
        """
        获取字段所属的类别

        Args:
            field: 字段名

        Returns:
            str: 类别名称 ("static", "mid", "high")
        """
        if field in self.STATIC_FIELDS:
            return "static"
        elif field in self.MID_FIELDS:
            return "mid"
        elif field in self.HIGH_FIELDS:
            return "high"
        else:
            return "mid"  # 默认中频

    def _get_stale_threshold(self, fields: list[str] | None = None) -> timedelta:
        """
        获取字段列表的最大过期容忍度

        Args:
            fields: 字段列表，None则返回默认容忍度

        Returns:
            timedelta: 最大过期容忍度
        """
        if not fields:
            # 默认使用mid的stale_threshold
            return self.TTL_CONFIG["mid"]["stale_threshold"]

        # 获取所有字段对应的stale_threshold，取最大值
        thresholds = []
        for field in fields:
            category = self._get_field_category(field)
            thresholds.append(self.TTL_CONFIG[category]["stale_threshold"])

        return max(thresholds) if thresholds else self.TTL_CONFIG["mid"]["stale_threshold"]

    def _is_cache_valid(self, metadata: CacheMetadata | None) -> bool:
        """
        检查缓存是否有效

        Args:
            metadata: 缓存元数据

        Returns:
            bool: 是否有效
        """
        if metadata is None:
            return False

        if metadata.cache_status not in ("valid", "stale"):
            return False

        # 检查是否过期
        if not metadata.expires_at:
            return False

        try:
            expires_at = datetime.fromisoformat(metadata.expires_at.replace("Z", ""))
            return datetime.now() < expires_at
        except (ValueError, TypeError):
            return False

    def _is_cache_stale(
        self, metadata: CacheMetadata | None, fields: list[str] | None = None
    ) -> bool:
        """
        检查缓存是否过期但可用（降级）

        Args:
            metadata: 缓存元数据
            fields: 字段列表，用于计算过期容忍度，None则使用默认容忍度

        Returns:
            bool: 是否过期但可用
        """
        if metadata is None:
            return False

        if metadata.cache_status not in ("valid", "stale", "error"):
            return False

        # 检查是否过期
        if not metadata.expires_at:
            return False

        try:
            expires_at = datetime.fromisoformat(metadata.expires_at.replace("Z", ""))
            # 根据字段类型获取过期容忍度
            stale_threshold = self._get_stale_threshold(fields)
            return datetime.now() < expires_at + stale_threshold
        except (ValueError, TypeError):
            return False

    async def get_with_cache(
        self,
        fund_code: str,
        fetch_func: Callable[[], Any],
        ttl: timedelta | None = None,
        fields: list[str] | None = None,
    ) -> CacheResult:
        """
        带缓存的数据获取方法

        实现数据库优先策略：
        1. 查询本地数据库
        2. 检查缓存状态和TTL
        3. 如有效则直接返回
        4. 如过期则尝试获取刷新锁
        5. 获取锁成功则回源API并更新
        6. 获取锁失败则返回旧数据（降级）

        Args:
            fund_code: 基金代码
            fetch_func: 数据获取函数（回源API）
            ttl: 缓存TTL，None则根据字段自动计算
            fields: 需要的字段列表，用于计算TTL

        Returns:
            CacheResult: 缓存结果
        """
        # 计算TTL
        if ttl is None:
            ttl = self._get_max_ttl(fields or [])

        # Step 1: 检查数据库缓存
        cache_metadata = await self.cache_metadata_dao.get_cache_status(fund_code)
        basic_info = self.basic_info_dao.get(fund_code)

        # Step 2: 如果缓存有效，直接返回
        if self._is_cache_valid(cache_metadata) and basic_info:
            return CacheResult(
                data=self._basic_info_to_dict(basic_info),
                from_cache=True,
                is_stale=False,
            )

        # Step 3: 如果缓存过期但数据存在，尝试后台刷新
        if basic_info and self._is_cache_stale(cache_metadata, fields):
            # 触发后台刷新
            asyncio.create_task(self._background_refresh(fund_code, fetch_func, ttl))

            # 返回旧数据（降级）
            logger.warning(f"使用过期缓存: {fund_code}, 过期时间: {cache_metadata.expires_at}")
            return CacheResult(
                data=self._basic_info_to_dict(basic_info),
                from_cache=True,
                is_stale=True,
            )

        # Step 4: 缓存不存在或状态为error，需要同步获取
        try:
            async with CacheLockManager.acquire(fund_code, timeout=30.0):
                # 双重检查：可能其他请求已经刷新了缓存
                cache_metadata = await self.cache_metadata_dao.get_cache_status(fund_code)
                basic_info = self.basic_info_dao.get(fund_code)

                if self._is_cache_valid(cache_metadata) and basic_info:
                    return CacheResult(
                        data=self._basic_info_to_dict(basic_info),
                        from_cache=True,
                        is_stale=False,
                    )

                # Step 5: API回源
                await self.cache_metadata_dao.mark_refreshing(fund_code)

                try:
                    result = await self._call_fetch_func(fetch_func)

                    if result:
                        # 保存到数据库
                        self._save_basic_info(fund_code, result)

                        # 更新缓存状态
                        expires_at = datetime.now() + ttl
                        await self.cache_metadata_dao.set_cache_status(
                            fund_code, "valid", expires_at
                        )

                        return CacheResult(
                            data=result,
                            from_cache=False,
                            is_stale=False,
                        )
                    else:
                        # API返回空结果
                        await self.cache_metadata_dao.mark_error(fund_code, "API返回空数据")
                        return CacheResult(
                            data=None,
                            from_cache=False,
                            is_stale=False,
                            error="API返回空数据",
                        )

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"API回源失败: {fund_code}, 错误: {error_msg}")
                    await self.cache_metadata_dao.mark_error(fund_code, error_msg)

                    # 如果有旧数据，返回降级
                    if basic_info:
                        return CacheResult(
                            data=self._basic_info_to_dict(basic_info),
                            from_cache=True,
                            is_stale=True,
                            error=error_msg,
                        )

                    return CacheResult(
                        data=None,
                        from_cache=False,
                        is_stale=False,
                        error=error_msg,
                    )

        except CacheLockTimeoutError:
            # 锁超时，可能是其他请求正在刷新
            logger.warning(f"缓存锁超时: {fund_code}")

            # 等待一小段时间后重试读取缓存
            await asyncio.sleep(0.5)

            basic_info = self.basic_info_dao.get(fund_code)
            if basic_info:
                return CacheResult(
                    data=self._basic_info_to_dict(basic_info),
                    from_cache=True,
                    is_stale=True,
                    error="缓存刷新超时，使用旧数据",
                )

            return CacheResult(
                data=None,
                from_cache=False,
                is_stale=False,
                error="缓存刷新超时",
            )

    async def _call_fetch_func(self, fetch_func: Callable[[], Any]) -> dict[str, Any] | None:
        """
        调用数据获取函数

        Args:
            fetch_func: 数据获取函数

        Returns:
            dict | None: 获取的数据
        """
        try:
            if asyncio.iscoroutinefunction(fetch_func):
                result = await fetch_func()
            else:
                result = fetch_func()

            # 处理 DataSourceResult 类型
            if hasattr(result, "success"):
                if result.success:
                    return result.data
                else:
                    logger.warning(f"数据获取失败: {result.error}")
                    return None

            return result
        except Exception as e:
            logger.error(f"调用数据获取函数失败: {e}")
            return None

    async def _background_refresh(
        self,
        fund_code: str,
        fetch_func: Callable[[], Any],
        ttl: timedelta,
    ) -> None:
        """
        后台刷新缓存

        Args:
            fund_code: 基金代码
            fetch_func: 数据获取函数
            ttl: 缓存TTL
        """
        try:
            async with CacheLockManager.acquire(fund_code, timeout=30.0):
                # 再次检查是否需要刷新
                cache_metadata = await self.cache_metadata_dao.get_cache_status(fund_code)
                if cache_metadata and cache_metadata.cache_status == "refreshing":
                    return  # 已有其他进程在刷新

                await self.cache_metadata_dao.mark_refreshing(fund_code)

                result = await self._call_fetch_func(fetch_func)

                if result:
                    self._save_basic_info(fund_code, result)
                    expires_at = datetime.now() + ttl
                    await self.cache_metadata_dao.set_cache_status(fund_code, "valid", expires_at)
                    logger.info(f"后台刷新成功: {fund_code}")
                else:
                    await self.cache_metadata_dao.mark_error(fund_code, "后台刷新获取数据为空")

        except CacheLockTimeoutError:
            logger.warning(f"后台刷新锁超时: {fund_code}")
        except Exception as e:
            logger.error(f"后台刷新失败: {fund_code}, 错误: {e}")
            await self.cache_metadata_dao.mark_error(fund_code, str(e))

    def _basic_info_to_dict(self, basic_info: Any) -> dict[str, Any]:
        """
        将 FundBasicInfo 转换为字典

        Args:
            basic_info: FundBasicInfo 实例

        Returns:
            dict: 字典形式的数据
        """
        if hasattr(basic_info, "__dataclass_fields__"):
            return {
                field: getattr(basic_info, field)
                for field in basic_info.__dataclass_fields__
            }
        elif hasattr(basic_info, "_asdict"):
            return basic_info._asdict()
        else:
            return dict(basic_info)

    def _save_basic_info(self, fund_code: str, data: dict[str, Any]) -> bool:
        """
        保存基金基本信息到数据库

        Args:
            fund_code: 基金代码
            data: 基金信息字典

        Returns:
            bool: 是否保存成功
        """
        return self.basic_info_dao.save_from_dict(fund_code, data)

    async def invalidate_cache(self, fund_code: str) -> bool:
        """
        使缓存失效

        Args:
            fund_code: 基金代码

        Returns:
            bool: 是否成功
        """
        return await self.cache_metadata_dao.mark_stale(fund_code)

    async def force_refresh(
        self,
        fund_code: str,
        fetch_func: Callable[[], Any],
        ttl: timedelta | None = None,
    ) -> CacheResult:
        """
        强制刷新缓存

        Args:
            fund_code: 基金代码
            fetch_func: 数据获取函数
            ttl: 缓存TTL

        Returns:
            CacheResult: 刷新结果
        """
        if ttl is None:
            ttl = self.MID_TTL

        try:
            async with CacheLockManager.acquire(fund_code, timeout=30.0):
                await self.cache_metadata_dao.mark_refreshing(fund_code)

                result = await self._call_fetch_func(fetch_func)

                if result:
                    self._save_basic_info(fund_code, result)
                    expires_at = datetime.now() + ttl
                    await self.cache_metadata_dao.set_cache_status(fund_code, "valid", expires_at)

                    return CacheResult(
                        data=result,
                        from_cache=False,
                        is_stale=False,
                    )
                else:
                    await self.cache_metadata_dao.mark_error(fund_code, "强制刷新获取数据为空")
                    return CacheResult(
                        data=None,
                        from_cache=False,
                        is_stale=False,
                        error="获取数据为空",
                    )

        except CacheLockTimeoutError:
            return CacheResult(
                data=None,
                from_cache=False,
                is_stale=False,
                error="获取缓存锁超时",
            )
        except Exception as e:
            logger.error(f"强制刷新失败: {fund_code}, 错误: {e}")
            return CacheResult(
                data=None,
                from_cache=False,
                is_stale=False,
                error=str(e),
            )


# 便捷函数
async def get_fund_data_with_cache(
    db_manager: DatabaseManager,
    fund_code: str,
    fetch_func: Callable[[], Any],
    ttl: timedelta | None = None,
    fields: list[str] | None = None,
) -> CacheResult:
    """
    便捷函数：带缓存获取基金数据

    Args:
        db_manager: 数据库管理器
        fund_code: 基金代码
        fetch_func: 数据获取函数
        ttl: 缓存TTL
        fields: 需要的字段列表

    Returns:
        CacheResult: 缓存结果
    """
    strategy = FundCacheStrategy(db_manager)
    return await strategy.get_with_cache(fund_code, fetch_func, ttl, fields)