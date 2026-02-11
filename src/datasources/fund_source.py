"""
基金数据源模块
实现从天天基金/新浪接口获取基金实时估值数据
"""

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from .base import (
    DataParseError,
    DataSource,
    DataSourceResult,
    DataSourceType,
)
from .dual_cache import DualLayerCache

# 全局缓存实例（单例模式）
_fund_cache: DualLayerCache | None = None


def get_fund_cache() -> DualLayerCache:
    """获取基金缓存单例"""
    global _fund_cache
    if _fund_cache is None:
        cache_dir = Path.home() / ".fund-tui" / "cache" / "funds"
        _fund_cache = DualLayerCache(
            cache_dir=cache_dir,
            memory_ttl=30,      # 内存缓存 30 秒
            file_ttl=300,        # 文件缓存 5 分钟
            max_memory_items=100
        )
    return _fund_cache


class FundDataSource(DataSource):
    """基金数据源 - 从天天基金接口获取数据"""

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_delay: float = 1.0
    ):
        """
        初始化基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(
            name="fund_tiantian",
            source_type=DataSourceType.FUND,
            timeout=timeout
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/javascript, */*;q=0.8",
                "Referer": "http://fundgz.1234567.com.cn/"
            }
        )

    async def fetch(self, fund_code: str, use_cache: bool = True) -> DataSourceResult:
        """
        获取单个基金数据

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
                metadata={"fund_code": fund_code}
            )

        cache_key = f"fund:{self.name}:{fund_code}"

        # 检查缓存
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
                    metadata={"fund_code": fund_code, "cache": cache_type}
                )

        # 判断基金类型
        # 场内基金（交易所交易）
        is_etf = fund_code.startswith("5") or fund_code.startswith("15")  # ETF
        is_lof = fund_code.startswith("16")  # LOF 基金

        for attempt in range(self.max_retries):
            try:
                # LOF 使用东方财富 LOF 接口
                if is_lof:
                    result = await self._fetch_lof(fund_code)
                    if result.success:
                        # 写入缓存
                        cache_key = f"fund:{self.name}:{fund_code}"
                        cache = get_fund_cache()
                        await cache.set(cache_key, result.data)
                        return result
                    # LOF 获取失败，返回错误（不再尝试其他接口）
                    return DataSourceResult(
                        success=False,
                        error=f"{fund_code} 是 LOF 基金，数据获取失败: {result.error}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code}
                    )

                # ETF 使用东方财富 ETF 接口
                if is_etf:
                    result = await self._fetch_etf(fund_code)
                    if result.success:
                        # 写入缓存
                        cache_key = f"fund:{self.name}:{fund_code}"
                        cache = get_fund_cache()
                        await cache.set(cache_key, result.data)
                        return result
                    # ETF 获取失败，返回错误（不再尝试其他接口）
                    return DataSourceResult(
                        success=False,
                        error=f"{fund_code} 是 ETF 基金，数据获取失败: {result.error}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code}
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
                            metadata={"fund_code": fund_code}
                        )
                    if fund_code.startswith("16"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 LOF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code}
                        )

                # 检查是否是空响应
                if response.text.strip() in ("jsonpgz();", "jsonpgz()"):
                    # 天天基金不支持的基金，尝试使用东方财富开放式基金接口
                    # QDII/FOF 基金（如 006476）可能在这里获取到
                    result = await self._fetch_lof(fund_code)
                    if result.success:
                        return result

                    # 东方财富接口也失败，返回友好错误
                    if fund_code.startswith("5") or fund_code.startswith("15"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 ETF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code}
                        )
                    if fund_code.startswith("16"):
                        return DataSourceResult(
                            success=False,
                            error=f"{fund_code} 是 LOF 基金，请使用场内基金交易接口",
                            timestamp=time.time(),
                            source=self.name,
                            metadata={"fund_code": fund_code}
                        )
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 数据获取失败: {result.error}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code}
                    )

                # 解析返回的 JS 数据
                data = self._parse_response(response.text, fund_code)

                if data:
                    # 获取基金类型
                    fund_type = await self._get_fund_type(fund_code)
                    if fund_type:
                        data["type"] = fund_type

                    self._record_success()

                    # 写入缓存
                    cache_key = f"fund:{self.name}:{fund_code}"
                    cache = get_fund_cache()
                    await cache.set(cache_key, data)

                    return DataSourceResult(
                        success=True,
                        data=data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code}
                    )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return DataSourceResult(
                        success=False,
                        error=f"基金不存在: {fund_code}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code, "status_code": 404}
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
                    metadata={"fund_code": fund_code}
                )

        # 如果是 LOF，返回更明确的错误信息
        if is_lof:
            return DataSourceResult(
                success=False,
                error=f"{fund_code} 是 QDII/LOF 基金，akshare 东方财富接口返回数据为空",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )

        # 如果是 ETF，返回更明确的错误信息
        if is_etf:
            return DataSourceResult(
                success=False,
                error=f"{fund_code} 是 ETF 基金，当前数据源暂不支持",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )

        return DataSourceResult(
            success=False,
            error=f"获取基金数据失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code}
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
            import asyncio
            loop = asyncio.get_event_loop()
            import akshare as ak

            # 获取 ETF 最新数据
            df = await loop.run_in_executor(
                None,
                lambda: ak.fund_etf_fund_info_em(fund=fund_code)
            )

            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    error=f"ETF {fund_code} 无数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code}
                )

            # 获取最新一条数据
            latest = df.iloc[0]

            # 提取数据
            data = {
                "fund_code": fund_code,
                "name": f"ETF {fund_code}",  # ETF 接口不直接返回名称
                "net_value_date": str(latest.get("净值日期", "")),
                "unit_net_value": float(latest.get("单位净值", 0)) if pd.notna(latest.get("单位净值")) else None,
                "estimated_net_value": float(latest.get("单位净值", 0)) if pd.notna(latest.get("单位净值")) else None,
                "estimated_growth_rate": float(latest.get("日增长率", 0)) if pd.notna(latest.get("日增长率")) else None,
                "estimate_time": str(latest.get("净值日期", "")),
            }

            self._record_success()
            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )
        except Exception as e:
            return DataSourceResult(
                success=False,
                error=f"ETF 数据获取失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )

    async def _fetch_lof(self, fund_code: str) -> DataSourceResult:
        """
        获取 LOF/QDII/FOF 基金数据 - 使用东方财富开放式基金接口

        支持: LOF、QDII、FOF 等所有在天天基金网显示的开放式基金

        Args:
            fund_code: 基金代码

        Returns:
            DataSourceResult: 基金数据结果
        """
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            import akshare as ak

            # 获取基金最新净值数据
            df = await loop.run_in_executor(
                None,
                lambda: ak.fund_open_fund_info_em(
                    symbol=fund_code,
                    indicator="单位净值走势",
                    period="近一年"
                )
            )

            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    error=f"基金 {fund_code} 无净值数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code}
                )

            # 获取最新一条数据（最后一行是最新的，因为数据是按日期升序排列的）
            latest = df.iloc[-1]

            # 获取基金简称和类型
            fund_name = ""
            fund_type = ""
            try:
                daily_df = ak.fund_open_fund_daily_em()
                if "基金代码" in daily_df.columns:
                    name_row = daily_df[daily_df["基金代码"] == fund_code]
                    if not name_row.empty:
                        fund_name = str(name_row.iloc[0].get("基金简称", ""))
            except Exception:
                pass

            # 如果没获取到名称，使用基金代码作为名称
            if not fund_name:
                fund_name = f"基金 {fund_code}"

            # 获取基金详细信息（包含类型）
            try:
                info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
                if info_df is not None and not info_df.empty:
                    # 查找基金类型
                    type_row = info_df[info_df["item"] == "基金类型"]
                    if not type_row.empty:
                        fund_type = str(type_row.iloc[0]["value"]).strip()
                        # 简化类型名称
                        if "-" in fund_type:
                            fund_type = fund_type.split("-")[0]  # "QDII-商品" -> "QDII"
            except Exception:
                pass

            # 提取数据
            net_date = str(latest.get("净值日期", ""))
            unit_net = float(latest.get("单位净值", 0)) if pd.notna(latest.get("单位净值")) else None
            daily_change = float(latest.get("日增长率", 0)) if pd.notna(latest.get("日增长率")) else None

            data = {
                "fund_code": fund_code,
                "name": fund_name,
                "type": fund_type,
                "net_value_date": net_date,
                "unit_net_value": unit_net,
                "estimated_net_value": unit_net,  # 开放式基金暂无实时估值
                "estimated_growth_rate": daily_change,
                "estimate_time": net_date,
            }

            self._record_success()
            return DataSourceResult(
                success=True,
                data=data,
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )
        except Exception as e:
            return DataSourceResult(
                success=False,
                error=f"基金数据获取失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
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
                        metadata={"fund_code": fund_codes[i]}
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
        try:
            import akshare as ak

            # 获取基金详细信息
            info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if info_df is not None and not info_df.empty:
                # 查找基金类型
                type_row = info_df[info_df["item"] == "基金类型"]
                if not type_row.empty:
                    fund_type = str(type_row.iloc[0]["value"]).strip()
                    # 简化类型名称
                    if "-" in fund_type:
                        fund_type = fund_type.split("-")[0]  # "QDII-商品" -> "QDII"
                    return fund_type

            return ""
        except Exception:
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
                    details={"response_preview": response_text[:100]}
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
                "raw_data": data
            }

        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            raise DataParseError(
                message=f"基金数据解析错误: {str(e)}",
                source_type=self.source_type,
                details={"fund_code": fund_code}
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
            if hasattr(self, 'client') and self.client.is_closed is False:
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


# 导出类
__all__ = ["FundDataSource", "SinaFundDataSource", "FundHistorySource", "FundHistoryYFinanceSource"]


class FundHistorySource(DataSource):
    """基金历史数据源 - 使用 akshare 获取基金净值历史数据"""

    def __init__(self, timeout: float = 30.0):
        """
        初始化基金历史数据源

        Args:
            timeout: 请求超时时间
        """
        super().__init__(
            name="fund_history_akshare",
            source_type=DataSourceType.FUND,
            timeout=timeout
        )

    async def fetch(self, fund_code: str, period: str = "近一年") -> DataSourceResult:
        """
        获取基金历史净值数据

        Args:
            fund_code: 基金代码 (6位数字)
            period: 时间周期，可选值: "近一周", "近一月", "近三月", "近六月", "近一年", "近三年", "近五年", "成立以来"

        Returns:
            DataSourceResult: 包含历史净值数据的结果
        """
        if not self._validate_fund_code(fund_code):
            return DataSourceResult(
                success=False,
                error=f"无效的基金代码: {fund_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )

        try:
            # 在异步上下文中使用 akshare
            import akshare as ak

            # 天天基金净值
            fund_df = ak.fund_ggmz(symbol=fund_code)

            if fund_df is None or fund_df.empty:
                return DataSourceResult(
                    success=False,
                    error="未获取到基金历史数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code}
                )

            # 解析数据
            history_data = []
            for _, row in fund_df.iterrows():
                date = row.get("日期", "")
                net_value = row.get("单位净值", None)
                accumulated_net = row.get("累计净值", None)

                if net_value is not None:
                    try:
                        history_data.append({
                            "date": str(date),
                            "net_value": float(net_value),
                            "accumulated_net": float(accumulated_net) if accumulated_net else None
                        })
                    except (ValueError, TypeError):
                        continue

            # 按日期排序
            history_data.sort(key=lambda x: x["date"])

            self._record_success()
            return DataSourceResult(
                success=True,
                data={
                    "fund_code": fund_code,
                    "history": history_data,
                    "count": len(history_data)
                },
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code, "period": period}
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装，请运行: pip install akshare",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )
        except Exception as e:
            self._request_count += 1
            self._error_count += 1
            return DataSourceResult(
                success=False,
                error=f"获取基金历史数据失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )

    async def fetch_async(self, fund_code: str, period: str = "近一年") -> DataSourceResult:
        """
        异步获取基金历史净值数据（推荐使用）

        Args:
            fund_code: 基金代码 (6位数字)
            period: 时间周期

        Returns:
            DataSourceResult: 包含历史净值数据的结果
        """
        # akshare 本身是同步的，我们在异步任务中运行
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.fetch(fund_code, period))

    def _validate_fund_code(self, fund_code: str) -> bool:
        """验证基金代码格式"""
        return bool(re.match(r"^\d{6}$", str(fund_code)))


class FundHistoryYFinanceSource(DataSource):
    """基金历史数据源 - 使用 yfinance 获取历史数据（备用方案）"""

    def __init__(self, timeout: float = 30.0):
        super().__init__(
            name="fund_history_yfinance",
            source_type=DataSourceType.FUND,
            timeout=timeout
        )

    async def fetch(self, fund_code: str, period: str = "1y") -> DataSourceResult:
        """
        使用 yfinance 获取基金历史数据

        Args:
            fund_code: 基金代码 (对于中国基金，需要添加 .SS 后缀)
            period: 时间周期: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

        Returns:
            DataSourceResult: 包含历史数据的结果
        """
        try:
            import yfinance as yf

            # 构建 ticker 符号
            ticker_symbol = f"{fund_code}.SS" if fund_code.isdigit() else fund_code

            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=period)

            if hist is None or hist.empty:
                return DataSourceResult(
                    success=False,
                    error="未获取到基金历史数据",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code}
                )

            history_data = []
            for index, row in hist.iterrows():
                history_data.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "open": row.get("Open"),
                    "high": row.get("High"),
                    "low": row.get("Low"),
                    "close": row.get("Close"),
                    "volume": row.get("Volume"),
                    "dividends": row.get("Dividends"),
                    "stock_splits": row.get("Stock Splits")
                })

            self._record_success()
            return DataSourceResult(
                success=True,
                data={
                    "fund_code": fund_code,
                    "ticker": ticker_symbol,
                    "history": history_data,
                    "count": len(history_data)
                },
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code, "period": period}
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="yfinance 库未安装，请运行: pip install yfinance",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )
        except Exception as e:
            self._request_count += 1
            self._error_count += 1
            return DataSourceResult(
                success=False,
                error=f"获取历史数据失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"fund_code": fund_code}
            )

    async def fetch_async(self, fund_code: str, period: str = "1y") -> DataSourceResult:
        """异步获取历史数据"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.fetch(fund_code, period))


class SinaFundDataSource(DataSource):
    """新浪基金数据源 - 备用基金数据源"""

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_delay: float = 1.0
    ):
        """
        初始化新浪基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(
            name="fund_sina",
            source_type=DataSourceType.FUND,
            timeout=timeout
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/javascript, */*;q=0.8",
            }
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
                metadata={"fund_code": fund_code}
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
                        metadata={"fund_code": fund_code}
                    )

                # 新浪返回格式: var LF_xx={...}
                json_match = re.search(r'\{.+\}', text)
                if not json_match:
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 数据解析失败",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code}
                    )

                data = json.loads(json_match.group())

                # 提取数据
                net_value = self._safe_float(data.get("NAV", data.get("unit_nav")))
                estimate_value = self._safe_float(data.get("ACC_NAV", data.get("acc_nav"))) or net_value
                change_percent = self._safe_float(data.get("NAV_CHG_PCT", data.get("change_percent")))

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
                    metadata={"fund_code": fund_code}
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
            metadata={"fund_code": fund_code}
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
                        metadata={"fund_code": fund_codes[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results


class EastMoneyFundDataSource(DataSource):
    """东方财富基金数据源 - 备用基金数据源"""

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_delay: float = 1.0
    ):
        """
        初始化东方财富基金数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(
            name="fund_eastmoney",
            source_type=DataSourceType.FUND,
            timeout=timeout
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
            }
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
                metadata={"fund_code": fund_code}
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
                        metadata={"fund_code": fund_code}
                    )

                # 解析 JS 格式数据
                # 格式: var API_FUND_xxxx={...}
                json_match = re.search(r'=\{[\s\S]*\};?$', text)
                if not json_match:
                    # 尝试另一种格式
                    json_match = re.search(r'\{.+\}', text)

                if not json_match:
                    return DataSourceResult(
                        success=False,
                        error=f"基金 {fund_code} 数据解析失败",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"fund_code": fund_code}
                    )

                data_str = json_match.group().rstrip(';')
                data = json.loads(data_str)

                # 提取数据
                net_value = self._safe_float(data.get("NET", data.get("unit_nav")))
                estimate_value = self._safe_float(data.get("ACC_NET", data.get("acc_nav"))) or net_value
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
                    metadata={"fund_code": fund_code}
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
            metadata={"fund_code": fund_code}
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
                        metadata={"fund_code": fund_codes[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results
