# A股指数分钟级数据源调研报告

**调研日期**: 2026-03-07  
**调研目标**: 寻找能替代当前模拟数据的有效A股指数分钟级数据源

---

## 执行摘要

经过全面调研，发现 **akshare 的 `stock_zh_a_minute` 接口** 可以有效获取A股指数分钟级数据，这是目前最佳的免费数据源方案。东方财富API在当前网络环境下无法访问，腾讯财经分钟线接口对指数支持有限。

---

## 1. akshare 指数分钟级接口

### 1.1 接口详情

| 项目 | 内容 |
|------|------|
| **接口名称** | `stock_zh_a_minute` |
| **支持数据** | A股指数分钟级数据 |
| **数据频率** | 1分钟 |
| **数据字段** | day(时间), open(开盘), high(最高), low(最低), close(收盘), volume(成交量), amount(成交额) |
| **覆盖范围** | 上证指数、深证成指、创业板指、上证50、沪深300等 |
| **稳定性** | 高 |
| **成本** | 免费 |

### 1.2 测试结果

```python
import akshare as ak

# 获取上证指数分钟级数据
df = ak.stock_zh_a_minute(symbol="sh000001", period="1", adjust="qfq")
print(f"获取到 {len(df)} 条数据")
print(df.tail(5))
```

**输出示例**:
```
获取到 1970 条数据
                  day     open     high      low    close    volume           amount
2026-03-06 14:55:00 4124.065 4124.342 4123.616 4124.109 384187400  5885067264.0000
2026-03-06 14:56:00 4124.233 4124.414 4123.601 4124.098 444101800  6585188352.0000
2026-03-06 14:57:00 4124.102 4124.479 4123.966 4124.479 500335100  7206535168.0000
2026-03-06 14:58:00 4124.725 4125.054 4124.725 4125.054  22792400   350617600.0000
2026-03-06 15:00:00 4124.827 4124.827 4124.175 4124.194 748915900 11017191424.0000
```

### 1.3 支持的指数代码

| 指数名称 | 代码 |
|---------|------|
| 上证指数 | sh000001 |
| 深证成指 | sz399001 |
| 创业板指 | sz399006 |
| 上证50 | sh000016 |
| 沪深300 | sh000300 |
| 中证500 | sh000905 |
| 科创50 | sh000688 |
| 中证1000 | sh000852 |

### 1.4 优缺点分析

**优点**:
- ✅ 完全免费
- ✅ 数据完整（包含开盘、收盘、最高、最低、成交量、成交额）
- ✅ 支持前复权
- ✅ 稳定性高
- ✅ 无需注册或API Key

**缺点**:
- ⚠️ 接口命名有误导性（`stock_zh_a_minute` 实际也支持指数）
- ⚠️ 数据有轻微延迟（约1-2分钟）

---

## 2. 东方财富分钟线API

### 2.1 接口详情

| 项目 | 内容 |
|------|------|
| **接口地址** | `https://push2his.eastmoney.com/api/qt/stock/kline/get` |
| **支持数据** | A股指数分钟级K线 |
| **数据频率** | 1分钟、5分钟、15分钟、30分钟、60分钟 |
| **数据字段** | 时间、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率 |
| **覆盖范围** | 全A股指数 |
| **成本** | 免费 |

### 2.2 测试结果

**状态**: ❌ 在当前网络环境下无法访问

错误信息: `RemoteProtocolError: Server disconnected without sending a response.`

可能原因:
1. 网络环境限制
2. 需要特定的请求头或Cookie
3. API可能已更新或限制访问

### 2.3 接口格式（参考）

```python
url = (
    "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    "?secid=1.000001"  # 1=上海, 0=深圳
    "&fields1=f1,f2,f3,f4,f5,f6"
    "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
    "&klt=1"  # 1=1分钟, 5=5分钟
    "&fqt=0"  # 0=不复权, 1=前复权
    "&end=20500101"
    "&lmt=240"
)
```

---

## 3. 新浪财经分钟线接口

### 3.1 测试结果

**状态**: ❌ 未找到公开的指数分钟线接口

新浪提供的接口:
- `hq.sinajs.cn` - 仅提供实时行情（当前价格），无历史分钟数据
- 其他分钟线接口返回404

---

## 4. 腾讯财经分钟线接口

### 4.1 当前项目使用情况

当前项目在 [`src/datasources/index_source.py`](src/datasources/index_source.py:1070) 中实现了腾讯财经数据源:

- **实时行情**: ✅ 支持（`qt.gtimg.cn`）
- **日线数据**: ✅ 支持（`web.ifzq.gtimg.cn`）
- **分钟线数据**: ⚠️ 部分支持（主要支持个股，指数支持有限）

### 4.2 测试结果

```python
# 腾讯分钟线接口测试
url = "https://ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000001,m1,,,240,qfq"
# 返回: {"code": -1, "msg": "bad params"}
```

**结论**: 腾讯财经分钟线接口对指数返回 `bad params` 错误，不支持A股指数分钟级数据。

### 4.3 当前实现的问题

当前代码在 [`_fetch_tencent_intraday`](src/datasources/index_source.py:926) 中:
1. 尝试调用分钟线接口获取数据
2. 失败后回退到日线接口
3. 基于日线数据**生成模拟的分时数据**（使用正弦波+随机扰动）

这导致:
- 分时图表是模拟生成的，非真实数据
- 用户看到的是"假"的分钟级走势

---

## 5. 同花顺iFinD API

### 5.1 接口详情

| 项目 | 内容 |
|------|------|
| **类型** | 付费专业数据服务 |
| **支持数据** | 全市场分钟级数据 |
| **成本** | 需付费订阅 |

**结论**: 成本较高，暂不考虑。

---

## 6. 数据源对比汇总

| 数据源 | 分钟级支持 | 数据质量 | 稳定性 | 成本 | 推荐度 |
|--------|-----------|---------|--------|------|--------|
| **akshare** | ✅ 支持 | 高 | 高 | 免费 | ⭐⭐⭐⭐⭐ |
| 东方财富 | ⚠️ 网络受限 | 高 | 未知 | 免费 | ⭐⭐⭐ |
| 新浪财经 | ❌ 不支持 | - | - | 免费 | ⭐ |
| 腾讯财经 | ❌ 不支持指数 | - | 高 | 免费 | ⭐⭐ |
| 同花顺iFinD | ✅ 支持 | 高 | 高 | 付费 | ⭐⭐⭐ |

---

## 7. 推荐方案

### 方案一: akshare 分钟级数据（强烈推荐）

使用 akshare 的 `stock_zh_a_minute` 接口获取A股指数分钟级数据。

**实现代码示例**:

```python
import asyncio
import akshare as ak
from src.datasources.base import DataSource, DataSourceResult, DataSourceType

class AKShareIndexMinuteSource(DataSource):
    """akshare A股指数分钟级数据源"""
    
    # 指数代码映射
    INDEX_CODES = {
        "shanghai": "sh000001",
        "shenzhen": "sz399001",
        "chi_next": "sz399006",
        "shanghai50": "sh000016",
        "hs300": "sh000300",
        "csi500": "sh000905",
        "star50": "sh000688",
        "csi1000": "sh000852",
    }
    
    async def fetch_intraday(self, index_type: str) -> DataSourceResult:
        """获取指数日内分钟级数据"""
        try:
            symbol = self.INDEX_CODES.get(index_type)
            if not symbol:
                return DataSourceResult(
                    success=False,
                    error=f"不支持的指数类型: {index_type}",
                    source=self.name
                )
            
            # 在线程池中执行同步的akshare调用
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None, 
                lambda: ak.stock_zh_a_minute(symbol=symbol, period="1", adjust="qfq")
            )
            
            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    error="无法获取分钟级数据",
                    source=self.name
                )
            
            # 转换为标准格式
            intraday_points = []
            for _, row in df.iterrows():
                time_str = row["day"].split(" ")[1][:5]  # 提取 HH:MM
                intraday_points.append({
                    "time": time_str,
                    "price": float(row["close"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "volume": int(row["volume"]),
                })
            
            return DataSourceResult(
                success=True,
                data={
                    "index": index_type,
                    "data": intraday_points,
                    "open": float(df["open"].iloc[0]),
                    "high": float(df["high"].max()),
                    "low": float(df["low"].min()),
                    "close": float(df["close"].iloc[-1]),
                },
                source=self.name
            )
            
        except Exception as e:
            return DataSourceResult(
                success=False,
                error=f"获取数据失败: {e}",
                source=self.name
            )
```

**优点**:
- ✅ 真实分钟级数据，非模拟
- ✅ 数据完整（OHLCV）
- ✅ 免费稳定
- ✅ 实现简单

**缺点**:
- ⚠️ 数据有1-2分钟延迟（可接受）

### 方案二: 混合数据源方案

| 市场 | 数据源 | 说明 |
|------|--------|------|
| A股指数 | akshare | 分钟级数据 |
| 港股指数 | 腾讯财经 | 实时行情（继续模拟分时） |
| 美股指数 | Yahoo Finance | 分钟级数据（yfinance支持） |
| 日经/欧洲 | Yahoo Finance | 分钟级数据 |

---

## 8. 实施建议

### 8.1 短期方案（推荐）

1. **立即替换A股指数分钟级数据源**
   - 使用 akshare `stock_zh_a_minute` 接口
   - 替换 [`_fetch_tencent_minute_intraday`](src/datasources/index_source.py:1070) 方法

2. **保留现有降级逻辑**
   - 如果akshare失败，继续回退到模拟数据
   - 确保服务可用性

### 8.2 代码修改位置

需要修改的文件:
- [`src/datasources/index_source.py`](src/datasources/index_source.py:1070) - 替换 `_fetch_tencent_minute_intraday` 方法

### 8.3 测试验证

修改后需要验证:
- [ ] 上证指数分钟级数据正常获取
- [ ] 深证成指分钟级数据正常获取
- [ ] 创业板指分钟级数据正常获取
- [ ] 分时图表显示真实数据
- [ ] 降级逻辑正常工作

---

## 9. 结论

**akshare 的 `stock_zh_a_minute` 接口是目前最佳的A股指数分钟级数据源**，虽然接口命名有误导性（包含"stock"），但实际支持指数数据。

建议**立即实施**方案一，替换当前的模拟数据方案，为用户提供真实的指数分钟级走势。

---

## 附录: 测试脚本

完整的测试脚本位于:
- [`scripts/test_index_minute_data.py`](scripts/test_index_minute_data.py) - 综合测试脚本
- [`scripts/test_eastmoney_minute.py`](scripts/test_eastmoney_minute.py) - 东方财富API测试
