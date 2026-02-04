# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基金实时估值 TUI 应用，基于 Python + Textual 框架，提供基金估值监控、自选管理、大宗商品行情和财经新闻功能。

## 常用命令

```bash
# 运行应用
python run_tui.py
./run_tui.py

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/ -v           # 运行所有测试
pytest tests/ -v --tb=short # 简洁错误输出
```

## 技术栈

- **UI 框架**: Textual
- **HTTP 客户端**: httpx
- **金融数据**: akshare, yfinance
- **配置格式**: YAML
- **网页解析**: beautifulsoup4

## 架构概览

```
run_tui.py          # 应用入口
src/
├── ui/              # 界面层
│   ├── app.py       # 主应用 (FundTUIApp)
│   ├── widgets.py   # 表格、面板组件
│   └── screens.py   # 视图屏幕
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

### 数据流

`配置 (YAML)` → `ConfigManager` → `DataSourceManager` → `UI 组件`

### 配置存储

配置文件位于 `~/.fund-tui/`:
- `config.yaml` - 应用主配置
- `funds.yaml` - 基金自选/持仓
- `commodities.yaml` - 商品关注列表

## 关键设计

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

### 响应式状态管理

应用使用 Textual 的响应式状态管理，通过 `@式` 装饰器实现 UI 自动更新。

### UI 快捷键

| 按键 | 功能 |
|------|------|
| `Tab` | 切换视图 (基金/商品/新闻) |
| `1/2/3` | 快速切换视图 |
| `r` | 手动刷新 |
| `t` | 切换主题 |
| `F1` | 帮助 |
| `q` / `Ctrl+C` | 退出 |
