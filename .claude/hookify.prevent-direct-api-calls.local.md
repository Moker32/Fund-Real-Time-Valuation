---
name: prevent-direct-api-calls
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/(?!datasources).*\.py$
  - field: new_text
    operator: regex_match
    pattern: httpx\.(get|post|put|delete|request)
---

⚠️ **检测到直接 API 调用！**

你正在非数据源模块中直接使用 `httpx` 进行网络请求。

**为什么这是问题：**
- 所有 API 调用应该通过 `DataSourceManager` 管理
- 这确保了统一的错误处理、重试机制和健康检查
- 绕过数据源管理会导致功能缺失

**正确做法：**
1. 在 `src/datasources/` 下创建新的数据源类
2. 使用 `DataSourceManager.register_source()` 注册
3. 通过管理器调用数据源方法

**参考现有实现：**
- `src/datasources/fund_source.py` - 基金数据源
- `src/datasources/news_source.py` - 新闻数据源
