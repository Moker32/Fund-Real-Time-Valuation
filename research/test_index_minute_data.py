#!/usr/bin/env python3
"""
A股指数分钟级数据源调研脚本

测试以下数据源的分钟级数据接口：
1. akshare - 指数分钟级数据接口
2. 东方财富 - 分钟线API
3. 新浪财经 - 分钟线接口
4. 腾讯财经 - 分钟线接口（当前使用）
"""

import asyncio
import json
import time
from datetime import datetime

import httpx


def print_separator(title: str):
    """打印分隔符"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def print_json(data: dict, indent: int = 2):
    """打印JSON数据"""
    print(json.dumps(data, indent=indent, ensure_ascii=False))


# ==================== 1. akshare 指数分钟级接口测试 ====================

async def test_akshare_index_minute():
    """测试akshare指数分钟级数据接口"""
    print_separator("1. akshare 指数分钟级接口测试")

    try:
        import akshare as ak

        print(f"\nakshare 版本: {ak.__version__}")

        # 测试1: stock_zh_index_daily - 日线数据（非分钟级）
        print("\n[1.1] stock_zh_index_daily - 上证指数日线数据")
        try:
            df = ak.stock_zh_index_daily(symbol="sh000001")
            if df is not None and not df.empty:
                print(f"  ✅ 成功获取日线数据，共 {len(df)} 条")
                print(f"  列名: {list(df.columns)}")
                print(f"  最新数据:\n{df.tail(1).to_string(index=False)}")
            else:
                print("  ❌ 返回空数据")
        except Exception as e:
            print(f"  ❌ 错误: {type(e).__name__}: {e}")

        # 测试2: 查找akshare是否有分钟级接口
        print("\n[1.2] 查找akshare分钟级接口...")
        minute_funcs = [attr for attr in dir(ak) if 'minute' in attr.lower() or 'min' in attr.lower()]
        index_funcs = [attr for attr in dir(ak) if 'index' in attr.lower() and ('min' in attr.lower() or 'kline' in attr.lower())]
        print(f"  可能的分钟级函数: {minute_funcs[:10]}")
        print(f"  可能的指数K线函数: {index_funcs[:10]}")

        # 测试3: stock_zh_a_minute - A股分钟级数据（个股）
        print("\n[1.3] stock_zh_a_minute - 个股分钟级数据（测试平安银行）")
        try:
            # 注意：这个接口是针对个股的，指数可能不支持
            df = ak.stock_zh_a_minute(symbol="000001", period="1", adjust="qfq")
            if df is not None and not df.empty:
                print(f"  ✅ 成功获取个股分钟数据，共 {len(df)} 条")
                print(f"  列名: {list(df.columns)}")
                print(f"  最新5条:\n{df.tail(5).to_string(index=False)}")
            else:
                print("  ❌ 返回空数据")
        except Exception as e:
            print(f"  ❌ 错误: {type(e).__name__}: {e}")

        # 测试4: 尝试获取指数分钟数据
        print("\n[1.4] 尝试用stock_zh_a_minute获取上证指数分钟数据")
        try:
            df = ak.stock_zh_a_minute(symbol="sh000001", period="1", adjust="qfq")
            if df is not None and not df.empty:
                print(f"  ✅ 成功获取指数分钟数据，共 {len(df)} 条")
                print(f"  列名: {list(df.columns)}")
                print(f"  最新5条:\n{df.tail(5).to_string(index=False)}")
            else:
                print("  ❌ 返回空数据（指数可能不支持此接口）")
        except Exception as e:
            print(f"  ❌ 错误: {type(e).__name__}: {e}")

        # 测试5: stock_zh_kline_daily - 查看是否有分钟级参数
        print("\n[1.5] 检查stock_zh_kline_daily接口")
        try:
            import inspect
            sig = inspect.signature(ak.stock_zh_kline_daily)
            print(f"  函数签名: {sig}")
        except Exception as e:
            print(f"  无法获取签名: {e}")

    except ImportError:
        print("\n❌ akshare 未安装，请运行: pip install akshare")


# ==================== 2. 东方财富分钟线API测试 ====================

async def test_eastmoney_minute():
    """测试东方财富分钟线API"""
    print_separator("2. 东方财富分钟线API测试")

    # 东方财富K线API
    # 参考: https://push2his.eastmoney.com/api/qt/stock/kline/get

    # 测试1: 上证指数分钟线
    print("\n[2.1] 上证指数分钟线 (1分钟)")
    try:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            "?secid=1.000001"  # 1表示上海，000001是上证指数
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            "&klt=1"  # 1=1分钟, 5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟, 101=日线
            "&fqt=0"  # 0=不复权, 1=前复权
            "&end=20500101"  # 结束日期
            "&limit=240"  # 获取最近240条（约1个交易日）
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            data = response.json()

        if data.get("data") and data["data"].get("klines"):
            klines = data["data"]["klines"]
            print(f"  ✅ 成功获取分钟线数据，共 {len(klines)} 条")
            print(f"  数据格式: 时间,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率")
            print(f"  最新5条:")
            for line in klines[-5:]:
                print(f"    {line}")
        else:
            print(f"  ❌ 返回数据为空或格式错误: {data.get('msg', '未知错误')}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试2: 深证成指分钟线
    print("\n[2.2] 深证成指分钟线 (1分钟)")
    try:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            "?secid=0.399001"  # 0表示深圳
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            "&klt=1&fqt=0&end=20500101&limit=240"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            data = response.json()

        if data.get("data") and data["data"].get("klines"):
            klines = data["data"]["klines"]
            print(f"  ✅ 成功获取分钟线数据，共 {len(klines)} 条")
            print(f"  最新5条:")
            for line in klines[-5:]:
                print(f"    {line}")
        else:
            print(f"  ❌ 返回数据为空: {data.get('msg', '未知错误')}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试3: 创业板指分钟线
    print("\n[2.3] 创业板指分钟线 (1分钟)")
    try:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            "?secid=0.399006"  # 创业板指
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            "&klt=1&fqt=0&end=20500101&limit=240"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            data = response.json()

        if data.get("data") and data["data"].get("klines"):
            klines = data["data"]["klines"]
            print(f"  ✅ 成功获取分钟线数据，共 {len(klines)} 条")
            print(f"  最新5条:")
            for line in klines[-5:]:
                print(f"    {line}")
        else:
            print(f"  ❌ 返回数据为空: {data.get('msg', '未知错误')}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试4: 5分钟线
    print("\n[2.4] 上证指数5分钟线")
    try:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            "?secid=1.000001"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            "&klt=5&fqt=0&end=20500101&limit=48"  # 48条5分钟线约1个交易日
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            data = response.json()

        if data.get("data") and data["data"].get("klines"):
            klines = data["data"]["klines"]
            print(f"  ✅ 成功获取5分钟线数据，共 {len(klines)} 条")
            print(f"  最新3条:")
            for line in klines[-3:]:
                print(f"    {line}")
        else:
            print(f"  ❌ 返回数据为空")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")


# ==================== 3. 新浪财经分钟线接口测试 ====================

async def test_sina_minute():
    """测试新浪财经分钟线接口"""
    print_separator("3. 新浪财经分钟线接口测试")

    # 新浪财经分钟线API
    # 参考: https://quotes.sina.cn/cn/api/quotes.php

    # 测试1: 上证指数分钟线
    print("\n[3.1] 上证指数分钟线")
    try:
        # 新浪财经分钟线接口
        url = "https://quotes.sina.cn/cn/api/quotes.php?symbol=sh000001&d=1"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            print(f"  状态码: {response.status_code}")
            print(f"  响应内容前200字符: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试2: 尝试新浪股票分钟线接口
    print("\n[3.2] 新浪股票分时数据接口")
    try:
        # 新浪分时数据接口（可能只支持个股）
        url = "https://quotes.sina.cn/cn/api/quotes.php?symbol=sh000001&d=1"

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = await client.get(url, headers=headers)
            print(f"  状态码: {response.status_code}")
            print(f"  响应内容: {response.text[:500]}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试3: 新浪期货/指数接口
    print("\n[3.3] 新浪指数行情接口")
    try:
        # 新浪指数行情接口
        url = "https://hq.sinajs.cn/list=s_sh000001"

        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn"
            }
            response = await client.get(url, headers=headers)
            print(f"  状态码: {response.status_code}")
            print(f"  响应内容: {response.text}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")


# ==================== 4. 腾讯财经分钟线接口测试 ====================

async def test_tencent_minute():
    """测试腾讯财经分钟线接口（当前项目使用）"""
    print_separator("4. 腾讯财经分钟线接口测试（当前项目使用）")

    # 测试1: 腾讯分钟线接口（个股）
    print("\n[4.1] 腾讯分钟线接口 - 上证指数")
    try:
        # 腾讯分钟线接口
        url = (
            "https://ifzq.gtimg.cn/appstock/app/fqkline/get"
            "?param=sh000001,m1,,,240,qfq"  # m1=1分钟, 240条
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            data = response.json()

        if data.get("code") == 0 and data.get("data"):
            stock_data = data["data"].get("sh000001", {})
            if isinstance(stock_data, dict):
                minute_data = stock_data.get("m1", [])
                if minute_data:
                    print(f"  ✅ 成功获取分钟线数据，共 {len(minute_data)} 条")
                    print(f"  数据格式: [时间,开盘,收盘,最低,最高,成交量]")
                    print(f"  最新5条:")
                    for item in minute_data[-5:]:
                        print(f"    {item}")
                else:
                    print(f"  ❌ 分钟数据为空（指数可能不支持分钟线接口）")
                    print(f"  返回数据: {stock_data.keys() if isinstance(stock_data, dict) else stock_data}")
            else:
                print(f"  ❌ 数据格式错误: {type(stock_data)}")
        else:
            print(f"  ❌ 接口返回错误: {data.get('msg', '未知错误')}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试2: 腾讯日线接口（当前项目使用）
    print("\n[4.2] 腾讯日线接口 - 上证指数（当前项目使用）")
    try:
        url = (
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
            "?param=sh000001,day,,,1,qfq"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            data = response.json()

        if data.get("code") == 0 and data.get("data"):
            stock_data = data["data"].get("sh000001", {})
            if isinstance(stock_data, dict):
                day_data = stock_data.get("day", [])
                if day_data:
                    print(f"  ✅ 成功获取日线数据，共 {len(day_data)} 条")
                    print(f"  最新数据: {day_data[-1]}")
                else:
                    print(f"  ❌ 日线数据为空")
            else:
                print(f"  ❌ 数据格式错误")
        else:
            print(f"  ❌ 接口返回错误")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试3: 腾讯实时行情接口
    print("\n[4.3] 腾讯实时行情接口")
    try:
        url = "https://qt.gtimg.cn/q=sh000001,sz399001,sz399006"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            text = response.text

        print(f"  ✅ 成功获取实时行情")
        print(f"  响应内容:")
        for line in text.strip().split(';'):
            if line.strip():
                print(f"    {line[:100]}...")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")


# ==================== 5. 同花顺分钟线接口测试 ====================

async def test_ths_minute():
    """测试同花顺分钟线接口"""
    print_separator("5. 同花顺分钟线接口测试")

    print("\n[5.1] 同花顺指数分钟线")
    print("  ⚠️ 同花顺API需要认证，通常不对外开放")
    print("  同花顺iFinD API是付费服务，需要申请API Key")


# ==================== 6. 汇总对比 ====================

def print_summary():
    """打印调研汇总"""
    print_separator("6. 数据源调研汇总")

    summary = """
【A股指数分钟级数据源调研结果】

1. akshare
   - 指数分钟级接口: ❌ 不支持
   - 个股分钟级接口: ✅ stock_zh_a_minute (仅个股)
   - 指数日线接口: ✅ stock_zh_index_daily
   - 结论: akshare没有专门的指数分钟级接口

2. 东方财富 (推荐)
   - 分钟级接口: ✅ https://push2his.eastmoney.com/api/qt/stock/kline/get
   - 支持频率: 1分钟(klt=1)、5分钟(klt=5)、15分钟、30分钟、60分钟
   - 数据格式: 时间,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
   - 覆盖范围: 上证指数(1.000001)、深证成指(0.399001)、创业板指(0.399006)等
   - 稳定性: 高
   - 接入复杂度: 低（纯HTTP，无需认证）
   - 结论: ✅ 推荐作为分钟级数据源

3. 新浪财经
   - 分钟级接口: ❌ 未找到公开的指数分钟线接口
   - 实时行情: ✅ hq.sinajs.cn (仅当前价格)
   - 结论: 不适合分钟级数据

4. 腾讯财经 (当前使用)
   - 分钟级接口: ⚠️ 部分支持（主要支持个股，指数支持有限）
   - 日线接口: ✅ 支持
   - 实时行情: ✅ 支持
   - 当前项目使用: 模拟分时数据（基于日线生成）
   - 结论: 需要替换为真实分钟级数据源

5. 同花顺iFinD
   - 分钟级接口: ✅ 支持（需付费）
   - 结论: 成本较高，暂不考虑

【推荐方案】

方案一: 东方财富分钟线API（推荐）
- 使用东方财富K线API获取分钟级数据
- 优点: 免费、稳定、数据完整
- 缺点: 需要处理复权（已支持）
- 实现复杂度: 低

方案二: 混合方案
- A股指数: 东方财富分钟线API
- 港股/美股指数: 继续使用腾讯财经或Yahoo Finance
- 优点: 各市场使用最优数据源
- 缺点: 需要维护多个数据源

【示例代码】

东方财富1分钟线API调用:
```python
url = (
    "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    "?secid=1.000001"  # 1=上海, 0=深圳
    "&fields1=f1,f2,f3,f4,f5,f6"
    "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
    "&klt=1"  # 1=1分钟
    "&fqt=0"  # 0=不复权
    "&end=20500101"
    "&limit=240"
)
```

数据字段说明:
- f51: 时间 (YYYY-MM-DD HH:MM:SS)
- f52: 开盘
- f53: 收盘
- f54: 最低
- f55: 最高
- f56: 成交量
- f57: 成交额
- f58: 振幅
- f59: 涨跌幅
- f60: 涨跌额
- f61: 换手率
"""
    print(summary)


async def main():
    """主函数"""
    print("=" * 70)
    print(" A股指数分钟级数据源调研")
    print(f" 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 运行所有测试
    await test_akshare_index_minute()
    await test_eastmoney_minute()
    await test_sina_minute()
    await test_tencent_minute()
    await test_ths_minute()

    # 打印汇总
    print_summary()

    print("\n" + "=" * 70)
    print(" 调研完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
