# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基金实时估值 Web 应用，基于 Vue 3 + FastAPI，提供基金估值监控、自选管理、大宗商品行情和财经新闻功能。

## 常用命令

```bash
# 安装所有依赖 (前后端)
pnpm run install:all

# 并行启动前后端开发服务器
pnpm run dev

# 单独启动
pnpm run dev:web    # 前端 (Vite + Vue 3)
uv run python run_api.py --reload  # 后端 (FastAPI)

# 构建
pnpm run build:web  # 构建前端

# 运行测试
uv run python -m pytest tests/ -v           # 运行所有测试
uv run python -m pytest tests/ -v --tb=short # 简洁错误输出
```

## 技术栈

- **前端框架**: Vue 3 + Vite + TypeScript
- **Web 框架**: FastAPI 0.104.0
- **HTTP 客户端**: httpx
- **金融数据**: akshare, yfinance
- **配置格式**: YAML
- **网页解析**: beautifulsoup4

## 架构概览

```
run_api.py          # Web 应用入口
web/                # Vue 3 前端
├── src/            # 前端源码
├── dist/           # 构建产物
└── package.json    # 前端依赖
api/
├── main.py         # FastAPI 应用入口
├── dependencies.py # 依赖注入
├── models.py       # Pydantic 数据模型
└── routes/
    ├── funds.py       # 基金 API 路由
    └── commodities.py # 商品 API 路由
src/
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
    ├── colors.py     # 颜色和格式化工具
    └── export.py     # 数据导出

### 配置存储

配置文件位于 `~/.fund-tui/`:
- `config.yaml` - 应用主配置
- `funds.yaml` - 基金自选/持仓
- `commodities.yaml` - 商品关注列表

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
