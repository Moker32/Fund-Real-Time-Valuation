# API 文档

## 数据源 API

### DataSourceBase

数据源抽象基类，所有数据源都应继承此类。

```python
from src.datasources.base import DataSourceBase

class CustomDataSource(DataSourceBase):
    name = "custom_source"

    async def fetch(self, code: str) -> Optional[Fund]:
        """获取数据"""
        pass
```

### DataSourceManager

数据源管理器，负责管理多个数据源并提供故障切换功能。

```python
from src.datasources.manager import DataSourceManager

# 创建管理器
manager = DataSourceManager()

# 注册数据源
manager.register_source(fund_source, "fund")

# 获取数据
fund = await manager.fetch(code, "fund")

# 健康感知获取（自动故障切换）
fund = await manager.fetch(code, "fund", health_aware=True)

# 健康检查
health = await manager.health_check_all_sources()
statistics = manager.get_health_statistics()
```

### DataSourceHealthChecker

数据源健康检查器，监控数据源状态。

```python
from src.datasources.health import DataSourceHealthChecker, HealthStatus

# 创建检查器
checker = DataSourceHealthChecker(check_interval=60)

# 检查单个数据源
result = await checker.check_source(source)
if result.status == HealthStatus.HEALTHY:
    print(f"响应时间: {result.response_time_ms}ms")
else:
    print(f"错误: {result.message}")

# 获取健康历史
history = checker.get_health_history(source.name)
```

## 配置 API

### ConfigManager

配置管理器，负责加载和保存配置。

```python
from src.config.manager import ConfigManager

# 创建配置管理器
config = ConfigManager()

# 加载配置
config.load()

# 获取基金列表
funds = config.get_funds()

# 添加基金
config.add_fund(Fund(code="000001", name="华夏成长"))

# 保存配置
config.save()
```

## 数据模型

### Fund

基金基础模型。

```python
from src.config.models import Fund

fund = Fund(
    code="000001",
    name="华夏成长"
)
```

### Holding

持仓模型，继承自 Fund。

```python
from src.config.models import Holding

holding = Holding(
    code="000001",
    name="华夏成长",
    shares=1000,  # 持有份额
    cost=1.5      # 成本价
)

# 计算总成本
total_cost = holding.total_cost
```

### Commodity

商品模型。

```python
from src.config.models import Commodity

commodity = Commodity(
    symbol="GC=F",  # 商品代码
    name="黄金期货",
    price=2024.50,  # 当前价格
    change=12.30    # 涨跌额
)
```

## GUI API

### FundGUIApp

主应用类。

```python
from src.gui.main import FundGUIApp
import flet as ft

# 创建应用
app = FundGUIApp()

# 启动 GUI
ft.app(target=app.main)
```

### FundCard

基金卡片组件。

```python
from src.gui.components import FundCard

card = FundCard(
    code="000001",
    name="华夏成长",
    net_value=1.5,
    change_pct=0.5,
    on_click=lambda e: print("点击了基金卡片")
)
```

## 完整示例

### 基金数据获取

```python
import asyncio
from src.datasources.manager import DataSourceManager
from src.config.manager import ConfigManager

async def fetch_fund_data():
    # 初始化管理器
    config = ConfigManager()
    config.load()

    manager = DataSourceManager()
    manager.initialize_from_config(config)

    # 获取基金数据
    fund = await manager.fetch("000001", "fund")
    if fund:
        print(f"{fund.name}: {fund.net_value}")

if __name__ == "__main__":
    asyncio.run(fetch_fund_data())
```

### 健康检查和故障切换

```python
import asyncio
from src.datasources.manager import DataSourceManager
from src.datasources.health import HealthStatus

async def monitor_data_sources():
    manager = DataSourceManager()

    # 检查所有数据源健康状态
    health_results = await manager.health_check_all_sources()

    for result in health_results:
        if result.status == HealthStatus.HEALTHY:
            print(f"✓ {result.source_name}: {result.response_time_ms:.0f}ms")
        elif result.status == HealthStatus.DEGRADED:
            print(f"⚠ {result.source_name}: 降级 ({result.response_time_ms:.0f}ms)")
        else:
            print(f"✗ {result.source_name}: 不可用")

    # 获取统计数据
    stats = manager.get_health_statistics()
    print(f"健康数据源: {stats['healthy_count']}")
    print(f"不健康数据源: {stats['unhealthy_count']}")

if __name__ == "__main__":
    asyncio.run(monitor_data_sources())
```

## 更多信息

- 生成的 API 文档: [docs/api/index.html](docs/api/index.html)
- 数据源实现: [src/datasources/](src/datasources/)
- 配置管理: [src/config/](src/config/)
- GUI 组件: [src/gui/](src/gui/)
