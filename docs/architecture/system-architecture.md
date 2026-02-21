# 基金实时估值系统架构设计

## 1. 系统概述

### 1.1 项目简介

**基金实时估值** 是一个基于 Vue 3 + FastAPI 的金融数据监控 Web 应用，提供基金净值实时估算、大宗商品行情、全球市场指数、财经新闻等功能。项目采用前后端分离架构，后端使用 Python FastAPI 框架，前端使用 Vue 3 + TypeScript + Vite。

### 1.2 核心功能

| 功能模块 | 描述 |
|---------|------|
| 基金估值 | 实时获取基金净值估算，支持自选管理、持仓管理 |
| 商品行情 | 黄金、原油、白银等大宗商品实时价格 |
| 全球指数 | 美股、A股、港股、日经等主要市场指数 |
| 行业板块 | A股行业板块和概念板块行情 |
| 财经新闻 | 多源财经新闻聚合 |
| 舆情数据 | 经济新闻、微博情绪指标 |
| 交易日历 | 全球多市场交易/休市日查询 |
| 债券行情 | 国债、企业债收益率 |
| 加密货币 | BTC、ETH 等主流加密货币价格 |

### 1.3 技术栈

#### 后端技术栈

| 类别 | 技术 | 版本 |
|-----|------|------|
| Web 框架 | FastAPI | ≥0.104.0 |
| ASGI 服务器 | Uvicorn | ≥0.24.0 |
| HTTP 客户端 | httpx | ≥0.24.0 |
| 金融数据 | akshare | ≥1.10.0 |
| 金融数据 | yfinance | ≥0.2.0 |
| 数据解析 | BeautifulSoup | ≥4.12.0 |
| 配置管理 | PyYAML | ≥6.0 |
| 节日日历 | holidays | ≥0.40 |
| 数据库 | SQLite3 | 内置 |
| 测试 | pytest | ≥7.0.0 |
| 代码检查 | ruff | - |

#### 前端技术栈

| 类别 | 技术 | 版本 |
|-----|------|------|
| 框架 | Vue 3 | ≥3.5.0 |
| 构建工具 | Vite | ≥7.0.0 |
| 语言 | TypeScript | ~5.9.0 |
| 路由 | Vue Router | ≥5.0.0 |
| 状态管理 | Pinia | ≥3.0.0 |
| HTTP 客户端 | Axios | ≥1.13.0 |
| 图表 | uPlot | ≥1.6.32 |
| 图表 | lightweight-charts | ≥5.1.0 |
| 时间处理 | dayjs | ≥1.11.0 |
| 样式 | Sass | ≥1.97.0 |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              客户端 (Browser)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Vue 3 + TypeScript + Vite                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │   │
│  │  │  Views   │  │Components│  │  Stores  │  │    Router        │  │   │
│  │  │  (页面)  │  │ (组件)   │  │ (Pinia)  │  │   (Vue Router)   │  │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │   │
│  │       └──────────────┴──────────────┴─────────────────┘            │   │
│  │                                  │                                    │   │
│  │                         ┌────────▼────────┐                          │   │
│  │                         │   API Client   │                          │   │
│  │                         │   (Axios)      │                          │   │
│  │                         └────────┬────────┘                          │   │
│  └──────────────────────────────────┼──────────────────────────────────┘   │
└──────────────────────────────────────┼────────────────────────────────────┘
                                       │ HTTP/JSON
┌──────────────────────────────────────┼────────────────────────────────────┐
│                              服务端 (Server)                               │
│  ┌──────────────────────────────────▼──────────────────────────────────┐  │
│  │                      FastAPI Application                             │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │                      API Routes                               │   │  │
│  │  │  funds │ commodities │ indices │ sectors │ news │ sentiment  │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │                    Exception Handlers                        │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────┬──────────────────────────────────┘  │
│                                    │                                       │
│  ┌─────────────────────────────────▼────────────────────────────────┐   │
│  │                    Data Source Manager                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │   │
│  │  │  Health     │  │   Cache      │  │   Warmer    │            │   │
│  │  │  Checker    │  │   Manager    │  │             │            │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │   │
│  └──────────────────────────────────┬────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────▼────────────────────────────────┐   │
│  │                    Data Sources (Multi-Source)                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│  │  │ akshare  │  │  yfinance │  │   Sina   │  │   East   │       │   │
│  │  │          │  │           │  │  Finance │  │  Money   │       │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │ └──────────────────────────────────   │
│ ┬────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────▼────────────────────────────────┐   │
│  │                       Persistence Layer                           │   │
│  │  ┌─────────────────────┐  ┌─────────────────────────────────┐  │   │
│  │  │    SQLite Database   │  │         YAML Config Files      │  │   │
│  │  │  ~/.fund-tui/*.db    │  │      ~/.fund-tui/*.yaml         │  │   │
│  │  └─────────────────────┘  └─────────────────────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 分层架构

系统采用经典的分层架构设计：

| 层次 | 职责 | 关键组件 |
|-----|------|---------|
| **表现层** | 用户界面交互 | Vue 3 组件、Pinia Store、Router |
| **应用层** | 请求路由、业务编排 | FastAPI Routes、Dependencies |
| **领域层** | 业务逻辑、数据处理 | DataSource、Aggregator、Manager |
| **数据层** | 数据获取、持久化 | DataSources、Database、Config |

---

## 3. 后端架构

### 3.1 项目结构

```
fund-real-time-valuation/
├── run_app.py                    # 应用入口
├── pyproject.toml                # Python 项目配置
├── package.json                  # pnpm 工作空间配置
├── requirements.txt              # Python 依赖
│
├── api/                          # FastAPI 应用
│   ├── main.py                   # FastAPI 应用实例、生命周期管理
│   ├── dependencies.py           # 依赖注入
│   ├── models.py                 # Pydantic 数据模型
│   └── routes/                   # API 路由
│       ├── __init__.py
│       ├── funds.py              # 基金 API
│       ├── commodities.py         # 商品 API
│       ├── indices.py            # 指数 API
│       ├── sectors.py            # 板块 API
│       ├── overview.py           # 市场概览 API
│       ├── news.py               # 新闻 API
│       ├── sentiment.py          # 舆情 API
│       ├── stocks.py             # 股票 API
│       ├── bonds.py              # 债券 API
│       ├── trading_calendar.py   # 交易日历 API
│       ├── cache.py              # 缓存管理 API
│       └── datasource.py         # 数据源管理 API
│
├── src/                          # 核心业务逻辑
│   ├── datasources/              # 数据源层
│   │   ├── __init__.py
│   │   ├── base.py               # 数据源基类、结果定义
│   │   ├── manager.py            # 数据源管理器
│   │   ├── aggregator.py         # 数据聚合器
│   │   ├── fund_source.py        # 基金数据源
│   │   ├── commodity_source.py   # 商品数据源
│   │   ├── index_source.py       # 指数数据源
│   │   ├── sector_source.py      # 板块数据源
│   │   ├── stock_source.py       # 股票数据源
│   │   ├── bond_source.py        # 债券数据源
│   │   ├── crypto_source.py      # 加密货币数据源
│   │   ├── news_source.py        # 新闻数据源
│   │   ├── sentiment_source.py   # 舆情数据源
│   │   ├── trading_calendar_source.py  # 交易日历数据源
│   │   ├── cache.py              # 缓存管理
│   │   ├── cache_warmer.py      # 缓存预热
│   │   ├── cache_cleaner.py      # 缓存清理
│   │   ├── health.py             # 健康检查
│   │   └── gateway.py            # API 网关
│   │
│   ├── db/                       # 数据库层
│   │   ├── __init__.py
│   │   ├── database.py           # SQLite 数据库管理
│   │   └── commodity_repo.py     # 商品数据仓库
│   │
│   ├── config/                   # 配置层
│   │   ├── __init__.py
│   │   ├── commodities_config.py # 商品配置
│   │   └── ...
│   │
│   └── utils/                    # 工具层
│       ├── __init__.py
│       ├── log_buffer.py         # 日志缓冲
│       └── ...
│
├── web/                          # Vue 3 前端
│   ├── src/
│   │   ├── main.ts               # 前端入口
│   │   ├── App.vue               # 根组件
│   │   ├── router/               # 路由配置
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── components/           # 组件
│   │   ├── views/                # 页面视图
│   │   ├── api/                  # API 调用
│   │   ├── utils/                # 工具函数
│   │   └── types/                # TypeScript 类型
│   ├── package.json
│   └── vite.config.ts
│
└── tests/                        # 测试
    └── ...
```

### 3.2 API 路由架构

API 路由采用模块化设计，每个功能模块对应一个独立的路由文件：

```
api/routes/
├── __init__.py          # 导出所有路由
├── funds.py             # 基金相关接口
│   GET /api/funds
│   GET /api/funds/{fund_code}
│   GET /api/funds/{fund_code}/estimate
│   GET /api/funds/{fund_code}/history
│   GET /api/funds/{fund_code}/intraday
│   POST /api/funds/watchlist
│   DELETE /api/funds/watchlist/{code}
│   PUT /api/funds/{code}/holding
│
├── commodities.py        # 商品相关接口
│   GET /api/commodities
│   GET /api/commodities/{type}
│   GET /api/commodities/gold/cny
│   GET /api/commodities/gold/international
│   GET /api/commodities/oil/wti
│   GET /api/commodities/oil/brent
│   GET /api/commodities/silver
│   GET /api/commodities/crypto
│   POST /api/commodities/watchlist
│   DELETE /api/commodities/watchlist/{symbol}
│
├── indices.py            # 指数相关接口
│   GET /api/indices
│   GET /api/indices/{index_type}
│   GET /api/indices/regions
│
├── sectors.py            # 板块相关接口
│   GET /api/sectors
│   GET /api/sectors/industry
│   GET /api/sectors/concept
│
├── news.py               # 新闻相关接口
│   GET /api/news
│   GET /api/news/categories
│
├── sentiment.py          # 舆情相关接口
│   GET /api/sentiment/economic
│   GET /api/sentiment/weibo
│   GET /api/sentiment/all
│
├── stocks.py             # 股票相关接口
│   GET /api/stocks
│   GET /api/stocks/{symbol}
│
├── bonds.py              # 债券相关接口
│   GET /api/bonds
│   GET /api/bonds/{bond_type}
│
├── trading_calendar.py   # 交易日历接口
│   GET /trading-calendar/calendar/{market}
│   GET /trading-calendar/is-trading-day/{market}
│   GET /trading-calendar/next-trading-day/{market}
│   GET /trading-calendar/market-status
│
├── cache.py              # 缓存管理接口
│   GET /api/cache/stats
│   DELETE /api/cache
│
└── datasource.py         # 数据源管理接口
    GET /api/datasource/statistics
    GET /api/datasource/health
    GET /api/datasource/sources
```

### 3.3 数据源架构

#### 3.3.1 数据源基类

所有数据源继承自 `DataSource` 抽象基类：

```python
# src/datasources/base.py
class DataSource(ABC):
    name: str
    source_type: DataSourceType
    
    @abstractmethod
    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        """获取数据"""
        pass
    
    def get_status(self) -> str:
        """获取数据源状态"""
        pass
```

#### 3.3.2 数据源类型枚举

```python
class DataSourceType(Enum):
    FUND = "fund"           # 基金
    COMMODITY = "commodity" # 商品
    NEWS = "news"           # 新闻
    SECTOR = "sector"       # 板块
    STOCK = "stock"         # 股票
    BOND = "bond"           # 债券
    CRYPTO = "crypto"       # 加密货币
```

#### 3.3.3 数据源管理器

`DataSourceManager` 是核心的调度组件，提供以下功能：

| 功能 | 描述 |
|-----|------|
| **注册管理** | 注册/注销数据源 |
| **故障切换** | 自动切换到备用数据源 |
| **负载均衡** | 轮询选择数据源 |
| **健康检查** | 监控数据源状态 |
| **请求限流** | 控制并发请求数量 |
| **批量获取** | 并行获取多个数据 |

```python
# 核心 API
class DataSourceManager:
    def register(self, source: DataSource, config: DataSourceConfig):
        """注册数据源"""
        
    async def fetch(self, source_type: DataSourceType, *args, 
                    failover: bool = True, health_aware: bool = True) -> DataSourceResult:
        """获取数据（自动选择数据源）"""
        
    async def fetch_batch(self, source_type: DataSourceType, 
                          params_list: list[dict]) -> list[DataSourceResult]:
        """批量获取数据"""
        
    async def health_check(self, source_name: str = None) -> dict:
        """健康检查"""
```

#### 3.3.4 已注册数据源

| 类型 | 数据源 | 优先级 | 状态 |
|-----|--------|-------|------|
| 基金 | Fund123DataSource | 1 | 启用 |
| 基金 | FundDataSource (天天基金) | 2 | 禁用 |
| 基金 | SinaFundDataSource | 2 | 禁用 |
| 基金 | EastMoneyFundDataSource | 3 | 禁用 |
| 商品 | AKShareCommoditySource | - | 启用 |
| 商品 | YFinanceCommoditySource | - | 启用 |
| 新闻 | SinaNewsDataSource | - | 启用 |
| 新闻 | EastMoneyNewsDataSource | - | 启用 |
| 舆情 | AKShareEconomicNewsDataSource | - | 启用 |
| 舆情 | AKShareWeiboSentimentDataSource | - | 启用 |
| 板块 | EastMoneyDirectSource | 1 | 启用 |
| 板块 | SinaSectorDataSource | 5 | 启用 |
| 板块 | EastMoneySectorSource | 5 | 启用 |
| 股票 | SinaStockDataSource | - | 启用 |
| 股票 | YahooStockSource | - | 启用 |
| 股票 | BaostockStockSource | - | 启用 |
| 债券 | SinaBondDataSource | - | 启用 |
| 债券 | AKShareBondSource | - | 启用 |
| 加密货币 | BinanceCryptoSource | - | 启用 |
| 加密货币 | CoinGeckoCryptoSource | - | 启用 |
| 指数 | HybridIndexSource | - | 启用 |

### 3.4 缓存架构

#### 3.4.1 三级缓存策略

系统采用三级缓存策略，优先级从高到低：

```
请求 → 内存缓存 → SQLite 缓存 → 外部 API
         ↓            ↓           ↓
      最快(瞬时)    较快(~ms)   最慢(~s)
```

#### 3.4.2 缓存组件

| 组件 | 职责 |
|-----|------|
| `DualCache` | 内存+SQLite 双层缓存 |
| `CacheWarmer` | 启动时预热缓存 |
| `CacheCleaner` | 定时清理过期缓存 |

#### 3.4.3 缓存表结构

```sql
-- 基金配置表
CREATE TABLE fund_config (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    watchlist INTEGER DEFAULT 1,
    shares REAL DEFAULT 0,
    cost REAL DEFAULT 0,
    is_hold INTEGER DEFAULT 0,
    sector TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT,
    updated_at TEXT
);

-- 基金净值历史表
CREATE TABLE fund_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL,
    fund_name TEXT,
    date TEXT NOT NULL,
    unit_net_value REAL,
    accumulated_net_value REAL,
    estimated_value REAL,
    growth_rate REAL,
    fetched_at TEXT,
    UNIQUE(fund_code, date)
);

-- 基金日内分时缓存表
CREATE TABLE fund_intraday_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    price REAL NOT NULL,
    change_rate REAL,
    fetched_at TEXT,
    UNIQUE(fund_code, date, time)
);

-- 基金每日缓存表
CREATE TABLE fund_daily_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_code TEXT NOT NULL,
    date TEXT NOT NULL,
    unit_net_value REAL,
    accumulated_net_value REAL,
    estimated_value REAL,
    change_rate REAL,
    fetched_at TEXT,
    UNIQUE(fund_code, date)
);

-- 商品行情缓存表
CREATE TABLE commodity_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commodity_type TEXT NOT NULL,
    symbol TEXT,
    name TEXT,
    price REAL DEFAULT 0,
    change REAL DEFAULT 0,
    change_percent REAL DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    exchange TEXT,
    high REAL DEFAULT 0,
    low REAL DEFAULT 0,
    open REAL DEFAULT 0,
    prev_close REAL DEFAULT 0,
    source TEXT,
    timestamp TEXT NOT NULL,
    created_at TEXT
);

-- 新闻缓存表
CREATE TABLE news_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT UNIQUE,
    source TEXT,
    category TEXT,
    publish_time TEXT,
    content TEXT,
    fetched_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
```

### 3.5 健康检查架构

#### 3.5.1 健康检查组件

```python
# src/datasources/health.py
class DataSourceHealthChecker:
    """数据源健康检查器"""
    
    async def check_source(self, source: DataSource) -> HealthCheckResult:
        """检查单个数据源"""
        
    async def check_all_sources(self, sources: list[DataSource]) -> dict:
        """并行检查所有数据源"""
        
    def get_source_health(self, source_name: str) -> HealthCheckResult:
        """获取数据源健康状态"""
```

#### 3.5.2 健康状态定义

| 状态 | 描述 | 条件 |
|-----|------|------|
| HEALTHY | 健康 | 成功率 ≥ 95% |
| DEGRADED | 降级 | 70% ≤ 成功率 < 95% |
| UNHEALTHY | 不健康 | 成功率 < 70% |

---

## 4. 前端架构

### 4.1 项目结构

```
web/src/
├── main.ts                    # 应用入口
├── App.vue                    # 根组件
├── env.d.ts                   # 环境变量类型定义
│
├── router/
│   └── index.ts               # Vue Router 配置
│
├── stores/                    # Pinia 状态管理
│   ├── fundStore.ts           # 基金状态
│   ├── commodityStore.ts      # 商品状态
│   ├── indexStore.ts          # 指数状态
│   ├── sectorStore.ts         # 板块状态
│   ├── newsStore.ts           # 新闻状态
│   └── stockStore.ts          # 股票状态
│
├── components/                # 可复用组件
│   ├── FundCard.vue           # 基金卡片
│   ├── CommodityCard.vue      # 商品卡片
│   ├── IndexCard.vue          # 指数卡片
│   ├── KLineChart.vue         # K线图表
│   ├── LineChart.vue          # 折线图
│   └── ...
│
├── views/                     # 页面视图
│   ├── HomeView.vue           # 首页
│   ├── FundsView.vue          # 基金页面
│   ├── CommoditiesView.vue    # 商品页面
│   ├── IndicesView.vue        # 指数页面
│   ├── SectorsView.vue        # 板块页面
│   └── ...
│
├── api/                       # API 调用
│   └── index.ts               # Axios 实例配置
│
├── utils/                     # 工具函数
│   ├── time.ts                # 时间处理
│   └── commodityNames.ts       # 商品名称映射
│
└── types/                     # TypeScript 类型
    └── index.ts               # 类型定义
```

### 4.2 状态管理 (Pinia)

每个功能模块对应一个 Pinia Store：

| Store | 职责 |
|-------|------|
| `fundStore` | 基金列表、自选、持仓管理 |
| `commodityStore` | 商品行情、关注列表 |
| `indexStore` | 全球指数数据 |
| `sectorStore` | 行业板块、概念板块 |
| `newsStore` | 财经新闻列表 |
| `stockStore` | 股票行情数据 |

### 4.3 API 客户端

```typescript
// web/src/api/index.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
});

// 请求拦截器
api.interceptors.request.use(config => {
  // 添加认证等
  return config;
});

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    // 统一错误处理
    return Promise.reject(error);
  }
);

export default api;
```

### 4.4 图表组件

| 组件 | 用途 | 库 |
|-----|------|-----|
| `LineChart` | 简单折线图 | uPlot |
| `KLineChart` | K线图 | lightweight-charts |
| `AreaChart` | 面积图 | uPlot |

---

## 5. 部署架构

### 5.1 开发环境

```bash
# 启动前后端
pnpm run dev

# 单独启动
pnpm run dev:web    # 前端 (Vite, 端口 3000)
uv run python run_app.py --reload  # 后端 (FastAPI, 端口 8000)
```

### 5.2 生产环境

```bash
# 构建前端
pnpm run build:web

# 启动后端
uv run python run_app.py
```

### 5.3 环境配置

| 配置项 | 开发环境 | 生产环境 |
|-------|---------|---------|
| API 地址 | http://localhost:8000 | 可配置 |
| CORS | * | 限制域名 |
| 日志级别 | DEBUG | INFO |
| 缓存 TTL | 较短 | 较长 |

---

## 6. 数据流设计

### 6.1 请求处理流程

```
客户端请求
    │
    ▼
FastAPI Route
    │
    ▼
Dependency Injection (获取 DataSourceManager)
    │
    ▼
DataSourceManager.fetch()
    │
    ├─▶ 健康检查 (可选)
    │
    ├─▶ 缓存查询 (内存 → SQLite)
    │       │
    │       ├─▶ 缓存命中 → 返回数据
    │       │
    │       └─▶ 缓存未命中 → 外部 API
    │
    ▼
数据返回 (自动包装为 DataSourceResult)
    │
    ▼
Pydantic Model 验证
    │
    ▼
JSON 响应
```

### 6.2 缓存更新流程

```
新请求到达
    │
    ▼
检查缓存是否过期
    │
    ├─▶ 未过期 → 直接返回缓存数据
    │
    └─▶ 已过期/不存在
            │
            ▼
        异步请求外部 API
            │
            ▼
        更新 SQLite 缓存
            │
            ▼
        更新内存缓存 (可选)
            │
            ▼
        返回新数据
```

---

## 7. 关键设计决策

### 7.1 为什么选择这些技术？

| 决策 | 理由 |
|-----|------|
| **FastAPI** | 高性能、自动生成 API 文档、原生异步支持 |
| **Vue 3 + Pinia** | 组合式 API、响应式状态管理、TypeScript 支持 |
| **SQLite** | 零配置、嵌入式、无服务器依赖 |
| **akshare** | 丰富的中国金融数据、开源免费 |
| **yfinance** | 可靠的国际金融市场数据 |
| **uPlot** | 轻量级(~30KB)、高性能、无水印 |

### 7.2 多数据源策略

- **优先级模式**: 按优先级顺序尝试数据源
- **故障切换**: 主数据源失败时自动切换备用
- **健康感知**: 跳过不健康的数据源
- **负载均衡**: 可选的轮询模式

### 7.3 缓存策略

- **三级缓存**: 内存 → SQLite → 外部 API
- **TTL 设计**: 不同数据类型使用不同 TTL
- **预热机制**: 启动时异步预加载热点数据
- **清理机制**: 定时清理过期缓存

---

## 8. 性能优化

### 8.1 后端优化

| 优化项 | 实现方式 |
|-------|---------|
| 异步 I/O | 使用 asyncio + httpx |
| 连接复用 | httpx 连接池 |
| 并发控制 | asyncio.Semaphore |
| 缓存减少请求 | 三级缓存策略 |
| 批量获取 | fetch_batch 并行请求 |

### 8.2 前端优化

| 优化项 | 实现方式 |
|-------|---------|
| 代码分割 | Vite 懒加载 |
| 图表优化 | 使用轻量级 uPlot |
| 状态缓存 | Pinia 持久化 |
| 请求防抖 | debounce 技术 |

---

## 9. 安全考虑

### 9.1 API 安全

- 请求参数验证 (Pydantic)
- CORS 限制 (生产环境)
- 错误信息脱敏 (生产环境)

### 9.2 数据安全

- 配置文件隔离 (~/.fund-tui/)
- 数据库备份机制
- 敏感信息不记录日志

---

## 10. 扩展性设计

### 10.1 添加新数据源

1. 继承 `DataSource` 基类
2. 实现 `fetch()` 方法
3. 在 `manager.py` 中注册
4. 配置优先级和启用状态

### 10.2 添加新功能

1. 在 `api/routes/` 添加路由
2. 在 `src/datasources/` 添加数据源
3. 在 `web/src/stores/` 添加状态管理
4. 在 `web/src/views/` 添加页面

---

## 11. 监控与运维

### 11.1 健康检查端点

```bash
# 详细健康检查
GET /api/health

# 简单健康检查  
GET /api/health/simple

# 数据源健康状态
GET /api/datasource/health

# 缓存统计
GET /api/cache/stats
```

### 11.2 日志管理

- 日志缓冲: `src/utils/log_buffer.py`
- 日志 API: `GET /api/logs`
- 日志清理: `DELETE /api/logs`

---

## 12. 相关文档

- [API 文档](../API.md)
- [数据源性能报告](../data-source-performance-report.md)
- [数据源指数研究](../data-sources-index-research.md)
- [性能评估](../performance-evaluation.md)
- [功能设计文档](../plans/)
