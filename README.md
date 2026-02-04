# Fund Real-Time Valuation

基金实时估值应用，基于 Flet 框架开发，提供图形化界面。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行 GUI
python run_tui.py

# 或 Web 模式
python run_tui.py --web

# TUI 模式（兼容）
python run_tui.py --tui
```

## 项目结构

```
├── run_tui.py              # 应用入口（默认运行 GUI）
├── run_gui.py              # GUI 专用入口
├── requirements.txt         # 依赖配置
├── src/
│   ├── gui/               # Flet GUI 界面
│   ├── db/                # SQLite 数据库
│   └── datasources/       # 数据源
└── tests/                  # 测试
```

## 功能

- 📊 基金实时估值监控
- 📈 大宗商品行情
- 📰 财经新闻
- 💾 数据持久化（SQLite）
