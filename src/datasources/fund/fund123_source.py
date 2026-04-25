"""fund123.cn 基金数据源模块

主要数据来源:
- fund123.cn API: 日内实时估算数据（需要 CSRF token）
- akshare (fund_open_fund_info_em): 基金净值和净值日期

注意: fund123.cn 本身不提供基金净值，净值数据来自 akshare
"""

import asyncio
import logging
import time

from ..base import DataSourceResult, DataSourceType
from .fund123_client import Fund123Client
from .fund_base_source import FundDataSourceBase
from .fund_cache_helpers import (
    get_daily_cache_dao,
    get_fund_cache,
    get_intraday_cache_dao,
)
from .fund_info_utils import (
    _get_latest_trading_day,
    _has_real_time_estimate,
    _infer_fund_type_from_name,
    get_basic_info_db,
    get_fund_basic_info,
    save_basic_info_to_db,
)
from .fund_net_value import NetValueResolver

logger = logging.getLogger(__name__)


class Fund123DataSource(FundDataSourceBase):
    """fund123.cn 基金数据源

    主要数据来源:
    - fund123.cn API: 日内实时估算数据（需要 CSRF token）
    - akshare (fund_open_fund_info_em): 基金净值和净值日期

    注意: fund123.cn 本身不提供基金净值，净值数据来自 akshare
    """

    BASE_URL = "https://www.fund123.cn"
    MAX_CONCURRENT_REQUESTS = 15

    def __init__(self, timeout: float = 15.0, max_retries: int = 3, retry_delay: float = 0.5):
        """
        初始化 fund123 基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(name="fund123", source_type=DataSourceType.FUND, timeout=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._net_value_resolver = NetValueResolver()
        self._client = Fund123Client.get_instance()

    async def _get_prev_net_value(self, fund_code: str) -> tuple[float | None, str | None]:
        """
        获取上一交易日净值（用于折线图基准线）

        委托给 NetValueResolver。

        Args:
            fund_code: 基金代码

        Returns:
            (prev_net_value, prev_net_value_date) 元组，获取失败返回 (None, None)
        """
        return await self._net_value_resolver.get_prev_net_value(fund_code)

    async def fetch(self, fund_code: str, use_cache: bool = True) -> DataSourceResult:
        """
        获取单个基金数据

        缓存策略：
        1. 优先从数据库读取每日缓存（5分钟过期）
        2. 数据库缓存过期时，从 API 获取并更新数据库
        3. 最后回退到内存/文件缓存

        Args:
            fund_code: 基金代码 (6位数字)
            use_cache: 是否使用缓存

        Returns:
            DataSourceResult: 包含基金数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        today = time.strftime("%Y-%m-%d")
        cache_key = f"fund:{self.name}:{fund_code}"

        # 1. 优先从数据库读取每日缓存
        if use_cache:
            daily_dao = get_daily_cache_dao()
            cached_daily = daily_dao.get_latest(fund_code)
            if cached_daily:
                from datetime import date

                # 获取上一交易日（最新净值日期）
                latest_trading_day = _get_latest_trading_day()
                cached_date_str = cached_daily.date
                use_cached = False

                # 检查缓存的净值日期是否是上一交易日
                if cached_date_str and latest_trading_day:
                    try:
                        cached_date = date.fromisoformat(cached_date_str)
                        latest_date = date.fromisoformat(latest_trading_day)
                        # 只有缓存净值日期是最新交易日，才使用缓存
                        if cached_date == latest_date and not daily_dao.is_expired(fund_code):
                            # 进一步检查：盘中时，缓存的 estimate_time 必须是今天的数据才使用
                            # 如果 estimate_time 是昨天的，说明盘中没有更新，需要重新获取
                            if cached_daily.estimate_time:
                                today_str = time.strftime("%Y-%m-%d")
                                if not cached_daily.estimate_time.startswith(today_str):
                                    # estimate_time 不是今天的，缓存可能已过时
                                    use_cached = False
                    except ValueError:
                        # 日期解析失败，不使用缓存
                        use_cached = False

                if use_cached:
                    # 获取基金类型（从基本信息表）
                    fund_type = ""
                    basic_info = get_basic_info_db(fund_code)
                    if basic_info:
                        fund_type = basic_info.get("type", "") or ""

                    # 获取上一交易日净值（用于折线图基准线）
                    prev_net_value, prev_net_value_date = await self._get_prev_net_value(fund_code)

                    # 优先使用 estimate_time，如果为空则回退到 date
                    estimate_time = cached_daily.estimate_time or cached_daily.date

                    # 构建返回数据格式
                    result_data = {
                        "fund_code": fund_code,
                        "name": basic_info.get("name", "") if basic_info else "",
                        "type": fund_type,
                        "net_value_date": cached_daily.date,
                        "unit_net_value": cached_daily.unit_net_value,
                        "prev_net_value": prev_net_value,
                        "prev_net_value_date": prev_net_value_date,
                        "estimated_net_value": cached_daily.estimated_value,
                        "estimated_growth_rate": cached_daily.change_rate,
                        "estimate_time": estimate_time,
                        "has_real_time_estimate": cached_daily.estimated_value is not None,
                        "from_cache": "database",
                    }
                    return DataSourceResult(
                        success=True,
                        data=result_data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code, "cache": "database"},
                    )

        # 2. 检查内存/文件缓存
        if use_cache:
            cache = get_fund_cache()
            cached_value, cache_type = await cache.get(cache_key)
            if cached_value is not None:
                cached_value["from_cache"] = cache_type
                return DataSourceResult(
                    success=True,
                    data=cached_value,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code, "cache": cache_type},
                )

        # 3. 从 API 获取数据
        for attempt in range(self.max_retries):
            try:
                # 直接调用异步方法
                result = await self._fetch_fund_data(fund_code)

                if result.success:
                    self._record_success()

                    # 写入数据库每日缓存
                    daily_dao = get_daily_cache_dao()
                    daily_dao.save_daily_from_fund_data(fund_code, result.data)

                    # 保存基金基本信息到数据库（使用已推断的类型）
                    save_basic_info_to_db(
                        fund_code,
                        {
                            "short_name": result.data.get("name", ""),
                            "name": result.data.get("name", ""),
                            "type": result.data.get("type", ""),
                            "net_value": result.data.get("unit_net_value"),
                            "net_value_date": result.data.get("net_value_date", ""),
                        },
                    )

                    # 写入内存/文件缓存
                    cache = get_fund_cache()
                    await cache.set(cache_key, result.data)

                    # 保存日内分时数据到数据库缓存
                    intraday_data = result.data.get("intraday", [])
                    if intraday_data:
                        intraday_dao = get_intraday_cache_dao()
                        intraday_dao.save_intraday(fund_code, today, intraday_data)

                    result.data["from_cache"] = "api"
                    return result
                else:
                    # 如果失败且还有重试次数，刷新 token 后重试
                    if attempt < self.max_retries - 1:
                        await Fund123Client._refresh_csrf_token()
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return result

            except Exception as e:
                logger.error(f"获取基金数据异常: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue

        return DataSourceResult(
            success=False,
            error=f"获取基金数据失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    async def _fetch_fund_data(self, fund_code: str) -> DataSourceResult:
        """获取基金数据（带并发控制）"""
        # 使用 semaphore 限制并发数
        async with Fund123Client._get_semaphore():
            return await self._do_fetch_fund_data(fund_code)

    async def _do_fetch_fund_data(self, fund_code: str) -> DataSourceResult:
        """实际获取基金数据的实现"""
        # 获取 CSRF token
        csrf_token = await Fund123Client._get_csrf_token()
        if not csrf_token:
            return DataSourceResult(
                success=False,
                error="获取 CSRF token 失败",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        # 1. 获取基金基本信息（fund_key 和 fund_name）
        search_url = f"{self.BASE_URL}/api/fund/searchFund?_csrf={csrf_token}"
        search_response = await Fund123Client._ensure_client().post(
            search_url, json={"fundCode": fund_code}, timeout=self.timeout
        )

        if not search_response.is_success:
            return DataSourceResult(
                success=False,
                error=f"搜索基金失败: {search_response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        search_data = search_response.json()
        if not search_data.get("success"):
            return DataSourceResult(
                success=False,
                error=f"基金不存在: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        fund_info = search_data.get("fundInfo", {})
        fund_key = fund_info.get("key")
        fund_name = fund_info.get("fundName", f"基金 {fund_code}")

        # 2. 获取日内估值数据
        today = time.strftime("%Y-%m-%d")
        intraday_url = f"{self.BASE_URL}/api/fund/queryFundEstimateIntraday?_csrf={csrf_token}"
        intraday_response = await Fund123Client._ensure_client().post(
            intraday_url,
            json={
                "startTime": today,
                "endTime": today,
                "limit": 200,
                "productId": fund_key,
                "format": True,
                "source": "WEALTHBFFWEB",
            },
            timeout=self.timeout,
        )

        if not intraday_response.is_success:
            return DataSourceResult(
                success=False,
                error=f"获取日内数据失败: {intraday_response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        intraday_data = intraday_response.json()
        intraday_list = intraday_data.get("list", [])

        # 解析数据
        growth_rate = None  # 初始化 growth_rate
        if intraday_list:
            latest = intraday_list[-1]
            estimate_value = float(latest.get("forecastNetValue", 0))
            # 暂时使用 API 提供的涨跌幅，后面会根据净值重新计算
            api_growth_rate = float(latest.get("forecastGrowth", 0)) * 100
            growth_rate = api_growth_rate  # 有日内数据时使用 api_growth_rate
            estimate_time = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(latest.get("time", 0) / 1000)
            )
        else:
            estimate_value = None
            api_growth_rate = 0.0
            estimate_time = ""

        # 4. 如果日内数据为空，尝试从 search 结果中获取 dayOfGrowth（QDII 基金会有这个字段）
        day_of_growth = fund_info.get("dayOfGrowth", "")
        if not intraday_list and day_of_growth:
            # 解析 "5.59%" -> 5.59
            try:
                growth_rate = float(day_of_growth.rstrip("%"))
            except (ValueError, AttributeError):
                growth_rate = 0.0

        # 3. 获取最新净值信息（使用 NetValueResolver 带回退）
        net_value = None
        net_date = ""

        # 使用 NetValueResolver 获取净值
        net_date, net_value = await self._net_value_resolver.resolve(fund_code)

        # 获取基金类型（优先从 akshare 获取并缓存到数据库）
        fund_type = ""
        basic_info = get_basic_info_db(fund_code)
        if basic_info:
            fund_type = basic_info.get("type", "") or ""

        # 如果数据库中没有类型，从 akshare 获取（首次获取时）
        if not fund_type:
            # get_fund_basic_info 会调用 akshare 获取类型并保存到数据库
            # 使用 run_in_executor 避免阻塞事件循环
            loop = asyncio.get_running_loop()
            fund_info_result = await loop.run_in_executor(None, get_fund_basic_info, fund_code)
            if fund_info_result:
                _, fund_type = fund_info_result

        # 备选方案：从基金名称中识别（akshare 获取失败时）
        if not fund_type:
            fund_type = _infer_fund_type_from_name(fund_name)

        # 判断是否有实时估值
        # QDII 基金和投资海外的 FOF 无实时估值，因为它们投资海外市场，净值更新延迟
        # ETF-联接和普通 FOF 基金有实时估值，因为它们跟踪的底层资产是国内基金
        has_real_time = _has_real_time_estimate(fund_type, fund_name) and estimate_value is not None

        # 获取上一交易日净值（用于折线图基准线）
        prev_net_value, prev_net_value_date = await self._get_prev_net_value(fund_code)

        # 验证涨跌幅数据一致性（调试日志）
        # 注意：fund123.cn 的涨跌幅是基于最新净值（net_value）计算的
        # 而不是前日净值（prev_net_value）
        if estimate_value and net_value and net_value > 0:
            calculated_growth_rate = (estimate_value - net_value) / net_value * 100
            logger.debug(
                "[FUND_DIAGNOSTIC] %s: API_growth_rate=%.4f%%, calculated_rate=%.4f%%, "
                "estimate_value=%s, net_value=%s, diff=%.4f%%",
                fund_code,
                api_growth_rate,
                calculated_growth_rate,
                estimate_value,
                net_value,
                abs(api_growth_rate - calculated_growth_rate),
            )
            # 如果差异超过 0.1%，记录警告
            if abs(api_growth_rate - calculated_growth_rate) > 0.1:
                logger.warning(
                    "[FUND_DIAGNOSTIC] %s: 涨跌幅不一致! API=%.4f%%, 计算=%.4f%%, 差异=%.4f%%",
                    fund_code,
                    api_growth_rate,
                    calculated_growth_rate,
                    api_growth_rate - calculated_growth_rate,
                )

        result_data = {
            "fund_code": fund_code,
            "name": fund_name,
            "type": fund_type,
            "net_value_date": net_date,
            "unit_net_value": net_value,
            "prev_net_value": prev_net_value,
            "prev_net_value_date": prev_net_value_date,
            "estimated_net_value": estimate_value,
            "estimated_growth_rate": growth_rate if growth_rate else None,
            "estimate_time": estimate_time,
            "has_real_time_estimate": has_real_time,
            "intraday": [
                {
                    "time": time.strftime("%H:%M", time.localtime(item.get("time", 0) / 1000)),
                    "price": float(item.get("forecastNetValue", 0)),
                    "change": round(float(item.get("forecastGrowth", 0)) * 100, 4),
                }
                for item in intraday_list
            ],
        }

        return DataSourceResult(
            success=True,
            data=result_data,
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    async def fetch_intraday(self, fund_code: str, use_cache: bool = True) -> DataSourceResult:
        """
        获取基金日内分时数据

        缓存策略：
        1. 优先从 SQLite 数据库读取（60秒过期）
        2. 数据库缓存过期时，从 API 获取并更新数据库
        3. 最后回退到内存/文件缓存

        Args:
            fund_code: 基金代码 (6位数字)
            use_cache: 是否使用缓存

        Returns:
            DataSourceResult: 包含日内分时数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        cache_key = f"fund:{self.name}:{fund_code}:intraday"
        today = time.strftime("%Y-%m-%d")

        # 1. 优先从数据库读取日内分时缓存（60秒过期）
        if use_cache:
            intraday_dao = get_intraday_cache_dao()
            if not intraday_dao.is_expired(fund_code, today):
                cached_records = intraday_dao.get_intraday(fund_code, today)
                if cached_records:
                    # 从数据库记录构建返回数据
                    intraday_points = [
                        {"time": record.time, "price": record.price, "change": record.change_rate}
                        for record in cached_records
                    ]
                    result_data = {
                        "fund_code": fund_code,
                        "name": "",
                        "date": today,
                        "data": intraday_points,
                        "count": len(intraday_points),
                        "from_cache": "database",
                        "cache_expired": False,
                    }
                    return DataSourceResult(
                        success=True,
                        data=result_data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={
                            "fund_code": fund_code,
                            "cache": "database",
                            "cache_expired": False,
                        },
                    )

        # 2. 检查内存/文件缓存
        if use_cache:
            cache = get_fund_cache()
            cached_value, cache_type = await cache.get(cache_key)
            if cached_value is not None:
                cached_value["from_cache"] = cache_type
                cached_value["cache_expired"] = True
                return DataSourceResult(
                    success=True,
                    data=cached_value,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code, "cache": cache_type, "cache_expired": True},
                )

        for attempt in range(self.max_retries):
            try:
                # 直接调用异步方法
                result = await self._fetch_intraday_data(fund_code)

                if result.success:
                    self._record_success()

                    # 写入数据库缓存
                    intraday_dao = get_intraday_cache_dao()
                    intraday_dao.save_intraday(fund_code, today, result.data.get("data", []))

                    # 写入内存/文件缓存（缓存时间较短，5分钟）
                    cache = get_fund_cache()
                    await cache.set(cache_key, result.data, ttl_seconds=300)

                    result.data["from_cache"] = "api"
                    result.data["cache_expired"] = False
                    return result
                else:
                    if attempt < self.max_retries - 1:
                        await Fund123Client._refresh_csrf_token()
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return result

            except Exception as e:
                logger.error(f"获取日内数据异常: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue

        return DataSourceResult(
            success=False,
            error=f"获取日内数据失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    async def _fetch_intraday_data(self, fund_code: str) -> DataSourceResult:
        """获取基金日内分时数据（带并发控制）"""
        # 使用 semaphore 限制并发数
        async with Fund123Client._get_semaphore():
            return await self._do_fetch_intraday_data(fund_code)

    async def _do_fetch_intraday_data(self, fund_code: str) -> DataSourceResult:
        """实际获取基金日内分时数据的实现"""
        # 获取 CSRF token
        csrf_token = await Fund123Client._get_csrf_token()
        if not csrf_token:
            return DataSourceResult(
                success=False,
                error="获取 CSRF token 失败",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        # 1. 获取基金基本信息（fund_key 和 fund_name）
        search_url = f"{self.BASE_URL}/api/fund/searchFund?_csrf={csrf_token}"
        search_response = await Fund123Client._ensure_client().post(
            search_url, json={"fundCode": fund_code}, timeout=self.timeout
        )

        if not search_response.is_success:
            return DataSourceResult(
                success=False,
                error=f"搜索基金失败: {search_response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        search_data = search_response.json()
        if not search_data.get("success"):
            return DataSourceResult(
                success=False,
                error=f"基金不存在: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        fund_info = search_data.get("fundInfo", {})
        fund_key = fund_info.get("key")
        fund_name = fund_info.get("fundName", f"基金 {fund_code}")

        # 2. 获取日内估值数据
        today = time.strftime("%Y-%m-%d")
        intraday_url = f"{self.BASE_URL}/api/fund/queryFundEstimateIntraday?_csrf={csrf_token}"
        intraday_response = await Fund123Client._ensure_client().post(
            intraday_url,
            json={
                "startTime": today,
                "endTime": today,
                "limit": 200,
                "productId": fund_key,
                "format": True,
                "source": "WEALTHBFFWEB",
            },
            timeout=self.timeout,
        )

        if not intraday_response.is_success:
            return DataSourceResult(
                success=False,
                error=f"获取日内数据失败: {intraday_response.status_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        intraday_data = intraday_response.json()
        intraday_list = intraday_data.get("list", [])

        # 解析数据，返回前端直接可用的格式
        intraday_points = []
        if intraday_list:
            for item in intraday_list:
                time_ms = item.get("time", 0)
                # 将毫秒时间戳转换为 HH:mm 格式
                time_str = time.strftime("%H:%M", time.localtime(time_ms / 1000))
                intraday_points.append(
                    {
                        "time": time_str,
                        "price": float(item.get("forecastNetValue", 0)),
                        "change": round(float(item.get("forecastGrowth", 0)) * 100, 4),
                    }
                )

        result_data = {
            "fund_code": fund_code,
            "name": fund_name,
            "date": today,
            "data": intraday_points,
            "count": len(intraday_points),
        }

        return DataSourceResult(
            success=True,
            data=result_data,
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    async def fetch_intraday_by_date(self, fund_code: str, date: str) -> DataSourceResult:
        """
        获取指定日期的基金日内分时数据（仅从缓存读取）

        Args:
            fund_code: 基金代码 (6位数字)
            date: 日期 (YYYY-MM-DD 格式)

        Returns:
            DataSourceResult: 包含日内分时数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        # 从数据库缓存读取指定日期的数据
        intraday_dao = get_intraday_cache_dao()
        cached_records = intraday_dao.get_intraday(fund_code, date)

        if cached_records:
            intraday_points = [
                {"time": record.time, "price": record.price, "change": record.change_rate}
                for record in cached_records
            ]
            result_data = {
                "fund_code": fund_code,
                "name": "",
                "date": date,
                "data": intraday_points,
                "count": len(intraday_points),
                "from_cache": "database",
            }
            return DataSourceResult(
                success=True,
                data=result_data,
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code, "date": date, "cache": "database"},
            )

        return DataSourceResult(
            success=False,
            error=f"指定日期 {date} 的数据不存在",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code, "date": date},
        )

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 健康状态
        """
        try:
            token = await Fund123Client._get_csrf_token()
            return token is not None
        except Exception:
            return False

    async def fetch_batch(self, fund_codes: list[str]) -> list[DataSourceResult]:
        """
        批量获取基金数据

        Args:
            fund_codes: 基金代码列表

        Returns:
            List[DataSourceResult]: 每个基金的结果列表
        """

        async def fetch_one(code: str) -> DataSourceResult:
            return await self.fetch(code)

        tasks = [fetch_one(code) for code in fund_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DataSourceResult(
                        success=False,
                        error=str(result),
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_codes[i]},
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def close(self):
        """关闭客户端"""
        await Fund123Client.close()
