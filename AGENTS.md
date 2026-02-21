# AGENTS.md

> **注意:** 对于 Claude Code，请优先参考 `CLAUDE.md` 获取项目指南。
> 本文件供在此仓库中工作的 AI 编程代理使用。

## 项目概览

- **项目**: Fund Real-Time Valuation
- **技术栈**: Python 3.10+, FastAPI, Vue 3 + TypeScript, SQLite, akshare, yfinance
- **pnpm 工作空间**: backend (FastAPI) + frontend (Vue 3)
- **部署模式**: 单端口部署 (FastAPI 统一处理前端和后端)

## 构建 / Lint / 测试命令

```bash
# 安装依赖
pnpm run install:all

# 运行开发服务器
pnpm run dev              # 前端 + 后端 (concurrently)
pnpm run dev:web         # 前端 (Vite, 端口 3000)
pnpm run dev:api         # 后端 (FastAPI, 端口 8000)

# 快速启动 (跳过缓存预热)
uv run python run_app.py --fast --reload

# Celery 后台任务
pnpm run dev:celery         # Celery Worker
pnpm run dev:celery:beat   # Celery Beat 定时任务

# Python 测试
uv run pytest tests/ -v                              # 所有测试
uv run pytest tests/test_file.py -v                  # 单个文件
uv run pytest tests/test_file.py::test_function -v   # 单个测试函数
uv run pytest tests/ -k "pattern" -v                # 按模式运行

# Python lint 和类型检查
uv run ruff check .              # Lint
uv run ruff check --fix .       # 自动修复
uv run mypy .                   # 类型检查
cd web && pnpm run lint         # 前端 lint (ESLint)
pnpm run check                  # Lint + 类型检查 (后端)
```

## 代码风格指南

### Python (后端)

**导入顺序**: 标准库 → 第三方 → 本地模块。使用绝对导入：
```python
from src.datasources.manager import DataSourceManager
from api.routes import funds
```

**格式**: 行长 100 字符，4 空格缩进，尾部逗号。

**类型**: Python 3.10+ 类型提示 (`| None` 而非 `Optional[]`)。除非必要否则避免 `Any`。

**命名**:
- 文件: snake_case (`fund_source.py`)
- 类: PascalCase (`DataSourceManager`)
- 函数: snake_case (`get_fund_data`)
- 常量: UPPER_SNAKE_CASE
- 私有: 前缀 `_`

**错误处理**:
- 外部调用用 try/except 包装
- 返回 `DataSourceResult(success=False, error=...)` 而非 raise
- 禁止 bare `except:`
- 使用 `logger.error()` / `logger.warning()` 记录日志

### TypeScript / Vue (前端)

- 绝对导入: `@/components/...`
- Composition API + `<script setup>`
- TypeScript 严格模式
- Props/Events: camelCase
- 组件: PascalCase
- 禁止使用 `as any`, `@ts-ignore`, `@ts-expect-error`

## 架构

```
api/           # FastAPI 路由
  routes/      # 端点处理器
src/
  datasources/ # 数据获取器 (akshare, yfinance 等)
  db/          # SQLite DAOs
  config/      # 配置管理
  tasks/       # Celery 异步任务
web/           # Vue 3 前端
tests/         # pytest 测试文件
docs/          # 设计文档
```

## 数据源模式

```python
class MyDataSource(DataSource):
    async def fetch(self, *args) -> DataSourceResult:
        try:
            data = await self._fetch(...)
            return DataSourceResult(success=True, data=data, source=self.name)
        except Exception as e:
            logger.warning(f"获取失败: {e}")
            return DataSourceResult(success=False, error=str(e))
```

## 反模式

- **禁止**: 使用 `as any`, `@ts-ignore`, `@ts-expect-error`
- **禁止**: bare `except:` 或空 catch 块
- **禁止**: 不运行 lint 就提交 (`pnpm run lint`)
- **禁止**: 跳过类型检查

## 测试

- 测试文件: `tests/test_*.py`
- 使用 `conftest.py` 中的 fixtures
- 异步测试: `@pytest.mark.asyncio`
- 命名: `test_<方法名>`

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

## 备注

- 配置: `~/.fund-tui/config.yaml`, `~/.fund-tui/funds.yaml`
- 数据库: `~/.fund-tui/fund_data.db`
- mypy 中禁用的第三方类型: akshare, yfinance, matplotlib, pandas, numpy
- Redis: Celery 依赖，需先启动 `redis-server`

## 常用 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/funds` | GET | 基金列表 |
| `/api/funds/{code}` | GET | 基金详情 |
| `/api/funds/{code}/estimate` | GET | 基金估值 |
| `/api/funds/watchlist` | POST/DELETE | 自选管理 |
| `/api/commodities` | GET | 商品行情 |
| `/api/commodities/watchlist` | GET/POST | 关注列表 |
| `/api/indices` | GET | 全球市场指数 |
| `/api/sectors` | GET | 行业板块 |
| `/api/news` | GET | 财经新闻 |
| `/api/sentiment` | GET | 舆情数据 |
| `/api/health` | GET | 健康检查 |
| `/trading-calendar/is-trading-day/{market}` | GET | 交易状态 |
| `/api/cache/stats` | GET | 缓存统计 |
| `/api/datasource/statistics` | GET | 数据源统计 |
| `/api/ws` | WebSocket | 实时数据推送 |
