# 模块设计文档

## 1. 概述

本文档详细描述基金实时估值系统的各核心模块的设计与实现。每个模块遵循单一职责原则，通过清晰的接口进行交互。

### 1.1 模块架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API 层 (api/)                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  funds   │  │commodities│  │  indices │  │ sectors  │  │  news   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │             │          │
│       └─────────────┴─────────────┴─────────────┴─────────────┘          │
│                                    │                                       │
│                          ┌────────▼────────┐                             │
│                          │  dependencies   │                             │
│                          └────────┬────────┘                             │
└────────────────────────────────────┼─────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼─────────────────────────────────────┐
│                          业务逻辑层 (src/)                                │
│                                    │                                       │
│  ┌─────────────────────────────────▼────────────────────────────────┐   │
│  │                    DataSourceManager                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │    Health    │  │    Cache     │  │    Warmer    │          │   │
│  │  │   Checker    │  │   Manager    │  │              │          │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │   │
│  └──────────────────────────────────┬────────────────────────────────┘   │
│                                     │                                       │
│  ┌─────────────────────────────────▼────────────────────────────────┐   │
│  │                      Data Sources                                  │   │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐     │   │
│  │  │  Fund  │  │ Commodity│ │  Index │  │ Sector │  │ Stock  │     │   │
│  │  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘     │   │
│  └──────────────────────────────────┬────────────────────────────────┘   │
└─────────────────────────────────────┼───────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼───────────────────────────────────┐
│                          数据持久化层 (src/db/, src/config/)             │
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐                   │
│  │   DatabaseManager    │    │    ConfigManager     │                   │
│  │      (SQLite)        │    │      (YAML)          │                   │
│  └─────────────────────┘    └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. API 路由模块 (api/)

### 2.1 模块职责

API 路由模块负责处理 HTTP 请求的路由、参数验证、响应格式化，是系统的对外接口层。

### 2.2 核心组件

| 文件 | 职责 | 主要类/函数 |
|------|------|-------------|
| `main.py` | FastAPI 应用入口、生命周期管理 | `app`, `lifespan` |
| `dependencies.py` | 依赖注入 | `get_data_source_manager` |
| `models.py` | Pydantic 数据模型 | 各类 Request/Response 模型 |
| `routes/funds.py` | 基金相关 API | `router` |
| `routes/commodities.py` | 商品相关 API | `router` |
| `routes/indices.py` | 指数相关 API | `router` |
| `routes/sectors.py` | 板块相关 API | `router` |
| `routes/news.py` | 新闻相关 API | `router` |
| `routes/sentiment.py` | 舆情相关 API | `router` |
| `routes/stocks.py` | 股票相关 API | `router` |
| `routes/bonds.py` | 债券相关 API | `router` |
| `routes/trading_calendar.py` | 交易日历 API | `router` |
| `routes/cache.py` | 缓存管理 API | `router` |
| `routes/datasource.py` | 数据源管理 API | `router` |

### 2.3 路由注册模式

每个路由文件遵循统一的模式：

```python
# routes/funds.py 示例
from fastapi import APIRouter, Depends, HTTPException
from src.datasources.manager import DataSourceManager, get_data_source_manager
from ..models import FundResponse, FundListResponse

router = APIRouter(prefix="/api/funds", tags=["funds"])

@router.get("", response_model=FundListResponse)
async def list_funds(
    manager: DataSourceManager = Depends(get_data_source_manager)
):
    """获取基金列表"""
    pass
```

### 2.4 异常处理

API 模块提供统一的异常处理：

```python
# HTTP 异常 (400, 404, 500)
@app.exception_handler(HTTPException)

# 请求验证错误 (422)
@app.exception_handler(RequestValidationError)

# 通用异常 (500)
@app.exception_handler(Exception)
```

响应格式统一为：
```json
{
  "success": false,
  "error": "错误信息",
  "detail": "详细错误",
  "timestamp": "ISO 时间戳"
}
```

---

## 3. 数据源管理模块 (src/datasources/)

### 3.1 模块职责

数据源模块是系统的核心，负责从外部获取金融数据，支持多数据源管理、故障切换、负载均衡和健康检查。

### 3.2 核心组件

#### 3.2.1 基类定义 (base.py)

```python
class DataSource(ABC):
    """数据源抽象基类"""
    name: str                    # 数据源名称
    source_type: DataSourceType  # 数据源类型
    
    @abstractmethod
    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        """获取数据"""
        pass
    
    def get_status(self) -> str:
        """获取状态"""
        pass

@dataclass
class DataSourceResult:
    """数据源结果"""
    success: bool
    data: Any = None
    error: str | None = None
    timestamp: float = 0.0
    source: str = ""
    metadata: dict | None = None

class DataSourceType(Enum):
    """数据源类型枚举"""
    FUND = "fund"
    COMMODITY = "commodity"
    NEWS = "news"
    SECTOR = "sector"
    STOCK = "stock"
    BOND = "bond"
    CRYPTO = "crypto"
```

#### 3.2.2 数据源管理器 (manager.py)

`DataSourceManager` 是核心调度组件：

| 方法 | 职责 |
|------|------|
| `register()` | 注册数据源 |
| `unregister()` | 注销数据源 |
| `get_source()` | 获取指定数据源 |
| `fetch()` | 自动选择数据源获取数据 |
| `fetch_batch()` | 批量获取数据 |
| `health_check()` | 健康检查 |
| `get_statistics()` | 获取统计数据 |

**关键特性：**

- **故障切换 (Failover)**: 按优先级顺序尝试数据源，直到成功
- **负载均衡 (Load Balancing)**: 轮询模式分发请求
- **健康感知**: 跳过不健康的数据源
- **并发控制**: 使用 `asyncio.Semaphore` 限制并发数

#### 3.2.3 健康检查 (health.py)

```python
class DataSourceHealthChecker:
    """数据源健康检查器"""
    
    async def check_source(self, source: DataSource) -> HealthCheckResult:
        """检查单个数据源"""
    
    async def check_all_sources(self, sources: list[DataSource]) -> dict:
        """并行检查所有数据源"""
    
    def get_source_health(self, source_name: str) -> HealthCheckResult:
        """获取数据源健康状态"""
```

**健康状态定义：**

| 状态 | 条件 |
|------|------|
| HEALTHY | 成功率 ≥ 95% |
| DEGRADED | 70% ≤ 成功率 < 95% |
| UNHEALTHY | 成功率 < 70% |

#### 3.2.4 缓存管理 (cache.py, dual_cache.py)

```python
class DualCache:
    """内存 + SQLite 双层缓存"""
    
    async def get(self, key: str) -> Any:
        """获取缓存"""
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存"""
    
    async def delete(self, key: str):
        """删除缓存"""
    
    async def clear(self):
        """清空缓存"""
```

**缓存策略：**
- 内存缓存：优先查询，速度最快
- SQLite 缓存：持久化存储，支持更长 TTL
- 外部 API：缓存未命中时查询

#### 3.2.5 缓存预热 (cache_warmer.py)

```python
class CacheWarmer:
    """缓存预热器"""
    
    async def preload_all_cache(self, timeout: int = 60):
        """预加载所有缓存数据"""
    
    async def preload_fund_info_cache(self, timeout: int = 60):
        """预热基金信息缓存"""
    
    def start_background_warmup(self, interval: int = 300):
        """启动后台定时预热"""
```

#### 3.2.6 缓存清理 (cache_cleaner.py)

```python
class CacheCleaner:
    """缓存清理器"""
    
    async def cleanup_expired_cache(self):
        """清理过期缓存"""
    
    def start_background_cleanup(self, interval: int = 3600):
        """启动后台定时清理"""
```

### 3.3 数据源实现

| 数据源 | 文件 | 类型 | 说明 |
|--------|------|------|------|
| 基金 | `fund_source.py` | FUND | Fund123、天天基金、新浪、东方财富、Tushare |
| 商品 | `commodity_source.py` | COMMODITY | AKShare、YFinance |
| 指数 | `index_source.py` | INDEX | 混合指数源 |
| 板块 | `sector_source.py` | SECTOR | 东方财富、新浪 |
| 股票 | `stock_source.py` | STOCK | 新浪、Yahoo、Baostock |
| 债券 | `bond_source.py` | BOND | 新浪、AKShare |
| 加密货币 | `crypto_source.py` | CRYPTO | Binance、CoinGecko |
| 新闻 | `news_source.py` | NEWS | 新浪、东方财富 |
| 舆情 | `akshare_sentiment_source.py` | SENTIMENT | AKShare 经济新闻、微博情绪 |
| 交易日历 | `trading_calendar_source.py` | TRADING_CALENDAR | 多市场交易日历 |

### 3.4 数据源注册配置

在 `manager.py` 的 `create_default_manager()` 中配置：

```python
# 基金数据源配置示例
fund123 = Fund123DataSource()
manager.register(
    fund123,
    DataSourceConfig(
        source_class=type(fund123),
        name=fund123.name,
        source_type=DataSourceType.FUND,
        enabled=True,
        priority=1,  # 数值越小优先级越高
    ),
)
```

---

## 4. 数据库模块 (src/db/)

### 4.1 模块职责

数据库模块负责数据的持久化存储，包括基金配置、商品配置、历史净值和新闻缓存。

### 4.2 核心组件

#### 4.2.1 数据库管理器 (database.py)

```python
class DatabaseManager:
    """SQLite 数据库管理器"""
    
    def __init__(self, db_path: str | None = None):
        """初始化数据库管理器"""
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
    
    def init_tables(self):
        """初始化数据表"""
    
    def _migrate_database(self):
        """数据库迁移"""
```

**支持的表：**

| 表名 | 用途 |
|------|------|
| `fund_config` | 基金配置（自选、持仓、成本） |
| `commodity_config` | 商品配置（关注列表） |
| `fund_history` | 基金净值历史 |
| `fund_intraday_cache` | 基金日内分时缓存 |
| `fund_daily_cache` | 基金每日缓存 |
| `commodity_cache` | 商品行情缓存 |
| `news_cache` | 新闻缓存 |

#### 4.2.2 数据模型

```python
@dataclass
class FundConfig:
    """基金配置"""
    code: str
    name: str
    watchlist: int = 1      # 是否在自选
    shares: float = 0.0      # 持有份额
    cost: float = 0.0       # 成本价
    is_hold: int = 0        # 是否持有
    sector: str = ""        # 板块标注
    notes: str = ""        # 备注

@dataclass
class CommodityConfig:
    """商品配置"""
    symbol: str
    name: str
    source: str = "akshare"
    enabled: int = 1

@dataclass
class FundHistoryRecord:
    """基金净值历史"""
    fund_code: str
    fund_name: str
    date: str
    unit_net_value: float
    accumulated_net_value: float | None
    estimated_value: float | None
    growth_rate: float | None
```

#### 4.2.3 DAO 操作

```python
class ConfigDAO:
    """配置数据访问对象"""
    
    def add_fund(self, fund: FundConfig) -> bool:
        """添加基金"""
    
    def update_fund(self, code: str, **kwargs) -> bool:
        """更新基金"""
    
    def get_fund(self, code: str) -> FundConfig | None:
        """获取基金"""
    
    def get_all_funds(self) -> list[FundConfig]:
        """获取所有基金"""
    
    def delete_fund(self, code: str) -> bool:
        """删除基金"""
    
    def add_commodity(self, commodity: CommodityConfig) -> bool:
        """添加商品"""
    
    def get_all_commodities(self) -> list[CommodityConfig]:
        """获取所有商品"""
```

### 4.3 设计决策

| 决策 | 理由 |
|------|------|
| 使用 INTEGER 存储布尔值 | SQLite 原生 BOOLEAN 存在问题 |
| 使用 @property 转换布尔值 | 保持数据类简洁 |
| 迁移机制自动添加列 | 向后兼容 |
| 使用 contextmanager 管理连接 | 确保连接正确关闭 |

---

## 5. 配置模块 (src/config/)

### 5.1 模块职责

配置模块负责应用配置的读取和管理，包括 YAML 配置文件和运行时配置。

### 5.2 核心组件

#### 5.2.1 配置模型 (models.py)

```python
@dataclass
class Fund:
    """基金基础模型"""
    code: str
    name: str

@dataclass
class Holding(Fund):
    """持仓模型"""
    shares: float = 0.0
    cost: float = 0.0
    
    @property
    def total_cost(self) -> float:
        return self.shares * self.cost

@dataclass
class Commodity:
    """商品模型"""
    symbol: str
    name: str
    source: str = DataSource.AKSHARE.value

@dataclass
class AppConfig:
    """应用主配置"""
    refresh_interval: int = 30
    theme: str = Theme.DARK.value
    default_fund_source: str = DataSource.SINA.value
    max_history_points: int = 100
    enable_auto_refresh: bool = True
```

#### 5.2.2 配置管理器 (manager.py)

```python
class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "~/.fund-tui"):
        """初始化配置管理器"""
    
    def load_config(self) -> AppConfig:
        """加载应用配置"""
    
    def save_config(self, config: AppConfig):
        """保存应用配置"""
    
    def get_funds_config(self) -> FundList:
        """获取基金配置"""
    
    def save_funds_config(self, funds: FundList):
        """保存基金配置"""
```

#### 5.2.3 商品配置 (commodities_config.py)

```python
class CommoditiesConfig:
    """商品配置管理"""
    
    def __init__(self, config_path: str = "~/.fund-tui/commodities.yaml"):
        """初始化"""
    
    def load(self) -> list[Commodity]:
        """加载商品配置"""
    
    def save(self, commodities: list[Commodity]):
        """保存商品配置"""
    
    def add(self, commodity: Commodity):
        """添加商品"""
    
    def remove(self, symbol: str):
        """移除商品"""
```

### 5.3 配置文件位置

| 配置文件 | 位置 |
|----------|------|
| 应用配置 | `~/.fund-tui/config.yaml` |
| 基金配置 | `~/.fund-tui/funds.yaml` |
| 商品配置 | `~/.fund-tui/commodities.yaml` |
| 数据库 | `~/.fund-tui/fund_data.db` |

---

## 6. 工具模块 (src/utils/)

### 6.1 模块职责

提供通用的工具函数和辅助功能。

### 6.2 核心组件

#### 6.2.1 日志缓冲 (log_buffer.py)

```python
class LogBuffer:
    """内存日志缓冲区"""
    
    def __init__(self, max_size: int = 1000):
        """初始化"""
    
    def add_log(self, level: str, logger: str, message: str):
        """添加日志"""
    
    def get_logs(self, level: str | None = None, 
                 limit: int = 100, 
                 logger: str | None = None) -> list[LogEntry]:
        """获取日志"""
    
    def clear(self):
        """清空日志"""
```

#### 6.2.2 其他工具

| 文件 | 职责 |
|------|------|
| `colors.py` | 终端颜色输出 |
| `export.py` | 数据导出功能 |

---

## 7. 前端模块 (web/)

### 7.1 模块职责

Vue 3 前端提供用户界面，展示基金、商品、指数等金融数据。

### 7.2 项目结构

```
web/src/
├── main.ts                    # 应用入口
├── App.vue                    # 根组件
├── env.d.ts                   # 环境变量类型
│
├── router/
│   └── index.ts               # 路由配置
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
│   └── index.ts               # Axios 实例
│
├── utils/                     # 工具函数
│   ├── time.ts                # 时间处理
│   └── commodityNames.ts      # 商品名称映射
│
└── types/                     # TypeScript 类型
    └── index.ts               # 类型定义
```

### 7.3 状态管理 (Pinia)

每个功能模块对应一个 Store：

```typescript
// fundStore.ts 示例
import { defineStore } from 'pinia'

export const useFundStore = defineStore('fund', {
  state: () => ({
    funds: [] as Fund[],
    watchlist: [] as string[],
    holdings: [] as Holding[],
    loading: false,
  }),
  
  actions: {
    async fetchFunds() {
      // 获取基金列表
    },
    
    async addToWatchlist(code: string) {
      // 添加到自选
    },
  },
})
```

### 7.4 API 客户端

```typescript
// api/index.ts
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
})

// 请求拦截器
api.interceptors.request.use(config => {
  return config
})

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => Promise.reject(error)
)

export default api
```

---

## 8. 模块交互流程

### 8.1 数据请求流程

```
1. 客户端发起请求
       │
       ▼
2. FastAPI Route 接收请求
       │
       ▼
3. 依赖注入获取 DataSourceManager
       │
       ▼
4. DataSourceManager.fetch() 处理
       │
       ├── 4.1 健康检查（可选）
       │
       ├── 4.2 缓存查询
       │     │
       │     ├── 内存缓存 → 命中 → 返回
       │     │
       │     └── 未命中 → SQLite 缓存
       │           │
       │           ├── 命中 → 更新内存缓存 → 返回
       │           │
       │           └── 未命中 → 外部 API
       │
       ▼
5. 返回 DataSourceResult
       │
       ▼
6. Pydantic 模型验证
       │
       ▼
7. JSON 响应
```

### 8.2 缓存更新流程

```
新请求到达
     │
     ▼
检查缓存 TTL
     │
     ├── 未过期 → 直接返回缓存
     │
     └── 已过期/不存在
             │
             ▼
         异步请求外部 API
             │
             ▼
         更新 SQLite 缓存
             │
             ▼
         更新内存缓存
             │
             ▼
         返回新数据
```

---

## 9. 扩展性设计

### 9.1 添加新数据源

1. 继承 `DataSource` 基类
2. 实现 `fetch()` 方法
3. 在 `manager.py` 中注册
4. 配置优先级和启用状态

```python
class MyCustomDataSource(DataSource):
    name = "my_custom_source"
    source_type = DataSourceType.FUND
    
    async def fetch(self, fund_code: str) -> DataSourceResult:
        # 实现数据获取逻辑
        pass

# 注册
manager.register(
    MyCustomDataSource(),
    DataSourceConfig(
        source_class=MyCustomDataSource,
        name="my_custom_source",
        source_type=DataSourceType.FUND,
        enabled=True,
        priority=2,
    ),
)
```

### 9.2 添加新 API 路由

1. 在 `api/routes/` 创建新路由文件
2. 实现路由逻辑
3. 在 `api/main.py` 注册路由

```python
# api/routes/my_new_route.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/new", tags=["new"])

@router.get("/data")
async def get_data():
    return {"data": "new endpoint"}

# api/main.py
app.include_router(router)
```

---

## 10. 测试策略

### 10.1 测试文件结构

```
tests/
├── test_fund_source.py        # 基金数据源测试
├── test_commodity_source.py   # 商品数据源测试
├── test_manager.py            # 数据源管理器测试
├── test_database.py           # 数据库测试
├── test_api_routes.py         # API 路由测试
└── conftest.py                # pytest 配置和 fixtures
```

### 10.2 测试类型

| 类型 | 覆盖范围 |
|------|----------|
| 单元测试 | 独立模块的功能测试 |
| 集成测试 | 模块间交互测试 |
| API 测试 | HTTP 端点测试 |

---

## 11. 相关文档

- [系统架构设计](architecture/system-architecture.md) - 系统整体架构
- [API 文档](../API.md) - API 接口详细文档
- [数据源性能报告](../data-source-performance-report.md) - 数据源性能分析
- [功能设计文档](../plans/) - 新功能规划
