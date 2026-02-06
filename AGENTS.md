# AGENTS.md

> **注意:** 对于 Claude Code，请优先参考 `CLAUDE.md` 获取项目指南。

本文件记录开发过程中的约定和历史信息。

## 项目信息

- **创建日期**: 2026-02-04
- **项目**: Fund Real-Time Valuation (Flet GUI)
- **技术栈**: Python 3.10+, Flet 0.80.5, SQLite, YAML, httpx, akshare

## 架构概览

```
run_gui.py               # 入口点 (依赖检查 + GUI 启动)
src/
├── gui/                # Flet GUI 层 (卡片、图表、主题)
├── datasources/        # 数据源层 (akshare, yfinance)
├── db/                 # SQLite 持久化
└── config/             # 配置模型
tests/                  # pytest 测试
docs/plans/             # 开发计划
```

## 代码结构速查

| 组件 | 位置 | 说明 |
|------|------|------|
| 主应用 | `src/gui/main.py` | FundGUIApp 类，标签页，事件处理 |
| 卡片组件 | `src/gui/components.py` | FundCard, FundPortfolioCard 等 |
| 主题/颜色 | `src/gui/theme.py` | AppColors, ChangeColors |
| 数据源 | `src/datasources/` | 所有数据源实现 |
| 源管理器 | `src/datasources/manager.py` | 多源故障切换 |
| 数据库 | `src/db/database.py` | SQLite 模式 |
| 配置模型 | `src/config/models.py` | Fund, Holding 等 |

## 子目录 AGENTS

- `src/gui/AGENTS.md` - Flet GUI 组件和模式
- `src/datasources/AGENTS.md` - 数据源架构
- `src/db/AGENTS.md` - 数据库模式和 DAO 模式
- `tests/AGENTS.md` - 测试约定和固件
