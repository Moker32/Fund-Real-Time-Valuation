"""天天基金数据源模块

从天天基金接口获取数据。
主要数据来源:
- 天天基金 (fundgz.1234567.com.cn): 实时估值数据
- 东方财富 LOF 接口 (akshare fund_open_fund_info_em): QDII/FOF/LOF 等基金净值
"""

import asyncio
import json
import logging
import re
import time
from typing import Any

import httpx
import pandas as pd

from ..base import DataParseError, DataSource, DataSourceResult, DataSourceType
from .fund_cache_helpers import (
    get_daily_cache_dao,
    get_fund_cache,
)
from .fund_info_utils import (
    _has_real_time_estimate,
    get_basic_info_db,
    get_fund_basic_info,
    save_basic_info_to_db,
)

logger = logging.getLogger(__name__)


class TiantianFundDataSource(DataSource):
    """天天基金数据源 - 从天天基金接口获取数据

    主要数据来源:
    - 天天基金 (fundgz.1234567.com.cn): 实时估值数据
    - 东方财富 LOF 接口 (akshare fund_open_fund_info_em): QDII/FOF/LOF 等基金净值

    注意: 对于 QDII 基金，天天基金返回的估值数据不准确，会跳过改用 akshare 数据源
    """

    def __init__(self, timeout: float = 30.0, max_retries: int = 2, retry_delay: float = 1.0):
        """初始化基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(name="fund_tiantian", source_type=DataSourceType.FUND, timeout=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/javascript, */*;q=0.8",
                "Referer": "http://fundgz.1234567.com.cn/",
            },
        )

    async def fetch(self, fund_code: str, use_cache: bool = True) -> DataSourceResult:
        """
        获取单个基金数据

        缓存策略：
        1. 优先从数据库读取（5分钟过期）
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

        cache_key = f"fund:{self.name}:{fund_code}"

        # 1. 优先从数据库读取每日缓存（5分钟过期）
        if use_cache:
            daily_dao = get_daily_cache_dao()
            if not daily_dao.is_expired(fund_code):
                cached_daily = daily_dao.get_latest(fund_code)
                if cached_daily:
                    # 获取基金类型（从基本信息表）
                    fund_type = ""
                    basic_info = get_basic_info_db(fund_code)
                    if basic_info:
                        fund_type = basic_info.get("type", "") or ""

                    # 优先使用 estimate_time，如果为空则回退到 date
                    estimate_time = cached_daily.estimate_time or cached_daily.date

                    # 构建返回数据格式
                    result_data = {
                        "fund_code": fund_code,
                        "name": basic_info.get("name", "") if basic_info else "",
                        "type": fund_type,
                        "net_value_date": cached_daily.date,
                        "unit_net_value": cached_daily.unit_net_value,
                        "estimated_net_value": cached_daily.estimated_value,
                        "estimated_growth_rate": cached_daily.change_rate,
                        "estimate_time": estimate_time,
                        "has_real_time_estimate": cached_daily.estimated_value is not None,
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
                # 缓存命中
                return DataSourceResult(
                    success=True,
                    data=cached_value,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code, "cache": cache_type},
                )

        # 3. 从 API 获取数据
        # 场内基金（交易所交易）
        is_etf = fund_code.startswith("5") or fund_code.startswith("15")  # ETF
        is_lof = fund_code.startswith("16")  # LOF 基金

        for attempt in range(self.max_retries):
            try:
                # LOF 使用东方财富 LOF 接口
                if is_lof:
                    result = await self._fetch_lof(fund_code, has_real_time_estimate=True)
                    if result.success:
                        # 写入数据库缓存
                        daily_dao = get_daily_cache_dao()
                        daily_dao.save_daily_from_fund_data(fund_code, result.data)
                        # 写入内存/文件缓存
                        cache = get_fund_cache()
                        await cache.set(cache_key, result.data)
                        return result
                    # LOF 获取失败，返回错误（不再尝试其他接口）
                    return DataSourceResult(
                        success=False,
                        error=f"{fund_code} 是 LOF 基金，数据获取失败: {result.error}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                # ETF 使用东方财富 ETF 接口
                if is_etf:
                    result = await self._fetch_etf(fund_code)
                    if result.success:
                        # 写入数据库缓存
                        daily_dao = get_daily_cache_dao()
                        daily_dao.save_daily_from_fund_data(fund_code, result.data)
                        # 写入内存/文件缓存
                        cache = get_fund_cache()
                        await cache.set(cache_key, result.data)
                        return result
                    # ETF 获取失败，返回错误（不再尝试其他接口）
                    return DataSourceResult(
                        success=False,
                        error=f"{fund_code} 是 ETF 基金，数据获取失败: {result.error}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                # 普通基金使用天天基金接口
                url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js?rt={int(time.time() * 1000)}"
                response = await self.client.get(url)
                response.raise_for_status()

                # 检查是否是空响应
                if response.text.strip() in ("jsonpgz();", "jsonpgz()"):
                    # 判断基金类型并返回友好错误
                    if fund_code.startswith("5") or fund_code.startswith("15"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 ETF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code},
                        )
                    if fund_code.startswith("16"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 LOF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code},
                        )

                # 检查是否是空响应
                if response.text.strip() in ("jsonpgz();", "jsonpgz()"):
                    # 天天基金不支持的基金，尝试使用东方财富开放式基金接口
                    # QDII/FOF 基金（如 470888）可能在这里获取到
                    # 这些基金没有实时估值，只有上一个交易日的日增长率
                    result = await self._fetch_lof(fund_code, has_real_time_estimate=False)
                    if result.success:
                        return result

                    # 东方财富接口也失败，返回友好错误
                    if fund_code.startswith("5") or fund_code.startswith("15"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 ETF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code},
                        )
                    if fund_code.startswith("16"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 LOF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code},
                        )
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 数据获取失败: {result.error}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                # 解析返回的 JS 数据
                data = self._parse_response(response.text, fund_code)

                if data:
                    # 获取基金类型
                    fund_type = await self._get_fund_type(fund_code)
                    if not fund_type:
                        # Fallback: 从基金名称中识别 QDII/FOF
                        fund_name = data.get("name", "")
                        if "(QDII)" in fund_name or fund_name.endswith("QDII"):
                            fund_type = "QDII"
                        elif fund_name.endswith("FOF") or "(FOF)" in fund_name:
                            fund_type = "FOF"

                    # QDII/FOF 基金不应该使用天天基金的数据（估值数据不准确）
                    # 跳过天天基金，直接使用 akshare 东方财富接口
                    fund_name = data.get("name", "")
                    if fund_type and (fund_type.startswith("QDII") or fund_type == "FOF"):
                        if fund_type == "FOF":
                            name_upper = fund_name.upper()
                            if (
                                "QDII" not in name_upper
                                and "海外" not in name_upper
                                and "全球" not in name_upper
                            ):
                                # 非投资海外的 FOF 可以使用天天基金数据
                                pass
                            else:
                                # QDII-FOF 或投资海外的 FOF，跳过天天基金
                                result = await self._fetch_lof(
                                    fund_code, has_real_time_estimate=False
                                )
                                if result.success:
                                    return result
                        else:
                            # QDII 基金，跳过天天基金
                            result = await self._fetch_lof(fund_code, has_real_time_estimate=False)
                            if result.success:
                                return result

                    data["type"] = fund_type

                    # 根据基金类型和名称判断是否有实时估值
                    data["has_real_time_estimate"] = _has_real_time_estimate(
                        fund_type or "", fund_name
                    )

                    # QDII 基金或投资海外的 FOF 需要获取上一交易日净值用于对比
                    if not data["has_real_time_estimate"]:
                        # 调用东方财富接口获取上一净值
                        lof_result = await self._fetch_lof(fund_code, has_real_time_estimate=False)
                        if lof_result.success:
                            data["prev_net_value"] = lof_result.data.get("prev_net_value")
                            data["prev_net_value_date"] = lof_result.data.get("prev_net_value_date")
                        else:
                            data["prev_net_value"] = None
                            data["prev_net_value_date"] = None
                    else:
                        data["prev_net_value"] = None
                        data["prev_net_value_date"] = None

                    self._record_success()

                    # 保存基金基本信息到数据库
                    save_basic_info_to_db(
                        fund_code,
                        {
                            "short_name": data.get("name", ""),
                            "name": data.get("name", ""),
                            "type": data.get("type", ""),
                            "net_value": data.get("unit_net_value"),
                            "net_value_date": data.get("net_value_date", ""),
                        },
                    )

                    # 写入数据库缓存
                    daily_dao = get_daily_cache_dao()
                    daily_dao.save_daily_from_fund_data(fund_code, data)
                    # 写入内存/文件缓存
                    cache = get_fund_cache()
                    await cache.set(cache_key, data)

                    return DataSourceResult(
                        success=True,
                        data=data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return DataSourceResult(
                        success=False,
                        error=f"基金不存在: {fund_code}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code, "status_code": 404},
                    )
                await self._handle_retry_delay(attempt)

            except httpx.RequestError:
                await self._handle_retry_delay(attempt)

            except json.JSONDecodeError as e:
                self._request_count += 1
                self._error_count += 1
                return DataSourceResult(
                    success=False,
                    error=f"数据解析失败: {str(e)}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

        # 如果是 LOF，返回更明确的错误信息
        if is_lof:
            return DataSourceResult(
                success=False,
                error=f"{fund_code} 是 QDII/LOF 基金，akshare 东方财富接口返回数据为空",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        # 如果是 ETF，返回更明确的错误信息
        if is_etf:
            return DataSourceResult(
                success=False,
                error=f"{fund_code} 是 ETF 基金，当前数据源暂不支持",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        return DataSourceResult(
            success=False,
            error=f"获取基金数据失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    async def _fetch_etf(self, fund_code: str) -> DataSourceResult:
        """
        获取 ETF 数据 - 使用东方财富接口

        Args:
            fund_code: ETF 代码

        Returns:
            DataSourceResult: ETF 数据结果
        """
        try:
            # 使用 akshare 获取 ETF 数据
            loop = asyncio.get_running_loop()
            import akshare as ak

            # 获取 ETF 最新数据
            df = await loop.run_in_executor(None, lambda: ak.fund_etf_fund_info_em(fund=fund_code))

            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    error=f"ETF {fund_code} 无数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            # 获取最新一条数据
            latest = df.iloc[0]

            # 使用缓存获取基金名称
            fund_info = get_fund_basic_info(fund_code)
            if fund_info:
                fund_name, fund_type = fund_info
            else:
                fund_name, fund_type = "", ""

            # 如果没获取到名称，使用基金代码作为名称
            if not fund_name:
                fund_name = f"ETF {fund_code}"

            # 提取数据
            data = {
                "fund_code": fund_code,
                "name": fund_name,
                "type": fund_type,
                "net_value_date": str(latest.get("净值日期", "")),
                "unit_net_value": float(latest.get("单位净值", 0))
                if pd.notna(latest.get("单位净值"))
                else None,
                "estimated_net_value": float(latest.get("单位净值", 0))
                if pd.notna(latest.get("单位净值"))
                else None,
                "estimated_growth_rate": float(latest.get("日增长率", 0))
                if pd.notna(latest.get("日增长率"))
                else None,
                "estimate_time": str(latest.get("净值日期", "")),
                "has_real_time_estimate": True,  # ETF 有实时估值
            }

            self._record_success()

            # 保存基金基本信息到数据库
            save_basic_info_to_db(
                fund_code,
                {
                    "short_name": fund_name,
                    "name": fund_name,
                    "type": fund_type,
                    "net_value": data.get("unit_net_value"),
                    "net_value_date": data.get("net_value_date", ""),
                },
            )

            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )
        except Exception as e:
            return DataSourceResult(
                success=False,
                error=f"ETF 数据获取失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

    async def _fetch_lof(
        self, fund_code: str, has_real_time_estimate: bool = True
    ) -> DataSourceResult:
        """
        获取 LOF/QDII/FOF 基金数据 - 使用东方财富开放式基金接口

        支持: LOF、QDII、FOF 等所有在天天基金网显示的开放式基金

        Args:
            fund_code: 基金代码
            has_real_time_estimate: 是否有实时估值（默认为 True，QDII/FOF 应设为 False）

        Returns:
            DataSourceResult: 基金数据结果
        """
        try:
            loop = asyncio.get_running_loop()
            import akshare as ak

            # 获取基金最新净值数据
            df = await loop.run_in_executor(
                None,
                lambda: ak.fund_open_fund_info_em(
                    symbol=fund_code, indicator="单位净值走势", period="近一年"
                ),
            )

            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    error=f"基金 {fund_code} 无净值数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            # 获取最新一条数据（最后一行是最新的，因为数据是按日期升序排列的）
            # 注意：akshare 可能返回末尾的"封闭期"记录（净值为 NaT），需要过滤
            df_valid = df[df["净值日期"].notna()]
            if df_valid.empty:
                return DataSourceResult(
                    success=False,
                    error=f"基金 {fund_code} 无有效净值数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            # 使用缓存获取基金简称和类型
            fund_info = get_fund_basic_info(fund_code)
            if fund_info:
                fund_name, fund_type = fund_info
            else:
                fund_name, fund_type = "", ""

            # 如果没获取到名称，使用基金代码作为名称
            if not fund_name:
                fund_name = f"基金 {fund_code}"

            # 根据基金类型和名称判断是否有实时估值
            has_real_time = has_real_time_estimate and _has_real_time_estimate(fund_type, fund_name)

            # 提取数据
            # 使用已过滤的有效数据 df_valid 获取最新和上一条记录
            latest = df_valid.iloc[-1]
            prev_row = df_valid.iloc[-2] if len(df_valid) >= 2 else df_valid.iloc[-1]

            net_date = str(latest.get("净值日期", ""))
            prev_net_date = str(prev_row.get("净值日期", ""))
            unit_net = (
                float(latest.get("单位净值", 0)) if pd.notna(latest.get("单位净值")) else None
            )
            prev_unit_net = (
                float(prev_row.get("单位净值", 0)) if pd.notna(prev_row.get("单位净值")) else None
            )
            daily_change = (
                float(latest.get("日增长率", 0)) if pd.notna(latest.get("日增长率")) else None
            )

            data = {
                "fund_code": fund_code,
                "name": fund_name,
                "type": fund_type,
                "net_value_date": net_date,
                "unit_net_value": unit_net,
                "prev_net_value_date": prev_net_date,
                "prev_net_value": prev_unit_net,
                "estimated_net_value": unit_net,  # 开放式基金暂无实时估值，使用单位净值
                "estimated_growth_rate": daily_change,
                "estimate_time": net_date,
                "has_real_time_estimate": has_real_time,  # 根据基金类型判断是否有实时估值
            }

            self._record_success()

            # 保存基金基本信息到数据库
            save_basic_info_to_db(
                fund_code,
                {
                    "short_name": fund_name,
                    "name": fund_name,
                    "type": fund_type,
                    "net_value": unit_net,
                    "net_value_date": net_date,
                },
            )

            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )
        except Exception as e:
            return DataSourceResult(
                success=False,
                error=f"基金数据获取失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code},
            )

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

        # 处理异常情况
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

    def _validate_fund_code(self, fund_code: str) -> bool:
        """
        验证基金代码格式

        Args:
            fund_code: 基金代码

        Returns:
            bool: 是否有效
        """
        return bool(re.match(r"^\d{6}$", str(fund_code)))

    async def _get_fund_type(self, fund_code: str) -> str:
        """
        获取基金类型信息

        Args:
            fund_code: 基金代码

        Returns:
            str: 基金类型（如：股票型、混合型、债券型、QDII、ETF等）
        """
        # 使用缓存获取基金信息
        fund_info = get_fund_basic_info(fund_code)
        if fund_info:
            _, fund_type = fund_info
            return fund_type
        return ""

    def _parse_response(self, response_text: str, fund_code: str) -> dict[str, Any] | None:
        """
        解析天天基金返回的 JS 数据

        Args:
            response_text: 原始响应文本
            fund_code: 基金代码

        Returns:
            Optional[Dict]: 解析后的数据字典
        """
        try:
            # 天天基金返回格式: jsonpgz({"fundcode":"161039",...});
            # 使用正则提取 JSON 内容
            pattern = r"jsonpgz\((.*)\);?"
            match = re.search(pattern, response_text)

            if not match:
                raise DataParseError(
                    message="无法解析基金数据响应",
                    source_type=self.source_type,
                    details={"response_preview": response_text[:100]},
                )

            json_str = match.group(1)
            data = json.loads(json_str)

            # 标准化字段名
            return {
                "fund_code": data.get("fundcode", ""),
                "name": data.get("name", ""),
                "net_value_date": data.get("jzrq", ""),
                "unit_net_value": self._safe_float(data.get("dwjz")),
                "estimated_net_value": self._safe_float(data.get("gsz")),
                "estimated_growth_rate": self._safe_float(data.get("gszzl")),
                "estimate_time": data.get("gztime", ""),
                "raw_data": data,
            }

        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            raise DataParseError(
                message=f"基金数据解析错误: {str(e)}",
                source_type=self.source_type,
                details={"fund_code": fund_code},
            )

    def _safe_float(self, value: Any) -> float | None:
        """
        安全转换为浮点数

        Args:
            value: 待转换的值

        Returns:
            Optional[float]: 转换后的值，失败返回 None
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def _handle_retry_delay(self, attempt: int):
        """处理重试延迟"""
        if attempt < self.max_retries - 1:
            await asyncio.sleep(self.retry_delay * (attempt + 1))

    async def close(self):
        """关闭异步客户端"""
        await self.client.aclose()

    def __del__(self):
        """析构时确保关闭客户端（异步客户端需要在异步上下文中关闭）"""
        try:
            if hasattr(self, "client") and self.client.is_closed is False:
                # Note: 异步客户端无法在 __del__ 中安全关闭
                # 应使用 async with 或显式调用 close() 方法
                pass
        except Exception:
            pass

    async def health_check(self) -> bool:
        """
        健康检查 - 天天基金接口

        Returns:
            bool: 健康状态
        """
        try:
            # 天天基金接口支持批量查询，使用一个示例基金代码
            url = f"http://fundgz.1234567.com.cn/js/161039.js?rt={int(time.time() * 1000)}"
            response = await self.client.get(url, timeout=self.timeout)
            response.raise_for_status()

            # 验证返回数据格式
            data = response.text
            if data and "jsonpgz" in data and "fundcode" in data:
                return True
            return False
        except Exception:
            return False
