"""基金净值解析器模块

提供多级回退的净值获取能力：
1. 天天基金（最快，~0.1s）
2. akshare（较慢，~14s）
3. SQLite 数据库缓存（兜底）

使用协议类设计，支持灵活的净值来源配置。
"""

import asyncio
import json
import logging
import re
import time
from typing import Any, Protocol

import httpx

from .fund_cache_helpers import get_daily_cache_dao

logger = logging.getLogger(__name__)


class NetValueSource(Protocol):
    """净值数据源协议"""

    async def get_net_value(self, fund_code: str) -> tuple[str | None, float | None]:
        """
        获取基金净值

        Returns:
            (净值日期, 单位净值) 元组，获取失败返回 (None, None)
        """
        ...


class TiantianNetValueSource:
    """天天基金净值数据源

    数据来源: fundgz.1234567.com.cn
    响应格式: jsonpgz({...})
    """

    _client: httpx.AsyncClient | None = None
    _lock: asyncio.Lock | None = None

    def __init__(self):
        pass

    @classmethod
    def _get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=30.0,
                ),
                timeout=5.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Referer": "http://fundgz.1234567.com.cn/",
                },
            )
        return cls._client

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    async def get_net_value(self, fund_code: str) -> tuple[str | None, float | None]:
        """
        从天天基金获取净值

        Returns:
            (jzrq, dwjz) 元组，获取失败返回 (None, None)
        """
        async with self._get_lock():
            try:
                url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js?rt={int(time.time() * 1000)}"
                resp = await self._get_client().get(url)
                if not resp.is_success:
                    return None, None

                text = resp.text.strip()
                if text in ("jsonpgz();", "jsonpgz()"):
                    return None, None

                match = re.match(r"jsonpgz\((.+)\);?", text)
                if not match:
                    return None, None

                data = json.loads(match.group(1))
                date = data.get("jzrq", "")
                value = self._safe_float(data.get("dwjz"))

                if date and value is not None:
                    logger.debug(f"从天天基金获取净值: {fund_code} -> {value}, 日期: {date}")
                    return date, value

                return None, None
            except Exception as e:
                logger.warning(f"从天天基金获取净值失败: {fund_code} - {e}")
                return None, None

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


class AkshareNetValueSource:
    """akshare 净值数据源

    数据来源: akshare fund_open_fund_info_em 接口
    作为天天基金的回退源
    """

    def __init__(self):
        from .fund_info_utils import _get_net_value_date_from_akshare

        self._get_net_value_date = _get_net_value_date_from_akshare

    async def get_net_value(self, fund_code: str) -> tuple[str | None, float | None]:
        """
        从 akshare 获取净值

        Returns:
            (净值日期, 单位净值) 元组，获取失败返回 (None, None)
        """
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._get_net_value_date, fund_code)
            if result:
                date, value = result
                if date and value is not None:
                    logger.debug(f"从 akshare 获取净值: {fund_code} -> {value}, 日期: {date}")
                    return date, value
            return None, None
        except Exception as e:
            logger.warning(f"从 akshare 获取净值失败: {fund_code} - {e}")
            return None, None


class DatabaseNetValueSource:
    """数据库缓存净值数据源

    数据来源: SQLite daily_cache 表
    作为最后的回退源
    """

    async def get_net_value(self, fund_code: str) -> tuple[str | None, float | None]:
        """
        从数据库缓存获取净值

        Returns:
            (净值日期, 单位净值) 元组，获取失败返回 (None, None)
        """
        try:
            dao = get_daily_cache_dao()
            record = dao.get_latest(fund_code)
            if record and record.date and record.unit_net_value is not None:
                logger.debug(
                    f"从数据库缓存获取净值: {fund_code} -> {record.unit_net_value}, 日期: {record.date}"
                )
                return record.date, record.unit_net_value
            return None, None
        except Exception as e:
            logger.warning(f"从数据库获取净值失败: {fund_code} - {e}")
            return None, None


class NetValueResolver:
    """净值解析器

    支持多级回退的净值获取，按顺序尝试每个数据源直到成功。
    """

    def __init__(self, sources: list[NetValueSource] | None = None):
        """
        初始化净值解析器

        Args:
            sources: 净值数据源列表，按优先级排序
        """
        if sources is None:
            sources = [
                TiantianNetValueSource(),
                AkshareNetValueSource(),
                DatabaseNetValueSource(),
            ]
        self._sources = sources

    async def resolve(self, fund_code: str) -> tuple[str | None, float | None]:
        """
        解析基金净值（带回退）

        按顺序尝试每个数据源，直到成功获取净值。

        Args:
            fund_code: 基金代码

        Returns:
            (净值日期, 单位净值) 元组，所有源都失败返回 (None, None)
        """
        for source in self._sources:
            date, value = await source.get_net_value(fund_code)
            if value is not None and date:
                return date, value

        logger.debug(f"所有净值数据源都失败: {fund_code}")
        return None, None

    async def get_prev_net_value(self, fund_code: str) -> tuple[float | None, str | None]:
        """
        获取上一交易日净值（用于折线图基准线）

        优先从数据库获取最近2个交易日的记录。

        Args:
            fund_code: 基金代码

        Returns:
            (上一交易日净值, 上一交易日净值日期) 元组
        """
        try:
            dao = get_daily_cache_dao()
            recent_days = dao.get_recent_days(fund_code, 2)
            if len(recent_days) >= 2:
                record = recent_days[1]
                if record.unit_net_value is not None:
                    logger.debug(
                        f"从数据库获取前日净值: {fund_code} -> {record.unit_net_value}, 日期: {record.date}"
                    )
                    return record.unit_net_value, record.date
        except Exception as e:
            logger.warning(f"获取前日净值失败: {e}")

        # 回退到天天基金
        try:
            tiantian = TiantianNetValueSource()
            date, value = await tiantian.get_net_value(fund_code)
            if value is not None and date:
                return value, date
        except Exception as e:
            logger.warning(f"从天天基金获取前日净值失败: {e}")

        return None, None
