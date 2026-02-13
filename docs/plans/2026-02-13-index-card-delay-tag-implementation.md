# 指数卡片延时标签实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在指数卡片右上角添加"延时"标签，标识使用 yfinance 数据源的指数

**Architecture:** 前端直接判断数据源类型，UI 侧展示延时标签，无需后端改动

**Tech Stack:** Vue 3 + TypeScript + SCSS

---

## 任务总览

本功能只需要修改一个文件：`web/src/components/IndexCard.vue`

预计工作量：2-3 个子任务

---

### Task 1: 添加延时判断计算属性

**Files:**
- Modify: `web/src/components/IndexCard.vue:77-90`

**Step 1: 在 script 中添加 isDelayed 计算属性**

打开 `web/src/components/IndexCard.vue`，在现有计算属性附近（大约 line 90 后面）添加：

```ts
// 判断是否为延时数据源
const isDelayed = computed(() => props.index.source === 'yfinance_index');
```

**Step 2: 验证代码**

检查代码是否正确添加，SCSS 文件中是否有 `delay-tag` 相关样式（预期没有，这是下一步）

---

### Task 2: 添加延时标签模板

**Files:**
- Modify: `web/src/components/IndexCard.vue:17-21`

**Step 1: 在 card-header 区域添加延时标签**

在 `card-header` 的 `trading-status` div 后面（大约 line 20）添加延时标签：

```vue
<div v-if="isDelayed" class="delay-tag">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 6V12L16 14"/>
  </svg>
  <span>延时</span>
</div>
```

添加位置在 `trading-status` div 后面，整个 `card-header` 结构变为：

```vue
<div class="card-header">
  <div class="index-info">
    <span class="index-name">{{ indexData.name }}</span>
    <span class="index-region" :class="`region-${indexData.region}`">{{ regionLabel }}</span>
  </div>
  <div class="header-right">
    <div class="trading-status" :class="`status-${indexData.tradingStatus}`">
      <span class="status-dot"></span>
      <span class="status-text">{{ statusText }}</span>
    </div>
    <!-- 添加这里 -->
    <div v-if="isDelayed" class="delay-tag">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6V12L16 14"/>
      </svg>
      <span>延时</span>
    </div>
  </div>
</div>
```

**Step 2: 验证模板语法**

确保模板没有语法错误。

---

### Task 3: 添加延时标签样式

**Files:**
- Modify: `web/src/components/IndexCard.vue:335-345`

**Step 1: 添加 delay-tag 样式**

在 `.trading-status` 样式块后面（大约 line 335）添加：

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

  svg {
    width: 12px;
    height: 12px;
  }
}
```

**Step 2: 调整 card-header 布局**

确保 `card-header` 能正确排列延时标签。更新 `.card-header` 样式为 flexbox 布局：

```scss
.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}
```

---

### Task 4: 验证实现

**Step 1: 启动开发服务器**

```bash
cd web && pnpm run dev
```

**Step 2: 检查浏览器渲染**

打开 http://localhost:3000/indices 页面，检查：
1. 使用 yfinance 的指数（如日经指数、欧洲指数）是否显示橙色"延时"标签
2. 非 yfinance 的指数是否不显示延时标签
3. 标签样式是否与其他标签（区域、交易状态）风格一致

**Step 3: 运行前端类型检查**

```bash
cd web && pnpm run typecheck
```

确保没有类型错误。

---

## 验收标准

1. ✅ 使用 yfinance 的指数卡片右上角显示橙色"延时"标签
2. ✅ 非 yfinance 数据源的卡片不显示延时标签
3. ✅ 标签样式与其他标签（区域、交易状态）风格一致
4. ✅ 响应式布局正常

---

## 提交

```bash
git add web/src/components/IndexCard.vue
git commit -m "feat: 指数卡片添加延时标签

- 添加 isDelayed 计算属性判断 yfinance 数据源
- 在卡片右上角显示延时标签
- 样式与现有标签风格一致"
```
