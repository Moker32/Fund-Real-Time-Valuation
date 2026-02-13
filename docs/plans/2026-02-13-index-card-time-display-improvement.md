# 指数卡片时间显示改进设计

## 背景

当前指数卡片存在以下问题：
1. 时间显示固定使用上海时区，无法显示对应市场的当地时间
2. 港股16:00收盘后仍显示"交易中"（已修复）
3. 收盘后可能显示盘后时间（如15:00收盘，显示16:14），造成困惑

## 目标

1. 数据更新时间显示为用户时区的时间
2. 显示最后有效交易时间（不超过市场收盘时间）
3. 辅助用户判断市场状态

## 设计方案

### 1. 后端改动

#### 1.1 API 返回新字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `dataTimestamp` | string | 数据更新时间，ISO 格式带时区（如 `2026-02-13T15:57:00+08:00`） |
| `timezone` | string | 市场时区（如 `Asia/Hong_Kong`） |

#### 1.2 最后有效交易时间计算逻辑

```python
def get_display_timestamp(index_type: str, data_timestamp: str | None) -> str | None:
    """获取显示用的时间戳（不超过市场收盘时间）"""
    market_info = MARKET_HOURS.get(index_type, {})
    if not market_info or not data_timestamp:
        return data_timestamp

    # 解析数据时间
    try:
        data_dt = datetime.fromisoformat(data_timestamp.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return data_timestamp

    # 获取市场时区
    tz_str = market_info.get("tz", "UTC")
    tz = pytz.timezone(tz_str)
    data_dt_tz = data_dt.astimezone(tz)

    # 计算当天收盘时间
    today = data_dt_tz.date()
    close_time_str = market_info.get("close")  # 如 "08:00" UTC
    close_dt = datetime.strptime(close_time_str, "%H:%M").time()

    # 如果数据时间超过收盘时间，返回收盘时间
    if data_dt_tz.time() > close_dt:
        # 返回当天收盘时间
        display_dt = datetime.combine(today, close_dt, tzinfo=tz)
        return display_dt.isoformat()

    return data_timestamp
```

### 2. 前端改动

#### 2.1 类型定义更新

```typescript
interface MarketIndex {
  // ... 现有字段
  dataTimestamp?: string;  // 数据更新时间（ISO 格式）
  timezone?: string;       // 市场时区
}
```

#### 2.2 时间格式化函数

```typescript
/**
 * 格式化时间为用户时区
 * @param isoTimestamp ISO 格式时间戳
 * @returns 格式化的时间字符串，如 "15:57"
 */
function formatToUserTimezone(isoTimestamp: string | undefined): string {
  if (!isoTimestamp) return '--';

  try {
    const date = new Date(isoTimestamp);
    // 使用用户浏览器时区
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

#### 2.3 卡片显示逻辑

```vue
<!-- 使用 dataTimestamp 显示 -->
<div class="market-time" v-if="indexData.dataTimestamp">
  <span>{{ formatToUserTimezone(indexData.dataTimestamp) }}</span>
</div>
```

## 数据流

```
数据源 (原始时间) → 后端 (添加 timezone，限制不超过收盘时间)
    → API 返回 (dataTimestamp + timezone)
    → 前端 (转换到用户浏览器时区显示)
```

## 改动文件清单

### 后端
- `src/datasources/index_source.py`: 添加 `timezone` 字段到返回数据
- `api/routes/indices.py`: 添加 `dataTimestamp` 字段，计算最后有效时间

### 前端
- `web/src/types/index.ts`: 添加 `dataTimestamp`, `timezone` 字段
- `web/src/components/IndexCard.vue`: 使用新字段，添加格式化函数
- `web/src/utils/time.ts` (可选): 添加通用时区转换函数

## 测试场景

| 场景 | 期望显示时间 | 期望状态 |
|------|-------------|---------|
| 港股 16:00 收盘，数据 15:57 | 15:57 | 收盘 |
| 港股 16:00 收盘，数据 16:02 | 16:00（收盘时间） | 收盘 |
| A股 15:00 收盘，数据 15:00 | 15:00 | 收盘 |
| A股 15:00 收盘，数据 16:14 | 15:00（收盘时间） | 收盘 |
| A股早盘 10:30，数据 10:30 | 10:30 | 交易中 |

## 后续优化（不在本次范围）

- 节假日判断（需要维护各国节假日列表或调用 API）
- 显示"盘后"状态
- 用户可选择显示原始时间或用户时间
