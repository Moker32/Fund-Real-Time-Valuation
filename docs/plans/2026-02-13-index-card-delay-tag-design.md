# 指数卡片数据源延时标注设计

## 背景

指数卡片需要标注数据来源，对于使用有严重延时的数据源（如 yfinance）需要显示延时标识，让用户了解数据的时效性。

## 需求

- 在指数卡片上显示数据来源
- 对于 yfinance 数据源的指数，显示"延时"标签
- 标签位置：卡片右上角，交易状态旁边

## UI 设计

```
┌─────────────────────────────────┐
│  指数名称        [区域] [延时]  │  ← 延时标签
│  交易状态                      │
├─────────────────────────────────┤
│  价格              涨跌幅      │
├─────────────────────────────────┤
│  高 | 低                      │
│  今开 | 昨收        更新时间    │
└─────────────────────────────────┘
```

### 延时标签样式

- 背景：橙色半透明 `rgba(255, 159, 10, 0.15)`
- 文字：橙色 `#ff9f0a`
- 图标：时钟 SVG 图标 + "延时" 文字
- 字体大小：12px
- 圆角：full

## 实现方案

### 前端改动

修改 `web/src/components/IndexCard.vue`：

1. 添加计算属性判断是否延时数据源：
```ts
const isDelayed = computed(() => props.index.source === 'yfinance_index');
```

2. 在 `card-header` 区域添加延时标签（交易状态右侧）：
```vue
<div v-if="isDelayed" class="delay-tag">
  <svg>时钟图标</svg>
  <span>延时</span>
</div>
```

3. 添加延时标签样式：
```scss
.delay-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  background: rgba(255, 159, 10, 0.15);
  color: #ff9f0a;
}
```

### 数据源判断逻辑

目前已知延时数据源：
- `yfinance_index` - 用于日经指数、欧洲指数等

后续如有更多延时源，可扩展判断逻辑。

## 验收标准

1. 使用 yfinance 的指数卡片右上角显示橙色"延时"标签
2. 非 yfinance 数据源的卡片不显示延时标签
3. 标签样式与其他标签（区域、交易状态）风格一致
4. 响应式布局正常
