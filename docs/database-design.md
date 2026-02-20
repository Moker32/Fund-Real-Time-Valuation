# 数据库设计文档

## 概述

本文档描述基金实时估值应用的 SQLite 数据库设计。数据库负责存储基金配置、商品配置、历史净值数据、新闻缓存和实时行情数据。

**数据库位置**: `~/.fund-tui/fund_data.db`

## 技术栈

- **数据库**: SQLite 3
- **Python 驱动**: sqlite3
- **连接管理**: 上下文管理器 (`with` 语句)
- **行工厂**: `sqlite3.Row` (字典式访问)

---

## 表结构

### 1. fund_config (基金配置表)

存储用户自选基金和持仓信息。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| code | TEXT | PRIMARY KEY | 基金代码 |
| name | TEXT | NOT NULL | 基金名称 |
| watchlist | INTEGER | DEFAULT 1 | 是否在自选列表 (1=是, 0=否) |
| shares | REAL | DEFAULT 0 | 持有份额 |
| cost | REAL | DEFAULT 0 | 成本价 |
| is_hold | INTEGER | DEFAULT 0 | 是否标记为持有 (1=持有, 0=不持有) |
| sector | TEXT | DEFAULT '' | 板块标注 |
| notes | TEXT | DEFAULT '' | 备注 |
| created_at | TEXT | | 创建时间 (ISO 格式) |
| updated_at | TEXT | | 更新时间 (ISO 格式) |

**索引**:
- PRIMARY KEY (code)

**默认值**:
- 自选基金: `161039` (富国中证新能源汽车指数), `161725` (招商中证白酒指数), `110022` (易方达消费行业股票)

---

### 2. commodity_config (商品配置表)

存储用户关注的商品列表。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| symbol | TEXT | PRIMARY KEY | 商品代码 (如 gold, wti, btc) |
| name | TEXT | NOT NULL | 商品名称 |
| source | TEXT | DEFAULT 'akshare' | 数据源 |
| enabled | INTEGER | DEFAULT 1 | 是否启用 (1=启用, 0=禁用) |
| notes | TEXT | DEFAULT '' | 备注 |
| created_at | TEXT | | 创建时间 |
| updated_at | TEXT | | 更新时间 |

**索引**:
- PRIMARY KEY (symbol)

---

### 3. fund_history (基金净值历史表)

存储基金单位净值和累计净值历史数据。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增 ID |
| fund_code | TEXT | NOT NULL, FK | 基金代码 |
| fund_name | TEXT | | 基金名称 |
| date | TEXT | NOT NULL | 净值日期 (YYYY-MM-DD) |
| unit_net_value | REAL | | 单位净值 |
| accumulated_net_value | REAL | | 累计净值 |
| estimated_value | REAL | | 估算净值 |
| growth_rate | REAL | | 增长率 (%) |
| fetched_at | TEXT | | 数据抓取时间 |

**约束**:
- UNIQUE (fund_code, date)
- FOREIGN KEY (fund_code) REFERENCES fund_config(code) ON DELETE CASCADE

**索引**:
- `idx_fund_history_code_date` ON (fund_code, date)

---

### 4. fund_intraday_cache (基金日内分时缓存表)

存储基金当日分时估值数据，用于实时行情展示。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增 ID |
| fund_code | TEXT | NOT NULL | 基金代码 |
| date | TEXT | NOT NULL | 日期 (YYYY-MM-DD) |
| time | TEXT | NOT NULL | 时间 (HH:mm) |
| price | REAL | NOT NULL | 估算净值 |
| change_rate | REAL | | 涨跌率 (%) |
| fetched_at | TEXT | | 抓取时间 |

**约束**:
- UNIQUE (fund_code, date, time)

**索引**:
- `idx_fund_intraday_code` ON (fund_code, date)

---

### 5. fund_daily_cache (基金每日缓存表)

存储基金每日基础数据，支持展示近一周历史走势。

| 字段 |类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增 ID |
| fund_code | TEXT | NOT NULL | 基金代码 |
| date | TEXT | NOT NULL | 日期 (YYYY-MM-DD) |
| unit_net_value | REAL | | 单位净值 |
| accumulated_net_value | REAL | | 累计净值 |
| estimated_value | REAL | | 估算净值 |
| change_rate | REAL | | 日增长率 (%) |
| fetched_at | TEXT | | 抓取时间 |

**约束**:
- UNIQUE (fund_code, date)

**索引**:
- `idx_fund_daily_code` ON (fund_code, date)

---

### 6. fund_basic_info (基金基本信息表)

存储基金的详细信息（名称、类型、规模、管理人等）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| code | TEXT | PRIMARY KEY | 基金代码 |
| name | TEXT | | 基金全称 |
| short_name | TEXT | | 基金简称 |
| type | TEXT | | 基金类型 |
| fund_key | TEXT | | 基金关键字 |
| net_value | REAL | | 单位净值 |
| net_value_date | TEXT | | 净值日期 |
| establishment_date | TEXT | | 成立日期 |
| manager | TEXT | | 基金管理人 |
| custodian | TEXT | | 基金托管人 |
| fund_scale | REAL | | 基金规模 |
| scale_date | TEXT | | 规模日期 |
| risk_level | TEXT | | 风险等级 |
| full_name | TEXT | | 基金完整名称 |
| fetched_at | TEXT | | 抓取时间 |
| updated_at | TEXT | | 更新时间 |

**索引**:
- PRIMARY KEY (code)

---

### 7. commodity_cache (商品行情缓存表)

存储大宗商品和加密货币的实时行情数据。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增 ID |
| commodity_type | TEXT | NOT NULL | 商品类型 (如 gold, wti, btc) |
| symbol | TEXT | | 交易所代码 |
| name | TEXT | | 商品名称 |
| price | REAL | DEFAULT 0 | 当前价格 |
| change | REAL | DEFAULT 0 | 涨跌额 |
| change_percent | REAL | DEFAULT 0 | 涨跌幅 (%) |
| currency | TEXT | DEFAULT 'USD' | 货币单位 |
| exchange | TEXT | | 交易所 |
| high | REAL | DEFAULT 0 | 最高价 |
| low | REAL | DEFAULT 0 | 最低价 |
| open | REAL | DEFAULT 0 | 开盘价 |
| prev_close | REAL | DEFAULT 0 | 昨收价 |
| source | TEXT | | 数据源 |
| timestamp | TEXT | NOT NULL | 数据时间戳 |
| created_at | TEXT | | 入库时间 |

**索引**:
- `idx_commodity_type` ON (commodity_type)
- `idx_commodity_timestamp` ON (created_at)

---

### 8. news_cache (新闻缓存表)

存储财经新闻的缓存数据。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增 ID |
| title | TEXT | NOT NULL | 新闻标题 |
| url | TEXT | UNIQUE | 新闻链接 |
| source | TEXT | | 来源 |
| category | TEXT | | 分类 |
| publish_time | TEXT | | 发布时间 |
| content | TEXT | | 新闻内容 |
| fetched_at | TEXT | | 抓取时间 |
| created_at | TEXT | DEFAULT (datetime('now')) | 创建时间 |

**索引**:
- `idx_news_cache_category` ON (category)
- `idx_news_cache_fetched_at` ON (fetched_at)

---

## 数据模型 (Python)

### Dataclass 定义

```python
@dataclass
class FundConfig:
    code: str
    name: str
    watchlist: int = 1
    shares: float = 0.0
    cost: float = 0.0
    is_hold: int = 0
    sector: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

@dataclass
class CommodityConfig:
    symbol: str
    name: str
    source: str = "akshare"
    enabled: int = 1
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

@dataclass
class FundHistoryRecord:
    id: int | None = None
    fund_code: str = ""
    fund_name: str = ""
    date: str = ""
    unit_net_value: float = 0.0
    accumulated_net_value: float | None = None
    estimated_value: float | None = None
    growth_rate: float | None = None
    fetched_at: str = ""

@dataclass
class FundIntradayRecord:
    id: int | None = None
    fund_code: str = ""
    date: str = ""
    time: str = ""
    price: float = 0.0
    change_rate: float | None = None
    fetched_at: str = ""

@dataclass
class FundDailyRecord:
    id: int | None = None
    fund_code: str = ""
    date: str = ""
    unit_net_value: float | None = None
    accumulated_net_value: float | None = None
    estimated_value: float | None = None
    change_rate: float | None = None
    fetched_at: str = ""

@dataclass
class FundBasicInfo:
    code: str = ""
    name: str = ""
    short_name: str = ""
    type: str = ""
    fund_key: str = ""
    net_value: float | None = None
    net_value_date: str = ""
    establishment_date: str = ""
    manager: str = ""
    custodian: str = ""
    fund_scale: float | None = None
    scale_date: str = ""
    risk_level: str = ""
    full_name: str = ""
    fetched_at: str = ""
    updated_at: str = ""

@dataclass
class CommodityCacheRecord:
    id: int | None = None
    commodity_type: str = ""
    symbol: str = ""
    name: str = ""
    price: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0
    currency: str = "USD"
    exchange: str = ""
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0
    prev_close: float = 0.0
    source: str = ""
    timestamp: str = ""
    created_at: str = ""

@dataclass
class NewsRecord:
    title: str
    url: str
    source: str
    category: str
    publish_time: str
    content: str = ""
    fetched_at: str = ""
```

---

## DAO 模式

数据库访问采用 DAO (Data Access Object) 模式，每个表对应一个 DAO 类。

### DAO 类列表

| DAO 类 | 职责 |
|--------|------|
| `DatabaseManager` | 连接管理、表初始化、迁移 |
| `ConfigDAO` | 基金/商品配置 CRUD |
| `FundHistoryDAO` | 基金净值历史存取 |
| `FundIntradayCacheDAO` | 日内分时缓存存取 |
| `FundDailyCacheDAO` | 每日缓存存取 |
| `FundBasicInfoDAO` | 基金基本信息存取 |
| `CommodityCacheDAO` | 商品行情缓存存取 |
| `CommodityCategoryDAO` | 商品分类查询 |
| `NewsDAO` | 新闻缓存存取 |

---

## 缓存策略

### 缓存层级

1. **内存缓存** → **SQLite 数据库** → **外部 API**

### 缓存 TTL

| 缓存类型 | 默认 TTL | 说明 |
|----------|----------|------|
| 日内分时 | 0 (禁用) | 可配置 |
| 每日缓存 | 0 (禁用) | 可配置 |
| 商品行情 | 24 小时 | 可配置 |
| 新闻缓存 | 24 小时 | 清理过期新闻 |

### 缓存清理

- `FundIntradayCacheDAO.cleanup_expired_cache()` - 清理过期日内缓存
- `FundDailyCacheDAO.cleanup_expired_cache(days=7)` - 清理过期每日缓存
- `CommodityCacheDAO.cleanup_expired(hours=24)` - 清理过期商品缓存
- `NewsDAO.cleanup_old_news(hours=24)` - 清理过期新闻

---

## 数据库迁移

数据库支持自动迁移，通过 `DatabaseManager._migrate_database()` 方法检查并添加缺失的列。

**已完成的迁移**:
1. `fund_config` 表添加 `is_hold` 列
2. `fund_intraday_cache` 表添加 `date` 列

---

## 备份与维护

### 备份

```python
db_manager.backup("/path/to/backup.db")
```

### 碎片整理

```python
db_manager.vacuum()
```

### 文件大小

```python
db_manager.get_size()  # 返回字节数
```

---

## 设计规范

### 命名约定

- 表名: snake_case (如 `fund_config`)
- 字段名: snake_case (如 `fund_code`)
- 类名: PascalCase (如 `DatabaseManager`)
- 文件名: snake_case (如 `database.py`)

### 布尔值处理

SQLite 原生不支持布尔类型，使用 INTEGER (0/1) 存储，通过 `@property` 转换:

```python
watchlist: int = 1  # SQLite 存储

@property
def is_watchlist(self) -> bool:
    return bool(self.watchlist)  # Python 使用
```

### 时间戳格式

- 使用 ISO 格式: `datetime.now().isoformat()`
- 示例: `2026-02-20T22:30:00`

### 错误处理

- 外部调用用 try/except 包装
- 使用 `logger.error()` / `logger.warning()` 记录日志
- 禁止 bare `except:`

---

## ER 关系图

```
┌─────────────────────┐       ┌─────────────────────┐
│    fund_config     │       │   commodity_config  │
├─────────────────────┤       ├─────────────────────┤
│ *code (PK)         │       │ *symbol (PK)        │
│ name               │       │ name                │
│ watchlist          │       │ source              │
│ shares             │       │ enabled             │
│ cost               │       │ notes               │
│ is_hold            │       │ created_at          │
│ sector             │       │ updated_at          │
│ notes              │       └─────────────────────┘
│ created_at         │
│ updated_at         │
└─────────┬───────────┘
          │ 1:N
          ▼
┌─────────────────────┐
│    fund_history     │
├─────────────────────┤
│ id (PK)            │
│ fund_code (FK)     │
│ fund_name          │
│ date               │
│ unit_net_value     │
│ accumulated_net_.. │
│ estimated_value    │
│ growth_rate        │
│ fetched_at         │
└─────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐
│fund_intraday_cache │  │  fund_daily_cache   │
├─────────────────────┤  ├─────────────────────┤
│ id (PK)            │  │ id (PK)            │
│ fund_code          │  │ fund_code          │
│ date               │  │ date               │
│ time               │  │ unit_net_value     │
│ price              │  │ accumulated_net_.. │
│ change_rate        │  │ estimated_value    │
│ fetched_at         │  │ change_rate        │
└─────────────────────┘  │ fetched_at         │
                        └─────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐
│  fund_basic_info   │  │  commodity_cache    │
├─────────────────────┤  ├─────────────────────┤
│ *code (PK)         │  │ id (PK)            │
│ name               │  │ commodity_type     │
│ short_name         │  │ symbol             │
│ type               │  │ name               │
│ fund_key           │  │ price              │
│ net_value          │  │ change             │
│ net_value_date     │  │ change_percent     │
│ establishment_date │  │ currency           │
│ manager            │  │ exchange           │
│ custodian          │  │ high               │
│ fund_scale         │  │ low                │
│ scale_date         │  │ open               │
│ risk_level         │  │ prev_close         │
│ full_name          │  │ source             │
│ fetched_at         │  │ timestamp          │
│ updated_at         │  │ created_at         │
└─────────────────────┘  └─────────────────────┘

┌─────────────────────┐
│    news_cache      │
├─────────────────────┤
│ id (PK)            │
│ title              │
│ url                │
│ source             │
│ category           │
│ publish_time       │
│ content            │
│ fetched_at         │
│ created_at         │
└─────────────────────┘
```

---

## 附录

### 默认数据

**默认自选基金**:
- `161039` - 富国中证新能源汽车指数
- `161725` - 招商中证白酒指数(LOF)
- `110022` - 易方达消费行业股票

**默认关注商品**:
- `gold_cny` - Au99.99 (上海黄金) - akshare
- `gold` - 黄金 (COMEX) - yfinance
- `wti` - WTI原油 - yfinance
- `silver` - 白银 - yfinance
- `natural_gas` - 天然气 - yfinance

### 商品分类

| 分类 | 标识 | 商品 |
|------|------|------|
| 贵金属 | precious_metal | gold, gold_cny, silver, platinum, palladium |
| 能源化工 | energy | wti, brent, natural_gas |
| 基本金属 | base_metal | copper, aluminum, zinc, nickel |
| 农产品 | agriculture | soybean, corn, wheat, coffee, sugar |
| 加密货币 | crypto | btc, btc_futures, eth, eth_futures |
