# Fund Real-Time Valuation API Specification

## Overview

REST API specification for the Fund Real-Time Valuation application. Base URL: `http://localhost:8000`

---

## Base Information

| Item | Value |
|------|-------|
| Base URL | `http://localhost:8000` |
| Documentation | `/docs` (Swagger UI) |
| Redoc | `/redoc` |
| Health Check | `/api/health` |

---

## Common Headers

| Header | Value | Required |
|--------|-------|----------|
| Content-Type | `application/json` | Yes |
| Accept | `application/json` | Recommended |

---

## Common Response Format

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2026-02-20T10:30:00Z"
}
```

### Error Response

```json
{
  "success": false,
  "error": "ErrorType",
  "detail": "Detailed error message",
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

## Endpoints

### 1. Funds API

#### 1.1 Get Fund List

| Item | Value |
|------|-------|
| Endpoint | `GET /api/funds` |
| Summary | 获取基金列表 |
| Description | 获取所有已注册基金数据源的基金信息 |

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| codes | string | No | Optional fund codes, comma-separated |

**Response**

```json
{
  "funds": [
    {
      "fund_code": "161039",
      "name": "易方达消费行业股票",
      "type": "股票型",
      "unit_net_value": 1.2345,
      "net_value_date": "2026-02-19",
      "prev_net_value": 1.2300,
      "prev_net_value_date": "2026-02-18",
      "estimated_net_value": 1.2360,
      "estimated_growth_rate": 0.32,
      "estimate_time": "2026-02-20 10:15:00",
      "estimateChange": 0.0015,
      "source": "eastmoney",
      "isHolding": true,
      "hasRealTimeEstimate": true
    }
  ],
  "total": 5,
  "timestamp": "2026-02-20T10:30:00Z",
  "progress": 100
}
```

---

#### 1.2 Get Fund Detail

| Item | Value |
|------|-------|
| Endpoint | `GET /api/funds/{code}` |
| Summary | 获取基金详情 |
| Description | 根据基金代码获取单个基金的详细信息 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| code | string | Yes | Fund code (6 digits) |

**Response**

```json
{
  "fund_code": "161039",
  "name": "易方达消费行业股票",
  "type": "股票型",
  "unit_net_value": 1.2345,
  "net_value_date": "2026-02-19",
  "prev_net_value": 1.2300,
  "prev_net_value_date": "2026-02-18",
  "estimated_net_value": 1.2360,
  "estimated_growth_rate": 0.32,
  "estimate_time": "2026-02-20 10:15:00",
  "estimateChange": 0.0015,
  "source": "eastmoney",
  "isHolding": true,
  "hasRealTimeEstimate": true
}
```

---

#### 1.3 Get Fund Estimate

| Item | Value |
|------|-------|
| Endpoint | `GET /api/funds/{code}/estimate` |
| Summary | 获取基金估值 |
| Description | 根据基金代码获取基金的实时估值信息 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| code | string | Yes | Fund code (6 digits) |

**Response**

```json
{
  "fund_code": "161039",
  "name": "易方达消费行业股票",
  "type": "股票型",
  "estimated_net_value": 1.2360,
  "estimated_growth_rate": 0.32,
  "estimate_time": "2026-02-20 10:15:00",
  "unit_net_value": 1.2345,
  "net_value_date": "2026-02-19",
  "estimateChange": 0.0015,
  "isHolding": true,
  "hasRealTimeEstimate": true
}
```

---

#### 1.4 Get Fund History

| Item | Value |
|------|-------|
| Endpoint | `GET /api/funds/{code}/history` |
| Summary | 获取基金历史净值 |
| Description | 根据基金代码获取基金的历史净值数据 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| code | string | Yes | Fund code (6 digits) |

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| period | string | No | Time period: "近一周", "近一月", "近三月", "近六月", "近一年", "近三年", "近五年", "成立以来" (default: "近一年") |

**Response**

```json
{
  "fund_code": "161039",
  "name": "易方达消费行业股票",
  "history": [
    {
      "date": "2026-02-19",
      "unit_net_value": 1.2345,
      "acc_net_value": 2.4567,
      "daily_growth_rate": 0.32
    }
  ],
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

#### 1.5 Get Fund Intraday

| Item | Value |
|------|-------|
| Endpoint | `GET /api/funds/{code}/intraday` |
| Summary | 获取基金日内分时数据 |
| Description | 根据基金代码获取 fund123.cn 的完整日内分时数据 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| code | string | Yes | Fund code (6 digits) |

**Response**

```json
{
  "fund_code": "161039",
  "name": "易方达消费行业股票",
  "date": "2026-02-20",
  "data": [
    {
      "time": "09:30",
      "price": 1.2340,
      "change": 0.28
    },
    {
      "time": "09:35",
      "price": 1.2350,
      "change": 0.36
    }
  ],
  "count": 90,
  "source": "fund123"
}
```

---

#### 1.6 Add to Watchlist

| Item | Value |
|------|-------|
| Endpoint | `POST /api/funds/watchlist` |
| Summary | 添加自选基金 |
| Description | 将基金添加到自选列表 |

**Request Body**

```json
{
  "code": "161039",
  "name": "易方达消费行业股票"
}
```

**Response**

```json
{
  "success": true,
  "message": "基金 161039 已添加到自选",
  "fund": {
    "code": "161039",
    "name": "易方达消费行业股票"
  }
}
```

---

#### 1.7 Remove from Watchlist

| Item | Value |
|------|-------|
| Endpoint | `DELETE /api/funds/watchlist/{code}` |
| Summary | 删除自选基金 |
| Description | 从自选列表中移除基金 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| code | string | Yes | Fund code (6 digits) |

**Response**

```json
{
  "success": true,
  "message": "基金 161039 已从自选移除"
}
```

---

#### 1.8 Toggle Holding

| Item | Value |
|------|-------|
| Endpoint | `PUT /api/funds/{code}/holding` |
| Summary | 标记/取消持有基金 |
| Description | 将基金标记为持有或取消持有 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| code | string | Yes | Fund code |

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| holding | boolean | Yes | True to mark as holding, False to remove |

**Response**

```json
{
  "success": true,
  "message": "基金 161039 已标记为持有"
}
```

---

### 2. Commodities API

#### 2.1 Get Commodity List

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities` |
| Summary | 获取商品行情 |
| Description | 获取所有支持的商品实时行情 |

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| types | string | No | Optional commodity types, comma-separated |

**Response**

```json
{
  "commodities": [
    {
      "commodity": "gold",
      "symbol": "GC=F",
      "name": "黄金期货",
      "price": 2024.50,
      "change": 12.30,
      "change_percent": 0.61,
      "currency": "USD",
      "exchange": "COMEX",
      "timestamp": "2026-02-20 10:30:00",
      "source": "yfinance",
      "high": 2030.00,
      "low": 2010.00,
      "open": 2015.00,
      "prev_close": 2012.20
    }
  ],
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

#### 2.2 Get Commodity Categories

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities/categories` |
| Summary | 获取商品分类 |
| Description | 获取所有商品分类及其包含的商品实时行情 |

**Response**

```json
{
  "categories": [
    {
      "id": "precious_metal",
      "name": "Precious Metal",
      "icon": "diamond",
      "commodities": [
        {
          "symbol": "GC=F",
          "name": "黄金期货",
          "price": 2024.50,
          "currency": "USD",
          "change": 12.30,
          "changePercent": 0.61,
          "high": 2030.00,
          "low": 2010.00,
          "open": 2015.00,
          "prevClose": 2012.20,
          "source": "yfinance",
          "timestamp": "2026-02-20 10:30:00"
        }
      ]
    }
  ],
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

#### 2.3 Get Commodity History

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities/history/{commodity_type}` |
| Summary | 获取商品历史行情 |
| Description | 获取指定商品的历史行情数据 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| commodity_type | string | Yes | Commodity type: gold, wti, brent, silver, natural_gas, gold_cny |

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| days | int | No | Number of days (default: 30) |

**Response**

```json
{
  "commodity_type": "gold",
  "name": "黄金期货",
  "history": [
    {
      "date": "2026-02-19",
      "price": 2024.50,
      "change": 12.30,
      "changePercent": 0.61,
      "high": 2030.00,
      "low": 2010.00,
      "open": 2015.00,
      "prevClose": 2012.20
    }
  ],
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

#### 2.4 Get Domestic Gold (CNY)

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities/gold/cny` |
| Summary | 获取国内黄金行情 |
| Description | 获取上海黄金交易所 Au99.99 实时行情 |

**Response**

```json
{
  "commodity": "gold_cny",
  "symbol": "au9999",
  "name": "Au99.99",
  "price": 456.78,
  "change_percent": 0.25,
  "currency": "CNY",
  "exchange": "SGE",
  "timestamp": "2026-02-20 10:30:00",
  "source": "akshare",
  "high": 458.00,
  "low": 455.00,
  "open": 456.00,
  "prev_close": 455.65
}
```

---

#### 2.5 Get International Gold

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities/gold/international` |
| Summary | 获取国际黄金行情 |
| Description | 获取 COMEX 黄金期货实时行情 |

---

#### 2.6 Get WTI Oil

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities/oil/wti` |
| Summary | 获取 WTI 原油行情 |
| Description | 获取 WTI 原油期货实时行情 |

---

#### 2.7 Get Commodity by Ticker

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities/by-ticker/{symbol}` |
| Summary | 按 ticker 获取商品行情 |
| Description | 根据 yfinance ticker 符号获取商品实时行情 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| symbol | string | Yes | yfinance ticker symbol (e.g., BTC=F, ETH=F) |

**Response**

```json
{
  "commodity": "btc=f",
  "symbol": "BTC=F",
  "name": "Bitcoin USD",
  "price": 52000.00,
  "currency": "USD",
  "change": 1200.00,
  "change_percent": 2.36,
  "source": "yfinance",
  "timestamp": "2026-02-20 10:30:00 UTC"
}
```

---

#### 2.8 Search Commodities

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities/search` |
| Summary | 搜索商品 |
| Description | 搜索可关注的大宗商品 |

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| q | string | Yes | Search keyword |

**Response**

```json
{
  "query": "gold",
  "results": [
    {
      "symbol": "GC=F",
      "name": "Gold Futures",
      "exchange": "COMEX",
      "currency": "USD",
      "category": "precious_metal"
    }
  ],
  "count": 1,
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

#### 2.9 Get Available Commodities

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities/available` |
| Summary | 获取所有可用商品 |
| Description | 获取所有可关注的大宗商品列表 |

---

#### 2.10 Get Watchlist

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities/watchlist` |
| Summary | 获取关注列表 |
| Description | 获取用户关注的大宗商品列表 |

**Response**

```json
{
  "watchlist": [
    {
      "symbol": "GC=F",
      "name": "黄金期货",
      "category": "precious_metal",
      "added_at": "2026-01-15T10:00:00Z"
    }
  ],
  "count": 1,
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

#### 2.11 Add to Watchlist

| Item | Value |
|------|-------|
| Endpoint | `POST /api/commodities/watchlist` |
| Summary | 添加关注商品 |
| Description | 将商品添加到关注列表 |

**Request Body**

```json
{
  "symbol": "GC=F",
  "name": "黄金期货",
  "category": "precious_metal"
}
```

**Response**

```json
{
  "success": true,
  "message": "商品 GC=F 已添加到关注列表"
}
```

---

#### 2.12 Remove from Watchlist

| Item | Value |
|------|-------|
| Endpoint | `DELETE /api/commodities/watchlist/{symbol}` |
| Summary | 移除关注商品 |
| Description | 将商品从关注列表移除 |

---

#### 2.13 Update Watchlist Commodity

| Item | Value |
|------|-------|
| Endpoint | `PUT /api/commodities/watchlist/{symbol}` |
| Summary | 更新关注商品 |
| Description | 更新关注商品的名称 |

**Request Body**

```json
{
  "name": "新名称"
}
```

---

#### 2.14 Get Watchlist by Category

| Item | Value |
|------|-------|
| Endpoint | `GET /api/commodities/watchlist/category/{category}` |
| Summary | 按分类获取关注 |
| Description | 按分类获取关注的大宗商品列表 |

---

### 3. Indices API

#### 3.1 Get Index List

| Item | Value |
|------|-------|
| Endpoint | `GET /api/indices` |
| Summary | 获取全球市场指数 |
| Description | 获取所有支持的全球市场指数实时行情 |

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| types | string | No | Optional index types, comma-separated |

**Response**

```json
{
  "indices": [
    {
      "index": "shanghai",
      "symbol": "000001.SS",
      "name": "上证指数",
      "price": 3456.78,
      "change": 12.34,
      "change_percent": 0.36,
      "currency": "CNY",
      "exchange": "SSE",
      "timestamp": "2026-02-20 10:30:00",
      "source": "tencent_index",
      "high": 3460.00,
      "low": 3440.00,
      "open": 3445.00,
      "prev_close": 3444.44,
      "region": "China",
      "tradingStatus": "open",
      "marketTime": "2026-02-20 10:30:00",
      "isDelayed": false,
      "dataTimestamp": "2026-02-20 10:30:00",
      "timezone": "Asia/Shanghai"
    }
  ],
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

#### 3.2 Get Single Index

| Item | Value |
|------|-------|
| Endpoint | `GET /api/indices/{index_type}` |
| Summary | 获取单个指数 |
| Description | 根据指数类型获取单个指数的实时行情 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| index_type | string | Yes | Index type: shanghai, shenzhen, hang_seng, nikkei225, dow_jones, nasdaq, sp500, dax, ftse, cac40 |

---

#### 3.3 Get Regions

| Item | Value |
|------|-------|
| Endpoint | `GET /api/indices/regions` |
| Summary | 获取支持的区域 |
| Description | 获取所有支持的指数区域列表 |

**Supported Index Types**

| Index Type | Region | Name |
|------------|--------|------|
| shanghai | China | 上证指数 |
| shenzhen | China | 深证成指 |
| hang_seng | Hong Kong | 恒生指数 |
| nikkei225 | Japan | 日经225 |
| dow_jones | USA | 道琼斯工业指数 |
| nasdaq | USA | 纳斯达克综合指数 |
| sp500 | USA | 标普500 |
| dax | Germany | 德国DAX指数 |
| ftse | UK | 富时100 |
| cac40 | France | 法国CAC40 |

---

### 4. Trading Calendar API

#### 4.1 Get Calendar

| Item | Value |
|------|-------|
| Endpoint | `GET /trading-calendar/calendar/{market}` |
| Summary | 获取市场日历 |
| Description | 获取指定市场在指定年份的交易日期历 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| market | string | Yes | Market code: china, hk, usa, japan, uk, germany, france |

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| year | int | No | Year (default: current year) |
| start_date | string | No | Start date (YYYY-MM-DD) |
| end_date | string | No | End date (YYYY-MM-DD) |

**Response**

```json
{
  "year": 2025,
  "market": "china",
  "total_trading_days": 250,
  "total_holidays": 115,
  "days": [
    {
      "date": "2025-01-01",
      "is_trading_day": false,
      "holiday_name": "元旦"
    }
  ]
}
```

---

#### 4.2 Is Trading Day

| Item | Value |
|------|-------|
| Endpoint | `GET /trading-calendar/is-trading-day/{market}` |
| Summary | 判断是否为交易日 |
| Description | 判断指定市场在指定日期是否为交易日 |

**Path Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| market | string | Yes | Market code |

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| check_date | string | No | Date to check (YYYY-MM-DD, default: today) |

**Response**

```json
{
  "market": "china",
  "date": "2026-02-20",
  "is_trading_day": true
}
```

---

#### 4.3 Next Trading Day

| Item | Value |
|------|-------|
| Endpoint | `GET /trading-calendar/next-trading-day/{market}` |
| Summary | 获取下一个交易日 |
| Description | 获取指定日期之后的下一个交易日 |

---

#### 4.4 Market Status

| Item | Value |
|------|-------|
| Endpoint | `GET /trading-calendar/market-status` |
| Summary | 获取多市场状态 |
| Description | 批量获取多个市场的当前交易状态 |

**Query Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| markets | string | No | Comma-separated markets (default: all) |

**Response**

```json
{
  "china": {
    "is_open": true,
    "date": "2026-02-20",
    "next_trading_day": "2026-02-21",
    "market": "china"
  },
  "usa": {
    "is_open": false,
    "date": "2026-02-20",
    "next_trading_day": "2026-02-21",
    "market": "usa"
  }
}
```

---

#### 4.5 List Markets

| Item | Value |
|------|-------|
| Endpoint | `GET /trading-calendar/markets` |
| Summary | 获取支持的市场列表 |
| Description | 获取所有支持的交易市场及其描述 |

**Supported Markets**

| Market | Description |
|--------|-------------|
| china | A股 (上海/深圳) |
| hk | 港股 |
| usa | 美股 |
| japan | 日股 |
| uk | 英股 |
| germany | 德股 |
| france | 法股 |
| sge | 上海黄金交易所 |
| comex | COMEX |
| cme | CME |
| lbma | LBMA |

---

### 5. Health Check API

#### 5.1 Simple Health Check

| Item | Value |
|------|-------|
| Endpoint | `GET /api/health/simple` |
| Summary | 健康检查 (简单) |

**Response**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

#### 5.2 Detailed Health Check

| Item | Value |
|------|-------|
| Endpoint | `GET /api/health` |
| Summary | 健康检查 (详细) |

**Response**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-02-20T10:30:00Z",
  "total_sources": 5,
  "healthy_count": 4,
  "unhealthy_count": 1,
  "data_sources": [
    {
      "source": "eastmoney",
      "status": "healthy",
      "response_time_ms": 120.5
    }
  ]
}
```

---

### 6. DataSource API

#### 6.1 Get DataSource Statistics

| Item | Value |
|------|-------|
| Endpoint | `GET /api/datasource/statistics` |
| Summary | 获取数据源请求统计 |

**Response**

```json
{
  "total_requests": 1000,
  "successful_requests": 950,
  "failed_requests": 50,
  "sources": {
    "eastmoney": {
      "requests": 500,
      "success_rate": 0.98
    }
  },
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

#### 6.2 Get DataSource Health

| Item | Value |
|------|-------|
| Endpoint | `GET /api/datasource/health` |
| Summary | 获取数据源健康状态 |

---

#### 6.3 Get Registered Sources

| Item | Value |
|------|-------|
| Endpoint | `GET /api/datasource/sources` |
| Summary | 获取已注册的数据源列表 |

---

### 7. Cache API

#### 7.1 Get Cache Statistics

| Item | Value |
|------|-------|
| Endpoint | `GET /api/cache/stats` |
| Summary | 获取缓存统计信息 |

**Response**

```json
{
  "total_entries": 1000,
  "memory_cache": 500,
  "database_cache": 450,
  "expired": 50,
  "timestamp": "2026-02-20T10:30:00Z"
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource not found |
| 500 | Internal Server Error |

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2026-02-20 | Initial API specification |

---

## Notes

- All timestamps are in UTC unless otherwise specified
- Some data sources may have delays (e.g., Tencent delayed indices)
- QDII/FOF funds may not have real-time estimates
- Response times and data freshness depend on external data sources
