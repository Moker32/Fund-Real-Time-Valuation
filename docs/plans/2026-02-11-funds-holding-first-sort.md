# 基金卡片持有优先排序功能实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 在基金列表中，持有基金排在前面，非持有基金保持原序

**架构：** 在 Vue store 中添加 computed getter `holdingFirstFunds`，按 `isHolding` 字段分组排序

**技术栈：** Vue 3 + Pinia + TypeScript

---

## 当前代码状态

| 组件 | 状态 | 说明 |
|------|------|------|
| 后端 API `isHolding` | 已完成 | `api/routes/funds.py` 中已实现 |
| 前端类型 `Fund.isHolding` | 已完成 | `web/src/types/index.ts:13` |
| FundCard 显示持有标签 | 已完成 | `web/src/components/FundCard.vue:18` |
| 排序逻辑 | 缺失 | 需要实现 |

---

## 任务清单

### Task 1: 在 fundStore.ts 添加排序 computed

**文件：**
- Modify: `web/src/stores/fundStore.ts`

**Step 1: 读取文件确认结构**

```bash
head -70 web/src/stores/fundStore.ts
```

**Step 2: 在 computed getters 区域添加新 getter**

在 `averageChange` getter（第 65-69 行）之后添加：

```typescript
  // 持有优先排序（保持原序）
  const holdingFirstFunds = computed(() => {
    const holding = funds.value.filter((f) => f.isHolding);
    const notHolding = funds.value.filter((f) => !f.isHolding);
    return [...holding, ...notHolding];
  });
```

**Step 3: 在 return 语句中导出**

在 `averageChange` 之后添加：

```typescript
    holdingFirstFunds,
```

**Step 4: 验证类型检查**

```bash
cd web && pnpm run typecheck
```

预期：无错误

---

### Task 2: 更新 FundsView.vue 使用排序后的列表

**文件：**
- Modify: `web/src/views/FundsView.vue`

**Step 1: 读取文件找到 fundStore.funds 引用**

```bash
grep -n "fundStore.funds" web/src/views/FundsView.vue
```

**Step 2: 将 `fundStore.funds` 替换为 `fundStore.holdingFirstFunds`**

**Step 3: 验证类型检查**

```bash
cd web && pnpm run typecheck
```

预期：无错误

---

### Task 3: 验证功能

**Step 1: 启动前端开发服务器**

```bash
cd web && pnpm run dev
```

**Step 2: 手动验证**
1. 打开浏览器访问 http://localhost:5173
2. 确认持有基金（isHolding=true）排在列表前面
3. 确认非持有基金顺序与 API 返回顺序一致

---

### Task 4: 提交代码

```bash
git add web/src/stores/fundStore.ts web/src/views/FundsView.vue
git commit -m "feat: 基金列表持有优先排序"
```

---

## 风险与注意事项

1. **向后兼容**：`funds` 保留用于其他 computed（如 `topGainers`、`topLosers`）
2. **性能影响**：排序在 computed 中完成，仅在 `funds` 变化时重新计算
3. **无测试覆盖**：当前无专门测试，如有需要可后续添加
