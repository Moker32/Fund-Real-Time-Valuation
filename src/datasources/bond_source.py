"""
债券数据源模块
实现从新浪财经和 AKShare 获取债券/可转债数据
"""

import asyncio
import re
import time
from typing import Any

import httpx

from .base import (
    DataSource,
    DataSourceResult,
    DataSourceType,
)


class SinaBondDataSource(DataSource):
    """新浪财经债券数据源"""

    def __init__(self, timeout: float = 10.0, max_retries: int = 3, retry_delay: float = 1.0):
        """
        初始化新浪债券数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_delay: 重试间隔(秒)
        """
        super().__init__(
            name="sina_bond",
            source_type=DataSourceType.BOND,
            timeout=timeout
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            }
        )

    async def fetch(self, bond_code: str) -> DataSourceResult:
        """
        获取债券/可转债实时行情

        Args:
            bond_code: 债券代码 (如: 113052, 110053)

        Returns:
            DataSourceResult: 包含债券数据的结果
        """
        if not self._validate_bond_code(bond_code):
            return DataSourceResult(
                success=False,
                error=f"无效的债券代码: {bond_code}",
                timestamp=time.time(),
                source=self.name,
                metadata={"bond_code": bond_code}
            )

        for attempt in range(self.max_retries):
            try:
                # 判断市场：深圳债券 sz，上海债券 sh
                market = "sh" if bond_code.startswith("1") else "sz"
                url = f"https://hq.sinajs.cn/list={market}{bond_code}"

                response = await self.client.get(url)
                response.raise_for_status()

                data = self._parse_response(response.text, bond_code)

                if data:
                    self._record_success()
                    return DataSourceResult(
                        success=True,
                        data=data,
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"bond_code": bond_code, "market": market}
                    )

                return DataSourceResult(
                    success=False,
                    error="解析债券数据失败",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"bond_code": bond_code}
                )

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return DataSourceResult(
                        success=False,
                        error=f"债券不存在: {bond_code}",
                        timestamp=time.time(),
                        source=self.name,
                        metadata={"bond_code": bond_code, "status_code": 404}
                    )
                await self._handle_retry_delay(attempt)

            except httpx.RequestError:
                await self._handle_retry_delay(attempt)

            except Exception as e:
                return self._handle_error(e, self.name)

        return DataSourceResult(
            success=False,
            error=f"获取债券数据失败，已重试 {self.max_retries} 次",
            timestamp=time.time(),
            source=self.name,
            metadata={"bond_code": bond_code}
        )

    def _validate_bond_code(self, bond_code: str) -> bool:
        """
        验证债券代码格式

        Args:
            bond_code: 债券代码

        Returns:
            bool: 是否有效
        """
        return bool(re.match(r"^\d{6}$", str(bond_code)))

    def _parse_response(self, response_text: str, bond_code: str) -> dict[str, Any] | None:
        """
        解析新浪债券响应

        Args:
            response_text: 原始响应文本
            bond_code: 债券代码 (未使用，用于参数兼容)

        Returns:
            Optional[Dict]: 解析后的数据字典
        """
        try:
            # 新浪返回格式: var hq_str_sh113052="可转债名称,..."
            match = re.search(r'hq_str_(sh|sz)(\d+?)="([^"]+)";', response_text)
            if not match:
                return None

            market = match.group(1)
            code = match.group(2)
            values = match.group(3).split(',')

            if len(values) < 6:
                return None

            # 新浪债券数据格式：
            # 0: 名称, 1: 开盘价, 2: 昨收价, 3: 当前价, 4: 最高价, 5: 最低价,
            # 6: 买入价, 7: 卖出价, 8: 成交量(手), 9: 成交额(万)
            name = values[0]
            pre_close = float(values[2])
            price = float(values[3])
            high = float(values[4]) if len(values) > 4 else 0
            low = float(values[5]) if len(values) > 5 else 0
            volume = int(values[8]) if len(values) > 8 else 0
            amount = float(values[9]) if len(values) > 9 else 0

            # 计算涨跌
            change = price - pre_close
            change_pct = (change / pre_close * 100) if pre_close > 0 else 0

            return {
                "code": code,
                "market": market,
                "name": name,
                "price": price,
                "pre_close": pre_close,
                "high": high,
                "low": low,
                "change": round(change, 4),
                "change_pct": round(change_pct, 4),
                "volume": volume,
                "amount": amount,
                "raw_data": values
            }

        except (ValueError, IndexError):
            return None

    async def _handle_retry_delay(self, attempt: int):
        """处理重试延迟"""
        if attempt < self.max_retries - 1:
            await asyncio.sleep(self.retry_delay * (attempt + 1))

    async def fetch_batch(self, bond_codes: list[str]) -> list[DataSourceResult]:
        """
        批量获取债券数据

        Args:
            bond_codes: 债券代码列表

        Returns:
            List[DataSourceResult]: 每个债券的结果列表
        """
        async def fetch_one(code: str) -> DataSourceResult:
            return await self.fetch(code)

        tasks = [fetch_one(code) for code in bond_codes]
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
                        metadata={"bond_code": bond_codes[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def close(self):
        """关闭异步客户端"""
        await self.client.aclose()

    def __del__(self):
        """析构时确保关闭客户端"""
        try:
            if hasattr(self, 'client') and self.client.is_closed is False:
                pass
        except Exception:
            pass

    async def health_check(self) -> bool:
        """
        健康检查 - 新浪债券接口

        Returns:
            bool: 健康状态
        """
        try:
            # 使用示例债券代码进行健康检查
            bond_code = "113052"  # 兴业转债
            market = "sh" if bond_code.startswith("1") else "sz"
            url = f"https://hq.sinajs.cn/list={market}{bond_code}"
            response = await self.client.get(url, timeout=self.timeout)
            response.raise_for_status()

            # 验证返回数据格式
            if response.text and "hq_str_" in response.text:
                return True
            return False
        except Exception:
            return False


class AKShareBondSource(DataSource):
    """AKShare 可转债数据源"""

    def __init__(self, timeout: float = 30.0):
        """
        初始化 AKShare 债券数据源

        Args:
            timeout: 请求超时时间(秒)
        """
        super().__init__(
            name="akshare_bond",
            source_type=DataSourceType.BOND,
            timeout=timeout
        )

    async def fetch(self, bond_type: str = "cbond") -> DataSourceResult:
        """
        获取可转债/债券数据

        Args:
            bond_type: 债券类型
                - "cbond": 可转债 (默认)
                - "bond_china": 中国债券

        Returns:
            DataSourceResult: 包含债券数据的结果
        """
        try:
            # akshare 是同步库，在异步任务中运行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self._fetch_sync(bond_type)
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装，请运行: pip install akshare",
                timestamp=time.time(),
                source=self.name
            )
        except Exception as e:
            return self._handle_error(e, self.name)

    def _fetch_sync(self, bond_type: str) -> DataSourceResult:
        """
        同步获取债券数据

        Args:
            bond_type: 债券类型

        Returns:
            DataSourceResult: 包含债券数据的结果
        """
        try:
            import akshare as ak

            bonds = []

            if bond_type == "cbond":
                # 可转债实时数据
                df = ak.bond_zh_hs_cov_spot()
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        bonds.append({
                            "code": str(row.get("代码", "")),
                            "name": str(row.get("名称", "")),
                            "price": self._safe_float(row.get("最新价")),
                            "change": self._safe_float(row.get("涨跌额")),
                            "change_pct": self._safe_float(row.get("涨跌幅")),
                            "volume": self._safe_int(row.get("成交量")),
                            "turnover": self._safe_float(row.get("成交额")),
                            "bid": self._safe_float(row.get("买一")),
                            "ask": self._safe_float(row.get("卖一")),
                        })
            elif bond_type == "bond_china":
                # 中国债券市场数据
                df = ak.bond_china_yield()
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        bonds.append({
                            "name": str(row.get("债券名称", "")),
                            "yield": self._safe_float(row.get("收益率")),
                            "change_pct": self._safe_float(row.get("涨跌幅")),
                            "volume": self._safe_int(row.get("成交量")),
                        })
            else:
                return DataSourceResult(
                    success=False,
                    error=f"不支持的债券类型: {bond_type}",
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"bond_type": bond_type}
                )

            if not bonds:
                return DataSourceResult(
                    success=False,
                    error=f"未获取到 {bond_type} 数据",
                    timestamp=time.time(),
                    source=self.name
                )

            self._record_success()
            return DataSourceResult(
                success=True,
                data={
                    "bond_type": bond_type,
                    "bonds": bonds,
                    "count": len(bonds)
                },
                timestamp=time.time(),
                source=self.name,
                metadata={"bond_type": bond_type}
            )

        except ImportError:
            return DataSourceResult(
                success=False,
                error="akshare 库未安装",
                timestamp=time.time(),
                source=self.name
            )
        except Exception as e:
            self._request_count += 1
            self._error_count += 1
            return DataSourceResult(
                success=False,
                error=f"获取债券数据失败: {str(e)}",
                timestamp=time.time(),
                source=self.name,
                metadata={"bond_type": bond_type}
            )

    def _safe_float(self, value: Any) -> float | None:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value: Any) -> int | None:
        """安全转换为整数"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    async def fetch_batch(self, bond_types: list[str]) -> list[DataSourceResult]:
        """
        批量获取不同类型债券数据

        Args:
            bond_types: 债券类型列表

        Returns:
            List[DataSourceResult]: 每个类型的结果列表
        """
        async def fetch_one(btype: str) -> DataSourceResult:
            return await self.fetch(btype)

        tasks = [fetch_one(btype) for btype in bond_types]
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
                        metadata={"bond_type": bond_types[i]}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results


class EastMoneyBondSource(DataSource):
    """东方财富债券数据源 - 备用数据源"""

    def __init__(self, timeout: float = 10.0, max_retries: int = 3):
        """
        初始化东方财富债券数据源

        Args:
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
        """
        super().__init__(
            name="eastmoney_bond",
            source_type=DataSourceType.BOND,
            timeout=timeout
        )
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://quote.eastmoney.com/"
            }
        )

    async def fetch(self, bond_code: str) -> DataSourceResult:
        """
        获取债券数据 - 东方财富接口

        Args:
            bond_code: 债券代码

        Returns:
            DataSourceResult: 包含债券数据的结果
        """
        try:
            # 东方财富债券行情 API
            url = "https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "fltt": "2",
                "fields": "f2,f3,f4,f5,f6,f8,f12,f13,f14",
                "secid": f"1.{bond_code}" if bond_code.startswith("1") else f"0.{bond_code}"
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("data"):
                stock_info = data["data"]
                return DataSourceResult(
                    success=True,
                    data={
                        "code": bond_code,
                        "name": stock_info.get("f14", ""),
                        "price": stock_info.get("f2"),
                        "change_pct": stock_info.get("f3"),
                        "change": stock_info.get("f4"),
                        "volume": stock_info.get("f6"),
                        "amount": stock_info.get("f8"),
                    },
                    timestamp=time.time(),
                    source=self.name,
                    metadata={"bond_code": bond_code}
                )

            return DataSourceResult(
                success=False,
                error="未获取到债券数据",
                timestamp=time.time(),
                source=self.name,
                metadata={"bond_code": bond_code}
            )

        except Exception as e:
            return self._handle_error(e, self.name)

    async def fetch_batch(self, bond_codes: list[str]) -> list[DataSourceResult]:
        """批量获取债券数据"""
        async def fetch_one(code: str) -> DataSourceResult:
            return await self.fetch(code)

        tasks = [fetch_one(code) for code in bond_codes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r if isinstance(r, DataSourceResult) else DataSourceResult(
            success=False, error=str(r), timestamp=time.time(), source=self.name
        ) for r in results]

    async def close(self):
        """关闭异步客户端"""
        await self.client.aclose()


# 导出类
__all__ = ["SinaBondDataSource", "AKShareBondSource", "EastMoneyBondSource"]
