# 实现计划

本文档描述数据层架构的分阶段实施计划。

---

## 阶段概览

| 阶段 | 内容 | 预计工作量 | 优先级 |
|------|------|-----------|--------|
| Phase 1 | 统一数据模型 | 2 天 | P0 |
| Phase 2 | DataGateway | 3 天 | P0 |
| Phase 3 | 热备份与熔断 | 3 天 | P1 |
| Phase 4 | 增强缓存 | 2 天 | P1 |
| Phase 5 | 数据降级 | 2 天 | P2 |
| Phase 6 | 测试与优化 | 2 天 | P0 |

---

## Phase 1: 统一数据模型

### 目标
创建统一的数据请求/响应模型，为后续组件提供基础。

### 交付物
- `src/datasources/unified_models.py`

### 详细任务

#### 1.1 创建统一请求模型
- [ ] 定义 `DataRequest` 数据类
- [ ] 实现请求验证逻辑
- [ ] 添加请求优先级枚举

#### 1.2 创建统一响应模型
- [ ] 定义 `DataResponse` 数据类
- [ ] 实现响应转换方法
- [ ] 添加降级相关字段

#### 1.3 添加辅助类
- [ ] 创建 `RequestPriority` 枚举
- [ ] 创建 `ResponseStatus` 枚举
- [ ] 实现错误码枚举

### 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/datasources/unified_models.py` | 新增 | 统一数据模型 |

### 验收标准

```python
# 验收测试
import pytest
from src.datasources.unified_models import (
    DataRequest,
    DataResponse,
    RequestPriority,
)

def test_request_creation():
    request = DataRequest(
        request_id="test-001",
        symbol="161039",
        source_type=DataSourceType.FUND
    )
    assert request.request_id == "test-001"
    assert request.symbol == "161039"
    assert request.priority == RequestPriority.NORMAL

def test_response_creation():
    response = DataResponse(
        request_id="test-001",
        success=True,
        data={"price": 1.2345}
    )
    assert response.success
    assert response.data["price"] == 1.2345
```

### 测试用例

| 用例 | 输入 | 期望输出 |
|------|------|---------|
| 创建有效请求 | 完整参数 | 创建成功 |
| 创建有效响应 | 成功状态 | success=True |
| 响应格式转换 | DataResponse | to_dict() 返回正确格式 |
| 优先级比较 | 不同优先级 | 高优先级正确排序 |

---

## Phase 2: DataGateway

### 目标
创建数据网关，统一所有数据请求入口。

### 交付物
- `src/datasources/gateway.py`

### 详细任务

#### 2.1 基础网关实现
- [ ] 创建 `DataGateway` 类
- [ ] 实现 `request()` 方法
- [ ] 实现 `request_batch()` 方法

#### 2.2 便捷方法
- [ ] 实现 `get_fund()` 方法
- [ ] 实现 `get_commodity()` 方法
- [ ] 实现 `get_stock()` 方法
- [ ] 实现 `get_crypto()` 方法

#### 2.3 统计与监控
- [ ] 添加请求计数
- [ ] 添加延迟统计
- [ ] 实现 `get_stats()` 方法

### 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/datasources/gateway.py` | 新增 | 数据网关 |
| `src/datasources/__init__.py` | 修改 | 添加导出 |
| `src/datasources/unified_models.py` | 修改 | 可能需要补充 |

### 验收标准

```python
# 验收测试
import pytest
from src.datasources.gateway import DataGateway
from src.datasources.unified_models import DataRequest

@pytest.fixture
def gateway(manager):
    return DataGateway(manager)

@pytest.mark.asyncio
async def test_gateway_request(gateway):
    request = DataRequest(
        request_id="test-001",
        symbol="161039",
        source_type=DataSourceType.FUND
    )
    response = await gateway.request(request)
    assert response.success or response.fallback_used

@pytest.mark.asyncio
async def test_gateway_batch(gateway):
    requests = [
        DataRequest(symbol="161039", source_type=DataSourceType.FUND),
        DataRequest(symbol="000001", source_type=DataSourceType.STOCK),
    ]
    responses = await gateway.request_batch(requests)
    assert len(responses) == 2

def test_gateway_stats(gateway):
    stats = gateway.get_stats()
    assert "total_requests" in stats
    assert "success_rate" in stats
```

### 测试用例

| 用例 | 场景 | 期望行为 |
|------|------|---------|
| 正常请求 | 数据源可用 | 返回成功响应 |
| 超时请求 | 数据源超时 | 触发降级 |
| 批量请求 | 多个请求 | 并行处理 |
| 统计收集 | 多次请求 | 统计数据正确 |

---

## Phase 3: 热备份与熔断

### 目标
实现热备份策略和熔断器，防止级联故障。

### 交付物
- `src/datasources/hot_backup.py`

### 详细任务

#### 3.1 熔断器实现
- [ ] 创建 `CircuitBreaker` 类
- [ ] 实现状态机 (CLOSED/OPEN/HALF_OPEN)
- [ ] 实现失败计数和恢复逻辑
- [ ] 添加配置类 `CircuitConfig`

#### 3.2 热备份管理器
- [ ] 创建 `HotBackupManager` 类
- [ ] 实现同步策略枚举 `SyncStrategy`
- [ ] 实现 `fetch_with_backup()` 方法
- [ ] 实现实时同步逻辑

#### 3.3 集成测试
- [ ] 集成熔断器到网关
- [ ] 集成热备份到网关

### 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/datasources/hot_backup.py` | 新增 | 热备份与熔断 |
| `src/datasources/gateway.py` | 修改 | 集成熔断器 |
| `src/datasources/__init__.py` | 修改 | 添加导出 |

### 验收标准

```python
# 验收测试
from src.datasources.hot_backup import (
    CircuitBreaker,
    CircuitConfig,
    HotBackupManager,
    SyncStrategy,
)

def test_circuit_breaker_closed():
    breaker = CircuitBreaker("test", CircuitConfig())
    assert breaker.get_state() == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_circuit_breaker_open():
    breaker = CircuitBreaker("test", CircuitConfig(
        failure_threshold=2,
        timeout_seconds=0.1
    ))
    await breaker.record_failure()
    await breaker.record_failure()
    assert breaker.get_state() == CircuitState.OPEN
    assert not breaker.can_execute()

@pytest.mark.asyncio
async def test_hot_backup_fetch(manager):
    backup_mgr = HotBackupManager(manager)
    result = await backup_mgr.fetch_with_backup(
        DataSourceType.FUND,
        "161039",
        primary_source="fund_tiantian",
        backup_sources=["fund_sina"]
    )
    assert result.primary_result or any(r.success for r in result.backup_results)
```

### 测试用例

| 用例 | 场景 | 期望行为 |
|------|------|---------|
| 熔断器打开 | 连续失败达到阈值 | 拒绝新请求 |
| 熔断器恢复 | 超时后测试请求 | 恢复闭合状态 |
| 热备份切换 | 主数据源失败 | 自动切换到备份 |
| 并行请求 | 多数据源并行 | 返回最快响应 |

---

## Phase 4: 增强缓存

### 目标
实现增强缓存策略，提升数据获取效率。

### 交付物
- `src/datasources/enhanced_cache.py`

### 详细任务

#### 4.1 增强缓存实现
- [ ] 创建 `EnhancedCache` 类
- [ ] 实现 L1 内存缓存 (LRU/LFU)
- [ ] 实现 L2 磁盘缓存 (SQLite)
- [ ] 实现 L3 持久化缓存

#### 4.2 缓存策略
- [ ] 实现 `Cache-Aside` 模式
- [ ] 实现 `Write-Through` 模式
- [ ] 实现 `Refresh-Ahead` 策略

#### 4.3 缓存工具
- [ ] 实现 `preheat()` 方法
- [ ] 实现 `invalidate_pattern()` 方法
- [ ] 实现压缩/解压缩

### 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/datasources/enhanced_cache.py` | 新增 | 增强缓存 |
| `src/datasources/gateway.py` | 修改 | 集成增强缓存 |
| `src/datasources/__init__.py` | 修改 | 添加导出 |

### 验收标准

```python
# 验收测试
from src.datasources.enhanced_cache import EnhancedCache, EnhancedCacheEntry

@pytest.fixture
def cache(tmp_path):
    return EnhancedCache(cache_dir=tmp_path)

@pytest.mark.asyncio
async def test_cache_set_get(cache):
    await cache.set("key1", {"price": 1.2345})
    entry = await cache.get("key1")
    assert entry.value["price"] == 1.2345
    assert not entry.is_expired

@pytest.mark.asyncio
async def test_cache_compression(cache):
    large_data = {"data": "x" * 10000}
    await cache.set("large", large_data, compress=True)
    entry = await cache.get("large")
    assert entry.value["data"] == large_data["data"]
    assert entry.compression == "zstd"

@pytest.mark.asyncio
async def test_cache_preheat(cache):
    keys = ["fund1", "fund2", "fund3"]
    results = await cache.preheat(
        keys,
        DataSourceType.FUND,
        lambda k: {"code": k}
    )
    assert all(results.values())
```

### 测试用例

| 用例 | 场景 | 期望行为 |
|------|------|---------|
| 缓存命中 | 数据在缓存中 | 直接返回 |
| 缓存未命中 | 数据不在缓存中 | 返回 None |
| 过期数据 | 缓存已过期 | 返回 stale=True |
| 预热成功 | 批量预热 | 缓存中有数据 |
| 压缩存储 | 大数据压缩 | 存储大小减少 |

---

## Phase 5: 数据降级

### 目标
实现优雅降级策略，保证系统可用性。

### 交付物
- `src/datasources/fallback.py`

### 详细任务

#### 5.1 降级管理器
- [ ] 创建 `FallbackManager` 类
- [ ] 定义降级级别枚举 `FallbackLevel`
- [ ] 实现降级链 `fetch_with_fallback()`

#### 5.2 降级处理器
- [ ] 实现备用数据源处理器
- [ ] 实现缓存处理器
- [ ] 实现静态数据处理器

#### 5.3 静态数据
- [ ] 创建静态数据文件
- [ ] 实现静态数据加载

### 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/datasources/fallback.py` | 新增 | 数据降级 |
| `src/datasources/static_data/` | 新增 | 静态数据目录 |
| `src/datasources/gateway.py` | 修改 | 集成降级 |
| `src/datasources/__init__.py` | 修改 | 添加导出 |

### 验收标准

```python
# 验收测试
from src.datasources.fallback import FallbackManager, FallbackLevel, FallbackResult

@pytest.fixture
def fallback_mgr(manager, cache):
    return FallbackManager(manager, cache)

@pytest.mark.asyncio
async def test_fallback_to_cache(fallback_mgr):
    # 先设置缓存
    await cache.set("test_key", {"price": 1.0})

    # 请求不存在的数据，触发降级到缓存
    request = DataRequest(
        request_id="test-001",
        symbol="UNKNOWN",
        source_type=DataSourceType.FUND,
        allow_fallback=True
    )
    result = await fallback_mgr.fetch_with_fallback(request)
    assert result.fallback_count > 0
    assert result.success or result.data is not None

@pytest.mark.asyncio
async def test_fallback_chain():
    # 测试降级链
    manager = FallbackManager(data_manager, cache)
    chain = [
        FallbackLevel.PRIMARY,
        FallbackLevel.SAME_TYPE_BACKUP,
        FallbackLevel.CACHE,
    ]
    result = await manager.fetch_with_fallback(request, fallback_chain=chain)
    assert result.fallback_count <= len(chain)
```

### 测试用例

| 用例 | 场景 | 期望行为 |
|------|------|---------|
| 主数据源失败 | 所有数据源不可用 | 降级到缓存 |
| 缓存也失败 | 无缓存数据 | 返回空响应 |
| 降级记录 | 发生降级 | 记录降级级别 |
| 静态数据 | 需要兜底数据 | 返回静态数据 |

---

## Phase 6: 测试与优化

### 目标
全面测试所有组件，优化性能和稳定性。

### 详细任务

#### 6.1 单元测试
- [ ] 统一模型测试
- [ ] 网关测试
- [ ] 熔断器测试
- [ ] 缓存测试
- [ ] 降级测试

#### 6.2 集成测试
- [ ] 端到端测试
- [ ] 与现有组件集成测试
- [ ] 性能测试

#### 6.3 性能优化
- [ ] 分析瓶颈
- [ ] 优化热点代码
- [ ] 添加性能监控

### 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `tests/test_unified_models.py` | 新增 | 模型测试 |
| `tests/test_gateway.py` | 新增 | 网关测试 |
| `tests/test_hot_backup.py` | 新增 | 热备份测试 |
| `tests/test_enhanced_cache.py` | 新增 | 缓存测试 |
| `tests/test_fallback.py` | 新增 | 降级测试 |
| `tests/test_integration.py` | 修改 | 添加集成测试 |

### 测试覆盖目标

| 指标 | 目标值 |
|------|-------|
| 单元测试覆盖率 | > 80% |
| 集成测试用例 | > 50 |
| P99 延迟 | < 500ms |

---

## 依赖关系

```
Phase 1 (统一模型)
     │
     ▼
Phase 2 (DataGateway) ────┐
     │                    │
     ▼                    │
Phase 3 (热备份) ─────────┤
     │                    │
     ▼                    │
Phase 4 (增强缓存) ────────┤
     │                    │
     ▼                    │
Phase 5 (数据降级) ────────┤
     │                    │
     ▼                    ▼
         Phase 6 (测试与优化)
```

---

## 资源估算

| 阶段 | 代码行数 | 测试用例 | 预计时间 |
|------|---------|---------|---------|
| Phase 1 | ~200 | 10 | 2 天 |
| Phase 2 | ~400 | 15 | 3 天 |
| Phase 3 | ~500 | 20 | 3 天 |
| Phase 4 | ~400 | 15 | 2 天 |
| Phase 5 | ~300 | 10 | 2 天 |
| Phase 6 | ~100 | 30 | 2 天 |
| **总计** | ~1900 | 100 | **14 天** |

---

## 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| 性能不达标 | 中 | 高 | 早期性能测试 |
| 复杂度高 | 高 | 中 | 分阶段实施 |
| 兼容性问题 | 中 | 中 | 向后兼容设计 |
| 测试覆盖不足 | 中 | 高 | 强制测试覆盖 |

---

## 监控指标

### 运行指标

```python
# DataGateway
- total_requests
- success_rate
- average_latency_ms
- fallback_rate

# CircuitBreaker
- state_transitions
- failure_count
- recovery_count

# EnhancedCache
- hit_rate
- memory_usage_mb
- disk_usage_mb

# HotBackupManager
- sync_count
- backup_success_rate
- switch_count
```

### 告警阈值

| 指标 | 警告 | 严重 |
|------|------|------|
| 成功率 | < 95% | < 90% |
| P99 延迟 | > 500ms | > 1000ms |
| 缓存命中率 | < 60% | < 40% |
| 熔断器打开 | > 0 | > 3 |

---

## 附录

### A. 代码风格指南

所有新代码应遵循：
- 使用类型注解
- 遵循 PEP 8
- 文档字符串使用中文
- 异步方法使用 `async/await`

### B. Git 提交规范

```
feat: 新功能
fix: 修复 bug
refactor: 重构
test: 测试相关
docs: 文档相关
chore: 构建/工具
```

### C. 评审清单

- [ ] 代码符合设计文档
- [ ] 单元测试覆盖 > 80%
- [ ] 无性能回归
- [ ] 向后兼容
- [ ] 文档更新
