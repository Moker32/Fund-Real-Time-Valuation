# 数据层架构设计文档

## 1. 概述

本文档描述基金实时估值应用的数据层架构设计，包括统一数据接口、多数据源热备份和智能缓存策略。

### 1.1 设计目标

- 提供统一的数据请求/响应模型
- 实现多数据源热备份和自动故障切换
- 增强缓存策略，提升数据获取效率
- 支持优雅降级，保证系统可用性
- 与现有 EventBus、Cache、ExtensionManager 集成

### 1.2 术语定义

| 术语 | 定义 |
|------|------|
| DataGateway | 数据网关，统一入口 |
| Hot Backup | 热备份，实时同步多个数据源 |
| Fallback | 降级策略，故障时的备选方案 |
| Circuit Breaker | 熔断器，防止级联故障 |

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         GUI Layer                                │
│              (FundGUIApp, Components, Pages)                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DataGateway Layer                           │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │                    DataGateway                          │  │
│    │  - 请求路由          - 熔断控制    - 统一响应格式       │  │
│    │  - 负载均衡          - 错误处理    - 性能监控           │  │
│    └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Hot Backup & Fallback Layer                    │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │                   HotBackupManager                      │  │
│    │  - 实时同步           - 故障检测    - 自动切换           │  │
│    └─────────────────────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │                     CircuitBreaker                      │  │
│    │  - 状态管理           - 阈值配置    - 自动恢复           │  │
│    └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Cache Layer                                     │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │                   SmartCache                              │  │
│    │  - L1 内存缓存        - L2 磁盘缓存                      │  │
│    │  - 预热机制           - 穿透防护                         │  │
│    └─────────────────────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │                   RateLimiter (已有)                    │  │
│    └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   DataSource Layer (已有)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ FundSrc  │ │ StockSrc │ │CryptoSrc │ │ Other Sources    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Event Bus Layer                             │
│              (EventBus - 发布/订阅, 异步处理)                    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流图

```
                          数据请求流程

    User Request
         │
         ▼
┌─────────────────┐
│  DataGateway    │
│  ────────────   │
│ 1. 验证请求    │
│ 2. 路由选择    │
│ 3. 熔断检查    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CircuitBreaker │◄──── 熔断检查 ──── 打开? ──► 返回降级数据
│  ────────────   │
│ 状态: 闭合       │
└────────┬────────┘
         │ 闭合
         ▼
┌─────────────────┐     命中?      ┌──────────────┐
│ SmartCache      │◄──────────────│ Cache Hit    │
│  ────────────   │               │ 返回缓存数据 │
└────────┬────────┘               └──────────────┘
         │ 未命中
         ▼
┌─────────────────┐
│ HotBackupManager │
│  ────────────   │
│ 1. 选择主数据源 │
│ 2. 并行请求     │
│ 3. 结果聚合     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐──── 成功? ────► 保存缓存 ──► 返回结果
│ DataSource      │
│ (Manager)       │
└─────────────────┘
         │ 失败
         ▼
┌─────────────────┐
│  Fallback       │◄── 尝试降级 ──► 返回降级数据
│  ────────────   │
│ 1. 备用数据源  │
│ 2. 缓存数据    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ EventBus        │──── 发布事件 ──► UI 更新/日志记录
│  ────────────   │
└─────────────────┘
```

---

## 3. 核心组件说明

### 3.1 统一数据模型 (unified_models.py)

#### 3.1.1 Request 模型

```python
@dataclass
class DataRequest:
    """统一数据请求"""
    request_id: str              # 请求唯一标识
    symbol: str                 # 标的代码 (如: 161039, BTC-USDT)
    source_type: DataSourceType # 数据类型
    source_name: str | None = None  # 指定数据源 (可选)
    params: dict[str, Any] = field(default_factory=dict)  # 附加参数
    priority: RequestPriority = RequestPriority.NORMAL
    timeout: float = 10.0        # 超时时间
    retry_count: int = 3         # 重试次数
    allow_fallback: bool = True  # 是否允许降级
    cache_ttl: int | None = None # 缓存 TTL (秒)
    timestamp: float = field(default_factory=time.time)
```

#### 3.1.2 Response 模型

```python
@dataclass
class DataResponse:
    """统一数据响应"""
    request_id: str             # 关联的请求 ID
    success: bool               # 是否成功
    data: Any | None = None     # 数据内容
    error: str | None = None    # 错误信息
    source: str = ""            # 数据来源
    source_type: DataSourceType | None = None
    from_cache: bool = False   # 是否来自缓存
    cache_age: float = 0.0      # 缓存年龄 (秒)
    response_time_ms: float = 0.0  # 响应时间
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    # 降级相关信息
    fallback_used: bool = False
    fallback_source: str | None = None
```

#### 3.1.3 RequestPriority

```python
class RequestPriority(Enum):
    """请求优先级"""
    CRITICAL = 0   # 关键请求 (用户刚操作)
    HIGH = 1       # 高优先级 (主视图数据)
    NORMAL = 2     # 普通优先级 (列表刷新)
    LOW = 3        # 低优先级 (后台预热)
```

### 3.2 DataGateway (gateway.py)

#### 3.2.1 主要职责

1. **请求入口**: 接收所有数据请求，统一处理流程
2. **请求路由**: 根据请求类型选择合适的处理策略
3. **熔断控制**: 集成熔断器，防止级联故障
4. **性能监控**: 记录请求耗时、成功率等指标
5. **统一响应**: 将不同数据源的结果统一封装

#### 3.2.2 核心方法

```python
class DataGateway:
    """数据网关"""

    def __init__(
        self,
        manager: DataSourceManager,
        event_bus: EventBus | None = None,
        enable_circuit_breaker: bool = True,
        circuit_config: CircuitConfig | None = None
    ):
        """初始化数据网关"""

    async def request(self, request: DataRequest) -> DataResponse:
        """处理数据请求"""

    async def request_batch(
        self,
        requests: list[DataRequest],
        parallel: bool = True
    ) -> list[DataResponse]:
        """批量处理数据请求"""

    async def get_fund(
        self,
        fund_code: str,
        allow_fallback: bool = True
    ) -> DataResponse:
        """便捷方法: 获取基金数据"""

    def get_stats(self) -> GatewayStats:
        """获取网关统计信息"""
```

### 3.3 热备份管理器 (hot_backup.py)

#### 3.3.1 热备份策略

```
┌─────────────────────────────────────────────────────────────┐
│                    Hot Backup 策略                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Primary          Secondary          Tertiary              │
│   ┌──────┐        ┌──────┐          ┌──────┐             │
│   │ 主数据源│──────▶│ 备数据源│──────▶│ 备数据源│          │
│   └──────┘        └──────┘          └──────┘             │
│       │               │                 │                   │
│       │               │                 │                   │
│       │               │                 │                   │
│       ▼               ▼                 ▼                   │
│   [主备同步]      [实时同步]        [定时同步]              │
│                                                             │
│   ────────────────────────────────────────────────────────   │
│   策略模式:                                                   │
│   - ACTIVE_ACTIVE: 所有数据源并行请求                        │
│   - ACTIVE_STANDBY: 主备模式，自动故障切换                  │
│   - PARALLEL_FALLBACK: 并行请求主备，取最快响应             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.3.2 核心类

```python
class HotBackupManager:
    """热备份管理器"""

    def __init__(
        self,
        manager: DataSourceManager,
        sync_interval: float = 60.0,
        sync_strategy: SyncStrategy = SyncStrategy.REAL_TIME
    ):
        """初始化热备份管理器"""

    async def fetch_with_backup(
        self,
        source_type: DataSourceType,
        *args,
        primary_source: str | None = None,
        backup_sources: list[str] | None = None,
        timeout: float = 5.0,
        **kwargs
    ) -> HotBackupResult:
        """带备份的数据获取"""

    async def start_sync(self, source_type: DataSourceType):
        """启动数据同步"""

    async def stop_sync(self, source_type: DataSourceType):
        """停止数据同步"""


@dataclass
class HotBackupResult:
    """热备份结果"""
    primary_result: DataSourceResult | None = None
    backup_results: list[DataSourceResult] = field(default_factory=list)
    used_backup: bool = False
    total_time_ms: float = 0.0
    synced_sources: list[str] = field(default_factory=list)


class SyncStrategy(Enum):
    """同步策略"""
    REAL_TIME = "real_time"     # 实时同步
    INTERVAL = "interval"       # 定时同步
    ON_DEMAND = "on_demand"     # 按需同步
```

### 3.4 熔断器 (hot_backup.py)

```python
@dataclass
class CircuitConfig:
    """熔断器配置"""
    failure_threshold: int = 5       # 失败次数阈值
    success_threshold: int = 3       # 恢复所需成功次数
    timeout_seconds: float = 60.0    # 熔断超时时间
    half_open_requests: int = 3     # 半开状态允许的请求数


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常
    OPEN = "open"         # 断开
    HALF_OPEN = "half_open"  # 半开 (测试恢复)


class CircuitBreaker:
    """熔断器"""

    def __init__(self, name: str, config: CircuitConfig | None = None):
        """初始化熔断器"""

    def can_execute(self) -> bool:
        """是否可以执行请求"""

    async def record_success(self):
        """记录成功"""

    async def record_failure(self):
        """记录失败"""

    def get_state(self) -> CircuitState:
        """获取当前状态"""
```

---

## 4. 错误处理策略

### 4.1 错误分类

| 错误类型 | 处理策略 |
|---------|---------|
| 网络超时 | 重试 -> 备用数据源 -> 缓存 |
| 连接拒绝 | 熔断器打开 -> 降级 |
| 数据解析错误 | 记录错误 -> 尝试备用数据源 |
| 速率限制 | 等待 -> 切换数据源 |
| 未知错误 | 降级 -> 通知用户 |

### 4.2 错误响应格式

```python
@dataclass
class ErrorResponse:
    """错误响应"""
    code: ErrorCode
    message: str
    details: dict | None = None
    recoverable: bool = True
    suggested_action: str | None = None
    retry_after: float | None = None


class ErrorCode(Enum):
    """错误码"""
    # 客户端错误 (4xx)
    INVALID_REQUEST = 4001
    UNKNOWN_SYMBOL = 4002

    # 服务端错误 (5xx)
    NETWORK_ERROR = 5001
    TIMEOUT = 5002
    DATA_SOURCE_ERROR = 5003

    # 降级相关
    FALLBACK_EXHAUSTED = 6001
    CIRCUIT_OPEN = 6002
```

---

## 5. 文件结构

```
src/datasources/
├── base.py              # 基础类定义 (DataSource, DataSourceResult, DataSourceType)
├── manager.py           # DataSourceManager (多源注册、故障切换、负载均衡)
├── cache.py             # SmartCache (内存+磁盘缓存)
├── cache_cleaner.py     # 缓存清理任务
├── cache_warmer.py      # 缓存预热
├── health.py            # 健康检查
├── aggregator.py        # 数据聚合器 (同源/负载均衡)
├── rate_limiter.py      # 速率限制
├── unified_models.py    # 统一数据模型 (DataRequest, DataResponse)
├── gateway.py           # DataGateway (统一入口)
├── hot_backup.py        # 热备份 & 熔断器
├── fund_source.py       # 基金数据源
├── stock_source.py      # 股票数据源
├── commodity_source.py  # 商品数据源
├── crypto_source.py     # 加密货币数据源
├── bond_source.py       # 债券数据源
├── news_source.py       # 新闻数据源
├── sector_source.py     # 板块数据源
├── index_source.py      # 指数数据源
└── portfolio.py         # 组合分析
```

---

## 6. 性能考虑

### 6.1 性能目标

| 指标 | 目标值 |
|------|-------|
| P99 延迟 | < 500ms |
| 缓存命中率 | > 70% |
| 数据新鲜度 | < TTL |
| 并发请求数 | < 100 |

### 6.2 优化策略

1. **连接池**: HTTP 客户端使用连接池
2. **批量请求**: 减少网络往返
3. **异步处理**: 使用 asyncio.gather 并行请求
4. **预热机制**: 提前加载热点数据

---

*文档最后更新: 2026-02-21*
