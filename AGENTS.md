# AGENTS.md

**基金实时估值 TUI 应用** - 供 AI Agent 操作的指南文档

## 项目概述

基于 Python + Textual 框架的基金实时估值 TUI 应用，提供基金估值监控、自选管理、大宗商品行情和财经新闻功能。

## 常用命令

```bash
# 运行应用
python run_tui.py
./run_tui.py

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/ -v               # 运行所有测试
pytest tests/ -v --tb=short    # 简洁错误输出
pytest tests/test_datasources.py -v  # 运行单个测试文件
pytest tests/ -k "test_name"   # 运行匹配的测试用例
```

## 技术栈

- **UI 框架**: Textual (TUI)
- **HTTP 客户端**: httpx
- **金融数据**: akshare, yfinance
- **配置格式**: YAML
- **网页解析**: beautifulsoup4
- **测试框架**: pytest, pytest-asyncio
- **Python 版本**: 3.10+

## 代码风格规范

### 导入顺序

```python
# 标准库
import asyncio
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# 第三方库
import httpx
import pytest

# 本地模块（相对导入）
from .base import DataSource, DataSourceResult
from ..config.models import Fund
```

### 数据模型

使用 `@dataclass` 定义数据模型，提供类型注解：

```python
@dataclass
class Fund:
    """基金基础模型"""
    code: str              # 基金代码
    name: str              # 基金名称

    def __hash__(self):
        return hash(self.code)

    def __eq__(self, other):
        if isinstance(other, Fund):
            return self.code == other.code
        return False
```

### 枚举类型

继承 `str, Enum` 以获得更好的序列化支持：

```python
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

### 抽象基类

使用 `ABC` 和 `@abstractmethod` 定义接口：

```python
class DataSource(ABC):
    """数据源抽象基类"""

    def __init__(self, name: str, source_type: DataSourceType, timeout: float = 10.0):
        self.name = name
        self.source_type = source_type
        self.timeout = timeout

    @abstractmethod
    async def fetch(self, *args, **kwargs) -> DataSourceResult:
        pass
```

### 异常处理

定义自定义异常类继承自 `DataSourceError`：

```python
class DataSourceError(Exception):
    """数据源基础异常类"""

    def __init__(self, message: str, source_type: DataSourceType, details: Optional[Dict] = None):
        self.message = message
        self.source_type = source_type
        self.details = details or {}
        super().__init__(self.message)


class NetworkError(DataSourceError):
    """网络异常"""
    pass


class DataParseError(DataSourceError):
    """数据解析异常"""
    pass
```

### 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 类名 | PascalCase | `FundTUIApp`, `DataSourceManager` |
| 函数/方法 | snake_case | `fetch_data()`, `get_status()` |
| 变量 | snake_case | `refresh_interval`, `total_cost` |
| 常量 | UPPER_SNAKE_CASE | `MAX_CONCURRENT`, `DEFAULT_TIMEOUT` |
| 私有成员 | 前缀 `_` | `_sources`, `_request_count` |
| 文件 | snake_case | `fund_source.py`, `test_datasources.py` |

### 注释规范

- 模块/类使用中文 docstring
- 复杂逻辑添加行内注释
- 类型注解必须完整

```python
async def fetch(self, source_type: DataSourceType, *args, **kwargs) -> DataSourceResult:
    """
    获取数据（自动选择数据源）

    Args:
        source_type: 数据源类型
        *args: 位置参数传递给数据源
        failover: 是否启用故障切换
        **kwargs: 关键字参数传递给数据源

    Returns:
        DataSourceResult: 第一个成功的数据源结果
    """
```

### 异步编程

- 使用 `async/await` 进行异步操作
- 使用 `asyncio.Semaphore` 控制并发
- 使用 `asyncio.gather` 并行执行

```python
async def fetch_batch(self, params_list: List[Dict[str, Any]], parallel: bool = True) -> List[DataSourceResult]:
    """批量获取数据"""
    async with self._semaphore:
        tasks = [self._fetch_one(params) for params in params_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
```

## 架构概览

```
run_tui.py              # 应用入口
src/
├── ui/                 # 界面层
│   ├── app.py          # 主应用 (FundTUIApp)
│   ├── widgets.py      # 表格、面板组件
│   └── screens.py      # 视图屏幕
├── datasources/        # 数据源层
│   ├── manager.py      # DataSourceManager (多数据源管理)
│   ├── base.py         # 数据源抽象基类
│   ├── aggregator.py   # 数据聚合器
│   ├── fund_source.py  # 基金数据源
│   ├── stock_source.py # 股票数据源
│   ├── bond_source.py  # 债券数据源
│   ├── crypto_source.py # 加密货币数据源
│   ├── sector_source.py # 行业数据源
│   ├── commodity_source.py # 商品数据源
│   ├── news_source.py  # 新闻数据源
│   └── portfolio.py    # 组合分析
└── config/             # 配置层
    ├── manager.py      # ConfigManager
    └── models.py       # 数据模型 (Fund, Holding, Commodity 等)
```

### 数据流

`配置 (YAML)` → `ConfigManager` → `DataSourceManager` → `UI 组件`

## 测试规范

### 测试文件命名

- 测试文件: `tests/test_*.py`
- Fixture 文件: `tests/conftest.py`

### 测试类结构

```python
class TestDataSourceType:
    """数据源类型枚举测试"""

    def test_fund_type(self):
        """测试基金类型"""
        assert DataSourceType.FUND.value == "fund"
```

### Mock 使用

```python
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_fetch_with_mock(self, source):
    """测试 Mock HTTP 响应"""
    mock_response = MagicMock()
    mock_response.json.return_value = {"price": 50000.0}

    with patch.object(source.client, 'get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        result = await source.fetch("BTCUSDT")

        assert result.success is True
```

### pytest-asyncio 标记

- 异步测试使用 `@pytest.mark.asyncio`
- Fixture 可以是异步函数

## 关键设计模式

### 数据源管理器

`DataSourceManager` 负责：
- 多数据源注册/注销
- 故障切换 (failover)
- 负载均衡 (round-robin)
- 健康检查与统计
- 请求限流

### 结果封装

所有数据源返回 `DataSourceResult`：

```python
@dataclass
class DataSourceResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: float = 0.0
    source: str = ""
    metadata: Optional[Dict] = None
```

### 响应式状态管理

应用使用 Textual 的响应式状态管理，通过 `@式` 装饰器实现 UI 自动更新。

## 配置存储

配置文件位于 `~/.fund-tui/`:
- `config.yaml` - 应用主配置
- `funds.yaml` - 基金自选/持仓
- `commodities.yaml` - 商品关注列表

## UI 快捷键

| 按键 | 功能 |
|------|------|
| `Tab` | 切换视图 (基金/商品/新闻) |
| `1/2/3` | 快速切换视图 |
| `r` | 手动刷新 |
| `t` | 切换主题 |
| `F1` | 帮助 |
| `q` / `Ctrl+C` | 退出 |

## 开发注意事项

1. **DRY 原则**: 避免重复代码，提取公共逻辑
2. **类型注解**: 所有函数必须包含完整类型注解
3. **错误处理**: 网络请求必须包含超时和错误处理
4. **API 调用限制**: 注意第三方 API 的调用频率限制
5. **中文注释**: 代码注释使用中文
