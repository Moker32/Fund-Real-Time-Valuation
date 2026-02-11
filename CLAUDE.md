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

# 代码检查
uv run ruff check .              # Python 代码检查
uv run ruff check --fix .        # 自动修复 Python 代码
uv run mypy .                    # Python 类型检查
cd web && pnpm run lint          # 前端代码检查
cd web && pnpm run typecheck     # 前端类型检查 (vue-tsc)
```

## 技术栈

- **前端框架**: Vue 3 + Vite + TypeScript
- **Web 框架**: FastAPI 0.104.0
- **HTTP 客户端**: httpx
- **金融数据**: akshare, yfinance
- **配置格式**: YAML
- **网页解析**: beautifulsoup4

## 项目结构

```
.
├── run_api.py              # Web 应用入口
├── pyproject.toml          # Python 项目配置
├── package.json            # pnpm 工作空间配置
├── requirements.txt        # Python 依赖
├── api/                    # FastAPI 后端
│   ├── main.py             # 应用入口
│   ├── dependencies.py     # 依赖注入
│   ├── models.py           # Pydantic 数据模型
│   └── routes/             # API 路由
│       ├── funds.py        # 基金 API
│       ├── commodities.py  # 商品 API
│       └── overview.py     # 概览 API
├── web/                    # Vue 3 前端
│   ├── src/                # 前端源码
│   ├── package.json        # 前端依赖
│   └── vite.config.ts      # Vite 配置
├── src/                    # Python 源码
│   ├── datasources/        # 数据源层
│   ├── config/             # 配置层
│   └── utils/              # 工具层
└── tests/                  # 测试目录
```

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
| `/api/funds/{code}/estimate` | GET | 获取基金实时估值 |
| `/api/funds/{code}/history` | GET | 获取基金历史净值 |
| `/api/funds/add` | POST | 添加基金到自选 |
| `/api/funds/{code}` | DELETE | 从自选移除基金 |
| `/api/commodities` | GET | 获取商品行情列表 |
| `/api/commodities/{type}` | GET | 获取单个商品行情 |
| `/api/commodities/gold/cny` | GET | 获取国内黄金行情 |
| `/api/commodities/gold/international` | GET | 获取国际黄金行情 |
| `/api/commodities/oil/wti` | GET | 获取 WTI 原油行情 |
| `/api/commodities/oil/brent` | GET | 获取布伦特原油行情 |
| `/api/commodities/silver` | GET | 获取白银行情 |
| `/api/commodities/crypto` | GET | 获取加密货币行情 |
| `/api/health` | GET | 健康检查 (详细) |
| `/api/health/simple` | GET | 健康检查 (简单) |
| `/api/overview` | GET | 市场概览 |
| `/api/overview/simple` | GET | 简版市场概览 |

#### Pydantic 模型 (api/models.py)

- `FundResponse` - 基金响应
- `FundListResponse` - 基金列表响应
- `FundDetailResponse` - 基金详情响应
- `FundEstimateResponse` - 基金估值响应
- `CommodityResponse` - 商品响应
- `CommodityListResponse` - 商品列表响应
- `HealthResponse` - 健康检查响应
- `HealthDetailResponse` - 详细健康检查响应
- `ErrorResponse` - 错误响应
- `OverviewResponse` - 市场概览响应
- `AddFundRequest` - 添加基金请求
- `AddFundResponse` - 添加基金响应

### 数据模型 (config/models.py)

- `Fund` - 基金基础信息
- `Holding(Fund)` - 持仓 (含份额、成本)
- `Commodity` - 商品信息
- `AppConfig` - 应用配置
- `FundList` - 基金列表
- `PriceAlert` - 价格提醒

## 注意事项

- **环境要求**: Python >= 3.10, Node >= 18, pnpm >= 8
- **配置目录**: 配置文件位于 `~/.fund-tui/`，首次运行前需确保目录存在
- **数据源超时**: 基金数据源默认超时 30 秒，某些数据源可能较慢
- **CORS 配置**: 生产环境应限制 CORS 来源域名
- **类型检查**: `src/datasources/*` 模块由于第三方库兼容性问题，在 mypy 中被禁用类型检查
