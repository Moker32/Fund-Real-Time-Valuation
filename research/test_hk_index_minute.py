#!/usr/bin/env python3
"""
港股指数分钟级数据测试脚本

测试数据源:
1. yfinance - 获取港股指数分钟级数据 (^HSI, HSTECH.HK)
2. 腾讯财经 - 港股指数分钟线接口 (对比测试)
"""

import asyncio
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, '/Users/huangxiang/work/Fund-Real-Time-Valuation')

from src.datasources.index_source import HybridIndexSource


async def test_yahoo_hk_intraday():
    """测试yfinance港股指数分钟数据"""
    print("=" * 70)
    print(" yfinance 港股指数分钟数据测试")
    print("=" * 70)
    
    source = HybridIndexSource()
    
    # 测试恒生指数
    print("\n[1] 恒生指数 (^HSI) 分钟数据:")
    try:
        result = await source._fetch_yahoo_intraday("hang_seng")
        if result.success:
            data = result.data
            print(f"  ✅ 成功获取数据")
            print(f"  数据点数: {len(data.get('data', []))}")
            print(f"  开盘价: {data.get('open')}")
            print(f"  最高价: {data.get('high')}")
            print(f"  最低价: {data.get('low')}")
            print(f"  收盘价: {data.get('close')}")
            print(f"  最新5个时间点:")
            for point in data.get('data', [])[-5:]:
                print(f"    {point['time']}: {point['price']} ({point['change']:+.2f}%)")
        else:
            print(f"  ❌ 失败: {result.error}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")
    
    # 测试恒生科技指数
    print("\n[2] 恒生科技指数 (HSTECH.HK) 分钟数据:")
    try:
        result = await source._fetch_yahoo_intraday("hang_seng_tech")
        if result.success:
            data = result.data
            print(f"  ✅ 成功获取数据")
            print(f"  数据点数: {len(data.get('data', []))}")
            print(f"  开盘价: {data.get('open')}")
            print(f"  最高价: {data.get('high')}")
            print(f"  最低价: {data.get('low')}")
            print(f"  收盘价: {data.get('close')}")
            print(f"  最新5个时间点:")
            for point in data.get('data', [])[-5:]:
                print(f"    {point['time']}: {point['price']} ({point['change']:+.2f}%)")
        else:
            print(f"  ❌ 失败: {result.error}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")
    
    await source.close()


async def test_hybrid_intraday():
    """测试混合数据源的港股指数分钟数据获取"""
    print("\n" + "=" * 70)
    print(" HybridIndexSource 港股指数分钟数据测试")
    print("=" * 70)
    
    source = HybridIndexSource()
    
    # 测试恒生指数
    print("\n[1] 恒生指数 - fetch_intraday:")
    try:
        result = await source.fetch_intraday("hang_seng")
        if result.success:
            data = result.data
            print(f"  ✅ 成功获取数据")
            print(f"  数据源: {result.metadata.get('source', 'unknown')}")
            print(f"  数据点数: {len(data.get('data', []))}")
            print(f"  开盘价: {data.get('open')}")
            print(f"  收盘价: {data.get('close')}")
            if len(data.get('data', [])) > 1:
                print(f"  时间范围: {data['data'][0]['time']} ~ {data['data'][-1]['time']}")
        else:
            print(f"  ❌ 失败: {result.error}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试恒生科技指数
    print("\n[2] 恒生科技指数 - fetch_intraday:")
    try:
        result = await source.fetch_intraday("hang_seng_tech")
        if result.success:
            data = result.data
            print(f"  ✅ 成功获取数据")
            print(f"  数据源: {result.metadata.get('source', 'unknown')}")
            print(f"  数据点数: {len(data.get('data', []))}")
            print(f"  开盘价: {data.get('open')}")
            print(f"  收盘价: {data.get('close')}")
            if len(data.get('data', [])) > 1:
                print(f"  时间范围: {data['data'][0]['time']} ~ {data['data'][-1]['time']}")
        else:
            print(f"  ❌ 失败: {result.error}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    await source.close()


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print(" 港股指数分钟级数据测试")
    print(f" 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 运行测试
    await test_yahoo_hk_intraday()
    await test_hybrid_intraday()
    
    print("\n" + "=" * 70)
    print(" 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
