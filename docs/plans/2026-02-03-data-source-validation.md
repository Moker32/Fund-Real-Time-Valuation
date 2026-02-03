# 基金实时估值 TUI 应用 - 数据源验证计划

**创建日期**: 2026-02-03
**目标**: 完整测试所有数据源的可用性

---

## 1. 验证范围

### 1.1 现有数据源

| 数据源 | 文件 | 状态 |
|--------|------|------|
| 天天基金 | `fund_source.py` | 待验证 |
| 新浪基金 | `fund_source.py` | 待验证 |
| AKShare 商品 | `commodity_source.py` | 待验证 |
| yfinance 商品 | `commodity_source.py` | 待验证 |
| 新浪新闻 | `news_source.py` | 待验证 |
| 新浪板块 | `sector_source.py` | 待验证 |
| 东方财富板块 | `sector_source.py` | 待验证 |

### 1.2 新增数据源 (计划中)

| 数据源 | 文件 | 状态 |
|--------|------|------|
| 新浪股票 | `stock_source.py` | 待实现 |
| Yahoo 股票 | `stock_source.py` | 待实现 |
| 新浪债券 | `bond_source.py` | 待实现 |
| AKShare 债券 | `bond_source.py` | 待实现 |
| Binance 加密 | `crypto_source.py` | 待实现 |
| CoinGecko 加密 | `crypto_source.py` | 待实现 |

---

## 2. 验证策略

### 2.1 测试分层

```
┌─────────────────────────────────────────────┐
│           Integration Tests                 │
│    (端到端验证 - 真实 API 调用)              │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│           Service Tests                     │
│    (服务层验证 - 模拟数据)                   │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│           Unit Tests                        │
│    (单元测试 - 数据结构与逻辑)               │
└─────────────────────────────────────────────┘
```

### 2.2 验证指标

- **可用性**: API 是否可访问
- **正确性**: 返回数据格式是否正确
- **时效性**: 响应时间是否可接受 (<5s)
- **稳定性**: 连续调用是否稳定

---

## 3. 测试用例设计

### 3.1 单元测试

**File**: `tests/test_base.py`

```python
import pytest
from src.datasources.base import (
    DataSourceType,
    DataSourceResult,
    DataSourceError,
)


class TestDataSourceType:
    """数据源类型枚举测试"""

    def test_all_types_defined(self):
        """验证所有类型已定义"""
        assert DataSourceType.FUND.value == "fund"
        assert DataSourceType.COMMODITY.value == "commodity"
        assert DataSourceType.NEWS.value == "news"
        assert DataSourceType.SECTOR.value == "sector"
        assert DataSourceType.STOCK.value == "stock"  # 新增
        assert DataSourceType.BOND.value == "bond"    # 新增
        assert DataSourceType.CRYPTO.value == "crypto"  # 新增


class TestDataSourceResult:
    """数据源结果测试"""

    def test_success_result(self):
        """成功结果"""
        result = DataSourceResult(
            success=True,
            data={"price": 100.0},
            source="test_source"
        )
        assert result.success is True
        assert result.data["price"] == 100.0
        assert result.error is None

    def test_failure_result(self):
        """失败结果"""
        result = DataSourceResult(
            success=False,
            error="Network error",
            source="test_source"
        )
        assert result.success is False
        assert result.error == "Network error"

    def test_timestamp_auto_set(self):
        """时间戳自动设置"""
        import time
        result = DataSourceResult(success=True)
        assert result.timestamp > 0
        assert abs(result.timestamp - time.time()) < 1
```

---

### 3.2 服务测试 (模拟数据)

**File**: `tests/test_fund_service.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.datasources.fund_source import FundDataSource
from src.datasources.base import DataSourceResult


class TestFundDataSourceService:
    """基金数据源服务测试 (Mock)"""

    @pytest.fixture
    def mock_client(self):
        """Mock HTTP 客户端"""
        client = AsyncMock()
        return client

    @pytest.fixture
    def source(self, mock_client):
        """创建数据源实例 (使用 Mock 客户端)"""
        source = FundDataSource()
        source.client = mock_client
        return source

    @pytest.mark.asyncio
    async def test_fetch_valid_fund(self, source, mock_client):
        """测试获取有效基金"""
        # Mock 响应
        mock_response = MagicMock()
        mock_response.text = 'jsonpgz({"fundcode":"161039","name":"测试","gsz":1.5,"gszzl":2.5});'
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        result = await source.fetch("161039")

        assert result.success is True
        assert result.data["fund_code"] == "161039"
        assert result.data["estimated_growth_rate"] == 2.5

    @pytest.mark.asyncio
    async def test_fetch_invalid_fund_code(self, source):
        """测试无效基金代码"""
        result = await source.fetch("invalid")

        assert result.success is False
        assert "无效" in result.error

    @pytest.mark.asyncio
    async def test_fetch_network_error(self, source, mock_client):
        """测试网络错误处理"""
        import httpx
        mock_client.get.side_effect = httpx.RequestError("Connection failed")

        result = await source.fetch("161039")

        assert result.success is False
        assert result.error is not None
```

---

### 3.3 集成测试 (真实 API)

**File**: `tests/test_integration.py`

```python
import pytest
import asyncio
from src.datasources.fund_source import FundDataSource
from src.datasources.commodity_source import YFinanceCommoditySource, AKShareCommoditySource


class TestFundIntegration:
    """基金数据源集成测试 (真实 API)"""

    @pytest.fixture
    def fund_source(self):
        return FundDataSource()

    @pytest.mark.asyncio
    async def test_fetch_real_fund(self, fund_source):
        """测试获取真实基金数据"""
        result = await fund_source.fetch("161039")

        # 由于是真实 API，结果可能是成功或网络问题
        assert result.source == "fund_tiantian"

        if result.success:
            assert result.data is not None
            assert "fund_code" in result.data
            assert "estimated_growth_rate" in result.data
        else:
            # 网络问题时应该有错误信息
            assert result.error is not None


class TestCommodityIntegration:
    """商品数据源集成测试 (真实 API)"""

    @pytest.fixture
    def yfinance_source(self):
        return YFinanceCommoditySource()

    @pytest.fixture
    def akshare_source(self):
        return AKShareCommoditySource()

    @pytest.mark.asyncio
    async def test_fetch_gold_yfinance(self, yfinance_source):
        """测试 yfinance 获取黄金"""
        result = await yfinance_source.fetch("gold")

        assert result.source == "yfinance_commodity"

        if result.success:
            assert result.data is not None
            assert "price" in result.data
            assert result.data["price"] > 0

    @pytest.mark.asyncio
    async def test_fetch_gold_cny_akshare(self, akshare_source):
        """测试 AKShare 获取国内黄金"""
        result = await akshare_source.fetch("gold_cny")

        assert result.source == "akshare_commodity"

        if result.success:
            assert result.data is not None
            assert result.data["commodity"] == "gold_cny"


class TestDataSourceManagerIntegration:
    """数据源管理器集成测试"""

    @pytest.fixture
    def manager(self):
        from src.datasources.manager import create_default_manager
        return create_default_manager()

    @pytest.mark.asyncio
    async def test_fetch_fund_via_manager(self, manager):
        """通过管理器获取基金数据"""
        from src.datasources.base import DataSourceType

        result = await manager.fetch(DataSourceType.FUND, "161039")

        assert result.source is not None

    @pytest.mark.asyncio
    async def test_health_check(self, manager):
        """健康检查"""
        health = await manager.health_check()

        assert "total_sources" in health
        assert "healthy_count" in health
        assert "sources" in health
```

---

## 4. 测试配置

### 4.1 pytest 配置

**File**: `pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
filterwarnings =
    ignore::DeprecationWarning
    ignore::pytest.PytestUnraisableExceptionWarning
```

### 4.2 conftest.py

**File**: `tests/conftest.py`

```python
import pytest
import asyncio
from typing import AsyncGenerator


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def anyio_backend():
    """指定 asyncio 后端"""
    return "asyncio"
```

---

## 5. 验证报告

### 5.1 报告模板

```markdown
## 数据源验证报告

### 执行时间: YYYY-MM-DD HH:MM

### 测试结果汇总

| 数据源 | 可用性 | 响应时间 | 数据正确性 |
|--------|--------|----------|------------|
| 天天基金 | ✅/❌ | XXXms | ✅/❌ |
| yfinance | ✅/❌ | XXXms | ✅/❌ |
| ... | ... | ... | ... |

### 问题列表

| # | 数据源 | 问题描述 | 严重程度 |
|---|--------|----------|----------|
| 1 | xxx | xxx | P0/P1/P2 |

### 建议措施

- xxx
```

### 5.2 自动化报告生成

```python
# scripts/generate_test_report.py
import pytest
import json
from datetime import datetime
from pathlib import Path


def generate_report(test_results: dict) -> str:
    """生成测试报告"""
    report = f"""
# 数据源验证报告

## 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 测试结果汇总

| 数据源 | 可用性 | 响应时间 |
|--------|--------|----------|
"""

    for source, result in test_results.items():
        status = "✅" if result["success"] else "❌"
        report += f"| {source} | {status} | {result['response_time']}ms |\n"

    return report
```

---

## 6. 运行命令

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_fund_source.py -v
pytest tests/test_comtegration.py -v

# 运行集成测试 (真实 API)
pytest tests/test_integration.py -v

# 生成覆盖率报告
pytest tests/ --cov=src/datasources --cov-report=html

# 生成验证报告
pytest tests/ --tb=no -q | python scripts/generate_test_report.py
```

---

## 7. 时间估算

| 阶段 | 任务 | 预估时间 |
|------|------|----------|
| 阶段 1 | 单元测试 (base, models) | 1h |
| 阶段 2 | 服务测试 (mock) | 2h |
| 阶段 3 | 集成测试 (真实 API) | 2h |
| 阶段 4 | 报告生成 | 30min |

**总计**: ~5.5h
