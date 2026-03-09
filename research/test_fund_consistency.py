"""
基金涨跌幅数据一致性测试脚本

用于验证基金涨跌幅与折线图数据是否一致。

使用方法:
    uv run python research/test_fund_consistency.py <基金代码>
    
示例:
    uv run python research/test_fund_consistency.py 021087
    uv run python research/test_fund_consistency.py 014415
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.fund_source import Fund123DataSource


async def test_fund_consistency(fund_code: str):
    """测试基金数据一致性"""
    print(f"\n{'='*60}")
    print(f"测试基金: {fund_code}")
    print(f"{'='*60}\n")
    
    source = Fund123DataSource()
    
    # 获取基金数据
    result = await source.fetch(fund_code)
    
    if not result.success:
        print(f"❌ 获取基金数据失败: {result.error}")
        return
    
    data = result.data
    
    # 打印关键数据
    print("📊 基金基本信息:")
    print(f"  基金名称: {data.get('name')}")
    print(f"  基金类型: {data.get('type')}")
    print(f"  是否有实时估值: {data.get('has_real_time_estimate')}")
    
    print("\n📈 净值数据:")
    print(f"  最新净值: {data.get('unit_net_value')}")
    print(f"  净值日期: {data.get('net_value_date')}")
    print(f"  前日净值: {data.get('prev_net_value')}")
    print(f"  前日净值日期: {data.get('prev_net_value_date')}")
    
    print("\n💰 估值数据:")
    print(f"  估算净值: {data.get('estimated_net_value')}")
    print(f"  API涨跌幅: {data.get('estimated_growth_rate')}%")
    print(f"  估值时间: {data.get('estimate_time')}")
    
    # 计算涨跌幅
    estimate_value = data.get('estimated_net_value')
    net_value = data.get('unit_net_value')  # 最新净值
    prev_net_value = data.get('prev_net_value')
    api_growth_rate = data.get('estimated_growth_rate')
    
    print("\n🔍 一致性检查（基于最新净值）:")
    if estimate_value and net_value and net_value > 0:
        calculated_rate = (estimate_value - net_value) / net_value * 100
        diff = abs(api_growth_rate - calculated_rate) if api_growth_rate else None
        
        print(f"  最新净值: {net_value}")
        print(f"  计算涨跌幅: {calculated_rate:.4f}%")
        if api_growth_rate:
            print(f"  API涨跌幅: {api_growth_rate:.4f}%")
            print(f"  差异: {api_growth_rate - calculated_rate:.4f}%")
            
            if diff and diff > 0.1:
                print(f"  ⚠️  警告: 涨跌幅差异超过 0.1%!")
            else:
                print(f"  ✅ 涨跌幅一致")
    else:
        print("  ⚠️  无法计算涨跌幅: 缺少估算净值或最新净值")
    
    # 也检查基于前日净值的计算（用于对比）
    if estimate_value and prev_net_value and prev_net_value > 0:
        calculated_rate_prev = (estimate_value - prev_net_value) / prev_net_value * 100
        print(f"\n🔍 对比检查（基于前日净值）:")
        print(f"  前日净值: {prev_net_value}")
        print(f"  计算涨跌幅: {calculated_rate_prev:.4f}%")
        if api_growth_rate:
            print(f"  与API差异: {api_growth_rate - calculated_rate_prev:.4f}%")
    
    # 检查日内数据
    intraday = data.get('intraday', [])
    print(f"\n📉 日内分时数据:")
    print(f"  数据点数量: {len(intraday)}")
    
    if intraday:
        first_point = intraday[0]
        last_point = intraday[-1]
        print(f"  第一个点: 时间={first_point['time']}, 价格={first_point['price']}, 涨跌幅={first_point.get('change')}%")
        print(f"  最后一个点: 时间={last_point['time']}, 价格={last_point['price']}, 涨跌幅={last_point.get('change')}%")
        
        # 验证最后一个点的涨跌幅
        if prev_net_value and prev_net_value > 0:
            last_price = last_point['price']
            calculated_last_rate = (last_price - prev_net_value) / prev_net_value * 100
            last_change = last_point.get('change')
            
            print(f"\n🔍 日内数据最后一个点一致性:")
            print(f"  价格: {last_price}")
            print(f"  计算涨跌幅: {calculated_last_rate:.4f}%")
            if last_change:
                print(f"  API涨跌幅: {last_change:.4f}%")
                print(f"  差异: {last_change - calculated_last_rate:.4f}%")
    
    print(f"\n{'='*60}\n")


async def main():
    """主函数"""
    # 从命令行参数获取基金代码，或使用默认代码
    fund_codes = sys.argv[1:] if len(sys.argv) > 1 else ['021087', '014415']
    
    print("\n" + "="*60)
    print("基金涨跌幅数据一致性测试")
    print("="*60)
    
    for code in fund_codes:
        await test_fund_consistency(code)


if __name__ == "__main__":
    asyncio.run(main())
