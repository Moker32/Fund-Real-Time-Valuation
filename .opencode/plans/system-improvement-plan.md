# 系统改进计划

## 概述

本计划基于对基金实时估值系统的逻辑审查，发现了一系列潜在问题并制定了改进方案。

## 问题总结与优先级排序

| 优先级 | 问题 | 影响范围 | 建议改进 |
|--------|------|----------|----------|
| **高** | 健康检查逻辑问题 | 数据源选择 | 优化故障切换逻辑 |
| **高** | 缓存策略不一致 | 数据新鲜度 | 按数据类型定义TTL |
| **中** | 批量获取无健康检查 | 性能/可靠性 | 添加health_aware参数 |
| **中** | 错误处理不一致 | 系统稳定性 | 统一错误处理策略 |
| **中** | 推送间隔固定 | API调用成本 | 动态调整间隔 |
| **低** | 交易时段检测 | 业务逻辑 | 增强节假日检查 |
| **低** | 缓存预热并发安全 | 系统启动 | 添加锁机制 |
| **低** | 静态数据源优先级 | 系统优化 | 考虑动态调整 |

---

## 详细改进方案

### 1. 统一错误处理策略

**文件**: `src/datasources/base.py`

**目标**: 定义统一的错误类型和处理策略

**修改内容**:
- 定义 `DataSourceErrorType` 枚举（网络错误、超时错误、解析错误等）
- 扩展 `DataSourceResult`，添加 `error_type` 字段和 `retryable` 标志
- 添加 `from_exception` 工厂方法
- 更新 `_handle_error` 方法使用新的错误类型

**代码示例**:
```python
# 在 base.py 中添加
class DataSourceErrorType(Enum):
    """统一的错误类型枚举"""
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    PARSE_ERROR = "parse_error"
    AUTH_ERROR = "auth_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    DATA_NOT_FOUND = "data_not_found"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class DataSourceResult:
    """数据源返回结果封装"""
    success: bool
    data: Any | None = None
    error: str | None = None
    error_type: DataSourceErrorType | None = None  # 新增
    retryable: bool = True  # 新增：是否可重试
    timestamp: float = 0.0
    source: str = ""
    metadata: dict | None = None
    
    @classmethod
    def from_exception(cls, e: Exception, source: str, data: Any = None):
        """从异常创建失败结果"""
        error_type = cls._infer_error_type(e)
        retryable = error_type not in (DataSourceErrorType.AUTH_ERROR,)
        
        return cls(
            success=False,
            data=data,
            error=str(e),
            error_type=error_type,
            retryable=retryable,
            source=source,
        )
    
    @staticmethod
    def _infer_error_type(e: Exception) -> DataSourceErrorType:
        """推断异常对应的错误类型"""
        if isinstance(e, asyncio.TimeoutError):
            return DataSourceErrorType.TIMEOUT_ERROR
        elif isinstance(e, ConnectionError):
            return DataSourceErrorType.NETWORK_ERROR
        elif isinstance(e, json.JSONDecodeError):
            return DataSourceErrorType.PARSE_ERROR
        else:
            return DataSourceErrorType.UNKNOWN_ERROR
```

**影响范围**:
- 所有数据源类（需要更新错误处理）
- `manager.py` 中的错误记录

**验证方法**: 运行单元测试，确保错误类型正确识别

---

### 2. 优化健康检查逻辑

**文件**: `src/datasources/manager.py`

**目标**: 在数据源选择阶段过滤不健康的数据源

**当前问题**:
- 当最健康的数据源失败时，系统会继续尝试所有数据源（包括不健康的）
- 没有区分临时故障和永久故障

**修改内容**: 修改 `fetch` 方法

**代码示例**:
```python
async def fetch(self, source_type: DataSourceType, *args,
                failover: bool = True, health_aware: bool = True, **kwargs):
    """获取数据（优化后的健康检查逻辑）"""
    async with await self._get_semaphore():
        sources = self._get_ordered_sources(source_type)
        
        # 如果启用健康感知，分类数据源
        if health_aware:
            healthy_sources = []
            degraded_sources = []
            unhealthy_sources = []
            
            for source in sources:
                health = self._health_interceptor.checker.get_source_health(source.name)
                if health is None or health.status == HealthStatus.HEALTHY:
                    healthy_sources.append(source)
                elif health.status == HealthStatus.DEGRADED:
                    degraded_sources.append(source)
                else:
                    unhealthy_sources.append(source)
            
            # 优先使用健康数据源，其次是降级数据源
            sources = healthy_sources + degraded_sources
            
            # 如果所有数据源都不健康，仍然尝试（避免完全无服务）
            if not sources and failover:
                sources = unhealthy_sources
        
        # 按顺序尝试数据源
        errors = []
        for source in sources:
            if not self._source_configs.get(source.name, ...).enabled:
                continue
            
            try:
                result = await source.fetch(*args, **kwargs)
                self._record_request(source.name, source_type, result)
                
                if result.success:
                    if health_aware:
                        await self._health_checker.check_source(source)
                    return result
                
                errors.append(f"{source.name}: {result.error}")
            except Exception as e:
                errors.append(f"{source.name}: {str(e)}")
        
        # 所有数据源都失败
        return DataSourceResult(
            success=False,
            error=f"所有数据源均失败: {'; '.join(errors)}",
            timestamp=time.time(),
            source="manager",
        )
```

**改进点**:
- 在数据源选择阶段就过滤不健康的数据源
- 优先使用健康数据源，其次是降级数据源
- 只有在所有数据源都不健康时才尝试不健康的数据源
- 减少不必要的尝试，提高响应速度

**验证方法**: 模拟不健康的数据源，验证系统是否正确跳过

---

### 3. 批量获取健康检查过滤

**文件**: `src/datasources/manager.py`

**目标**: 为 `fetch_batch` 方法添加健康检查过滤

**当前问题**:
- `fetch_batch`方法没有健康检查过滤
- 无法跳过不健康的数据源

**修改内容**: 修改 `fetch_batch` 方法，添加 `health_aware` 参数

**代码示例**:
```python
async def fetch_batch(self, source_type: DataSourceType,
                      params_list: list[dict[str, Any]], *args,
                      parallel: bool = True, failover: bool = True,
                      health_aware: bool = True,  # 新增参数
                      **kwargs):
    """批量获取数据（支持健康检查过滤）"""
    sources = self._get_ordered_sources(source_type)
    
    # 如果启用健康感知，过滤不健康的数据源
    if health_aware:
        sources = [
            s for s in sources
            if not self._health_interceptor.should_skip_source(s.name)
        ]
    
    if not sources:
        return [DataSourceResult(success=False, error="没有可用的数据源")] * len(params_list)
    
    # 后续逻辑保持不变...
```

**改进点**:
- 新增`health_aware`参数，默认启用
- 在批量获取前过滤不健康的数据源
- 与`fetch`方法的健康检查逻辑保持一致

**验证方法**: 批量获取时验证是否跳过不健康的数据源

---

### 4. 统一缓存策略

**文件**: `src/datasources/fund/cache_strategy.py`

**目标**: 按数据类型定义不同的TTL和过期容忍度

**当前问题**:
- 过期阈值（stale_threshold = 7天）是硬编码的
- 没有根据数据类型调整

**修改内容**: 添加 `TTL_CONFIG` 配置，修改相关方法

**代码示例**:
```python
class FundCacheStrategy:
    # 按数据类型定义TTL配置
    TTL_CONFIG = {
        "static": {
            "fields": {"name", "short_name", "type", "establishment_date", "manager", "custodian", "risk_level"},
            "ttl": timedelta(days=30),
            "stale_threshold": timedelta(days=90),  # 静态数据可容忍更长的过期时间
        },
        "mid": {
            "fields": {"fund_scale", "scale_date"},
            "ttl": timedelta(days=7),
            "stale_threshold": timedelta(days=30),
        },
        "high": {
            "fields": {"net_value", "net_value_date", "fund_key"},
            "ttl": timedelta(days=1),
            "stale_threshold": timedelta(days=7),  # 高频数据过期容忍度较低
        },
    }
    
    def _get_field_category(self, field: str) -> str:
        """获取字段所属的类别"""
        for category, config in self.TTL_CONFIG.items():
            if field in config["fields"]:
                return category
        return "mid"  # 默认中频
    
    def _get_stale_threshold(self, fields: list[str]) -> timedelta:
        """获取字段列表的最大过期容忍度"""
        if not fields:
            return self.TTL_CONFIG["mid"]["stale_threshold"]
        
        max_threshold = timedelta(0)
        for field in fields:
            category = self._get_field_category(field)
            threshold = self.TTL_CONFIG[category]["stale_threshold"]
            max_threshold = max(max_threshold, threshold)
        
        return max_threshold
    
    def _is_cache_stale(self, metadata: CacheMetadata | None, fields: list[str] | None = None) -> bool:
        """检查缓存是否过期但可用（降级）- 按数据类型调整"""
        if metadata is None:
            return False
        
        # 获取对应的过期容忍度
        stale_threshold = self._get_stale_threshold(fields or [])
        
        # 检查是否过期但在容忍度内
        expires_at = datetime.fromisoformat(metadata.expires_at.replace("Z", ""))
        return datetime.now() < expires_at + stale_threshold
```

**改进点**:
- 按数据类型定义不同的TTL和过期容忍度
- 静态数据可以容忍更长的过期时间
- 高频数据（如净值）的过期容忍度较低
- 提高缓存策略的灵活性

**验证方法**: 验证不同类型数据的缓存过期行为是否符合预期

---

### 5. 实时推送器优化

**文件**: `src/utils/realtime_pusher.py`

**目标**: 根据数据变化情况自适应调整推送间隔

**当前问题**:
- 推送间隔是固定的
- 没有考虑数据源的更新频率

**修改内容**: 添加 `INTERVAL_CONFIG` 和自适应间隔方法

**代码示例**:
```python
class RealtimePusher:
    # 动态间隔配置
    INTERVAL_CONFIG = {
        "funds": {
            "trading": 30,
            "non_trading": 60,
            "min": 10,
            "max": 300,
        },
        "commodities": {
            "trading": 10,
            "non_trading": 30,
            "min": 5,
            "max": 120,
        },
        "indices": {
            "trading": 10,
            "non_trading": 30,
            "min": 5,
            "max": 120,
        },
    }
    
    def _get_adaptive_interval(self, data_type: str, data_changed: bool) -> int:
        """根据数据变化情况自适应调整间隔"""
        config = self.INTERVAL_CONFIG.get(data_type, self.INTERVAL_CONFIG["funds"])
        is_trading = self._is_trading_hours()
        
        base_interval = config["trading"] if is_trading else config["non_trading"]
        min_interval = config["min"]
        max_interval = config["max"]
        
        if data_changed:
            # 数据有变化，保持当前间隔或缩短
            return max(min_interval, base_interval // 2)
        else:
            # 数据没有变化，适当延长间隔
            return min(max_interval, base_interval * 2)
```

**改进点**:
- 根据数据变化情况自适应调整推送间隔
- 数据有变化时缩短间隔，无变化时延长间隔
- 设置最小和最大间隔限制
- 减少不必要的API调用

**验证方法**: 验证推送间隔是否根据数据变化动态调整

---

### 6. 交易时段检测增强

**文件**: 
- `api/routes/funds.py` (第108-116行)
- `src/datasources/trading_calendar_source.py`

**目标**: 在检查交易时段前先检查是否是交易日

**当前问题**:
- 交易时段检测没有显式检查节假日
- 可能导致在节假日仍然尝试获取数据

**修改内容**:
- 修改 `_is_trading_hours` 方法，先检查是否是交易日
- 在 `TradingCalendarSource` 中添加 `is_trading_day` 方法
- 添加节假日检查逻辑

**代码示例**:
```python
# trading_calendar_source.py 中添加
def is_trading_day(self, market: Market, date: datetime.date | None = None) -> bool:
    """检查指定日期是否是交易日"""
    if date is None:
        date = datetime.now().date()
    
    # 检查是否是周末
    if date.weekday() >= 5:
        return False
    
    # 检查是否是节假日
    holidays = self._get_holidays(market, date.year)
    return date not in holidays

# funds.py 中修改
def _is_trading_hours() -> bool:
    """检查当前是否为交易时段（增强版）"""
    try:
        calendar = _get_trading_calendar_source()
        today = datetime.now().date()
        
        # 先检查是否是交易日
        if not calendar.is_trading_day(Market.CHINA, today):
            return False
        
        # 再检查是否在交易时段内
        result = calendar.is_within_trading_hours(Market.CHINA)
        return result.get("status") == "open"
    except Exception as e:
        logger.warning(f"检查交易时段失败: {e}")
        return False
```

**改进点**:
- 在检查交易时段前先检查是否是交易日
- 显式检查周末和节假日
- 提高交易时段检测的准确性

**验证方法**: 在节假日验证系统是否正确识别为非交易时段

---

### 7. 缓存预热并发安全

**文件**: `src/datasources/cache_warmer.py`

**目标**: 使用锁保护缓存预热过程，防止竞争条件

**当前问题**:
- 多个实例同时启动可能导致竞争条件

**修改内容**: 添加类级别的锁和标志位

**代码示例**:
```python
class CacheWarmer:
    _preload_lock = asyncio.Lock()
    _preload_completed = False
    
    async def preload_all_cache(self, timeout: float = 10.0):
        """预加载所有文件缓存到内存（带锁保护）"""
        async with self._preload_lock:
            if self._preload_completed:
                logger.debug("缓存预加载已完成，跳过")
                return
            
            try:
                # 执行预加载逻辑...
                self._preload_completed = True
            except Exception as e:
                logger.error(f"缓存预加载失败: {e}")
                self._preload_completed = True
```

**改进点**:
- 使用asyncio.Lock保护预加载过程
- 添加标志位防止重复预加载
- 提高并发安全性

**验证方法**: 并发启动多个实例，验证是否只预加载一次

---

### 8. 动态数据源优先级

**文件**: `src/datasources/manager.py`

**目标**: 根据运行时性能动态调整数据源优先级

**当前问题**:
- 数据源优先级是静态配置的
- 无法根据运行时性能动态调整

**修改内容**: 添加性能统计和动态优先级方法

**代码示例**:
```python
class DataSourceManager:
    def __init__(self, ...):
        # 现有代码...
        self._performance_stats: dict[str, dict[str, Any]] = {}
    
    def _record_request(self, source_name: str, source_type: DataSourceType,
                       result: DataSourceResult | None, error: str | None = None):
        """记录请求并更新性能统计"""
        # 现有的记录逻辑...
        
        # 更新性能统计
        if source_name not in self._performance_stats:
            self._performance_stats[source_name] = {
                "total_requests": 0,
                "successful_requests": 0,
                "consecutive_failures": 0,
            }
        
        stats = self._performance_stats[source_name]
        stats["total_requests"] += 1
        
        if result and result.success:
            stats["successful_requests"] += 1
            stats["consecutive_failures"] = 0
        else:
            stats["consecutive_failures"] += 1
    
    def _get_dynamic_priority(self, source_name: str, base_priority: int) -> int:
        """根据性能统计动态调整优先级"""
        stats = self._performance_stats.get(source_name)
        if not stats or stats["total_requests"] < 10:
            return base_priority  # 样本太少，不调整
        
        success_rate = stats["successful_requests"] / stats["total_requests"]
        
        if success_rate < 0.5:
            return base_priority + 10  # 大幅降低优先级
        elif success_rate < 0.8:
            return base_priority + 5
        elif stats["consecutive_failures"] > 5:
            return base_priority + 3
        else:
            return base_priority
    
    def _get_ordered_sources(self, source_type: DataSourceType) -> list[DataSource]:
        """获取排序后的数据源列表（考虑动态优先级）"""
        source_ids = self._type_sources[source_type]
        
        def get_priority(sid):
            config = self._source_configs.get(sid)
            base_priority = config.priority if config else 0
            return self._get_dynamic_priority(sid, base_priority)
        
        return [self._sources[sid] for sid in sorted(source_ids, key=get_priority)]
```

**改进点**:
- 记录每个数据源的性能统计
- 根据成功率和连续失败次数动态调整优先级
- 自动将性能差的数据源优先级降低

**验证方法**: 模拟数据源性能变化，验证优先级是否动态调整

---

## 实施计划

### 实施顺序与依赖关系

```
1. 统一错误处理策略 (base.py)
   ↓
2. 优化健康检查逻辑 (manager.py)
   ↓
3. 批量获取健康检查过滤 (manager.py)
   ↓
4. 统一缓存策略 (cache_strategy.py)
   ↓
5. 实时推送器优化 (realtime_pusher.py)
   ↓
6. 交易时段检测增强 (funds.py, trading_calendar_source.py)
   ↓
7. 缓存预热并发安全 (cache_warmer.py)
   ↓
8. 动态数据源优先级 (manager.py)
```

### 实施概览

| 序号 | 改进项 | 修改文件 | 预计工时 |
|------|--------|----------|----------|
| 1 | 统一错误处理策略 | `base.py` | 2小时 |
| 2 | 优化健康检查逻辑 | `manager.py` | 3小时 |
| 3 | 批量获取健康检查过滤 | `manager.py` | 2小时 |
| 4 | 统一缓存策略 | `cache_strategy.py` | 2小时 |
| 5 | 实时推送器优化 | `realtime_pusher.py` | 2小时 |
| 6 | 交易时段检测增强 | `funds.py`, `trading_calendar_source.py` | 2小时 |
| 7 | 缓存预热并发安全 | `cache_warmer.py` | 1小时 |
| 8 | 动态数据源优先级 | `manager.py` | 2小时 |
| **总计** | | | **16小时** |

### 实施阶段

#### 第一阶段（基础设施改进，无依赖）
- 统一错误处理策略
- 统一缓存策略
- 缓存预热并发安全

#### 第二阶段（核心逻辑优化，依赖第一阶段）
- 优化健康检查逻辑
- 批量获取健康检查过滤

#### 第三阶段（业务逻辑优化，依赖第二阶段）
- 实时推送器优化
- 交易时段检测增强
- 动态数据源优先级

---

## 测试计划

### 单元测试

每个改进项都需要编写相应的单元测试：

1. **错误处理测试**
   - 测试 `DataSourceResult.from_exception` 方法
   - 测试错误类型推断

2. **健康检查测试**
   - 测试不健康数据源过滤
   - 测试故障切换逻辑

3. **缓存策略测试**
   - 测试不同数据类型的TTL
   - 测试过期容忍度

4. **推送器测试**
   - 测试自适应间隔调整

### 集成测试

1. **端到端测试**
   - 测试完整的数据获取流程
   - 测试缓存命中和失效场景

2. **并发测试**
   - 测试缓存预热并发安全
   - 测试多数据源并发获取

### 性能测试

1. **响应时间测试**
   - 验证健康检查过滤是否提高响应速度
   - 验证缓存策略是否减少API调用

---

## 风险评估与缓解措施

| 改进项 | 风险等级 | 风险描述 | 缓解措施 |
|--------|----------|----------|----------|
| 错误处理 | 中 | 可能影响错误传播 | 保持向后兼容，渐进式迁移 |
| 健康检查 | 中 | 可能影响故障切换 | 保留降级机制 |
| 缓存策略 | 低 | 可能影响数据新鲜度 | 提供配置选项 |
| 推送器 | 低 | 可能影响实时性 | 设置最小间隔限制 |
| 交易时段 | 低 | 可能影响节假日期间的数据获取 | 提供手动覆盖选项 |
| 动态优先级 | 低 | 可能导致优先级波动 | 设置调整幅度限制 |

---

## 实施检查清单

### 每个改进项完成后检查

- [ ] 代码修改完成
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 代码审查通过
- [ ] 文档更新

### 全部完成后检查

- [ ] 所有改进项完成
- [ ] 回归测试通过
- [ ] 性能测试通过
- [ ] 用户验收测试通过
- [ ] 部署准备就绪

---

## 总结

本改进计划涵盖了系统的主要逻辑问题，按照优先级和实施难度进行了排序。通过实施这些改进，可以：

1. **提高系统稳定性** - 统一的错误处理和健康检查机制
2. **优化性能** - 动态推送间隔和缓存策略优化
3. **增强可靠性** - 并发安全和故障切换改进
4. **提升用户体验** - 更准确的交易时段检测和数据更新

建议按照计划顺序逐步实施，每个阶段完成后进行测试和验证。
