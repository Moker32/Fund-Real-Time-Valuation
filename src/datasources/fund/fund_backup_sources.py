"""基金备用数据源模块

包含新浪基金和东方财富基金数据源作为备用选项。
"""

import asyncio
import json
import logging
import re
import time
from typing import Any

import httpx

from ..base import DataSource, DataSourceResult, DataSourceType

logger = logging.getLogger(__name__)


class SinaFundDataSource(DataSource):
    """新浪基金数据源 - 备用基金数据源"""

    def __init__(self, timeout: float = 30.0, max_retries: int = 2, retry_delay: float = 1.0):
        """
        初始化新浪基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(name="fund_sina", source_type=DataSourceType.FUND, timeout=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/javascript, */*;q=0.8",
            },
        )

    async def fetch(self, fund_code: str) -> DataSourceResult:
        """
        获取单个基金数据 - 使用新浪基金接口

        Args:
            fund_code: 基金代码 (6位数字)

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

        for attempt in range(self.max_retries):
            try:
                # 使用新浪基金 API
                url = f"https://finance.sina.com.cn/fund/qqjl/{fund_code}.js"
                response = await self.client.get(url, follow_redirects=True)
                response.raise_for_status()

                # 解析 JSON 数据
                text = response.text.strip()
                if not text or text == "null":
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 无数据",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                # 新浪返回格式: var LF_xx={...}
                json_match = re.search(r"\{.+\}", text)
                if not json_match:
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 数据解析失败",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                data = json.loads(json_match.group())

                # 提取数据
                net_value = self._safe_float(data.get("NAV", data.get("unit_nav")))
                estimate_value = (
                    self._safe_float(data.get("ACC_NAV", data.get("acc_nav"))) or net_value
                )
                change_percent = self._safe_float(
                    data.get("NAV_CHG_PCT", data.get("change_percent"))
                )

                # 解析日期
                net_date = str(data.get("UPDATE_DATE", data.get("nav_date", "")))

                result_data = {
                    "fund_code": fund_code,
                    "name": data.get("NAME", data.get("name", f"基金 {fund_code}")),
                    "net_value_date": net_date,
                    "unit_net_value": net_value,
                    "estimated_net_value": estimate_value,
                    "estimated_growth_rate": change_percent,
                    "estimate_time": net_date,
                }

                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=result_data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            except asyncio.TimeoutError:
                await asyncio.sleep(self.retry_delay)
                continue
            except Exception:
                await asyncio.sleep(self.retry_delay)
                continue

        return DataSourceResult(
            success=False,
            error=f"基金 {fund_code} 获取失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    def _validate_fund_code(self, fund_code: str) -> bool:
        """验证基金代码格式"""
        return bool(re.match(r"^\d{6}$", str(fund_code)))

    def _safe_float(self, value: Any) -> float | None:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def fetch_batch(self, fund_codes: list[str]) -> list[DataSourceResult]:
        """批量获取基金数据"""

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


class EastMoneyFundDataSource(DataSource):
    """东方财富基金数据源 - 备用基金数据源"""

    def __init__(self, timeout: float = 30.0, max_retries: int = 2, retry_delay: float = 1.0):
        """
        初始化东方财富基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(name="fund_eastmoney", source_type=DataSourceType.FUND, timeout=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
            },
        )

    async def fetch(self, fund_code: str) -> DataSourceResult:
        """
        获取单个基金数据 - 使用东方财富基金接口

        Args:
            fund_code: 基金代码 (6位数字)

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

        for attempt in range(self.max_retries):
            try:
                # 使用东方财富基金 API
                url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
                response = await self.client.get(url)
                response.raise_for_status()

                text = response.text.strip()
                if not text:
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 无数据",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                # 解析 JS 格式数据
                # 格式: var API_FUND_xxxx={...}
                json_match = re.search(r"=\{[\s\S]*\};?$", text)
                if not json_match:
                    # 尝试另一种格式
                    json_match = re.search(r"\{.+\}", text)

                if not json_match:
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 数据解析失败",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code},
                    )

                data_str = json_match.group().rstrip(";")
                data = json.loads(data_str)

                # 提取数据
                net_value = self._safe_float(data.get("NET", data.get("unit_nav")))
                estimate_value = (
                    self._safe_float(data.get("ACC_NET", data.get("acc_nav"))) or net_value
                )
                change_percent = self._safe_float(data.get("CHANGEPCT", data.get("change_percent")))

                # 解析日期
                net_date = str(data.get("ENDDATE", data.get("nav_date", "")))

                # 获取基金名称
                fund_name = data.get("FUNDNAME", data.get("name", ""))
                if not fund_name:
                    fund_name = f"基金 {fund_code}"

                result_data = {
                    "fund_code": fund_code,
                    "name": fund_name,
                    "net_value_date": net_date,
                    "unit_net_value": net_value,
                    "estimated_net_value": estimate_value,
                    "estimated_growth_rate": change_percent,
                    "estimate_time": net_date,
                }

                self._record_success()
                return DataSourceResult(
                    success=True,
                    data=result_data,
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code},
                )

            except asyncio.TimeoutError:
                await asyncio.sleep(self.retry_delay)
                continue
            except Exception:
                await asyncio.sleep(self.retry_delay)
                continue

        return DataSourceResult(
            success=False,
            error=f"基金 {fund_code} 获取失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code},
        )

    def _validate_fund_code(self, fund_code: str) -> bool:
        """验证基金代码格式"""
        return bool(re.match(r"^\d{6}$", str(fund_code)))

    def _safe_float(self, value: Any) -> float | None:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def fetch_batch(self, fund_codes: list[str]) -> list[DataSourceResult]:
        """批量获取基金数据"""

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
