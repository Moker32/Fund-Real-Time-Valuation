"""
数据源性能评估测试
对比新旧数据源的响应时间和稳定性
"""

import asyncio
import time
from dataclasses import dataclass

import pytest

from src.datasources import (
    BaostockStockSource,
    Fund123DataSource,
    SinaStockDataSource,
    TushareFundSource,
)
from src.datasources.crypto_source import BinanceCryptoSource, CoinGeckoCryptoSource


@dataclass
class BenchmarkResult:
    source_name: str
    total_requests: int
    success_count: int
    response_times: list[float]

    @property
    def success_rate(self) -> float:
        return self.success_count / self.total_requests * 100 if self.total_requests > 0 else 0

    @property
    def avg_response_time(self) -> float:
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0

    @property
    def p95_response_time(self) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx]


async def benchmark_source(source, test_symbols, iterations=2):
    response_times = []
    success_count = 0

    for _ in range(iterations):
        for symbol in test_symbols:
            start_time = time.time()
            try:
                result = await source.fetch(symbol)
                elapsed = time.time() - start_time
                response_times.append(elapsed)
                if result.success:
                    success_count += 1
            except Exception:
                elapsed = time.time() - start_time
                response_times.append(elapsed)
            await asyncio.sleep(0.5)

    return BenchmarkResult(
        source_name=source.name,
        total_requests=len(test_symbols) * iterations,
        success_count=success_count,
        response_times=response_times
    )


class TestDataSourcePerformance:
    @pytest.mark.asyncio
    async def test_crypto_sources(self):
        print("\n" + "="*60)
        print("加密货币数据源性能对比")
        print("="*60)

        coingecko = CoinGeckoCryptoSource()
        cg_result = await benchmark_source(coingecko, ["bitcoin", "ethereum"], 2)

        binance = BinanceCryptoSource()
        bn_result = await benchmark_source(binance, ["BTCUSDT", "ETHUSDT"], 2)

        print("\nCoinGecko (新备份源):")
        print(f"  成功率: {cg_result.success_rate:.0f}%")
        print(f"  平均响应: {cg_result.avg_response_time:.2f}s")
        print(f"  P95响应: {cg_result.p95_response_time:.2f}s")

        print("\nBinance (现有主源):")
        print(f"  成功率: {bn_result.success_rate:.0f}%")
        print(f"  平均响应: {bn_result.avg_response_time:.2f}s")
        print(f"  P95响应: {bn_result.p95_response_time:.2f}s")

        if cg_result.avg_response_time < bn_result.avg_response_time:
            print(f"\n✓ CoinGecko 更快 ({cg_result.avg_response_time:.2f}s)")
        else:
            print(f"\n✓ Binance 更快 ({bn_result.avg_response_time:.2f}s)")

        assert cg_result.success_rate >= 50
        assert bn_result.success_rate >= 50

    @pytest.mark.asyncio
    async def test_stock_sources(self):
        print("\n" + "="*60)
        print("股票数据源性能对比")
        print("="*60)

        baostock = BaostockStockSource()
        bs_result = await benchmark_source(baostock, ["sh.600000"], 2)

        sina = SinaStockDataSource()
        sina_result = await benchmark_source(sina, ["sh600000"], 2)

        print("\nBaostock (新数据源):")
        print(f"  成功率: {bs_result.success_rate:.0f}%")
        print(f"  平均响应: {bs_result.avg_response_time:.2f}s")

        print("\nSina (现有数据源):")
        print(f"  成功率: {sina_result.success_rate:.0f}%")
        print(f"  平均响应: {sina_result.avg_response_time:.2f}s")

        if bs_result.avg_response_time < sina_result.avg_response_time:
            print("\n✓ Baostock 更快")
        else:
            print("\n✓ Sina 更快")

    @pytest.mark.asyncio
    async def test_fund_sources(self):
        print("\n" + "="*60)
        print("基金数据源性能对比")
        print("="*60)

        fund123 = Fund123DataSource()
        f123_result = await benchmark_source(fund123, ["161039"], 2)

        print("\nFund123 (现有主源):")
        print(f"  成功率: {f123_result.success_rate:.0f}%")
        print(f"  平均响应: {f123_result.avg_response_time:.2f}s")

        tushare = TushareFundSource()
        ts_result = await benchmark_source(tushare, ["161039"], 2)

        print("\nTushare (新数据源 - 无Token):")
        print(f"  成功率: {ts_result.success_rate:.0f}%")
        if ts_result.success_rate == 0:
            print("  说明: 需要配置 TUSHARE_TOKEN 环境变量")

        assert f123_result.success_rate >= 50
