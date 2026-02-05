# 项目推进计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 完善项目占位功能、优化用户体验、增强实用功能，使项目达到稳定可用的 Beta 2.0 版本

**架构:** 基于现有的清晰分层架构 (GUI/DataSource/Config/DB)，继续完善功能模块，遵循 DRY 和 YAGNI 原则

**技术栈:** Python 3.10+, Flet 0.80.5, SQLite, YAML, httpx, akshare

---

## 阶段一：完善占位功能 (优先级: P0)

### Task 1: 实现通知系统

**文件:**
- Modify: `src/gui/main.py:1450-1470` (实现 `_show_notifications`)
- Create: `src/gui/notifications.py` (通知管理模块)
- Modify: `src/config/models.py` (添加通知配置模型)
- Test: `tests/test_notifications.py`

**Step 1: 设计并创建通知数据模型**

```python
# src/config/models.py 添加
class NotificationConfig(BaseModel):
    enabled: bool = True
    price_alerts: List[PriceAlert] = []
    daily_summary: bool = True
    alert_sound: bool = False

class PriceAlert(BaseModel):
    fund_code: str
    target_price: float
    direction: Literal["above", "below"]  # above/below
    triggered: bool = False
    created_at: datetime
```

**Step 2: 创建通知管理模块**

```python
# src/gui/notifications.py
class NotificationManager:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.alerts: List[PriceAlert] = []

    async def check_price_alerts(self, funds: List[Fund]):
        """检查价格预警"""
        # 遍历基金和预警配置
        # 触发时显示通知

    def show_notification(self, title: str, message: str):
        """显示系统通知 (Flet)"""
        pass
```

**Step 3: 实现通知对话框 UI**

```python
# src/gui/notifications.py
class NotificationDialog(BaseDialog):
    def __init__(self):
        # 显示预警列表
        # 提供添加/编辑/删除功能
```

**Step 4: 运行测试验证**

Run: `pytest tests/test_notifications.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/gui/notifications.py src/config/models.py
git commit -m "feat: 实现通知系统基础框架"
```

---

### Task 2: 实现设置对话框

**文件:**
- Modify: `src/gui/main.py:1480-1510` (实现 `_show_settings`)
- Create: `src/gui/settings.py` (设置对话框组件)
- Modify: `src/config/manager.py` (添加设置保存方法)
- Test: `tests/test_settings.py`

**Step 1: 创建设置对话框组件**

```python
# src/gui/settings.py
class SettingsDialog(BaseDialog):
    def __init__(self, app_config: AppConfig, on_save: Callable):
        self.on_save = on_save
        self.refresh_interval = TextField(
            label="刷新间隔(秒)",
            value=str(app_config.refresh_interval),
        )
        self.dark_theme = Switch(
            label="深色模式",
            value=app_config.theme == "dark",
        )
        self.notifications = Switch(
            label="启用通知",
            value=app_config.notification_enabled,
        )

    def build(self):
        return AlertDialog(
            title="设置",
            content=Column([
                self.refresh_interval,
                self.dark_theme,
                self.notifications,
            ]),
            actions=[
                TextButton("取消"),
                TextButton("保存", on_click=self._save),
            ],
        )
```

**Step 2: 添加配置保存方法**

```python
# src/config/manager.py
class ConfigManager:
    def save_app_config(self, config: AppConfig):
        """保存应用配置"""
        self._data["app"] = config.model_dump()
        self.save()
```

**Step 3: 测试设置对话框**

```python
# tests/test_settings.py
def test_settings_dialog_renders():
    dialog = SettingsDialog(AppConfig(), lambda: None)
    assert dialog.refresh_interval is not None
    assert dialog.dark_theme is not None
```

**Step 4: Commit**

```bash
git add src/gui/settings.py src/config/manager.py
git commit -m "feat: 实现设置对话框"
```

---

### Task 3: 整合设置入口到主界面

**文件:**
- Modify: `src/gui/main.py:600-650` (添加工具栏设置按钮)
- Modify: `src/gui/theme.py` (添加图标颜色)

**Step 1: 在主界面添加工具栏**

```python
# src/gui/main.py
self.settings_button = IconButton(
    icon=Icons.SETTINGS,
    on_click=self._show_settings,
    tooltip="设置",
)
self.tool_bar.controls.insert(0, self.settings_button)
```

**Step 2: Commit**

```bash
git add src/gui/main.py
git commit -m "feat: 添加工具栏设置入口"
```

---

## 阶段二：错误处理与用户体验优化 (优先级: P0)

### Task 4: 全局错误处理

**文件:**
- Modify: `src/gui/main.py:100-150` (添加错误处理器)
- Create: `src/gui/error_handling.py` (错误处理工具)
- Test: `tests/test_error_handling.py`

**Step 1: 创建错误处理工具**

```python
# src/gui/error_handling.py
import traceback
from flet import Page

def setup_error_handling(page: Page):
    def handle_error(e):
        # 收集错误信息
        error_msg = f"错误: {str(e)}\n{traceback.format_exc()}"
        # 显示错误对话框
        page.show_error_dialog(error_msg)

    page.on_error = handle_error

def show_error_dialog(page: Page, message: str):
    page.show_dialog(
        AlertDialog(
            title=Text("错误"),
            content=Text(message),
            actions=[TextButton("确定", on_click=lambda _: page.close_dialog())],
        )
    )
```

**Step 2: 在主应用初始化时调用**

```python
# src/gui/main.py
class FundGUIApp:
    def __init__(self):
        self.page.on_error = self._handle_error
```

**Step 3: 测试错误处理**

```python
# tests/test_error_handling.py
def test_error_dialog_shows():
    page = Page()
    show_error_dialog(page, "Test error")
    # 验证对话框已显示
```

**Step 4: Commit**

```bash
git add src/gui/error_handling.py src/gui/main.py
git commit -m "feat: 添加全局错误处理"
```

---

### Task 5: 加载状态优化

**文件:**
- Modify: `src/gui/main.py:800-900` (优化数据加载反馈)
- Modify: `src/gui/components.py` (FundCard 添加加载状态)
- Test: `tests/test_loading.py`

**Step 1: 为 FundCard 添加加载状态**

```python
# src/gui/components.py
class FundCard:
    def __init__(self, fund: Fund):
        self.loading = False
        self.loading_indicator = ProgressRing(visible=False)

    def set_loading(self, loading: bool):
        self.loading = loading
        self.loading_indicator.visible = loading
        self.update()
```

**Step 2: 在数据加载时显示状态**

```python
# src/gui/main.py
async def _load_funds(self):
    self.refresh_button.disabled = True
    self.refresh_indicator.visible = True
    try:
        funds = await self.data_source.get_all_funds()
        # 更新数据...
    finally:
        self.refresh_button.disabled = False
        self.refresh_indicator.visible = False
```

**Step 3: Commit**

```bash
git add src/gui/components.py src/gui/main.py
git commit -m "feat: 优化加载状态反馈"
```

---

### Task 6: 空状态处理

**文件:**
- Modify: `src/gui/main.py:700-750` (添加空状态提示)
- Create: `src/gui/empty_states.py` (空状态组件)

**Step 1: 创建空状态组件**

```python
# src/gui/empty_states.py
def empty_funds_state() -> Container:
    return Container(
        content=Column([
            Icon(Icons.INBOX, size=48, color=Grey),
            Text("暂无自选基金", color=Grey),
            Text("点击右上角添加基金", color=Grey, size=12),
        ], alignment=MainAxisAlignment.CENTER, horizontal_alignment=CrossAxisAlignment.CENTER),
        expand=True,
    )
```

**Step 2: 在基金列表为空时显示**

```python
# src/gui/main.py
if len(self.fund_cards) == 0:
    self.fund_list_content.content = empty_funds_state()
else:
    self.fund_list_content.content = fund_list
```

**Step 3: Commit**

```bash
git add src/gui/empty_states.py src/gui/main.py
git commit -m "feat: 添加空状态处理"
```

---

## 阶段三：增强实用功能 (优先级: P1)

### Task 7: 数据导出功能

**文件:**
- Create: `src/utils/export.py` (导出工具)
- Modify: `src/gui/main.py` (添加导出按钮)
- Test: `tests/test_export.py`

**Step 1: 创建导出工具**

```python
# src/utils/export.py
import csv
from datetime import datetime
from pathlib import Path

def export_funds_to_csv(funds: list, filepath: Path):
    """导出基金列表到 CSV"""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "code", "name", "price", "change_pct", "hold_shares",
            "cost", "profit", "profit_pct", "updated_at"
        ])
        writer.writeheader()
        for fund in funds:
            writer.writerow({
                "code": fund.code,
                "name": fund.name,
                # ...
            })

def export_portfolio_report(holdings: list, filepath: Path):
    """导出持仓报告"""
    # 生成详细的 Markdown 报告
```

**Step 2: 在主界面添导出菜单**

```python
# src/gui/main.py
def _export_data(self, e):
    filepath = self.page.get_save_file(
        allowed_extensions=[".csv", ".md"],
    )
    if filepath:
        export_funds_to_csv(self.funds, Path(filepath))
        self.page.show_snack("导出成功")
```

**Step 3: 测试导出功能**

```python
# tests/test_export.py
def test_export_funds_to_csv(tmp_path):
    funds = [Fund(code="000001", name="测试基金")]
    export_funds_to_csv(funds, tmp_path / "funds.csv")
    assert (tmp_path / "funds.csv").exists()
```

**Step 4: Commit**

```bash
git add src/utils/export.py
git commit -m "feat: 添加数据导出功能"
```

---

### Task 8: 价格预警功能

**文件:**
- Modify: `src/gui/notifications.py` (添加预警功能)
- Modify: `src/config/models.py` (添加 PriceAlert 模型)
- Test: `tests/test_price_alerts.py`

**Step 1: 添加价格预警逻辑**

```python
# src/gui/notifications.py
class PriceAlertManager:
    def __init__(self, alerts: List[PriceAlert]):
        self.alerts = alerts

    def check_alerts(self, fund: Fund) -> List[PriceAlert]:
        """检查基金是否触发预警"""
        triggered = []
        for alert in self.alerts:
            if alert.fund_code == fund.code:
                if alert.direction == "above" and fund.price >= alert.target_price:
                    triggered.append(alert)
                elif alert.direction == "below" and fund.price <= alert.target_price:
                    triggered.append(alert)
        return triggered
```

**Step 2: 创建预警设置对话框**

```python
# src/gui/notifications.py
class PriceAlertDialog(BaseDialog):
    def __init__(self, fund: Fund, on_save: Callable):
        # 选择目标价格和方向 (高于/低于)
```

**Step 3: Commit**

```bash
git add src/gui/notifications.py src/config/models.py
git commit -m "feat: 添加价格预警功能"
```

---

### Task 9: 数据缓存层

**文件:**
- Create: `src/datasources/cache.py` (缓存管理器)
- Modify: `src/datasources/manager.py` (集成缓存)
- Test: `tests/test_cache.py`

**Step 1: 创建缓存管理器**

```python
# src/datasources/cache.py
import json
from datetime import datetime, timedelta
from pathlib import Path

class DataCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        filepath = self.cache_dir / f"{key}.json"
        if filepath.exists():
            with open(filepath) as f:
                data = json.load(f)
                if datetime.fromisoformat(data["expires"]) > datetime.now():
                    return data["value"]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """设置缓存"""
        filepath = self.cache_dir / f"{key}.json"
        data = {
            "value": value,
            "expires": (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat(),
        }
        with open(filepath, "w") as f:
            json.dump(data, f)
```

**Step 2: 在数据源管理器中集成**

```python
# src/datasources/manager.py
class DataSourceManager:
    def __init__(self):
        self.cache = DataCache(Path.home() / ".fund-tui/cache")

    async def get_fund_with_cache(self, code: str) -> Optional[Fund]:
        """带缓存的基金获取"""
        cached = self.cache.get(f"fund_{code}")
        if cached:
            return Fund(**cached)
        fund = await self.get_fund(code)
        if fund:
            self.cache.set(f"fund_{code}", fund.model_dump(), ttl_seconds=60)
        return fund
```

**Step 3: Commit**

```bash
git add src/datasources/cache.py src/datasources/manager.py
git commit -m "feat: 添加数据缓存层"
```

---

## 阶段四：测试与质量保障 (优先级: P1)

### Task 10: 集成测试

**文件:**
- Create: `tests/test_integration.py` (端到端测试)
- Modify: `tests/conftest.py` (添加 fixtures)

**Step 1: 创建集成测试 fixtures**

```python
# tests/conftest.py
@pytest.fixture
def app_config():
    return AppConfig(refresh_interval=60)

@pytest.fixture
def sample_funds():
    return [
        Fund(code="000001", name="测试基金", price=1.5),
        Fund(code="000002", name="测试基金2", price=2.0),
    ]
```

**Step 2: 编写集成测试**

```python
# tests/test_integration.py
def test_fund_list_workflow(app_config, sample_funds):
    """测试基金列表完整工作流程"""
    # 添加基金 -> 刷新数据 -> 显示卡片 -> 触发预警
```

**Step 3: Commit**

```bash
git add tests/test_integration.py tests/conftest.py
git commit -m "test: 添加集成测试"
```

---

### Task 11: 代码质量检查

**文件:**
- Create: `pyproject.toml` 添加类型检查配置
- Run: `mypy src/`
- Run: `ruff check src/`

**Step 1: 添加 mypy 配置**

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
```

**Step 2: 运行类型检查并修复**

```bash
pip install mypy ruff
mypy src/ --no-error-summary
ruff check src/ --fix
```

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: 添加代码质量检查配置"
```

---

## 阶段五：文档与发布准备 (优先级: P2)

### Task 12: 更新文档

**文件:**
- Modify: `README.md` (添加新功能说明)
- Modify: `AGENTS.md` (更新开发指南)
- Create: `CHANGELOG.md`

**Step 1: 创建 CHANGELOG**

```markdown
# Changelog

## [2.0.0] - 2025-02-XX

### Added
- 通知系统
- 设置对话框
- 数据导出功能
- 价格预警
- 数据缓存

### Fixed
- 错误处理优化
- 加载状态反馈
- 空状态处理

### Changed
- 升级到 Flet 0.80.5 最佳实践
```

**Step 2: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: 更新项目文档"
```

---

## 任务依赖关系

```
阶段一 (占位功能)
├── Task 1: 通知系统
├── Task 2: 设置对话框 ──┐
└── Task 3: 整合入口 ────┘

阶段二 (错误处理)
├── Task 4: 全局错误处理 ──┐
├── Task 5: 加载状态优化 ──┤
└── Task 6: 空状态处理 ────┘

阶段三 (实用功能)
├── Task 7: 数据导出
├── Task 8: 价格预警 (依赖 Task 1)
└── Task 9: 数据缓存

阶段四 (测试)
├── Task 10: 集成测试
└── Task 11: 代码质量检查

阶段五 (文档)
└── Task 12: 更新文档
```

---

## 执行顺序建议

1. **第一周**: Task 1-3 (完善占位功能，项目可用的基础)
2. **第二周**: Task 4-6 (用户体验优化)
3. **第三周**: Task 7-9 (实用功能)
4. **第四周**: Task 10-12 (测试、质量、文档)
