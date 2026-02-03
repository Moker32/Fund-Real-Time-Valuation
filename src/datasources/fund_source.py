"""
基金数据源模块
实现从天天基金/新浪接口获取基金实时估值数据
"""

import re
import json
import time
import asyncio
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime
from .base import (
    DataSource,
    DataSourceType,
    DataSourceResult,
    DataSourceError,
    NetworkError,
    DataParseError
)


class FundDataSource(DataSource):
    """基金数据源 - 从天天基金接口获取数据"""

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化基金数据源

        Args:
            timeout: 请求超时时间
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

    async def fetch(self, fund_code: str) -> DataSourceResult:
        """
        获取单个基金数据

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
                url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js?rt={int(time.time() * 1000)}"
                response = await self.client.get(url)
                response.raise_for_status()

                # 解析返回的 JS 数据
                data = self._parse_response(response.text, fund_code)

                if data:
                    self._record_success()
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

            except httpx.RequestError as e:
                await self._handle_retry_delay(attempt)

            except json.JSONDecodeError as e:
                self._request_count += 1
                self._error_count += 1
                return DataSourceResult(
                    success=False,
                    error=f"数据解析失败: {str(e)}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"fund_code": fund_code, "raw_response": response.text[:200]}
                )

        return DataSourceResult(
            success=False,
            error=f"获取基金数据失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code}
        )

    async def fetch_batch(self, fund_codes: List[str]) -> List[DataSourceResult]:
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

    def _parse_response(self, response_text: str, fund_code: str) -> Optional[Dict[str, Any]]:
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

    def _safe_float(self, value: Any) -> Optional[float]:
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
        """析构时确保关闭客户端"""
        try:
            if hasattr(self, 'client') and self.client.is_closed is False:
                # Note: 异步客户端需要在异步上下文中关闭
                pass
        except Exception:
            pass


class SinaFundDataSource(DataSource):
    """新浪基金数据源 - 备用数据源"""

    def __init__(self, timeout: float = 10.0, max_retries: int = 3, retry_delay: float = 1.0):
        """
        初始化新浪基金数据源

        Args:
            timeout: 请求超时时间
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
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )

    async def fetch(self, fund_code: str) -> DataSourceResult:
        """获取基金数据 - 新浪接口"""
        for attempt in range(self.max_retries):
            try:
                # 新浪基金接口
                url = f"https://finance.sina.com.cn/fund/qqjl/{fund_code}.shtml"
                response = await self.client.get(url)
                response.raise_for_status()

                # 从 HTML 中提取数据
                data = self._parse_html(response.text, fund_code)

                self._record_success()
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

            except httpx.RequestError as e:
                await self._handle_retry_delay(attempt)

            except Exception as e:
                return self._handle_error(e, self.name)

        return DataSourceResult(
            success=False,
            error=f"获取基金数据失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"fund_code": fund_code}
        )

    async def _handle_retry_delay(self, attempt: int):
        """处理重试延迟"""
        if attempt < self.max_retries - 1:
            await asyncio.sleep(self.retry_delay * (attempt + 1))

    async def fetch_batch(self, fund_codes: List[str]) -> List[DataSourceResult]:
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

    def _parse_html(self, html: str, fund_code: str) -> Optional[Dict[str, Any]]:
        """解析新浪基金页面 HTML"""
        # 简化实现 - 实际需要使用 BeautifulSoup 解析
        # 这里预留解析逻辑
        return {
            "fund_code": fund_code,
            "note": "新浪接口需要完整解析实现"
        }

    async def close(self):
        """关闭异步客户端"""
        await self.client.aclose()


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
