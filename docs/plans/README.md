# Feature Plans

功能设计文档目录。

## 概述

本目录包含项目的功能设计文档，记录新功能的规划、设计和实现细节。

## 目录结构

```
plans/
├── 2026-02-09-web-frontend-design.md      # Web 前端设计
├── 2026-02-11-funds-holding-first-sort.md # 基金持仓排序
├── 2026-02-11-kline-chart.md             # K 线图功能
├── 2026-02-12-commodity-category-design.md  # 商品分类设计
├── 2026-02-13-index-card-delay-tag-design.md  # 指数延迟标签设计
├── 2026-02-13-index-card-delay-tag-implementation.md  # 指数延迟标签实现
├── 2026-02-13-index-card-time-display-improvement.md  # 指数时间显示优化
├── 2026-02-13-index-card-time-implementation.md  # 指数时间功能实现
├── commodity-watchlist-design.md         # 商品关注列表设计
├── fund-holding-management-design.md     # 基金持仓管理设计
└── ARCHIVE/                              # 归档的设计文档
    └── (历史设计文档)
```

## 已完成功能 (待归档)

以下功能已实现，相关设计文档可考虑归档：

| 功能 | 状态 | 对应提交 |
|------|------|----------|
| 前后端单端口部署 | ✅ 完成 | e0fb979 |
| Celery 异步任务 | ✅ 完成 | fa7ff03 |
| WebSocket 实时推送 | ✅ 完成 | fa7ff03 |
| 节假日数据库管理 | ✅ 完成 | f3fc52e |
| 统一交易日历 | ✅ 完成 | f3fc52e |

## 命名规范

设计文档命名格式：`YYYY-MM-DD-功能名称.md`

## 使用说明

1. 新功能设计 → 在本目录创建新文档
2. 已完成/废弃 → 移动到 `ARCHIVE/` 子目录

## 相关资源

- [架构文档](../architecture/)
- [API 文档](../API.md)
