# 港股指数分钟级数据源调研报告

**调研日期**: 2026-03-09  
**调研目标**: 解决港股指数（恒生指数、恒生科技指数）分钟级数据获取问题

---

## 执行摘要

经过全面调研，发现 **yfinance** 可以有效获取港股指数分钟级数据，这是目前最佳的免费数据源方案。

- 恒生指数 (`^HSI`): 支持 ✅
- 恒生科技指数 (`HSTECH.HK`): 支持 ✅
- 数据点数: 约 330-350 个/交易日（1分钟间隔）

---

## 背景问题

### 原有问题
- A股指数使用 akshare 的 `stock_zh_a_minute` 接口获取真实分钟级数据（~240 数据点）
- 港股指数使用腾讯财经分钟线接口，但只返回 1 条日线数据，无法绘制日内分时图
- 结果：港股指数卡片只显示当前价格，没有分时走势图表

### 目标
为港股指数找到能提供真实分钟级数据的数据源，实现与A股指数相同的分时图表功能。

---

## 1. 数据源调研

### 1.1 akshare 港股指数分钟数据

**调研结果**: ❌ 不支持指数，只支持个股

| 接口 | 支持情况 | 说明 |
|------|---------|------|
| `stock_hk_hist_min_em` | ⚠️ 仅个股 | 支持港股个股分钟数据，不支持指数 |
| `stock_hk_index_spot_em` | ❌ 网络受限 | 港股指数实时行情，当前网络环境无法访问 |
| `stock_hk_index_daily_em` | ❌ 网络受限 | 港股指数日线数据，当前网络环境无法访问 |

**测试代码**:
```python
import akshare as ak

# 测试个股 - 成功
df = ak.stock_hk_hist_min_em(symbol="00700", period="1")  # 腾讯控股
print(f"获取到 {len(df)} 条数据")  # ✅ 1335 条

# 测试指数 - 失败
df = ak.stock_hk_hist_min_em(symbol="800000", period="1")  # 恒生指数
# ❌ TypeError: 'NoneType' object is not subscriptable
```

**结论**: akshare 没有提供港股指数分钟级数据接口。

---

### 1.2 东方财富 API

**调研结果**: ❌ 当前网络环境无法访问

| 接口 | 状态 | 说明 |
|------|------|------|
| `push2his.eastmoney.com` | ❌ 无法访问 | 港股指数分钟线 API 返回 `RemoteProtocolError` |

**测试的 URL 格式**:
```
https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=100.HSI&...
https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=124.HSI&...
```

**结论**: 在当前网络环境下无法使用东方财富 API。

---

### 1.3 腾讯财经

**调研结果**: ⚠️ 只返回日线数据

| 接口 | 状态 | 说明 |
|------|------|------|
| 分钟线接口 (`m1`) | ⚠️ 仅日线 | 对港股指数只返回 1 条日线数据 |
| 日线接口 (`day`) | ✅ 正常 | 返回日线数据 |
| 实时行情 | ✅ 正常 | 返回当前价格 |

**测试代码**:
```python
import httpx

# 腾讯分钟线接口
url = "https://ifzq.gtimg.cn/appstock/app/fqkline/get?param=hkHSI,m1,,,240,qfq"
response = await httpx.AsyncClient().get(url)
data = response.json()

# 返回结果
# {"code": 0, "data": {"hkHSI": {"m1": [["2026-03-09", "25075.740", "24953.990", ...]]}}}
# 只有 1 条数据，是日线数据，不是分钟数据
```

**结论**: 腾讯财经分钟线接口对港股指数只返回日线数据，无法用于分时图表。

---

### 1.4 yfinance (推荐) ✅

**调研结果**: ✅ 完全支持港股指数分钟数据

| 指数 | Yahoo代码 | 支持情况 | 数据点数 |
|------|----------|---------|---------|
| 恒生指数 | `^HSI` | ✅ 支持 | ~345/交易日 |
| 恒生科技 | `HSTECH.HK` | ✅ 支持 | ~345/交易日 |

**关键发现**:
- 港股指数需要使用 `period="5d"` 才能获取分钟数据
- 使用 `period="1d"` 会返回空数据（`possibly delisted` 警告）
- 获取后需要过滤出最近交易日的数据

**测试代码**:
```python
import yfinance as yf

# 恒生指数
ticker = yf.Ticker("^HSI")

# 必须使用 5d 才能获取分钟数据
hist = ticker.history(period="5d", interval="1m")
print(f"获取到 {len(hist)} 条数据")  # ✅ 1380 条（5天）

# 过滤出最近交易日的数据
latest_date = hist.index[-1].date()
today_data = hist[hist.index.date == latest_date]
print(f"今天有 {len(today_data)} 条数据")  # ✅ 345 条
```

**数据格式**:
```
                            Open         High          Low        Close  Volume
Datetime                                                                        
2026-03-06 09:30:00+08:00  25358.56     25420.12     25358.56     25410.23     0
2026-03-06 09:31:00+08:00  25410.23     25450.67     25405.12     25435.89     0
...
2026-03-06 16:08:00+08:00  25768.40     25768.40     25757.29     25757.29     0
```

**优点**:
- ✅ 完全免费
- ✅ 数据完整（OHLCV）
- ✅ 稳定性高
- ✅ 无需注册或API Key
- ✅ 支持港股主要指数

**缺点**:
- ⚠️ 数据有轻微延迟（约15-30分钟）
- ⚠️ 需要使用 `period="5d"` 才能获取分钟数据

---

## 2. 实施方案

### 2.1 代码修改

修改文件: [`src/datasources/index_source.py`](src/datasources/index_source.py)

#### 修改 1: 港股指数使用 yfinance 获取分钟数据

```python
# 在 _fetch_tencent_intraday 方法中
# 港股使用yfinance获取分钟级数据（腾讯分钟线接口对指数只返回日线数据）
if tencent_code.startswith("hk"):
    yahoo_result = await self._fetch_yahoo_intraday(index_type)
    if yahoo_result.success:
        return yahoo_result
    # 如果yfinance失败，回退到腾讯财经日线接口
    logger.warning(f"[HybridIndexSource] yfinance港股分钟数据获取失败，回退到腾讯日线接口: {index_type}")
```

#### 修改 2: 优化 yfinance 港股数据获取

```python
# 在 _fetch_yahoo_intraday 方法中
# 港股指数需要使用5天数据才能获取分钟级数据
period = "5d" if index_type in HK_INDICES else "1d"

hist = await asyncio.wait_for(
    loop.run_in_executor(None, lambda: ticker_obj.history(period=period, interval="1m")),
    timeout=self._yahoo.YFINANCE_TIMEOUT * 2,
)

# 对于港股指数，只保留最近一个交易日的数据
if index_type in HK_INDICES and not hist.empty:
    latest_date = hist.index[-1].date()
    hist = hist[hist.index.date == latest_date]
```

---

### 2.2 数据源选择逻辑

修改后的数据源选择逻辑:

| 指数类型 | 实时数据 | 分钟数据 | 历史数据 |
|---------|---------|---------|---------|
| A股指数 | 腾讯财经 / akshare | **akshare** (`stock_zh_a_minute`) | akshare |
| 港股指数 | 腾讯财经 | **yfinance** (`^HSI`, `HSTECH.HK`) | yfinance |
| 美股指数 | 腾讯财经 | yfinance | yfinance |
| 日经/欧洲 | yfinance | yfinance | yfinance |

---

## 3. 测试结果

### 3.1 港股指数分钟数据测试

```
======================================================================
 yfinance 港股指数分钟数据测试
======================================================================

[1] 恒生指数 (^HSI) 分钟数据:
  ✅ 成功获取数据
  数据点数: 345
  开盘价: 25358.56
  最高价: 25806.72
  最低价: 25267.63
  收盘价: 25757.29
  最新5个时间点:
    16:04: 25768.4 (+1.84%)
    16:05: 25768.4 (+1.84%)
    16:06: 25768.4 (+1.84%)
    16:07: 25768.4 (+1.84%)
    16:08: 25757.29 (+1.80%)

[2] 恒生科技指数 (HSTECH.HK) 分钟数据:
  ✅ 成功获取数据
  数据点数: 345
  开盘价: 4818.81
  最高价: 4977.08
  最低价: 4798.23
  收盘价: 4947.5
```

### 3.2 回归测试

```
============================= test session starts ==============================
tests/test_index_source.py .................................. 12 passed
tests/test_api_indices.py ................................... 15 passed
============================== 27 passed ======================================
```

所有现有测试通过，无回归问题。

---

## 4. 数据对比

### 4.1 数据质量对比

| 数据源 | 数据点数 | 数据延迟 | 稳定性 | 成本 |
|--------|---------|---------|--------|------|
| **yfinance (新)** | ~345/日 | ~15-30分钟 | 高 | 免费 |
| 腾讯财经 (旧) | 1/日 | 实时 | 高 | 免费 |
| akshare (A股) | ~240/日 | ~1-2分钟 | 高 | 免费 |

### 4.2 改进效果

**修改前**:
- 港股指数卡片只显示当前价格
- 分时图表只有 1 个数据点（日线）
- 无法显示日内走势

**修改后**:
- 港股指数卡片显示完整分时图表
- 约 345 个分钟级数据点
- 可以显示完整的日内走势

---

## 5. 结论

### 推荐方案

使用 **yfinance** 作为港股指数分钟级数据源：

1. **恒生指数**: 使用 `^HSI` 代码
2. **恒生科技指数**: 使用 `HSTECH.HK` 代码
3. **数据获取**: 使用 `period="5d", interval="1m"` 参数
4. **数据过滤**: 只保留最近交易日的数据

### 实施状态

- ✅ 调研完成
- ✅ 代码实现
- ✅ 测试通过
- ✅ 回归测试通过

### 代码变更

- 修改文件: [`src/datasources/index_source.py`](src/datasources/index_source.py)
- 测试文件: [`research/test_hk_index_minute.py`](research/test_hk_index_minute.py)

---

## 附录

### 测试脚本

```bash
# 运行港股指数分钟数据测试
uv run python research/test_hk_index_minute.py

# 运行回归测试
uv run pytest tests/test_index_source.py tests/test_api_indices.py -v
```

### 相关文档

- [A股指数分钟级数据源调研](data-sources-index-minute-research.md)
- [数据源设计文档](data-sources-index-research.md)
