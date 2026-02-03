---
name: require-source-suffix
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: src/datasources/[^/]+\.py$
  - field: new_text
    operator: regex_match
    pattern: ^class\s+[A-Z][a-zA-Z0-9]*\s*\(
---

⚠️ **数据源类命名不规范！**

数据源类应该以 `Source` 结尾。

**命名规则：**
- ✅ `class FundSource(DataSource)` - 正确
- ✅ `class NewsSource(DataSource)` - 正确
- ❌ `class FundAPI(DataSource)` - 错误
- ❌ `class DataGetter(DataSource)` - 错误

**为什么重要：**
- 保持命名一致性
- 便于识别数据源类
- 与 `DataSourceManager` 的注册逻辑一致
