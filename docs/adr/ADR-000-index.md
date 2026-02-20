# ADR-001: 采用 FastAPI + Vue 3 分离架构

**状态**: 已接受

**日期**: 2026-02-09

**决策者**: 项目架构团队

## 1. 背景

项目最初使用 Flet 桌面框架开发，但存在以下问题：

- Flet 框架定制能力有限，难以实现复杂的金融数据可视化
- 部署方式受限，无法轻松实现 Web 访问
- 社区支持和生态相对较弱

需要选择新的技术栈来支持更灵活的部署和更好的用户体验。

## 2. 决策

采用 **FastAPI (后端) + Vue 3 (前端)** 分离架构：

| 层级 | 技术选择 | 说明 |
|------|----------|------|
| 后端框架 | FastAPI 0.104.0 | 高性能异步 Web 框架，原生支持 OpenAPI |
| 前端框架 | Vue 3.4+ | Composition API，响应式数据绑定 |
| 构建工具 | Vite 5.x | 极速开发体验，热更新 |
| 语言 | TypeScript 5.x | 类型安全 |
| 状态管理 | Pinia | 轻量级 Vue 状态管理 |
| HTTP 客户端 | httpx (后端) / Axios (前端) | 异步 HTTP 请求 |

## 3. 后果

### 正面

- **灵活性**: 支持 Web 部署，可跨平台访问
- **性能**: FastAPI 异步非阻塞，高并发处理能力强
- **开发效率**: Vue 3 + Vite 提供出色的开发体验
- **类型安全**: TypeScript 全链路类型检查
- **生态丰富**: FastAPI 和 Vue 都有庞大的社区支持

### 负面

- 需要维护两套代码仓库（虽然在同一项目下）
- 前后端联调需要额外沟通成本
- 部署复杂度增加（需要同时部署前后端）

## 4. 相关文档

- [Web 前端设计方案](./2026-02-09-web-frontend-design.md)

---

# ADR-002: 数据源抽象基类与管理器模式

**状态**: 已接受

**日期**: 2026-02-04

**决策者**: 项目架构团队

## 1. 背景

项目需要从多个外部数据源获取金融数据（基金、商品、指数等），不同数据源：

- API 接口和返回格式各异
- 稳定性和响应时间不同
- 可能随时出现故障

需要统一的数据获取抽象层。

## 2. 决策

采用 **数据源抽象基类 (DataSource)** + **管理器 (DataSourceManager)** 模式：

### 2.1 抽象基类定义

```python
class DataSource(ABC):
    name: str
    source_type: DataSourceType
    timeout: float
    
    @abstractmethod
    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        pass
```

### 2.2 返回结果封装

```python
@dataclass
class DataSourceResult:
    success: bool
    data: Any | None = None
    error: str | None = None
    timestamp: float = 0.0
    source: str = ""
    metadata: dict | None = None
```

### 2.3 管理器核心功能

- **多数据源注册**: 统一管理多个数据源实例
- **故障切换 (Failover)**: 主数据源失败时自动切换到备用源
- **负载均衡**: 支持轮询模式的负载均衡
- **健康检查**: 定期检查数据源状态，动态调整选择策略
- **请求限流**: 使用信号量控制并发数量

### 2.4 数据源类型枚举

```python
class DataSourceType(Enum):
    FUND = "fund"
    COMMODITY = "commodity"
    NEWS = "news"
    SECTOR = "sector"
    STOCK = "stock"
    BOND = "bond"
    CRYPTO = "crypto"
```

## 3. 后果

### 正面

- **统一接口**: 所有数据源遵循相同接口，便于扩展
- **高可用**: 故障自动切换，减少服务中断
- **可观测**: 健康检查和请求统计便于监控
- **可测试**: 抽象基类便于 Mock 和单元测试

### 负面

- 增加了代码复杂度
- 需要维护数据源配置和优先级

## 4. 相关文档

- [数据源模块 AGENTS.md](../src/datasources/AGENTS.md)

---

# ADR-003: 三级缓存策略

**状态**: 已接受

**日期**: 2026-02-04

**决策者**: 项目架构团队

## 1. 背景

外部金融数据 API 存在以下问题：

- 请求频率限制
- 网络延迟不稳定
- 数据可能频繁更新

需要实现有效的缓存策略来平衡数据新鲜度和 API 负载。

## 2. 决策

实现 **三级缓存**策略，按优先级依次为：

```
内存缓存 → SQLite 数据库 → 外部 API
```

### 2.1 缓存层级

| 层级 | 存储介质 | 访问速度 | 容量 | 持久化 |
|------|----------|----------|------|--------|
| L1 | 内存 (dict/async cache) | 最快 (~1ms) | 小 | 否 |
| L2 | SQLite 数据库 | 中等 (~10ms) | 中 | 是 |
| L3 | 外部 API | 慢 (~100ms-30s) | 无限制 | N/A |

### 2.2 缓存键设计

```python
# 缓存键格式
cache_key = f"{source_type}:{data_type}:{identifier}:{time_range}"
# 例如: "fund:nav:161039:2024-01"
```

### 2.3 缓存过期策略

- **实时数据** (基金估值): 30 秒 - 1 分钟
- **日线数据** (历史净值): 1 天
- **静态数据** (基金基本信息): 1 周

### 2.4 缓存预热

应用启动时异步预加载热门数据到内存缓存：

```python
# 启动时预热
asyncio.create_task(cache_warmer.preload_all_cache(timeout=5))
asyncio.create_task(cache_warmer.preload_fund_info_cache(timeout=60))
```

## 3. 后果

### 正面

- **减少 API 调用**: 有效降低外部 API 请求频率
- **提升响应速度**: 内存缓存提供毫秒级响应
- **提高可用性**: API 故障时仍可从缓存提供服务
- **数据持久化**: SQLite 确保重启后仍有缓存

### 负面

- 内存占用增加
- 需要处理缓存一致性
- SQLite 在高并发下可能成为瓶颈

---

# ADR-004: 异步架构设计

**状态**: 已接受

**日期**: 2026-02-04

**决策者**: 项目架构团队

## 1. 背景

金融数据获取涉及大量外部 API 调用，存在网络 IO 等待。使用同步阻塞方式会导致：

- 并发能力受限
- 资源利用率低
- 响应时间过长

## 2. 决策

全面采用 **异步架构**：

### 2.1 异步 HTTP 客户端

```python
import httpx

async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get(url)
```

### 2.2 异步数据源

所有数据源继承 `DataSource` 抽象类，实现异步 `fetch()` 方法：

```python
class DataSource(ABC):
    @abstractmethod
    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        pass
```

### 2.3 FastAPI 异步路由

```python
@app.get("/api/funds/{code}")
async def get_fund(code: str):
    result = await data_source_manager.fetch(DataSourceType.FUND, code)
    return result
```

### 2.4 并发控制

使用 `asyncio.Semaphore` 控制最大并发数：

```python
self._semaphore = asyncio.Semaphore(max_concurrent=10)

async def fetch_data():
    async with self._semaphore:
        # 执行请求
```

### 2.5 后台任务

使用 `asyncio.create_task()` 启动非阻塞后台任务：

```python
# 缓存预热（不阻塞服务启动）
asyncio.create_task(cache_warmer.preload_all_cache(timeout=5))

# 健康检查
asyncio.create_task(manager.start_background_health_check())
```

## 3. 后果

### 正面

- **高并发**: 单进程可处理大量并发请求
- **低资源**: 减少线程开销
- **快速响应**: 异步 IO 减少等待时间

### 负面

- 学习曲线较陡
- 调试异步代码相对困难
- 需要注意 async/await 配套使用

---

# ADR-005: 全局异常处理与错误响应

**状态**: 已接受

**标准化日期**: 2026-02-09

**决策者**: 项目架构团队

## 1. 背景

API 需要向客户端返回一致的错误信息，便于前端统一处理和展示。

## 2. 决策

### 2.1 统一错误响应格式

```python
{
    "success": False,
    "error": "错误描述",
    "detail": "详细错误信息（可选）",
    "timestamp": "2026-02-09T10:00:00Z"
}
```

### 2.2 异常处理器

FastAPI 全局注册异常处理器：

```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.now().isoformat() + "Z",
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": str(exc) if app.debug else "服务器内部错误，请稍后重试",
            "timestamp": datetime.now().isoformat() + "Z",
        },
    )
```

### 2.3 数据源错误封装

所有数据源错误封装为 `DataSourceResult`：

```python
@dataclass
class DataSourceResult:
    success: bool
    data: Any | None = None
    error: str | None = None
    timestamp: float = 0.0
    source: str = ""
    metadata: dict | None = None
```

## 3. 后果

### 正面

- 前端可统一处理错误
- 便于日志记录和监控
- 调试信息可按需开启/关闭

### 负面

- 错误信息需要谨慎设计，避免泄露敏感信息

---

# ADR-006: 前端组件化与状态管理

**状态**: 已接受

**日期**: 2026-02-09

**决策者**: 项目架构团队

## 1. 背景

Vue 3 前端需要管理多种数据类型（基金、商品、指数等），需要清晰的组件结构和状态管理。

## 2. 决策

### 2.1 组件目录结构

```
web/src/
├── components/     # 公共组件 (FundCard, CommodityCard, etc.)
├── views/          # 页面视图 (FundsView, CommoditiesView, etc.)
├── stores/         # Pinia 状态管理
├── api/            # API 请求封装
├── composables/    # 组合式函数
└── types/          # TypeScript 类型定义
```

### 2.2 Pinia Store 设计

按功能模块划分 Store：

```typescript
// stores/fundStore.ts
export const useFundStore = defineStore('fund', () => {
  const funds = ref<Fund[]>([])
  const loading = ref(false)
  
  async function fetchFunds() { /* ... */ }
  
  return { funds, loading, fetchFunds }
})
```

### 2.3 类型定义

集中管理 TypeScript 类型：

```typescript
// types/index.ts
export interface Fund {
  code: string
  name: string
  netValue: number
  estimateValue?: number
  estimateChangePercent?: number
  // ...
}
```

### 2.4 API 请求封装

使用 Axios 封装请求：

```typescript
// api/index.ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
})
```

## 3. 后果

### 正面

- 代码结构清晰，易于维护
- 状态管理集中，便于调试
- 类型安全，减少运行时错误

### 负面

- 初始学习成本
- 小项目可能过度设计

---

# ADR-007: 交易日历多市场支持

**状态**: 已接受

**日期**: 2026-02-11

**决策者**: 项目架构团队

## 1. 背景

应用需要支持全球多个市场的交易日期查询，包括 A 股、港股、美股、日本股市、黄金交易所等。

## 2. 决策

### 2.1 支持的市场

| 市场代码 | 名称 | 数据源 |
|----------|------|--------|
| china | A股 (上海/深圳) | akshare |
| hk | 港股 | akshare |
| usa | 美股 | akshare |
| japan | 日本股市 | akshare |
| uk | 英国股市 | akshare |
| germany | 德国股市 | akshare |
| france | 法国股市 | akshare |
| sge | 上海黄金交易所 | akshare |
| comex | COMEX 黄金 | akshare |
| cme | CME 股指 | akshare |
| lbma | LBMA 黄金 | akshare |

### 2.2 API 端点设计

```bash
# 获取交易日历
GET /trading-calendar/calendar/{market}?year=2025

# 判断是否为交易日
GET /trading-calendar/is-trading-day/{market}?check_date=2025-01-28

# 获取下一个交易日
GET /trading-calendar/next-trading-day/{market}

# 批量获取市场状态
GET /trading-calendar/market-status?markets=china,usa
```

### 2.3 交易日历数据源

使用 akshare 的 `trade_cal` 接口获取各国交易日历。

## 3. 后果

### 正面

- 统一接口支持多市场
- 便于根据市场开放状态调整数据获取策略

### 负面

- 需要维护各市场节假日数据
- 部分市场数据可能不完整

---

# ADR-008: K 线图采用 lightweight-charts

**状态**: 已接受

**日期**: 2026-02-11

**决策者**: 项目架构团队

## 1. 背景

需要在基金卡片中展示历史净值的 K 线图/折线图，可视化展示基金走势。

## 2. 决策

采用 **lightweight-charts** 库实现 K 线图：

### 2.1 技术选型对比

| 库 | 体积 | 许可证 | 水印 | 适合场景 |
|------|------|--------|------|----------|
| lightweight-charts | ~30KB | Apache 2.0 | 无 | 金融图表（推荐） |
| uPlot | ~30KB | MIT | 无 | 简单折线图 |
| TradingView lightweight-charts | ~30KB | GPL v3 | 强制显示 | 不推荐（许可证问题） |

### 2.2 组件设计

```vue
<!-- FundChart.vue -->
<template>
  <div class="fund-chart" ref="chartContainer"></div>
</template>

<script setup>
import { createChart, ColorType } from 'lightweight-charts'

const props = defineProps<{
  data: FundHistory[]
  height?: number
}>()

// 初始化图表
const initChart = () => {
  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: props.height || 120,
    layout: { background: { type: ColorType.Solid, color: 'transparent' } },
    grid: { vertLines: { visible: false }, horzLines: { color: '#f0f0f0' } },
  })
  
  const candleSeries = chart.addCandlestickSeries({
    upColor: '#ef4444',
    downColor: '#22c55e',
  })
  
  if (props.data.length > 0) {
    candleSeries.setData(props.data)
  }
}
</script>
```

### 2.3 数据格式

OHLCV 格式：

```typescript
interface FundHistory {
  time: string      // 日期时间
  open: number      // 开盘价
  high: number      // 最高价
  low: number       // 最低价
  close: number    // 收盘价
  volume: number    // 成交量
}
```

## 3. 后果

### 正面

- 体积小，性能好
- 专为金融图表设计
- 无水印，许可证友好

### 负面

- 需要处理窗口 resize 事件
- 需要适配数据格式

---

# ADR-009: 配置管理与敏感信息分离

**状态**: 已接受

**日期**: 2026-02-04

**决策者**: 项目架构团队

## 1. 背景

项目配置包含敏感信息（如 API 密钥）和用户自定义数据，需要安全且灵活的管理方式。

## 2. 决策

### 2.1 配置文件位置

用户配置存放在 `~/.fund-tui/` 目录：

```
~/.fund-tui/
├── config.yaml      # 应用主配置
├── funds.yaml       # 基金自选/持仓
├── commodities.yaml # 商品关注列表
└── fund_data.db    # SQLite 数据库（缓存）
```

### 2.2 配置格式

使用 YAML 格式，便于阅读和编辑：

```yaml
# config.yaml
app:
  log_level: INFO
  refresh_interval: 30

datasources:
  timeout: 30
  retry_count: 3

# funds.yaml
funds:
  - code: 161039
    name: 富国中证新能源汽车
    holding: true
    shares: 1000
    cost: 1.85
```

### 2.3 配置加载

```python
from pathlib import Path
import yaml

CONFIG_DIR = Path.home() / ".fund-tui"

def load_config(name: str) -> dict:
    config_path = CONFIG_DIR / f"{name}.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}
```

## 3. 后果

### 正面

- 敏感信息不随代码仓库泄露
- 用户可自定义配置
- 便于迁移和备份

### 负面

- 需要处理配置文件不存在的情况
- 多环境配置需要额外管理

---

# ADR-010: 数据源健康检查与动态路由

**状态**: 已接受

**日期**: 2026-02-13

**决策者**: 项目架构团队

## 1. 背景

外部数据源可能随时出现故障或性能下降，需要实时监控并在请求时动态选择最健康的数据源。

## 2. 决策

### 2.1 健康检查机制

```python
class DataSourceHealthChecker:
    def __init__(self, check_interval: int = 60):
        # check_interval: 健康检查间隔（秒）
    
    async def check_source(self, source: DataSource) -> HealthCheckResult:
        # 执行实际请求测试
        # 返回：健康/降级/不健康
    
    async def check_all_sources(self, sources: list[DataSource]) -> dict[str, HealthCheckResult]:
        # 并行检查所有数据源
```

### 2.2 健康状态枚举

```python
class HealthStatus(Enum):
    HEALTHY = "healthy"    # 正常
    DEGRADED = "degraded"  # 降级（响应慢）
    UNHEALTHY = "unhealthy" # 不健康（频繁失败）
```

### 2.3 动态路由策略

请求时优先选择最健康的数据源：

```python
async def fetch(self, source_type: DataSourceType, health_aware: bool = True):
    if health_aware:
        # 获取最健康的数据源排在前面
        healthy_source = await health_interceptor.get_healthy_source(sources)
        sources = [healthy_source] + [s for s in sources if s != healthy_source]
    
    for source in sources:
        if health_interceptor.should_skip_source(source.name):
            continue  # 跳过不健康的数据源
        
        result = await source.fetch(...)
        if result.success:
            return result
```

### 2.4 后台健康检查

应用启动时启动后台健康检查任务：

```python
asyncio.create_task(manager.start_background_health_check())
```

## 3. 后果

### 正面

- 自动绕过故障数据源
- 实时监控数据源状态
- 提高服务可用性

### 负面

- 增加系统复杂度
- 健康检查本身消耗资源
- 需要合理设置检查间隔

---

# ADR-011: 前端 K 线图时间显示优化

**状态**: 已接受

**日期**: 2026-02-13

**决策者**: 项目架构团队

## 1. 背景

K 线图需要展示多个市场（A股、港股、美股）的数据，不同市场有时区差异，需要正确处理时间显示。

## 2. 决策

### 2.1 时间戳处理

- A 股数据：使用中国时区 (UTC+8)
- 港股数据：使用香港时区 (UTC+8)
- 美股数据：使用美国时区 (EST/EDT)
- 国际商品：使用 UTC 时间

### 2.2 延迟标签显示

根据数据延迟情况显示标签：

```typescript
const getDelayTag = (timestamp: number): string => {
  const now = Date.now()
  const delayMinutes = (now - timestamp) / 60000
  
  if (delayMinutes < 5) return '实时'
  if (delayMinutes < 60) return `${Math.floor(delayMinutes)}分钟前`
  if (delayMinutes < 1440) return `${Math.floor(delayMinutes / 60)}小时前`
  return `${Math.floor(delayMinutes / 1440)}天前`
}
```

### 2.3 时区自动适配

```typescript
const getTimezone = (market: string): string => {
  const timezoneMap: Record<string, string> = {
    china: 'Asia/Shanghai',
    hk: 'Asia/Hong_Kong',
    usa: 'America/New_York',
    japan: 'Asia/Tokyo',
  }
  return timezoneMap[market] || 'UTC'
}
```

## 3. 后果

### 正面

- 用户可清晰了解数据时效性
- 多市场数据时间展示准确

### 负面

- 需要维护市场与时区的映射关系

---

# ADR-012: 商品分类与关注列表设计

**状态**: 已接受

**日期**: 2026-02-12

**决策者**: 项目架构团队

## 1. 背景

商品市场包含多种类型（贵金属、能源化工、农产品等），用户需要按分类浏览和关注特定商品。

## 2. 决策

### 2.1 商品分类体系

| 分类 | 商品示例 |
|------|----------|
| 贵金属 | 黄金、白银、铂金、钯金 |
| 能源 | WTI 原油、布伦特原油、天然气 |
| 基础金属 | 铜、铝、锌、镍 |
| 农产品 | 大豆、玉米、小麦 |
| 加密货币 | BTC、ETH |

### 2.2 API 设计

```bash
# 获取商品分类
GET /api/commodities/categories

# 按分类获取商品
GET /api/commodities?category=贵金属

# 获取关注列表
GET /api/commodities/watchlist

# 添加关注
POST /api/commodities/watchlist
{
  "symbol": "XAU",
  "category": "贵金属",
  "name": "黄金"
}

# 移除关注
DELETE /api/commodities/watchlist/{symbol}
```

### 2.3 数据源集成

- **国内黄金 (SGE)**: 上海黄金交易所（akshare）
- **国际黄金/白银 (XAU/XAG)**: yfinance
- **原油 (WTI/Brent)**: yfinance
- **加密货币**: Binance / CoinGecko

## 3. 后果

### 正面

- 商品分类清晰，便于浏览
- 关注列表支持个性化
- 多数据源确保数据可用性

### 负面

- 分类标准可能需要调整
- 部分商品数据源可能不稳定
