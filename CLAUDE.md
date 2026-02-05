# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基金实时估值 GUI 应用，基于 Python + Flet 框架，提供基金估值监控、自选管理、大宗商品行情和财经新闻功能。

## 常用命令

```bash
# 运行 GUI 应用
python run_gui.py
./run_gui.py

# 运行 TUI 应用
python run_tui.py
./run_tui.py

# 安装依赖
uv pip install -r requirements.txt

# 运行测试
pytest tests/ -v           # 运行所有测试
pytest tests/ -v --tb=short # 简洁错误输出
```

## 技术栈

- **UI 框架**: Flet 0.80.5
- **HTTP 客户端**: httpx
- **金融数据**: akshare, yfinance
- **配置格式**: YAML
- **网页解析**: beautifulsoup4

## 架构概览

```
run_gui.py          # GUI 应用入口
run_tui.py          # TUI 应用入口
src/
├── gui/              # Flet GUI 界面层
│   ├── main.py       # 主应用 (FundGUIApp)
│   ├── components.py # 基金卡片、组合卡片等组件
│   ├── detail.py     # 基金详情对话框
│   ├── theme.py      # 主题和颜色
│   └── AGENTS.md     # GUI 开发指南
├── datasources/      # 数据源层
│   ├── manager.py    # DataSourceManager (多数据源管理)
│   ├── base.py       # 数据源抽象基类
│   ├── aggregator.py # 数据聚合器
│   ├── fund_source.py  # 基金数据源
│   ├── stock_source.py # 股票数据源
│   ├── bond_source.py  # 债券数据源
│   ├── crypto_source.py # 加密货币数据源
│   ├── sector_source.py # 行业数据源
│   ├── commodity_source.py # 商品数据源
│   ├── news_source.py   # 新闻数据源
│   └── portfolio.py     # 组合分析
└── config/           # 配置层
    ├── manager.py    # ConfigManager
    └── models.py     # 数据模型 (Fund, Holding, Commodity 等)
```

### GUI 数据流

`配置 (YAML)` → `ConfigManager` → `DataSourceManager` → `FundGUIApp` → `FundCard` 组件

### 配置存储

配置文件位于 `~/.fund-tui/`:
- `config.yaml` - 应用主配置
- `funds.yaml` - 基金自选/持仓
- `commodities.yaml` - 商品关注列表

## Flet 0.80.5 适配说明

### Tabs 组件

Flet 0.80.5 使用 `TabBar` + `Tabs` 组合：

```python
from flet import TabBar, Tab, Tabs

# TabBar 负责标签
tab_bar = TabBar(
    tabs=[
        Tab(label="自选", icon=Icons.STAR_BORDER),
        Tab(label="商品", icon=Icons.TRENDING_UP),
        Tab(label="新闻", icon=Icons.NEWSPAPER),
    ],
    on_click=self._on_tab_click,
)

# Tabs 负责内容
tabs = Tabs(
    content=Column([
        Container(expand=True, content=page1, visible=True),
        Container(expand=True, content=page2, visible=False),
        Container(expand=True, content=page3, visible=False),
    ]),
    length=3,
)
```

### 颜色属性

| 组件 | 参数 | 示例 |
|------|------|------|
| Container | `bgcolor` | `Container(bgcolor="#3C3C3C")` |
| Text | `color` | `Text("Hello", color="#FFFFFF")` |
| Icon | `color` | `Icon(Icons.STAR, color="#FF3B30")` |
| IconButton | `icon_color` | `IconButton(icon_color="#007AFF")` |
| Card | `bgcolor` | `Card(bgcolor="#3C3C3C")` |

### 关键设计

### 数据源管理 (datasources/manager.py)

`DataSourceManager` 负责：
- 多数据源注册/注销
- 故障切换 (failover)
- 负载均衡 (可选)
- 健康检查与统计

### 数据模型 (config/models.py)

- `Fund` - 基金基础信息
- `Holding(Fund)` - 持仓 (含份额、成本)
- `Commodity` - 商品信息
- `AppConfig` - 应用配置
