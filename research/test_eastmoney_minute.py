#!/usr/bin/env python3
"""
东方财富分钟线API详细测试
"""

import asyncio
from datetime import datetime

import httpx


def print_separator(title: str):
    """打印分隔符"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


async def test_eastmoney_with_headers():
    """使用正确的请求头测试东方财富API"""
    print_separator("东方财富分钟线API测试（带请求头）")

    # 东方财富K线API - 需要正确的请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://quote.eastmoney.com/",
        "Connection": "keep-alive",
    }

    # 测试1: 上证指数1分钟线
    print("\n[1] 上证指数1分钟线")
    try:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            "?secid=1.000001"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            "&klt=1"
            "&fqt=0"
            "&end=20500101"
            "&lmt=240"
        )

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(url)
            print(f"  状态码: {response.status_code}")
            print(f"  响应头: {dict(response.headers)}")

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("klines"):
                    klines = data["data"]["klines"]
                    print(f"  ✅ 成功获取分钟线数据，共 {len(klines)} 条")
                    print("  数据格式: 时间,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率")
                    print("  最新5条:")
                    for line in klines[-5:]:
                        parts = line.split(",")
                        print(f"    时间:{parts[0]} 开盘:{parts[1]} 收盘:{parts[2]} 最高:{parts[4]} 最低:{parts[3]} 成交量:{parts[5]}")
                else:
                    print(f"  ❌ 数据为空: {data}")
            else:
                print(f"  ❌ 请求失败: {response.text[:200]}")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试2: 深证成指1分钟线
    print("\n[2] 深证成指1分钟线")
    try:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            "?secid=0.399001"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            "&klt=1"
            "&fqt=0"
            "&end=20500101"
            "&lmt=240"
        )

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(url)
            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("klines"):
                    klines = data["data"]["klines"]
                    print(f"  ✅ 成功获取分钟线数据，共 {len(klines)} 条")
                    print("  最新3条:")
                    for line in klines[-3:]:
                        print(f"    {line}")
                else:
                    print("  ❌ 数据为空")
            else:
                print("  ❌ 请求失败")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试3: 创业板指1分钟线
    print("\n[3] 创业板指1分钟线")
    try:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            "?secid=0.399006"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            "&klt=1"
            "&fqt=0"
            "&end=20500101"
            "&lmt=240"
        )

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(url)
            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("klines"):
                    klines = data["data"]["klines"]
                    print(f"  ✅ 成功获取分钟线数据，共 {len(klines)} 条")
                    print("  最新3条:")
                    for line in klines[-3:]:
                        print(f"    {line}")
                else:
                    print("  ❌ 数据为空")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试4: 上证50
    print("\n[4] 上证50指数1分钟线")
    try:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            "?secid=1.000016"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            "&klt=1"
            "&fqt=0"
            "&end=20500101"
            "&lmt=240"
        )

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(url)
            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("klines"):
                    klines = data["data"]["klines"]
                    print(f"  ✅ 成功获取分钟线数据，共 {len(klines)} 条")
                else:
                    print("  ❌ 数据为空")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试5: 沪深300
    print("\n[5] 沪深300指数1分钟线")
    try:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            "?secid=1.000300"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            "&klt=1"
            "&fqt=0"
            "&end=20500101"
            "&lmt=240"
        )

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(url)
            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("klines"):
                    klines = data["data"]["klines"]
                    print(f"  ✅ 成功获取分钟线数据，共 {len(klines)} 条")
                else:
                    print("  ❌ 数据为空")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")

    # 测试6: 5分钟线
    print("\n[6] 上证指数5分钟线")
    try:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            "?secid=1.000001"
            "&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            "&klt=5"
            "&fqt=0"
            "&end=20500101"
            "&lmt=48"
        )

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(url)
            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and data["data"].get("klines"):
                    klines = data["data"]["klines"]
                    print(f"  ✅ 成功获取5分钟线数据，共 {len(klines)} 条")
                    print("  最新3条:")
                    for line in klines[-3:]:
                        print(f"    {line}")
                else:
                    print("  ❌ 数据为空")
    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")


async def main():
    """主函数"""
    print("=" * 70)
    print(" 东方财富分钟线API详细测试")
    print(f" 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    await test_eastmoney_with_headers()

    print("\n" + "=" * 70)
    print(" 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
