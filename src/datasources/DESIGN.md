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
│                   Cache & Rate Limit Layer                       │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │                   EnhancedCache                         │  │
│    │  - L1 内存缓存        - L2 磁盘缓存  - L3 持久化        │  │
│    │  - 预热机制           - 穿透防护     - 压缩存储          │  │
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
│  1. 验证请求    │
│  2. 路由选择    │
│  3. 熔断检查    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CircuitBreaker │◄──── 熔断检查 ──── 打开? ──► 返回降级数据
│  ────────────   │
│  状态: 闭合     │
└────────┬────────┘
         │ 闭合
         ▼
┌─────────────────┐     命中?      ┌──────────────┐
│ EnhancedCache   │◄──────────────│ Cache Hit    │
│  ────────────   │               │ 返回缓存数据 │
└────────┬────────┘               └──────────────┘
         │ 未命中
         ▼
┌─────────────────┐
│ HotBackupManager │
│  ────────────   │
│  1. 选择主数据源 │
│  2. 并行请求     │
│  3. 结果聚合     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DataSource      │──── 成功? ────► 保存缓存 ──► 返回结果
│ (Manager)       │
└─────────────────┘
         │ 失败
         ▼
┌─────────────────┐
│  Fallback       │◄── 尝试降级 ──► 返回降级数据
│  ────────────   │
│  1. 备用数据源  │
│  2. 缓存数据    │
│  3. 静态数据    │
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

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @property
    def is_stale(self) -> bool:
        """是否过期数据"""
        return self.cache_age > 0 and self.from_cache
```

#### 3.1.3 RequestPriority
class RequestPriority枚举

```python(Enum):
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
        """
        处理数据请求

        Args:
            request: 数据请求

        Returns:
            DataResponse: 数据响应
        """

    async def request_batch(
        self,
        requests: list[DataRequest],
        parallel: bool = True
    ) -> list[DataResponse]:
        """
        批量处理数据请求

        Args:
            requests: 请求列表
            parallel: 是否并行执行

        Returns:
            List[DataResponse]: 响应列表
        """

    async def get_fund(
        self,
        fund_code: str,
        allow_fallback: bool = True
    ) -> DataResponse:
        """便捷方法: 获取基金数据"""

    async def get_commodity(
        self,
        symbol: str,
        allow_fallback: bool = True
    ) -> DataResponse:
        """便捷方法: 获取商品数据"""

    async def get_stock(
        self,
        symbol: str,
        allow_fallback: bool = True
    ) -> DataResponse:
        """便捷方法: 获取股票数据"""

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
│   ┌──────┐        ┌──────┐          ┌──────┐               │
│   │ 主数据源│──────▶│ 备数据源│──────▶│ 备数据源│          │
│   └──────┘        └──────┘          └──────┘               │
│       │               │                 │                   │
│       │               │                 │                   │
│       │               │                 │                   │
│       ▼               ▼                 ▼                   │
│   [主备同步]      [实时同步]        [定时同步]              │
│                                                             │
│   ──────────────────────────────────────────────────────── │
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
        """
        初始化热备份管理器

        Args:
            manager: 数据源管理器
            sync_interval: 同步间隔 (秒)
            sync_strategy: 同步策略
        """

    async def fetch_with_backup(
        self,
        source_type: DataSourceType,
        *args,
        primary_source: str | None = None,
        backup_sources: list[str] | None = None,
        timeout: float = 5.0,
        **kwargs
    ) -> HotBackupResult:
        """
        带备份的数据获取

        Args:
            source_type: 数据源类型
            *args: 位置参数
            primary_source: 主数据源名称
            backup_sources: 备用数据源列表
            timeout: 超时时间
            **kwargs: 关键字参数

        Returns:
            HotBackupResult: 包含主备结果的对象
        """

    async def start_sync(self, source_type: DataSourceType):
        """启动数据同步"""

    async def stop_sync(self, source_type: DataSourceType):
        """停止数据同步"""

    async def force_sync(self, source_type: DataSourceType):
        """强制同步"""


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

    def get_stats(self) -> CircuitStats:
        """获取统计信息"""
```

### 3.5 增强缓存 (enhanced_cache.py)

#### 3.5.1 缓存层级

```
┌─────────────────────────────────────────────────────────────┐
│                    Enhanced Cache Architecture              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Level 1: Memory Cache (L1)                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ - 实现: LRU + LFU 混合策略                          │    │
│  │ - 大小: 1000 条目 / 50MB                            │    │
│  │ - TTL: 动态计算 (基于数据类型)                       │    │
│  │ - 命中率目标: > 80%                                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                         │                                    │
│                         ▼ (未命中)                          │
│  Level 2: Disk Cache (L2)                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ - 实现: SQLite / JSON 文件                          │    │
│  │ - 大小: 无限制 (受磁盘空间限制)                      │    │
│  │ - TTL: 24 小时 (可配置)                             │    │
│  │ - 压缩: zstd / gzip                                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                         │                                    │
│                         ▼ (未命中)                          │
│  Level 3: Persistent Cache (L3)                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ - 实现: SQLite 数据库                               │    │
│  │ - 保留: 7 天历史数据                                │    │
│  │ - 用途: 历史数据、统计信息                          │    │
│  │ - 压缩: 只保留元数据                                │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Cache Strategy:                                           │
│  - Cache-Aside: 应用直接读写缓存                            │
│  - Write-Through: 写操作同时更新缓存                       │
│  - Refresh-Ahead: 过期前主动刷新                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.5.2 核心类

```python
class EnhancedCache:
    """增强缓存管理器"""

    def __init__(
        self,
        memory_config: MemoryCacheConfig | None = None,
        disk_config: DiskCacheConfig | None = None,
        persistent_config: PersistentCacheConfig | None = None
    ):
        """初始化增强缓存"""

    async def get(
        self,
        key: str,
        source_type: DataSourceType | None = None,
        allow_stale: bool = True
    ) -> EnhancedCacheEntry:
        """获取缓存"""

    async def set(
        self,
        key: str,
        value: Any,
        source_type: DataSourceType | None = None,
        ttl_seconds: int | None = None,
        compress: bool = True
    ):
        """设置缓存"""

    async def invalidate(self, key: str):
        """使缓存失效"""

    async def invalidate_pattern(self, pattern: str):
        """按模式使缓存失效"""

    async def preheat(
        self,
        keys: list[str],
        source_type: DataSourceType,
        fetch_func: Callable[[str], Any]
    ):
        """缓存预热"""

    def get_stats(self) -> EnhancedCacheStats:
        """获取缓存统计"""


@dataclass
class EnhancedCacheEntry:
    """增强缓存条目"""
    key: str
    value: Any
    created_at: float
    expires_at: float
    stale_until: float
    source_type: DataSourceType | None = None
    compression: str | None = None
    size_bytes: int = 0
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        ...

    @property
    def is_stale(self) -> bool:
        ...
```

### 3.6 数据降级 (fallback.py)

#### 3.6.1 降级策略

```
┌─────────────────────────────────────────────────────────────┐
│                    Fallback Strategy                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Request ──► Primary Source                                │
│      │                                                       │
│      ├─► Success ──► Return Data                           │
│      │                                                       │
│      └─► Failure ──► Check Fallback Chain                  │
│                            │                                 │
│                            ▼                                 │
│                   ┌─────────────────┐                        │
│                   │  Fallback Chain │                        │
│                   ├─────────────────┤                        │
│                   │ 1. Backup Src  │◄── 尝试备用数据源      │
│                   │ 2. Cache Data  │◄── 尝试缓存数据       │
│                   │ 3. Stale Data  │◄── 尝试过期数据       │
│                   │ 4. Static Data │◄── 使用静态数据       │
│                   │ 5. Empty Data  │◄── 返回空数据         │
│                   └─────────────────┘                        │
│                            │                                 │
│                            ▼                                 │
│                   Return with Warning                       │
│                                                             │
│   Fallback Levels:                                          │
│   - Level 1: SAME_TYPE_BACKUP (同类型备用源)               │
│   - Level 2: CACHE (缓存数据)                               │
│   - Level 3: STALE_CACHE (过期缓存)                        │
│   - Level 4: STATIC_DATA (静态数据)                         │
│   - Level 5: EMPTY_RESPONSE (空响应)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.6.2 核心类

```python
class FallbackManager:
    """降级管理器"""

    def __init__(
        self,
        manager: DataSourceManager,
        cache: EnhancedCache | None = None
    ):
        """初始化降级管理器"""

    async def fetch_with_fallback(
        self,
        request: DataRequest,
        fallback_chain: list[FallbackLevel] | None = None
    ) -> FallbackResult:
        """
        带降级策略的数据获取

        Args:
            request: 数据请求
            fallback_chain: 降级链配置

        Returns:
            FallbackResult: 降级结果
        """

    def register_fallback_handler(
        self,
        source_type: DataSourceType,
        level: FallbackLevel,
        handler: FallbackHandler
    ):
        """注册降级处理器"""

    async def get_static_data(
        self,
        source_type: DataSourceType,
        symbol: str
    ) -> Any | None:
        """获取静态数据"""


@dataclass
class FallbackResult:
    """降级结果"""
    success: bool
    data: Any | None = None
    final_source: str = ""
    fallback_level: FallbackLevel | None = None
    fallback_count: int = 0
    warnings: list[str] = field(default_factory=list)
    original_error: str | None = None


class FallbackLevel(Enum):
    """降级级别"""
    PRIMARY = 0              # 主数据源
    SAME_TYPE_BACKUP = 1     # 同类型备用数据源
    CACHE = 2                # 缓存数据
    STALE_CACHE = 3          # 过期缓存
    STATIC_DATA = 4         # 静态数据
    EMPTY_RESPONSE = 5       # 空响应


FallbackHandler = Callable[[DataRequest], Awaitable[Any]]
```

---

## 4. API 设计

### 4.1 DataGateway API

```python
# 创建网关
gateway = DataGateway(
    manager=manager,
    event_bus=event_bus,
    enable_circuit_breaker=True
)

# 简单请求
response = await gateway.request_fund("161039")

# 带选项的请求
response = await gateway.request(
    DataRequest(
        request_id="req-001",
        symbol="161039",
        source_type=DataSourceType.FUND,
        priority=RequestPriority.HIGH,
        allow_fallback=True,
        timeout=5.0
    )
)

# 批量请求
responses = await gateway.request_batch([
    DataRequest(symbol="161039", source_type=DataSourceType.FUND),
    DataRequest(symbol="BTC-USDT", source_type=DataSourceType.CRYPTO),
])

# 获取统计
stats = gateway.get_stats()
```

### 4.2 事件集成

```python
# 发布数据请求事件
from src.events import EventType, EventBus

bus = EventBus.get_instance()
bus.publish_event(
    EventType.DATA_SOURCE_ERROR,
    source="gateway",
    data={
        "request_id": "req-001",
        "source": "fund_tiantian",
        "error": "Connection timeout"
    }
)

# 订阅数据就绪事件
def handle_data_ready(event):
    print(f"数据就绪: {event.data}")

bus.subscribe(handle_data_ready, event_type=EventType.DATA_READY)
```

---

## 5. 错误处理策略

### 5.1 错误分类

| 错误类型 | 处理策略 |
|---------|---------|
| 网络超时 | 重试 -> 备用数据源 -> 缓存 |
| 连接拒绝 | 熔断器打开 -> 降级 |
| 数据解析错误 | 记录错误 -> 尝试备用数据源 |
| 速率限制 | 等待 -> 切换数据源 |
| 未知错误 | 降级 -> 通知用户 |

### 5.2 错误响应格式

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

## 6. 文件结构

```
src/datasources/
├── base.py              # 已有: 基础类定义
├── manager.py           # 已有: DataSourceManager
├── cache.py             # 已有: SmartCache
├── health.py            # 已有: 健康检查
├── extension.py         # 已有: 扩展系统
├── rate_limiter.py      # 已有: 速率限制
├── unified_models.py    # 新增: 统一数据模型
├── gateway.py           # 新增: DataGateway
├── hot_backup.py        # 新增: 热备份 & 熔断
├── enhanced_cache.py    # 新增: 增强缓存
└── fallback.py          # 新增: 数据降级
```

---

## 7. 兼容性说明

### 7.1 向后兼容

- 所有新组件均通过 DataGateway 封装，不影响现有代码
- 保留 DataSourceManager 原有接口
- EventBus 集成采用可选方式

### 7.2 迁移策略

```python
# 方式1: 渐进式迁移
# 旧代码继续使用
result = await manager.fetch(DataSourceType.FUND, "161039")

# 新代码可以使用网关
response = await gateway.request_fund("161039")

# 方式2: 完全迁移
# 替换 manager 为 gateway
gateway = DataGateway(manager)
```

---

## 8. 性能考虑

### 8.1 性能目标

| 指标 | 目标值 |
|------|-------|
| P99 延迟 | < 500ms |
| 缓存命中率 | > 70% |
| 数据新鲜度 | < TTL |
| 并发请求数 | < 100 |

### 8.2 优化策略

1. **连接池**: HTTP 客户端使用连接池
2. **批量请求**: 减少网络往返
3. **异步处理**: 使用 asyncio.gather 并行请求
4. **压缩存储**: 减少磁盘 I/O
5. **预热机制**: 提前加载热点数据
