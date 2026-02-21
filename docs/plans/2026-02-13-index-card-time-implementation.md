# 指数卡片时间显示改进实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 改进指数卡片时间显示，使用数据源原始时间戳转换到用户时区，并限制不超过市场收盘时间

**Architecture:** 后端添加 timezone 和 dataTimestamp 字段，计算最后有效交易时间；前端使用新字段转换到用户浏览器时区显示

**Tech Stack:** Python (FastAPI), TypeScript (Vue 3)

---

## Task 1: 后端 - 添加 get_display_timestamp 函数

**Files:**
- Modify: `api/routes/indices.py:37-136` (在 get_trading_status 函数后添加新函数)

**Step 1: 添加 get_display_timestamp 函数**

在 `get_trading_status` 函数后（约第136行）添加以下函数：

```python
def get_display_timestamp(index_type: str, data_timestamp: str | None) -> str | None:
    """
    获取显示用的时间戳（不超过市场收盘时间）

    Args:
        index_type: 指数类型
        data_timestamp: 数据源返回的时间戳 (ISO格式)

    Returns:
        处理后的时间戳，如果数据时间超过收盘时间则返回收盘时间
    """
    market_info = MARKET_HOURS.get(index_type, {})
    if not market_info or not data_timestamp:
        return data_timestamp

    # 解析数据时间
    try:
        # 处理 Z 后缀和 +00:00 格式
        ts_str = data_timestamp.replace('Z', '+00:00')
        data_dt = datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return data_timestamp

    # 获取市场时区
    tz_str = market_info.get("tz", "UTC")
    try:
        tz = pytz.timezone(tz_str)
    except pytz.exceptions.UnknownTimeZoneError:
        return data_timestamp

    data_dt_tz = data_dt.astimezone(tz)

    # 计算当天收盘时间
    today = data_dt_tz.date()
    close_time_str = market_info.get("close")  # 如 "08:00" (UTC时间)
    try:
        close_time = datetime.strptime(close_time_str, "%H:%M").time()
    except ValueError:
        return data_timestamp

    # 特殊处理A股午间休市
    if index_type in ["shanghai", "shenzhen", "shanghai50", "chi_next", "star50",
                      "csi500", "csi1000", "hs300", "csiall"]:
        # A股午间休市时间是 11:30-13:00
        # 如果数据时间在休市时段，使用上午收盘时间 11:30
        morning_close = time(11, 30)
        afternoon_open = time(13, 0)

        if morning_close < data_dt_tz.time() < afternoon_open:
            # 在午间休市时段，返回上午收盘时间
            display_dt = datetime.combine(today, morning_close, tzinfo=tz)
            return display_dt.isoformat()

    # 如果数据时间超过收盘时间，返回收盘时间
    if data_dt_tz.time() > close_time:
        display_dt = datetime.combine(today, close_time, tzinfo=tz)
        return display_dt.isoformat()

    return data_timestamp
```

**Step 2: 添加 time 导入**

确保文件顶部导入 `time`:
```python
from datetime import datetime, time
```

**Step 3: 验证语法**

Run: `python -m py_compile api/routes/indices.py`
Expected: 无错误输出

**Step 4: 提交**

```bash
git add api/routes/indices.py
git commit -m "feat: 添加 get_display_timestamp 函数计算最后有效交易时间"
```

---

## Task 2: 后端 - 修改 API 返回数据添加新字段

**Files:**
- Modify: `api/routes/indices.py:194-213` (批量获取指数)
- Modify: `api/routes/indices.py:260-281` (单个指数)

**Step 1: 修改 get_indices 函数 (第194-213行)**

在 `get_indices` 函数中添加 `dataTimestamp` 和 `timezone` 字段：

```python
        # 计算显示用的时间戳（不超过收盘时间）
        display_timestamp = get_display_timestamp(index_type, data_timestamp)

        all_indices.append({
            "index": index_type,
            "symbol": data.get("symbol", ""),
            "name": data.get("name", ""),
            "price": data.get("price", 0.0),
            "change": data.get("change"),
            "changePercent": data.get("change_percent"),
            "currency": data.get("currency", ""),
            "exchange": data.get("exchange"),
            "timestamp": data.get("time"),
            "dataTimestamp": display_timestamp,  # 新增：处理后的时间戳
            "timezone": market_info.get("tz"),  # 新增：市场时区
            "source": result.source,
            "high": data.get("high"),
            "low": data.get("low"),
            "open": data.get("open"),
            "prevClose": data.get("prev_close"),
            "region": INDEX_REGIONS.get(index_type),
            "tradingStatus": trading_status.get("status"),
            "marketTime": trading_status.get("market_time"),
            "isDelayed": is_delayed,
        })
```

**Step 2: 修改 get_index 函数 (第260-281行)**

同样添加 `dataTimestamp` 和 `timezone` 字段：

```python
    # 计算显示用的时间戳
    display_timestamp = get_display_timestamp(index_type, data_timestamp)
    market_info = MARKET_HOURS.get(index_type, {})

    return {
        "index": data.get("index", ""),
        "symbol": data.get("symbol", ""),
        "name": data.get("name", ""),
        "price": data.get("price", 0.0),
        "change": data.get("change"),
        "changePercent": data.get("change_percent"),
        "currency": data.get("currency", ""),
        "exchange": data.get("exchange"),
        "timestamp": data.get("time"),
        "dataTimestamp": display_timestamp,  # 新增
        "timezone": market_info.get("tz"),   # 新增
        "source": result.source,
        "high": data.get("high"),
        "low": data.get("low"),
        "open": data.get("open"),
        "prevClose": data.get("prev_close"),
        "region": INDEX_REGIONS.get(index_type),
        "tradingStatus": trading_status.get("status"),
        "marketTime": trading_status.get("market_time"),
        "isDelayed": is_delayed,
    }
```

**Step 3: 验证语法**

Run: `python -m py_compile api/routes/indices.py`
Expected: 无错误输出

**Step 4: 提交**

```bash
git add api/routes/indices.py
git commit -m "feat: API 返回 dataTimestamp 和 timezone 字段"
```

---

## Task 3: 前端 - 更新类型定义

**Files:**
- Modify: `web/src/types/index.ts:154-173`

**Step 1: 添加新字段到 MarketIndex 接口**

```typescript
export interface MarketIndex {
  index: string;
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  currency: string;
  exchange?: string;
  timestamp: string;
  dataTimestamp?: string;   // 新增：数据更新时间（ISO 格式）
  timezone?: string;        // 新增：市场时区
  source: string;
  high?: number;
  low?: number;
  open?: number;
  prevClose?: number;
  region?: string;
  tradingStatus?: string;
  marketTime?: string;
  isDelayed?: boolean;
}
```

**Step 2: 运行类型检查**

Run: `cd web && pnpm run typecheck`
Expected: 无 TypeScript 错误

**Step 3: 提交**

```bash
git add web/src/types/index.ts
git commit -f "feat: 添加 dataTimestamp 和 timezone 字段到 MarketIndex 类型"
```

---

## Task 4: 前端 - 修改 IndexCard 使用新字段

**Files:**
- Modify: `web/src/components/IndexCard.vue:73-79` (模板)
- Modify: `web/src/components/IndexCard.vue:191-202` (格式化函数)

**Step 1: 修改模板使用 dataTimestamp**

将第 73-78 行：
```vue
<div class="market-time" v-if="indexData.timestamp">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 6V12L16 14"/>
  </svg>
  <span>{{ formatMarketTime(indexData.timestamp) }}</span>
</div>
```

改为：
```vue
<div class="market-time" v-if="indexData.dataTimestamp">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 6V12L16 14"/>
  </svg>
  <span>{{ formatToUserTimezone(indexData.dataTimestamp) }}</span>
</div>
```

**Step 2: 修改格式化函数**

将 `formatMarketTime` 函数替换为 `formatToUserTimezone`：

```typescript
function formatToUserTimezone(isoTimestamp: string | undefined): string {
  if (!isoTimestamp) return '--';
  try {
    const date = new Date(isoTimestamp);
    // 使用用户浏览器时区自动转换
    return date.toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '--';
  }
}
```

**Step 3: 删除旧函数**

删除原来的 `formatMarketTime` 函数（如果不再使用）。

**Step 4: 运行类型检查**

Run: `cd web && pnpm run typecheck`
Expected: 无 TypeScript 错误

**Step 5: 提交**

```bash
git add web/src/components/IndexCard.vue
git commit -m "feat: IndexCard 使用 dataTimestamp 显示用户时区时间"
```

---

## Task 5: 验证功能

**Step 1: 启动后端服务**

Run: `uv run python run_app.py`
Expected: 服务启动成功

**Step 2: 测试 API 返回**

Run: `curl http://localhost:8000/api/indices`
Expected: 响应包含 `dataTimestamp` 和 `timezone` 字段

**Step 3: 启动前端服务**

Run: `pnpm run dev:web`
Expected: 前端启动成功

**Step 4: 验证浏览器显示**

使用 Playwright 检查控制台是否有错误：
Run: `mcp__plugin_playwright_playwright__browser_console_messages`

**Step 5: 提交**

```bash
git add .
git commit -m "feat: 完成指数卡片时间显示改进功能"
```

---

## 执行方式选择

**Plan complete and saved to `docs/plans/2026-02-13-index-card-time-display-improvement.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
