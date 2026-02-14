# Fund Real-Time Valuation

基金实时估值 Web 应用，基于 Vue 3 + FastAPI 开发。

## 功能特性

- **基金实时估值监控** - 实时追踪基金净值和估值变化
- **大宗商品行情** - 黄金、原油等商品实时价格
- **财经新闻** - 聚合多来源财经新闻
- **价格预警** - 设置目标价格，自动触发通知
- **数据缓存** - 智能缓存减少 API 调用
- **交易日历** - 全球市场交易/休市日查询

## 快速开始

```bash
# 安装依赖 (前端 + 后端)
pnpm run install:all

# 并行启动前后端开发服务器
pnpm run dev

# 访问 http://localhost:3000 查看前端
# 访问 http://localhost:8000/docs 查看 API 文档
```

## 项目结构

```
├── run_api.py              # Web 应用入口
├── pyproject.toml          # Python 项目配置
├── package.json            # pnpm 工作空间配置
├── api/                    # FastAPI 后端
│   ├── main.py             # FastAPI 应用
│   ├── dependencies.py     # 依赖注入
│   ├── models.py           # Pydantic 数据模型
│   └── routes/             # API 路由
│       ├── funds.py        # 基金 API
│       ├── commodities.py  # 商品 API
│       ├── indices.py      # 指数 API
│       ├── sectors.py      # 板块 API
│       └── trading_calendar.py # 交易日历 API
├── web/                    # Vue 3 前端
│   └── src/               # 前端源码
├── src/                    # Python 源码
│   ├── datasources/       # 数据源层
│   ├── config/            # 配置管理
│   └── utils/             # 工具模块
└── tests/                 # 测试
```

## 开发

```bash
# 安装依赖 (前端 + 后端)
pnpm run install:all

# 并行启动前后端开发服务器
pnpm run dev

# 单独启动
pnpm run dev:web    # 前端 (Vite + Vue 3)
uv run python run_api.py --reload  # 后端 (FastAPI)

# 运行测试
uv run pytest tests/ -v

# 代码检查
uv run ruff check .              # Python 代码检查
uv run ruff check --fix .        # 自动修复
uv run mypy .                    # 类型检查
cd web && pnpm run lint          # 前端代码检查

# 构建前端
pnpm run build:web
```

## API 示例

### 交易日历

```bash
# 获取A股2025年交易日历
curl "http://localhost:8000/trading-calendar/calendar/china?year=2025"

# 判断是否为交易日
curl "http://localhost:8000/trading-calendar/is-trading-day/china?check_date=2025-01-28"

# 获取下一个交易日
curl "http://localhost:8000/trading-calendar/next-trading-day/china"

# 获取多市场状态
curl "http://localhost:8000/trading-calendar/market-status?markets=china,usa"
```

## 许可证

MIT License
