# 大宗商品分类扩展设计

## 1. 概述

为大宗商品模块添加分类功能，支持按贵金属、能源、基本金属三类展示，并使用 SQLite 数据库存储历史数据。

## 2. 现状分析

### 2.1 当前实现

- **数据源**: yfinance + AKShare
- **商品类型**: 黄金(国内/国际)、WTI原油、布伦特原油、白银、天然气
- **缓存**: 内存缓存(60s) + 文件缓存(300s)
- **存储**: 无数据库存储

### 2.2 问题

- 商品缺乏分类，扁平展示
- 数据未持久化到 SQLite，无法查看历史

## 3. 设计方案

### 3.1 商品分类

| 分类 | ID | 商品 | 数据源 |
|------|-----|------|--------|
| 贵金属 | `precious_metal` | 黄金(COMEX)、黄金(上海)、白银、铂金、钯金 | yfinance + akshare |
| 能源化工 | `energy` | WTI原油、布伦特原油、天然气 | yfinance |
| 基本金属 | `base_metal` | 铜、铝、锌、镍 | yfinance |

### 3.2 数据库设计

#### commodity_cache 表

```sql
CREATE TABLE IF NOT EXISTS commodity_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commodity_type TEXT NOT NULL,      -- commodity_type 标识 (gold, wti, etc.)
    symbol TEXT,                       -- 交易所代码 (GC=F, CL=F)
    name TEXT,                         -- 商品名称
    price REAL,                        -- 当前价格
    change REAL,                       -- 涨跌
    change_percent REAL,               -- 涨跌幅
    currency TEXT,                     -- 货币
    exchange TEXT,                     -- 交易所
    high REAL,                         -- 最高价
    low REAL,                          -- 最低价
    open REAL,                         -- 开盘价
    prev_close REAL,                   -- 昨收价
    source TEXT,                       -- 数据源 (yfinance/akshare)
    timestamp TEXT NOT NULL,           -- 数据时间
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX idx_commodity_type ON commodity_cache(commodity_type);
CREATE INDEX idx_timestamp ON commodity_cache(timestamp);
```

### 3.3 API 设计

#### 新增端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/commodities/categories` | GET | 获取分类列表及商品 |
| `/api/commodities/history/{type}` | GET | 获取商品历史K线 |
| `/api/commodities` | GET | 支持 `?category=xxx` 筛选 |

#### /api/commodities/categories 响应

```json
{
  "categories": [
    {
      "id": "precious_metal",
      "name": "贵金属",
      "icon": "diamond",
      "commodities": [
        {
          "symbol": "GC=F",
          "name": "黄金 (COMEX)",
          "price": 2050.30,
          "currency": "USD",
          "changePercent": 1.23,
          "high": 2060.00,
          "low": 2035.50,
          "open": 2040.00,
          "prevClose": 2025.00,
          "source": "yfinance",
          "timestamp": "2026-02-12T20:00:00Z"
        }
      ]
    },
    {
      "id": "energy",
      "name": "能源化工",
      "icon": "flame",
      "commodities": [...]
    },
    {
      "id": "base_metal",
      "name": "基本金属",
      "icon": "cube",
      "commodities": [...]
    }
  ],
  "timestamp": "2026-02-12T20:00:00Z"
}
```

### 3.4 后端模块

#### 新增文件

```
src/db/
├── database.py           # 现有，SQLite 连接管理
└── commodity_repo.py     # 新增，商品数据访问层
```

#### commodity_repo.py

```python
class CommodityRepository:
    """商品数据访问层"""

    async def save(commodity: dict) -> None:
        """保存商品数据到数据库"""

    async def get_latest(commodity_type: str) -> dict | None:
        """获取最新商品数据"""

    async def get_history(
        self,
        commodity_type: str,
        days: int = 30,
        interval: str = "1d"
    ) -> list[dict]:
        """获取历史K线数据"""

    async def cleanup_expired(self, ttl_hours: int = 24) -> int:
        """清理过期数据"""
```

### 3.5 前端设计

#### 类型定义

```typescript
interface CommodityCategory {
  id: string;
  name: string;
  icon: string;
  commodities: Commodity[];
}

interface CommodityCategoriesResponse {
  categories: CommodityCategory[];
  timestamp: string;
}

interface CommodityHistoryResponse {
  commodity_type: string;
  history: OHLCV[];
  timestamp: string;
}
```

#### Store 变更

```typescript
// commodityStore.ts
interface CommodityState {
  categories: CommodityCategory[];
  activeCategory: string;
  // 保留现有字段兼容旧接口
  commodities: Commodity[];
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

async function fetchCategories(): Promise<void>
async function fetchHistory(type: string, days: number): Promise<OHLCV[]>
```

#### 组件结构

```
CommodityView.vue (新增)
├── CommodityTabs.vue (新增)  -- Tab 切换
├── CommodityList.vue (改造)  -- 按分类展示
└── CommodityCard.vue (复用)  -- 保持现有样式
```

### 3.6 缓存策略

```
请求 → 内存缓存 (60s) → 数据库 → 外部 API
                ↓
           命中返回
                ↓
           异步更新数据库
```

#### 优先级

1. 内存缓存 (60s)
2. SQLite 数据库 (24h)
3. 外部 API (yfinance/akshare)

### 3.7 配置变更

commodity.yaml 新增分类配置：

```yaml
commodities:
  categories:
    - id: precious_metal
      name: 贵金属
      icon: diamond
      items:
        - gold        # COMEX 黄金
        - gold_cny    # 上海黄金
        - silver      # 白银
        - platinum    # 铂金 (预留)
        - palladium   # 钯金 (预留)
    - id: energy
      name: 能源化工
      icon: flame
      items:
        - wti         # WTI 原油
        - brent       # 布伦特原油
        - natural_gas # 天然气
    - id: base_metal
      name: 基本金属
      icon: cube
      items:
        - copper      # 铜
        - aluminum    # 铝
        - zinc        # 锌
        - nickel      # 镍
```

## 4. 实现计划

### 阶段 1: 后端基础

- [ ] 创建 commodity_repo.py
- [ ] 实现数据库表和 CRUD 操作
- [ ] 修改 commodity_source.py 支持数据库读写
- [ ] 新增 /api/commodities/categories 端点

### 阶段 2: API 扩展

- [ ] 新增 /api/commodities/history/{type} 端点
- [ ] 完善 /api/commodities 端点支持分类筛选
- [ ] 添加缓存预热和清理任务

### 阶段 3: 前端实现

- [ ] 更新 TypeScript 类型定义
- [ ] 改造 commodityStore 支持分类
- [ ] 新增 CommodityTabs 组件
- [ ] 新增 CommodityView 组件
- [ ] 适配后端分类 API

## 5. 注意事项

- 保持向后兼容，现有 API 端点不变
- 数据库表在应用启动时自动创建
- 预留商品(铂金、钯金等)暂不实现数据源
- 前端组件保持现有样式，仅添加分类切换
