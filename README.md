# Fund Real-Time Valuation

基金实时估值 Web 应用，基于 Vue 3 + FastAPI 开发。

## 功能特性

- **基金实时估值监控** - 实时追踪基金净值和估值变化
- **大宗商品行情** - 黄金、原油等商品实时价格
- **财经新闻** - 聚合多来源财经新闻
- **价格预警** - 设置目标价格，自动触发通知
- **数据缓存** - 智能缓存减少 API 调用

## 快速开始

```bash
# 安装依赖 (前端 + 后端)
pnpm run install:all

# 并行启动前后端开发服务器
pnpm run dev

# 访问 http://localhost:5173 查看前端
# 访问 http://localhost:8000/docs 查看 API 文档
```

## 项目结构

```
├── run_api.py              # Web 应用入口
├── web/                    # Vue 3 前端
│   ├── src/               # 前端源码
│   ├── dist/              # 构建产物
│   └── package.json       # 前端依赖
├── api/                   # FastAPI 后端
│   ├── main.py           # FastAPI 应用
│   ├── dependencies.py   # 依赖注入
│   ├── models.py         # 数据模型
│   └── routes/           # API 路由
│       ├── funds.py      # 基金 API
│       └── commodities.py # 商品 API
├── src/                   # Python 源码
│   ├── datasources/      # 数据源层
│   ├── config/           # 配置管理
│   └── utils/            # 工具模块
└── tests/                 # 测试
```

## 开发

```bash
# 运行后端测试
uv run python -m pytest tests/ -v

# 类型检查
uv run python -m mypy src/

# 代码风格检查
uv run python -m ruff check src/

# 构建前端
pnpm run build:web
```

## 许可证

MIT License
