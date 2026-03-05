# 已知问题

## 1. QDII 基金估值延迟显示问题

**问题描述**: QDII 基金（投资海外市场的基金）估值显示为 T+1 日数据

**影响范围**: 所有 QDII 基金和投资海外的 FOF 基金

**当前状态**: 已知限制，无法完全解决

**根本原因**:
- QDII 基金投资海外市场，净值更新时间与 A 股不同步
- 海外市场交易时间与 A 股存在时差
- 基金公司通常在 T+1 日公布 T 日净值

**临时解决方案**:
- 前端显示估值更新时间，提醒用户数据可能延迟
- 对于 QDII 基金，不提供日内分时数据（API 返回 400 错误）

**相关代码**:
- [`api/routes/funds.py:_is_qdii_fund()`](api/routes/funds.py:65) - QDII 基金判断逻辑
- [`src/datasources/fund_source.py:_has_real_time_estimate()`](src/datasources/fund_source.py) - 实时估值判断

---

## 2. akshare py_mini_racer 依赖问题

**问题描述**: akshare 库的 py_mini_racer 依赖导致应用崩溃和类型检查失败

**影响范围**: 
- 应用启动时崩溃（`Check failed: !pool->IsInitialized()`）
- mypy 类型检查失败
- 部分 akshare 数据源功能

**当前状态**: ✅ **已解决**（2026-03-05）

**根本原因**:
- py_mini_racer 包（v0.6.0，2021年停止维护）与新版 mini_racer（v0.14.1）存在二进制兼容性问题
- macOS 上的 V8 引擎初始化失败，触发断言崩溃
- `py_mini_racer 0.6.0` 期望的符号 `mr_eval_context` 在新版中已不存在

**解决方案**:
- 卸载 `mini_racer` 和 `py_mini_racer` 依赖
- akshare 核心功能（基金、指数、板块等）不依赖 JS 执行，仍可正常工作
- 如需使用同花顺等依赖 JS 执行的数据源，需使用其他方案（如 execjs + Node.js）

```bash
uv pip uninstall mini_racer py_mini_racer
```

**相关配置**:
```toml
# pyproject.toml
[[tool.mypy.overrides]]
module = ["akshare.*", "py_mini_racer.*"]
ignore_missing_imports = true
```

---

## 3. Sina 数据源网络限制问题

**问题描述**: Sina 数据源在某些网络环境下无法访问

**影响范围**: 
- Sina 股票数据源（A 股行情）
- Sina 债券数据源
- Sina 指数数据源（部分指数）

**当前状态**: 已实现多数据源故障转移

**根本原因**:
- Sina API 为非公开接口，可能被防火墙拦截
- 某些网络环境（企业网络、VPN）对 Sina 服务器访问受限
- 请求频率过高可能被限流

**临时解决方案**:
- 实现多数据源备份（如腾讯、东方财富）
- 使用 DataGateway 进行自动故障转移
- 添加请求缓存减少重复请求

**相关代码**:
- [`src/datasources/gateway.py`](src/datasources/gateway.py) - 数据网关故障转移
- [`src/datasources/hot_backup.py`](src/datasources/hot_backup.py) - 热备份机制

---

## 4. 基金基准线问题

**问题描述**: 折线图的昨日收盘基准线无法正确获取

**影响范围**: 基金详情页的日内分时折线图

**当前状态**: 已部分解决（使用日内数据开盘价作为后备基准线）

**根本原因**:
1. 后端 `fund123.cn` API 未返回 `prev_net_value` 字段
2. 原 akshare 库因 py_mini_racer 兼容性问题无法使用（现已卸载）
3. 数据库 `fund_daily_cache` 表为空，无历史净值数据

**临时解决方案**:
- 前端优先使用 `prevNetValue`
- 后备方案：使用日内分时数据的第一个价格（开盘价）作为基准线

**待解决**:
- [x] 修复 akshare/py_mini_racer 依赖问题（已通过卸载解决）
- [ ] 建立基金历史净值数据缓存机制
- [ ] 当获取到真实昨日净值后，优先使用昨日净值作为基准线

---

## 5. 指数数据延迟问题

**问题描述**: 部分指数数据存在 15 分钟延迟

**影响范围**: 腾讯指数数据源覆盖的指数

**当前状态**: 已知限制，前端显示延迟标签

**根本原因**:
- 免费行情数据源通常有 15-20 分钟延迟
- 实时数据需要付费订阅

**临时解决方案**:
- 前端显示数据时间戳和延迟标签
- 对比多个数据源取最新数据

**相关代码**:
- [`web/src/components/IndexCard.vue`](web/src/components/IndexCard.vue) - 延迟标签显示

---

## 6. 商品期货交易时间问题

**问题描述**: 商品期货交易时间与 A 股不同，导致非交易时段数据为空

**影响范围**: 黄金、原油等商品期货

**当前状态**: 已知限制

**根本原因**:
- COMEX、CME 等国际商品期货交易时间与 A 股不同
- 国内黄金交易所（SGE）交易时间与其他市场不一致

**临时解决方案**:
- 显示最近有效交易日的数据
- 前端显示交易状态提示
