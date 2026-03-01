# QDII 基金卡片展示优化设计

## 1. 概述

### 1.1 优化目标

为 QDII 基金卡片提供更清晰的信息展示，让用户能够：
- 快速识别 QDII 基金类型
- 理解数据更新时间

### 1.2 设计原则

1. **一致性**：QDII 卡片与普通基金卡片保持整体布局一致
2. **简洁性**：避免添加过多标签和信息，保持界面清爽
3. **视觉区分**：通过 QDII 类型标签的视觉差异区分，而非增加额外标签

### 1.3 QDII 基金特殊性

- 无实时估值（投资海外市场，T+N 确认）
- 净值更新延迟（美国市场 T+1，其他市场可能更长）
- 受汇率波动影响

---

## 2. UI 优化方案

### 2.1 整体布局

保持 FundCard 现有布局结构，QDII 卡片与普通基金卡片完全一致：

```
┌─────────────────────────────────────────────┐
│ card-header                                 │
│  基金代码  [持有] [删除] [QDII类型标签]     │  ← QDII类型标签更显眼
│  基金名称                                   │
├─────────────────────────────────────────────┤
│ card-body                                   │
│  净值  1.2345  02/28                        │
│  前日  1.2300  02/27                        │
│                        [涨跌幅区域 + 图表]   │
├─────────────────────────────────────────────┤
│ card-footer                                 │
│  更新: 02/28  来源: fund123                 │  ← 统一使用"更新"标签
└─────────────────────────────────────────────┘
```

### 2.2 QDII 类型标签优化

**目标**：让 QDII 类型标签更显眼，一眼就能识别

**位置**：header 区域，与现有类型标签位置相同

**优化方案**：紫色背景样式

```scss
.fund-type {
  // QDII 特殊样式
  &.type-qdii {
    background: rgba(88, 86, 214, 0.2);  // 紫色背景，更明显
    color: #5856d6;
    font-weight: 500;
  }
}
```

紫色更符合国际/海外的视觉联想，与 QDII 投资海外市场的特点相呼应。

**视觉效果**：

```
┌─────────────────────────────────────────────┐
│  161725  [持有] [删除]  QDII               │  ← 紫色背景
│  易方达中证海外中国互联网50                 │
└─────────────────────────────────────────────┘
```

### 2.3 时间显示统一

**当前问题**：QDII 卡片左下角显示"净值日期: MM/DD"，与其他基金显示的"更新: HH:MM"格式不一致

**优化方案**：统一使用"更新"标签

```vue
<!-- 统一的时间显示格式 -->
<span class="update-time">
  更新: {{ formatUpdateTime(fund) }}
</span>
```

**格式规则**：
- 当天更新的数据：显示"更新: HH:MM"（如"更新: 14:30"）
- 非当天更新的数据：显示"更新: MM/DD"（如"更新: 02/28"）

对于 QDII 基金，由于净值延迟，通常显示为"更新: MM/DD"格式。

### 2.4 QDII 时间显示特殊处理

**背景**：外部数据源没有返回 QDII 基金的数据更新时间，因此 QDII 基金不应显示"更新时间"字段。

**实现方式**：

```vue
<span v-if="fund.hasRealTimeEstimate !== false" class="update-time">
  更新: {{ formatTime(fund.estimateTime) }}
</span>
```

**判断逻辑**：
- `hasRealTimeEstimate === false`：QDII 基金，不显示更新时间
- `hasRealTimeEstimate !== false`：普通基金，显示更新时间

**显示效果**：

| 基金类型 | 更新时间 | 数据来源 |
|---------|---------|---------|
| 普通基金 | ✅ 显示"更新: xx:xx" | ✅ 显示 |
| QDII 基金 | ❌ 不显示 | ✅ 显示 |

**卡片对比**：

```
普通基金卡片:
┌─────────────────────────────────────────────┐
│  ...                                        │
│  更新: 14:30  来源: eastmoney               │
└─────────────────────────────────────────────┘

QDII 基金卡片:
┌─────────────────────────────────────────────┐
│  ...                                        │
│  来源: fund123                              │  ← 只显示数据来源
└─────────────────────────────────────────────┘
```

---

## 3. 实施方案

### 3.1 前端改动

#### 3.1.1 FundCard.vue 组件改动

**改动点 1**：为 QDII 类型标签添加特殊样式

```vue
<template>
  <div class="fund-card">
    <div class="card-header">
      <div class="header-row">
        <span class="fund-code">{{ fund.code }}</span>
        <div class="card-actions">
          <!-- 现有按钮 -->
          <span 
            class="fund-type" 
            :class="typeClass"
          >
            {{ fund.type || '其他' }}
          </span>
        </div>
      </div>
      <!-- ... -->
    </div>
    <!-- ... -->
  </div>
</template>

<script setup lang="ts">
const isQDII = computed(() => 
  props.fund.hasRealTimeEstimate === false || 
  props.fund.type === 'QDII'
);

const typeClass = computed(() => {
  if (isQDII.value) {
    return 'type-qdii';
  }
  // 其他类型样式...
  return '';
});
</script>
```

**改动点 2**：统一时间显示格式

```vue
<template>
  <div class="card-footer">
    <span class="update-time">
      更新: {{ formatUpdateTime(fund) }}
    </span>
    <span class="data-source">{{ fund.source }}</span>
  </div>
</template>

<script setup lang="ts">
const formatUpdateTime = (fund: Fund) => {
  // 统一格式化逻辑
  if (isToday(fund.updateTime)) {
    return format(fund.updateTime, 'HH:mm');
  }
  return format(fund.updateTime, 'MM/DD');
};
</script>
```

#### 3.1.2 样式文件改动

```scss
// web/src/components/FundCard.vue 或全局样式

.fund-type {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  
  // QDII 特殊样式
  &.type-qdii {
    background: rgba(88, 86, 214, 0.2);
    color: #5856d6;
    font-weight: 500;
  }
  
  // 深色模式适配
  @media (prefers-color-scheme: dark) {
    &.type-qdii {
      background: rgba(138, 136, 224, 0.25);
      color: #a8a4e0;
    }
  }
}
```

### 3.2 后端改动

无需后端改动。现有 API 已返回 `hasRealTimeEstimate` 字段用于识别 QDII 基金，时间字段也已包含在响应中。

---

## 4. 视觉规范

### 4.1 QDII 类型标签

| 属性 | 值 |
|------|-----|
| 背景色 | `rgba(88, 86, 214, 0.2)` |
| 文字色 | `#5856d6` |
| 字重 | `500` (Medium) |
| 圆角 | `var(--radius-full)` |
| 内边距 | `2px 8px` |

### 4.2 深色模式

| 属性 | 值 |
|------|-----|
| 背景色 | `rgba(138, 136, 224, 0.25)` |
| 文字色 | `#a8a4e0` |

---

## 5. 实施步骤

### 步骤 1：添加 QDII 类型标签样式

**文件**：`web/src/components/FundCard.vue`

**任务**：
1. 添加 `.type-qdii` 样式类
2. 确保深色模式适配

### 步骤 2：统一时间显示

**文件**：`web/src/components/FundCard.vue`

**任务**：
1. 移除 QDII 卡片中特殊的"净值日期"显示逻辑
2. 统一使用"更新: MM/DD"或"更新: HH:MM"格式
3. 确保所有基金卡片时间显示一致

### 步骤 3：测试验证

**测试项**：
1. QDII 基金卡片显示紫色标签
2. 普通 A 股基金不受影响
3. 时间显示格式统一
4. 响应式布局正常
5. 深色模式正常

---

## 6. 改动前后对比

### 改动前

```
┌─────────────────────────────────────────────┐
│  161725  [持有] [删除]  QDII                │  ← 普通类型标签样式
│  易方达中证海外中国互联网50                 │
│  ...                                        │
│  净值日期: 02/28  来源: fund123             │  ← 特殊的时间标签
└─────────────────────────────────────────────┘
```

### 改动后

```
┌─────────────────────────────────────────────┐
│  161725  [持有] [删除]  QDII               │  ← 紫色背景
│  易方达中证海外中国互联网50                 │
│  ...                                        │
│  更新: 02/28  来源: fund123                 │  ← 统一的"更新"标签
└─────────────────────────────────────────────┘
```

---

## 7. 参考文档

- [IndexCard 延迟标签设计](2026-02-13-index-card-delay-tag-design.md)
- [项目代码风格指南](../../AGENTS.md)
- [响应式设计断点](../../AGENTS.md)

---

## 8. 类型标签格式说明

### 8.1 实际类型标签格式

基金类型字段 `fund.type` 采用**两级类型格式**：`主类型-子类型`

**常见示例**：

| 类型值 | 主类型 | 子类型 |
|--------|--------|--------|
| QDII-商品 | QDII | 商品 |
| QDII-混合 | QDII | 混合 |
| QDII-股票 | QDII | 股票 |
| 股票型-标准指数 | 股票型 | 标准指数 |
| 混合型-偏股 | 混合型 | 偏股 |
| 债券型-长债 | 债券型 | 长债 |

### 8.2 当前渲染方式

整个类型字符串在单个 `<span>` 中统一渲染，不做拆分：

```vue
<span class="fund-type">{{ fund.type || '其他' }}</span>
```

---

## 9. QDII 类型标签优化方案

### 9.1 方案说明

当类型以 `"QDII"` 开头时，整个标签应用紫色背景样式。

### 9.2 代码实现

```vue
<span 
  class="fund-type" 
  :class="{ 'fund-type--qdii': fund.type?.startsWith('QDII') }"
>
  {{ fund.type || '其他' }}
</span>
```

```scss
.fund-type {
  // 现有样式保持不变...
  
  &--qdii {
    background: rgba(139, 92, 246, 0.15);
    color: #8b5cf6;
  }
}
```

### 9.3 影响分析

| 类型示例 | 是否受影响 | 说明 |
|---------|-----------|------|
| QDII-商品 | ✅ 紫色背景 | 以 QDII 开头 |
| QDII-混合 | ✅ 紫色背景 | 以 QDII 开头 |
| QDII-股票 | ✅ 紫色背景 | 以 QDII 开头 |
| 股票型-标准指数 | ❌ 不受影响 | 不以 QDII 开头 |
| 混合型-偏股 | ❌ 不受影响 | 不以 QDII 开头 |
| 债券型-长债 | ❌ 不受影响 | 不以 QDII 开头 |

---

## 10. 发现的后端 Bug

### 10.1 问题描述

在分析类型标签时发现，后端 `_has_real_time_estimate` 和 `_is_qdii_fund` 函数使用**精确匹配**判断 QDII 类型：

```python
# 问题代码：精确匹配
fund_type == "QDII"
```

但实际 `fund.type` 值是两级格式如 `"QDII-商品"`，导致判断失效。

### 10.2 建议修复

```python
# 修复方案：使用前缀匹配
fund_type.startswith("QDII")

# 或使用包含匹配
"QDII" in fund_type
```

### 10.3 影响范围

- `_has_real_time_estimate` 函数：影响 QDII 基金实时估值判断
- `_is_qdii_fund` 函数：影响 QDII 基金识别

建议在后续迭代中修复此问题。