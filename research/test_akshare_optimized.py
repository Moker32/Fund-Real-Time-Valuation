"""
AKShare 优化配置测试脚本

测试内容：
1. stock_zh_index_spot_em - A股指数实时行情
2. stock_hk_spot_em - 港股实时行情
3. stock_us_spot_em - 美股实时行情

记录成功率和响应时间
"""

import asyncio
import logging
import sys
import time
from dataclasses import dataclass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, ".")

from src.datasources.akshare_config import (
    DEFAULT_RATE_LIMIT,
    MAX_RETRIES,
    call_akshare_with_retry,
)
from src.datasources.index_source import AKShareIndexSource


@dataclass
class TestResult:
    """测试结果数据类"""

    name: str
    success: bool
    duration: float
    error: str | None = None
    data: dict | None = None


async def test_akshare_config_module() -> list[TestResult]:
    """测试 akshare_config 模块的基础功能"""
    results = []

    # 测试1: 限流器
    logger.info("=" * 60)
    logger.info("测试1: 限流器功能")
    logger.info("=" * 60)

    from src.datasources.akshare_config import RateLimiter

    start_time = time.time()
    limiter = RateLimiter(calls_per_second=2)

    for i in range(3):
        await limiter.acquire()
        logger.info(f"  请求 {i + 1} 执行时间: {time.time() - start_time:.2f}s")

    duration = time.time() - start_time
    success = duration >= 1.0  # 2个请求间隔至少0.5s，3个请求至少1s

    results.append(
        TestResult(
            name="限流器 (2 req/s)",
            success=success,
            duration=duration,
            error=None if success else f"限流间隔不足: {duration:.2f}s",
        )
    )

    # 测试2: 重试机制
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 重试机制")
    logger.info("=" * 60)

    call_count = 0

    def failing_function() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception(f"模拟失败 #{call_count}")
        return f"成功 (尝试 {call_count})"

    start_time = time.time()
    try:
        result = await call_akshare_with_retry(
            failing_function,
            max_retries=3,
            rate_limit_cps=10,  # 高速限流以便快速测试
        )
        duration = time.time() - start_time
        success = True
        error = None
        logger.info(f"  重试成功: {result}")
    except Exception as e:
        duration = time.time() - start_time
        success = False
        error = str(e)
        logger.error(f"  重试失败: {e}")

    results.append(
        TestResult(
            name="重试机制 (3次)",
            success=success,
            duration=duration,
            error=error,
        )
    )

    return results


async def test_stock_zh_index_spot_em() -> TestResult:
    """测试 A股指数实时行情接口"""
    logger.info("\n" + "=" * 60)
    logger.info("测试: stock_zh_index_spot_em (A股指数实时行情)")
    logger.info("=" * 60)

    try:
        import akshare as ak

        start_time = time.time()

        # 使用优化配置调用
        df = await call_akshare_with_retry(
            ak.stock_zh_index_spot_em,
            max_retries=MAX_RETRIES,
            rate_limit_cps=DEFAULT_RATE_LIMIT,
        )

        duration = time.time() - start_time

        if df is not None and not df.empty:
            logger.info("  ✓ 成功获取数据")
            logger.info(f"  - 数据条数: {len(df)}")
            logger.info(f"  - 响应时间: {duration:.2f}s")
            logger.info(f"  - 列名: {list(df.columns)}")
            logger.info("  - 前3条数据:")
            for idx, row in df.head(3).iterrows():
                logger.info(f"    {row.get('名称', 'N/A')}: {row.get('最新价', 'N/A')}")

            return TestResult(
                name="stock_zh_index_spot_em",
                success=True,
                duration=duration,
                data={
                    "count": len(df),
                    "columns": list(df.columns),
                    "sample": df.head(3).to_dict("records"),
                },
            )
        else:
            return TestResult(
                name="stock_zh_index_spot_em",
                success=False,
                duration=duration,
                error="返回数据为空",
            )

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"  ✗ 失败: {e}")
        return TestResult(
            name="stock_zh_index_spot_em",
            success=False,
            duration=duration,
            error=str(e),
        )


async def test_stock_hk_spot_em() -> TestResult:
    """测试港股实时行情接口"""
    logger.info("\n" + "=" * 60)
    logger.info("测试: stock_hk_spot_em (港股实时行情)")
    logger.info("=" * 60)

    try:
        import akshare as ak

        start_time = time.time()

        df = await call_akshare_with_retry(
            ak.stock_hk_spot_em,
            max_retries=MAX_RETRIES,
            rate_limit_cps=DEFAULT_RATE_LIMIT,
        )

        duration = time.time() - start_time

        if df is not None and not df.empty:
            logger.info("  ✓ 成功获取数据")
            logger.info(f"  - 数据条数: {len(df)}")
            logger.info(f"  - 响应时间: {duration:.2f}s")
            logger.info(f"  - 列名: {list(df.columns)}")
            logger.info("  - 前3条数据:")
            for idx, row in df.head(3).iterrows():
                logger.info(f"    {row.get('名称', 'N/A')}: {row.get('最新价', 'N/A')}")

            return TestResult(
                name="stock_hk_spot_em",
                success=True,
                duration=duration,
                data={
                    "count": len(df),
                    "columns": list(df.columns),
                    "sample": df.head(3).to_dict("records"),
                },
            )
        else:
            return TestResult(
                name="stock_hk_spot_em",
                success=False,
                duration=duration,
                error="返回数据为空",
            )

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"  ✗ 失败: {e}")
        return TestResult(
            name="stock_hk_spot_em",
            success=False,
            duration=duration,
            error=str(e),
        )


async def test_stock_us_spot_em() -> TestResult:
    """测试美股实时行情接口"""
    logger.info("\n" + "=" * 60)
    logger.info("测试: stock_us_spot_em (美股实时行情)")
    logger.info("=" * 60)

    try:
        import akshare as ak

        start_time = time.time()

        df = await call_akshare_with_retry(
            ak.stock_us_spot_em,
            max_retries=MAX_RETRIES,
            rate_limit_cps=DEFAULT_RATE_LIMIT,
        )

        duration = time.time() - start_time

        if df is not None and not df.empty:
            logger.info("  ✓ 成功获取数据")
            logger.info(f"  - 数据条数: {len(df)}")
            logger.info(f"  - 响应时间: {duration:.2f}s")
            logger.info(f"  - 列名: {list(df.columns)}")
            logger.info("  - 前3条数据:")
            for idx, row in df.head(3).iterrows():
                logger.info(f"    {row.get('名称', 'N/A')}: {row.get('最新价', 'N/A')}")

            return TestResult(
                name="stock_us_spot_em",
                success=True,
                duration=duration,
                data={
                    "count": len(df),
                    "columns": list(df.columns),
                    "sample": df.head(3).to_dict("records"),
                },
            )
        else:
            return TestResult(
                name="stock_us_spot_em",
                success=False,
                duration=duration,
                error="返回数据为空",
            )

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"  ✗ 失败: {e}")
        return TestResult(
            name="stock_us_spot_em",
            success=False,
            duration=duration,
            error=str(e),
        )


async def test_akshare_index_source() -> list[TestResult]:
    """测试 AKShareIndexSource 类"""
    logger.info("\n" + "=" * 60)
    logger.info("测试: AKShareIndexSource 类")
    logger.info("=" * 60)

    results = []
    source = AKShareIndexSource()

    # 测试1: 获取上证指数实时数据
    logger.info("\n  测试1: 获取上证指数实时数据")
    start_time = time.time()
    result = await source.fetch("shanghai")
    duration = time.time() - start_time

    if result.success:
        logger.info("    ✓ 成功")
        logger.info(f"    - 响应时间: {duration:.2f}s")
        logger.info(f"    - 数据: {result.data}")
    else:
        logger.error(f"    ✗ 失败: {result.error}")

    results.append(
        TestResult(
            name="AKShareIndexSource.fetch(shanghai)",
            success=result.success,
            duration=duration,
            error=result.error,
            data=result.data if result.success else None,
        )
    )

    # 测试2: 获取深证成指实时数据
    logger.info("\n  测试2: 获取深证成指实时数据")
    start_time = time.time()
    result = await source.fetch("shenzhen")
    duration = time.time() - start_time

    if result.success:
        logger.info("    ✓ 成功")
        logger.info(f"    - 响应时间: {duration:.2f}s")
    else:
        logger.error(f"    ✗ 失败: {result.error}")

    results.append(
        TestResult(
            name="AKShareIndexSource.fetch(shenzhen)",
            success=result.success,
            duration=duration,
            error=result.error,
        )
    )

    # 测试3: 获取港股实时数据
    logger.info("\n  测试3: 获取港股实时数据")
    start_time = time.time()
    result = await source.fetch_hk_spot()
    duration = time.time() - start_time

    if result.success:
        logger.info("    ✓ 成功")
        logger.info(f"    - 响应时间: {duration:.2f}s")
        logger.info(f"    - 数据条数: {result.data.get('count', 0)}")
    else:
        logger.error(f"    ✗ 失败: {result.error}")

    results.append(
        TestResult(
            name="AKShareIndexSource.fetch_hk_spot()",
            success=result.success,
            duration=duration,
            error=result.error,
        )
    )

    # 测试4: 获取美股实时数据
    logger.info("\n  测试4: 获取美股实时数据")
    start_time = time.time()
    result = await source.fetch_us_spot()
    duration = time.time() - start_time

    if result.success:
        logger.info("    ✓ 成功")
        logger.info(f"    - 响应时间: {duration:.2f}s")
        logger.info(f"    - 数据条数: {result.data.get('count', 0)}")
    else:
        logger.error(f"    ✗ 失败: {result.error}")

    results.append(
        TestResult(
            name="AKShareIndexSource.fetch_us_spot()",
            success=result.success,
            duration=duration,
            error=result.error,
        )
    )

    return results


def print_summary(results: list[TestResult]) -> None:
    """打印测试摘要"""
    logger.info("\n" + "=" * 60)
    logger.info("测试摘要")
    logger.info("=" * 60)

    total = len(results)
    success = sum(1 for r in results if r.success)
    failed = total - success
    total_duration = sum(r.duration for r in results)
    avg_duration = total_duration / total if total > 0 else 0

    logger.info(f"总测试数: {total}")
    logger.info(f"成功: {success}")
    logger.info(f"失败: {failed}")
    logger.info(f"成功率: {success / total * 100:.1f}%")
    logger.info(f"总耗时: {total_duration:.2f}s")
    logger.info(f"平均耗时: {avg_duration:.2f}s")

    logger.info("\n详细结果:")
    for r in results:
        status = "✓" if r.success else "✗"
        logger.info(f"  {status} {r.name}: {r.duration:.2f}s")
        if r.error:
            logger.info(f"    错误: {r.error}")


async def main() -> None:
    """主函数"""
    logger.info("=" * 60)
    logger.info("AKShare 优化配置测试")
    logger.info("=" * 60)

    all_results: list[TestResult] = []

    # 测试配置模块
    config_results = await test_akshare_config_module()
    all_results.extend(config_results)

    # 测试实时接口
    all_results.append(await test_stock_zh_index_spot_em())
    all_results.append(await test_stock_hk_spot_em())
    all_results.append(await test_stock_us_spot_em())

    # 测试 AKShareIndexSource 类
    source_results = await test_akshare_index_source()
    all_results.extend(source_results)

    # 打印摘要
    print_summary(all_results)


if __name__ == "__main__":
    asyncio.run(main())
