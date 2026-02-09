# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基金实时估值 GUI 应用，基于 Python + Flet 框架，提供基金估值监控、自选管理、大宗商品行情和财经新闻功能。

## 常用命令

```bash
# 运行 GUI 应用
python run_gui.py
./run_gui.py

# 运行 FastAPI 服务 (Web API)
python run_api.py --host 0.0.0.0 --port 8000
python run_api.py --reload  # 开发模式热重载

# 安装依赖
uv pip install -r requirements.txt

# 运行测试
uv run python -m pytest tests/ -v           # 运行所有测试
uv run python -m pytest tests/ -v --tb=short # 简洁错误输出
```

## 技术栈

- **UI 框架**: Flet 0.80.5
- **Web 框架**: FastAPI 0.104.0
- **HTTP 客户端**: httpx
- **金融数据**: akshare, yfinance
- **配置格式**: YAML
- **网页解析**: beautifulsoup4

## 架构概览

```
run_gui.py          # GUI 应用入口
run_api.py          # FastAPI 服务入口
api/
├── main.py         # FastAPI 应用入口
├── dependencies.py # 依赖注入
├── models.py       # Pydantic 数据模型
└── routes/
    ├── funds.py       # 基金 API 路由
    └── commodities.py # 商品 API 路由
src/
├── gui/              # Flet GUI 界面层
│   ├── main.py       # 主应用 (FundGUIApp)
│   ├── components.py # 基金卡片、组合卡片等组件
│   ├── notifications.py # 通知系统
│   ├── settings.py   # 设置对话框
│   ├── error_handling.py # 错误处理
│   ├── empty_states.py # 空状态组件
│   ├── detail.py     # 基金详情对话框
│   ├── theme.py      # 主题和颜色
│   └── AGENTS.md     # GUI 开发指南
├── datasources/      # 数据源层
│   ├── manager.py    # DataSourceManager (多数据源管理)
│   ├── cache.py      # 数据缓存层
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
├── config/           # 配置层
│   ├── manager.py    # ConfigManager
│   └── models.py     # 数据模型 (Fund, Holding, Commodity, PriceAlert 等)
└── utils/            # 工具层
    └── export.py     # 数据导出
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

### FastAPI 后端 (api/)

#### API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/funds` | GET | 获取基金列表 |
| `/api/funds/{code}` | GET | 获取基金详情 |
| `/api/funds/{code}/estimate` | GET | 获取基金估值 |
| `/api/funds/{code}/history` | GET | 获取基金历史净值 |
| `/api/commodities` | GET | 获取商品行情列表 |
| `/api/commodities/{type}` | GET | 获取单个商品行情 |
| `/api/commodities/gold/cny` | GET | 获取国内黄金行情 |
| `/api/commodities/gold/international` | GET | 获取国际黄金行情 |
| `/api/commodities/oil/wti` | GET | 获取 WTI 原油行情 |
| `/api/health` | GET | 健康检查 (详细) |
| `/api/health/simple` | GET | 健康检查 (简单) |

#### Pydantic 模型 (api/models.py)

- `FundResponse` - 基金响应
- `FundDetailResponse` - 基金详情响应
- `FundEstimateResponse` - 基金估值响应
- `CommodityResponse` - 商品响应
- `HealthResponse` - 健康检查响应
- `HealthDetailResponse` - 详细健康检查响应
- `ErrorResponse` - 错误响应

### 数据模型 (config/models.py)

- `Fund` - 基金基础信息
- `Holding(Fund)` - 持仓 (含份额、成本)
- `Commodity` - 商品信息
- `AppConfig` - 应用配置
