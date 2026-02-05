# Fund Real-Time Valuation

基金实时估值应用，基于 Flet 框架开发，提供图形化界面。

## 功能特性

- 📊 **基金实时估值监控** - 实时追踪基金净值和估值变化
- 📈 **大宗商品行情** - 黄金、原油等商品实时价格
- 📰 **财经新闻** - 聚合多来源财经新闻
- 🔔 **价格预警** - 设置目标价格，自动触发通知
- ⚙️ **个性化设置** - 主题切换、刷新间隔等配置
- 💾 **数据持久化** - SQLite 存储，支持数据导出
- 🚀 **数据缓存** - 智能缓存减少 API 调用

## 快速开始

```bash
# 安装依赖
uv pip install -r requirements.txt

# 运行 GUI
python run_gui.py

# 或直接执行（需要 uv）
./run_gui.py

# Web 模式
python run_gui.py --web
```

## 项目结构

```
├── run_gui.py              # GUI 应用入口
├── requirements.txt        # 依赖配置
├── src/
│   ├── gui/               # Flet GUI 界面
│   │   ├── main.py        # 主应用 (FundGUIApp)
│   │   ├── components.py  # 基金卡片、组合卡片等组件
│   │   ├── notifications.py # 通知系统
│   │   ├── settings.py    # 设置对话框
│   │   ├── error_handling.py # 错误处理
│   │   ├── empty_states.py # 空状态组件
│   │   ├── detail.py      # 基金详情对话框
│   │   └── theme.py       # 主题和颜色
│   ├── config/            # 配置管理
│   │   ├── manager.py     # ConfigManager
│   │   └── models.py      # 数据模型
│   ├── datasources/       # 数据源
│   │   ├── manager.py     # DataSourceManager
│   │   ├── cache.py       # 数据缓存层
│   │   └── ...            # 各类数据源
│   ├── db/                # SQLite 数据库
│   └── utils/             # 工具模块
│       └── export.py      # 数据导出
└── tests/                 # 测试（120+ 用例）
```

## 新功能 (v2.0.0)

### 通知系统
- 价格预警：设置目标价格和方向（高于/低于）
- 预警管理：添加、删除、清除已触发预警
- 自动检查：数据刷新后自动检查预警

### 设置对话框
- 刷新间隔配置（10-300秒）
- 主题切换（深色/浅色）
- 自动刷新开关
- 显示盈亏开关

### 数据导出
- 基金列表导出为 CSV
- 持仓报告导出（含成本计算）

### 数据缓存
- JSON 持久化存储
- 可配置 TTL（默认 5 分钟）
- 自动清理过期缓存

## 技术栈

- **UI 框架**: Flet 0.80.5
- **HTTP 客户端**: httpx
- **金融数据**: akshare, yfinance
- **数据库**: SQLite
- **配置格式**: YAML
- **网页解析**: beautifulsoup4

## 文档

- 📖 [API 文档](docs/API.md) - 核心模块 API 使用指南
- 📊 [性能评估报告](docs/performance-evaluation.md) - 基金列表渲染性能分析
- 🔧 [开发指南](src/gui/AGENTS.md) - GUI 开发指南

## 开发

```bash
# 运行测试
uv run python -m pytest tests/ -v

# 类型检查
uv run python -m mypy src/

# 代码风格检查
uv run python -m ruff check src/
```

## 许可证

MIT License
