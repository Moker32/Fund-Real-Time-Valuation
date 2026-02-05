# 核心功能优化实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 修复失败的测试，重构自定义 Tabs 为官方 Flet API，优化数据源稳定性，提升整体代码质量和用户体验

**架构:** 保持现有分层架构，重点优化 GUI 层组件使用官方 API，修复数据源层的网络请求错误处理

**技术栈:** Python 3.10+, Flet 0.80.5, pytest, httpx, akshare

---

## 优先级说明

- **P0 (Critical)**: 影响核心功能的错误，必须修复
- **P1 (High)**: 代码质量问题，影响维护性
- **P2 (Medium)**: 用户体验优化

---

## 阶段一：修复失败测试 (优先级: P0)

### Task 1: 修复商品数据源测试失败

**问题分析:**
- `test_akshare_commodity.py`: 8个测试失败
- `test_akshare_sector.py`: 15个测试失败
- 失败原因可能是网络请求、API 变更、或数据格式问题

**文件:**
- Modify: `src/datasources/commodity_source.py`
- Modify: `src/datasources/sector_source.py`
- Modify: `tests/test_akshare_commodity.py`
- Modify: `tests/test_akshare_sector.py`

**Step 1: 运行失败测试并查看详细错误**

```bash
# 查看具体失败原因
pytest tests/test_akshare_commodity.py::TestYFinanceCommoditySource::test_commodity_tickers -vv
```

Expected: 看到具体错误信息（网络错误、断言失败等）

**Step 2: 检查 yfinance 数据源实现**

```python
# 检查 src/datasources/commodity_source.py 中的 YFinanceCommoditySource
# 确认是否有：
# 1. 网络请求超时设置
# 2. 错误处理逻辑
# 3. 数据格式验证
```

**Step 3: 添加超时和重试机制**

```python
# src/datasources/commodity_source.py
import asyncio
from httpx import TimeoutException

class YFinanceCommoditySource(DataSourceBase):
    REQUEST_TIMEOUT = 10.0  # 10秒超时
    MAX_RETRIES = 2

    async def _fetch_with_retry(self, url: str) -> dict:
        """带重试的网络请求"""
        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.json()
            except (TimeoutException, httpx.HTTPError) as e:
                if attempt == self.MAX_RETRIES - 1:
                    logger.warning(f"Failed after {self.MAX_RETRIES} retries: {e}")
                    raise
                await asyncio.sleep(1 * (attempt + 1))  # 指数退避
```

**Step 4: 修复数据解析逻辑**

```python
# 确保数据解析能处理空响应和异常格式
def _parse_response(self, data: dict) -> Optional[Commodity]:
    try:
        # 添加数据验证
        if not data or 'symbol' not in data:
            logger.warning(f"Invalid data format: {data}")
            return None

        return Commodity(
            symbol=data['symbol'],
            name=data.get('name', 'N/A'),
            price=float(data.get('regularMarketPrice', 0)),
            change=float(data.get('regularMarketChange', 0)),
        )
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Failed to parse commodity data: {e}")
        return None
```

**Step 5: 更新测试用例使用 Mock**

```python
# tests/test_akshare_commodity.py
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_fetch_gold():
    """测试获取黄金价格（使用 Mock）"""
    source = YFinanceCommoditySource()

    # Mock 网络请求
    mock_response = {
        'symbol': 'GC=F',
        'name': 'Gold Futures',
        'regularMarketPrice': 2024.50,
        'regularMarketChange': 12.30,
    }

    with patch.object(source, '_fetch_with_retry', new=AsyncMock(return_value=mock_response)):
        commodity = await source.fetch('GC=F')

    assert commodity is not None
    assert commodity.symbol == 'GC=F'
    assert commodity.price == 2024.50
```

**Step 6: 运行测试验证修复**

```bash
pytest tests/test_akshare_commodity.py -v
```

Expected: 测试通过率提高

**Step 7: Commit**

```bash
git add src/datasources/commodity_source.py tests/test_akshare_commodity.py
git commit -m "fix: 修复商品数据源测试，添加超时重试机制"
```

---

### Task 2: 修复行业数据源测试失败

**文件:**
- Modify: `src/datasources/sector_source.py`
- Modify: `tests/test_akshare_sector.py`

**Step 1: 查看失败测试详情**

```bash
pytest tests/test_akshare_sector.py::TestSinaSectorDataSource::test_fetch_all -vv
```

**Step 2: 应用与 Task 1 相同的修复模式**

- 添加超时和重试机制
- 改进数据解析错误处理
- 使用 Mock 重写测试

**Step 3: Commit**

```bash
git add src/datasources/sector_source.py tests/test_akshare_sector.py
git commit -m "fix: 修复行业数据源测试，改进错误处理"
```

---

### Task 3: 修复依赖检查测试

**文件:**
- Modify: `src/gui/check_deps.py`
- Modify: `tests/test_check_deps.py`

**Step 1: 查看错误详情**

```bash
pytest tests/test_check_deps.py::TestDependencyCheck::test_check_package_version -vv
```

**Step 2: 修复导入路径或逻辑错误**

根据错误信息修复 `src/gui/check_deps.py` 中的问题

**Step 3: Commit**

```bash
git add src/gui/check_deps.py tests/test_check_deps.py
git commit -m "fix: 修复依赖检查测试"
```

---

## 阶段二：重构 Tabs 组件 (优先级: P1)

### Task 4: 使用官方 TabBar+Tabs API 替代自定义实现

**问题:** 当前使用自定义 Container+Row 实现 Tabs，与 CLAUDE.md 规范不符

**文件:**
- Modify: `src/gui/main.py:259-293` (移除自定义 Tabs)
- Modify: `src/gui/main.py:145-155` (使用官方 API)

**Step 1: 创建新分支测试 Tabs 重构**

```bash
git checkout -b refactor/tabs-api
```

**Step 2: 编写 TabBar+Tabs 的测试**

```python
# tests/test_gui_tabs.py
import flet as ft
from flet import TabBar, Tab, Tabs

def test_tab_bar_creation():
    """测试 TabBar 组件创建"""
    tab_bar = TabBar(
        tabs=[
            Tab(label="自选", icon=Icons.STAR_BORDER),
            Tab(label="商品", icon=Icons.TRENDING_UP),
            Tab(label="新闻", icon=Icons.NEWSPAPER),
        ],
    )

    assert len(tab_bar.tabs) == 3
    assert tab_bar.tabs[0].label == "自选"
```

**Step 3: 运行测试确保 Flet API 可用**

```bash
pytest tests/test_gui_tabs.py -v
```

Expected: PASS

**Step 4: 重构 main.py 使用官方 API**

```python
# src/gui/main.py
def _build_tabs(self):
    """构建 Tab 组件（使用官方 API）"""

    # TabBar 负责标签
    self.tab_bar = TabBar(
        tabs=[
            Tab(label="自选", icon=Icons.STAR_BORDER),
            Tab(label="商品", icon=Icons.TRENDING_UP),
            Tab(label="新闻", icon=Icons.NEWSPAPER),
        ],
        on_click=self._on_tab_click,
    )

    # Tabs 负责内容
    fund_tab = Container(content=self._fund_list_stack, expand=True)
    commodity_tab = Container(content=self._commodity_list_view, expand=True)
    news_tab = Container(content=self._news_list_view, expand=True)

    self.tabs = Tabs(
        content=Column([
            fund_tab,
            commodity_tab,
            news_tab,
        ]),
        length=3,
    )

    return Column([self.tab_bar, self.tabs])
```

**Step 5: 更新 _on_tab_click 处理逻辑**

```python
def _on_tab_click(self, e):
    """Tab 点击处理"""
    # Flet 0.80.5 的 TabBar 会自动管理选中状态
    # 只需要更新内容可见性
    selected_index = e.control.selected_index

    for i, tab_content in enumerate(self.tabs.content.controls[:]):
        tab_content.visible = (i == selected_index)
        tab_content.update()

    # 更新状态栏
    self.status_bar.content.controls[0].text = f"已切换到{['自选', '商品', '新闻'][selected_index]}"
    self.status_bar.update()
```

**Step 6: 运行集成测试**

```bash
pytest tests/test_integration.py -v
```

Expected: PASS

**Step 7: 手动测试 GUI**

```bash
python run_gui.py
```

验证：
- 点击 Tab 能正确切换
- 选中状态显示正确
- 内容区域正确切换

**Step 8: Commit**

```bash
git add src/gui/main.py tests/test_gui_tabs.py
git commit -m "refactor: 使用官方 TabBar+Tabs API 替代自定义实现"
```

---

## 阶段三：数据源稳定性优化 (优先级: P1)

### Task 5: 实现数据源健康检查和故障切换

**文件:**
- Modify: `src/datasources/manager.py`
- Create: `src/datasources/health.py` (健康检查模块)
- Test: `tests/test_datasource_health.py`

**Step 1: 创建健康检查模型**

```python
# src/datasources/health.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheckResult:
    source_name: str
    status: HealthStatus
    response_time_ms: float
    error_count: int
    last_check: datetime
    message: str = ""
```

**Step 2: 实现健康检查器**

```python
# src/datasources/health.py
class DataSourceHealthChecker:
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.health_history: dict[str, list[HealthCheckResult]] = {}

    async def check_source(self, source: DataSourceBase) -> HealthCheckResult:
        """检查单个数据源健康状态"""
        start_time = time.time()

        try:
            # 尝试获取少量数据
            test_data = await source.fetch_test()

            response_time = (time.time() - start_time) * 1000

            return HealthCheckResult(
                source_name=source.name,
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                error_count=0,
                last_check=datetime.now(),
                message="OK",
            )

        except Exception as e:
            return HealthCheckResult(
                source_name=source.name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error_count=1,
                last_check=datetime.now(),
                message=str(e),
            )
```

**Step 3: 集成到 DataSourceManager**

```python
# src/datasources/manager.py
class DataSourceManager:
    def __init__(self):
        self.health_checker = DataSourceHealthChecker()

    async def get_fund_data(self, code: str) -> Optional[Fund]:
        """获取基金数据（带故障切换）"""
        # 按优先级尝试数据源
        for source in self.sources['fund']:
            # 检查健康状态
            health = await self.health_checker.check_source(source)

            if health.status == HealthStatus.HEALTHY:
                try:
                    data = await source.fetch(code)
                    if data:
                        return data
                except Exception as e:
                    logger.warning(f"Source {source.name} failed: {e}")
                    continue

        return None
```

**Step 4: 编写测试**

```python
# tests/test_datasource_health.py
@pytest.mark.asyncio
async def test_health_check_healthy_source():
    """测试健康数据源检查"""
    source = MockFundSource(healthy=True)
    checker = DataSourceHealthChecker()

    result = await checker.check_source(source)

    assert result.status == HealthStatus.HEALTHY
    assert result.response_time_ms > 0

@pytest.mark.asyncio
async def test_health_check_unhealthy_source():
    """测试不健康数据源检查"""
    source = MockFundSource(healthy=False)
    checker = DataSourceHealthChecker()

    result = await checker.check_source(source)

    assert result.status == HealthStatus.UNHEALTHY
    assert result.error_count == 1
```

**Step 5: 运行测试**

```bash
pytest tests/test_datasource_health.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/datasources/manager.py src/datasources/health.py tests/test_datasource_health.py
git commit -m "feat: 添加数据源健康检查和故障切换"
```

---

## 阶段四：性能优化 (优先级: P2)

### Task 6: 优化基金卡片渲染性能

**文件:**
- Modify: `src/gui/components.py`
- Modify: `src/gui/main.py`

**Step 1: 分析性能瓶颈**

```python
# 添加性能日志
import time

def update_fund_cards(self, funds: list[Fund]):
    start = time.time()
    # ... 现有代码 ...
    elapsed = time.time() - start
    logger.info(f"Updated {len(funds)} fund cards in {elapsed:.3f}s")
```

**Step 2: 实现虚拟滚动**

对于大量基金列表，只渲染可见的卡片：

```python
# src/gui/components.py
class VirtualListView(Container):
    """虚拟滚动列表视图"""

    def __init__(self, item_builder: Callable, item_height: float = 100):
        self.item_builder = item_builder
        self.item_height = item_height
        self.visible_items = 10  # 可见项目数
        self.start_index = 0

        super().__init__(content=Column([]))

    def update_data(self, data: list):
        """更新数据（只渲染可见项）"""
        visible_data = data[self.start_index:self.start_index + self.visible_items]

        controls = [self.item_builder(item) for item in visible_data]
        self.content.content = controls
        self.update()
```

**Step 3: Commit**

```bash
git add src/gui/components.py
git commit -m "perf: 优化基金列表渲染性能，实现虚拟滚动"
```

---

## 阶段五：代码质量提升 (优先级: P1)

### Task 7: 完善 mypy 类型检查

**文件:**
- Create: `pyproject.toml` (配置 mypy)
- Modify: `src/gui/*.py` (添加缺失的类型注解)

**Step 1: 运行 mypy 检查**

```bash
uv run mypy src/ --ignore-missing-imports
```

**Step 2: 修复类型错误**

根据 mypy 输出逐一修复类型注解问题

**Step 3: Commit**

```bash
git add pyproject.toml src/
git commit -m "style: 完善 mypy 类型检查配置"
```

---

## 阶段六：文档和测试完善 (优先级: P2)

### Task 8: 完善 API 文档

**文件:**
- Create: `docs/API.md` (API 文档)
- Modify: `README.md` (补充使用示例)

**Step 1: 生成 API 文档**

```bash
# 使用 pdoc 生成文档
uv pip install pdoc
uv run pdoc src/datasources/base.py -o docs/
```

**Step 2: Commit**

```bash
git add docs/API.md README.md
git commit -m "docs: 完善 API 文档"
```

---

## 任务依赖关系

```
阶段一 (修复测试)
├── Task 1: 修复商品数据源 ──┐
├── Task 2: 修复行业数据源 ───┤
└── Task 3: 修复依赖检查 ─────┘

阶段二 (重构 Tabs)
└── Task 4: 使用官方 API

阶段三 (数据源稳定性)
└── Task 5: 健康检查 (无依赖)

阶段四 (性能优化)
└── Task 6: 虚拟滚动

阶段五 (代码质量)
└── Task 7: mypy 配置

阶段六 (文档)
└── Task 8: API 文档
```

---

## 执行顺序建议

1. **Day 1-2**: Task 1-3 (修复所有失败测试)
2. **Day 3**: Task 4 (重构 Tabs)
3. **Day 4-5**: Task 5 (数据源稳定性)
4. **Day 6**: Task 6-7 (性能和质量)
5. **Day 7**: Task 8 (文档) + 测试全部通过

---

## 验收标准

- [ ] 所有测试通过 (`pytest tests/ -v`)
- [ ] mypy 类型检查无错误 (`mypy src/`)
- [ ] ruff 代码风格检查无警告 (`ruff check src/`)
- [ ] GUI 手动测试 Tabs 切换正常
- [ ] 数据源故障切换工作正常
- [ ] 性能: 100 个基金卡片渲染 < 2秒

---

## 风险和注意事项

1. **网络依赖**: 商品和行业数据源测试依赖外部 API，可能不稳定
   - **缓解**: 使用 Mock 进行测试，真实 API 测试作为集成测试

2. **Flet API 兼容性**: TabBar+Tabs API 可能有未文档化的行为
   - **缓解**: 在新分支充分测试后再合并

3. **性能优化效果**: 虚拟滚动可能带来新的复杂度
   - **缓解**: 先测量性能瓶颈，确认需要优化再实施
