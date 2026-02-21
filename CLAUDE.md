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
pnpm run dev:web    # 前端 (Vite + Vue 3, 端口 3000)
pnpm run dev:api    # 后端 (FastAPI, 端口 8000, 基于 run_app.py)
uv run python run_app.py --reload  # 后端 (FastAPI)
uv run python run_app.py --fast --reload  # 后端 (快速启动，跳过缓存预热)

# Celery 后台任务
pnpm run dev:celery     # 启动 Celery Worker
pnpm run dev:celery:beat  # 启动 Celery Beat 定时任务

# 构建
pnpm run build:web  # 构建前端

# 运行测试
uv run python -m pytest tests/ -v           # 运行所有测试

# 代码检查
uv run ruff check .              # Python lint
uv run ruff check --fix .        # Python lint 自动修复
uv run mypy .                    # Python 类型检查
cd web && pnpm run lint          # 前端 lint (ESLint)
cd web && pnpm run typecheck     # 前端类型检查 (vue-tsc)
# 或使用统一命令
pnpm run lint                    # 后端 lint
pnpm run lint:fix               # 后端 lint 自动修复
pnpm run lint:web               # 前端 lint
pnpm run typecheck              # 后端 + 前端 类型检查
pnpm run check                  # 运行所有检查 (lint + typecheck)
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
├── run_app.py              # Web 应用入口
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
│       ├── indices.py      # 指数 API
│       └── overview.py     # 概览 API
├── web/                    # Vue 3 前端
│   ├── src/                # 前端源码
│   ├── package.json        # 前端依赖
│   └── vite.config.ts      # Vite 配置
├── src/                    # Python 源码
│   ├── datasources/        # 数据源层
│   ├── config/             # 配置层
│   ├── db/                 # 数据库层
│   └── utils/              # 工具层
├── tests/                  # 测试目录
└── docs/                   # 设计文档
    └── plans/              # 功能设计文档
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
| `/api/funds/watchlist` | POST | 添加基金到自选 |
| `/api/funds/watchlist/{code}` | DELETE | 从自选移除基金 |
| `/api/funds/{code}/holding` | PUT | 标记/取消持有基金 |
| `/api/commodities` | GET | 获取商品行情列表 |
| `/api/commodities/{type}` | GET | 获取单个商品行情 |
| `/api/commodities/categories` | GET | 获取商品分类 |
| `/api/commodities/history/{commodity_type}` | GET | 获取商品历史行情 |
| `/api/commodities/search` | GET | 搜索商品 |
| `/api/commodities/available` | GET | 获取所有可用商品 |
| `/api/commodities/watchlist` | GET | 获取关注列表 |
| `/api/commodities/watchlist` | POST | 添加关注商品 |
| `/api/commodities/watchlist/{symbol}` | DELETE | 移除关注商品 |
| `/api/commodities/watchlist/{symbol}` | PUT | 更新关注商品 |
| `/api/commodities/watchlist/category/{category}` | GET | 按分类获取关注 |
| `/api/commodities/gold/cny` | GET | 获取国内黄金行情 |
| `/api/commodities/gold/international` | GET | 获取国际黄金行情 |
| `/api/commodities/oil/wti` | GET | 获取 WTI 原油行情 |
| `/api/commodities/oil/brent` | GET | 获取布伦特原油行情 |
| `/api/commodities/silver` | GET | 获取白银行情 |
| `/api/commodities/crypto` | GET | 获取加密货币行情 |
| `/api/indices` | GET | 获取全球市场指数 |
| `/api/indices/{index_type}` | GET | 获取单个指数 |
| `/api/indices/regions` | GET | 获取支持的区域 |
| `/api/sectors` | GET | 获取行业板块 |
| `/api/sectors/industry` | GET | 获取行业板块行情 |
| `/api/sectors/concept` | GET | 获取概念板块行情 |
| `/api/news` | GET | 获取财经新闻 |
| `/api/news/categories` | GET | 获取新闻分类 |
| `/api/sentiment` | GET | 获取舆情数据 |
| `/api/sentiment/economic` | GET | 获取经济舆情 |
| `/api/sentiment/weibo` | GET | 获取微博舆情 |
| `/trading-calendar/calendar/{market}` | GET | 获取交易日历 |
| `/trading-calendar/is-trading-day/{market}` | GET | 判断是否交易日 |
| `/trading-calendar/next-trading-day/{market}` | GET | 获取下一个交易日 |
| `/trading-calendar/market-status` | GET | 获取多市场状态 |
| `/api/holidays` | GET | 获取节假日列表 |
| `/api/holidays` | POST | 添加节假日 |
| `/api/holidays/{id}` | PUT | 更新节假日 |
| `/api/holidays/{id}` | DELETE | 删除节假日 |
| `/api/ws` | WebSocket | 实时数据推送 |
| `/api/cache/stats` | GET | 缓存统计 |
| `/api/datasource/statistics` | GET | 数据源统计 |
| `/api/datasource/health` | GET | 数据源健康状态 |
| `/api/datasource/sources` | GET | 数据源列表 |
| `/api/logs` | GET | 获取日志 |

#### Pydantic 模型 (api/models.py)

- `FundResponse` - 基金响应（基类）
- `FundListData` - 基金列表响应（TypedDict）
- `FundDetailResponse` - 基金详情响应（继承 FundResponse）
- `FundEstimateResponse` - 基金估值响应（继承 FundResponse）
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
- **Redis**: Celery 依赖 Redis，运行前需启动 `redis-server`

## 交易日历 API

支持多市场交易状态查询：

```bash
# A股
curl "http://localhost:8000/trading-calendar/is-trading-day/china"
# 上海黄金交易所
curl "http://localhost:8000/trading-calendar/is-trading-day/sge"
# COMEX
curl "http://localhost:8000/trading-calendar/is-trading-day/comex"

# 获取年度交易日历
curl "http://localhost:8000/trading-calendar/calendar/china?year=2025"

# 获取多市场状态
curl "http://localhost:8000/trading-calendar/market-status?markets=china,usa,comex"
```

支持的交易所: china, hk, usa, japan, uk, germany, france, sge, comex, cme, lbma

## 测试方法

- **Playwright 浏览器测试**: `pnpm run dev:web` 启动后用 Playwright 检查控制台错误
- **控制台错误检查**: 使用 `mcp__plugin_playwright_playwright__browser_console_messages` 获取错误日志

## 图表库选择

- **uPlot** (推荐): MIT 许可证，无水印，体积小 (~30KB)，适合简单折线图
- **lightweight-charts**: GPL v3 许可证，强制显示 TradingView 水印
- 避免使用 GPL 许可证的库在前端，会强制显示品牌链接

## 数据库缓存策略

- **SQLite 数据库**: `~/.fund-tui/fund_data.db`
- **缓存表**: `fund_basic_info`, `fund_daily_cache`, `fund_intraday_cache`, `commodity_cache`
- **缓存优先级**: 内存 → 数据库 → 外部 API
- **获取数据后必须保存到数据库**，减轻 API 压力

### 数据库层 (src/db/)

- `database.py` - DatabaseManager 类，管理 SQLite 连接和缓存
- `commodity_repo.py` - 商品缓存 DAO，三级缓存实现

### 配置层 (src/config/)

- `commodities_config.py` - 商品配置管理，关注列表 YAML 读写

## 常见问题

- **Vue 模板语法**: 确保 computed/watch 中的 `return` 在正确位置，避免 "return outside function" 错误
- **字段名映射**: 保存数据时字段名要一致（如 `price` vs `value`），否则会存储空值
- **TypeScript**: 可选字段用 `| None` 类型，赋值时处理 `undefined`

## 前端组件模式

- **Pinia Store**: 使用 `useFundStore` 管理基金状态
- **组件 Props**: 用 `withDefaults(defineProps<Props>(), {...})` 设置默认值
- **条件渲染**: 用 `v-if` 控制组件显示/隐藏
