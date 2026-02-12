# 基金持仓管理功能设计方案

## 背景

当前系统已有基础的持仓标记功能（`isHolding`），后端 `Holding` 模型支持 `shares`（份额）和 `cost`（成本价）字段，但前端和 API 尚未实现份额/成本价的设置和展示功能。

## 目标

1. **Overview 卡片展开** - 点击展开显示所有持仓基金的收益汇总和列表
2. **基金详情弹窗** - 点击基金卡片打开弹窗展示详情
3. 根据实时估值动态计算持有收益
4. 基金卡片上不展示收益信息（点击卡片查看详情）

---

## 设计方案

### 1. 后端 API 扩展

#### 1.1 修改 `PUT /api/funds/{code}/holding` 接口

**新增请求参数**：
```python
shares: float | None = Query(None, ge=0, description="持有份额")
cost: float | None = Query(None, ge=0, description="单位成本价")
```

**行为**：
- 当 `holding=true` 时，允许同时传入 `shares` 和 `cost` 创建/更新持仓信息
- 当 `holding=false` 时，忽略份额和成本价参数（移除持仓）
- 仅传入 `shares` 或 `cost` 时，更新对应字段

#### 1.2 新增获取持仓列表 API

**接口**：`GET /api/funds/holdings`

**响应**：
```json
{
  "holdings": [
    {
      "code": "161039",
      "name": "易方达消费行业股票",
      "shares": 10000.00,
      "cost": 1.2345,
      "totalCost": 12345.00,
      "netValue": 1.4567,
      "estimateValue": 1.4678,
      "holdingProfit": 233.00,
      "holdingProfitPercent": 18.88,
      "estimateTotalValue": 14678.00
    }
  ],
  "totalProfit": 12345.67,
  "totalProfitPercent": 15.23,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### 1.3 修改 `FundResponse` 模型

**新增字段**：
```python
shares: float | None = None        # 持有份额
cost: float | None = None          # 单位成本价
totalCost: float | None = None     # 总成本 (shares * cost)
holdingProfit: float | None = None     # 持有收益（基于估算净值）
holdingProfitPercent: float | None = None  # 持有收益率
estimateTotalValue: float | None = None   # 估算总市值
```

### 2. 前端类型扩展

#### 2.1 扩展 `Fund` 接口 (`web/src/types/index.ts`)

```typescript
export interface Fund {
  // ... 现有字段
  shares?: number;           // 持有份额
  cost?: number;             // 单位成本价
  totalCost?: number;        // 总成本
  holdingProfit?: number;    // 持有收益
  holdingProfitPercent?: number; // 持有收益率
  estimateTotalValue?: number;   // 估算总市值
}
```

#### 2.2 新增 `Holding` 接口

```typescript
export interface Holding {
  code: string;
  name: string;
  shares: number;
  cost: number;
  totalCost: number;
  netValue: number;
  netValueDate: string;
  estimateValue: number;
  estimateChange: number;
  estimateChangePercent: number;
  holdingProfit: number;
  holdingProfitPercent: number;
  estimateTotalValue: number;
}
```

### 3. 前端 API 扩展 (`web/src/api/index.ts`)

```typescript
export const fundApi = {
  // ... 现有方法

  async getHoldings(): Promise<{
    holdings: Holding[];
    totalProfit: number;
    totalProfitPercent: number;
    timestamp: string;
  }> {
    return api.get('/api/funds/holdings');
  },

  async updateHolding(
    code: string,
    holding: boolean,
    shares?: number,
    cost?: number
  ): Promise<{ success: boolean; message: string }> {
    return api.put(`/api/funds/${code}/holding`, null, {
      params: { holding, shares, cost }
    });
  },
};
```

### 4. 创建持仓管理 Store (`web/src/stores/holdingStore.ts`)

```typescript
export const useHoldingStore = defineStore('holdings', () => {
  const holdings = ref<Holding[]>([]);
  const totalProfit = ref(0);
  const totalProfitPercent = ref(0);
  const loading = ref(false);

  async function fetchHoldings() {
    loading.value = true;
    try {
      const response = await fundApi.getHoldings();
      holdings.value = response.holdings || [];
      totalProfit.value = response.totalProfit;
      totalProfitPercent.value = response.totalProfitPercent;
    } finally {
      loading.value = false;
    }
  }

  async function updateHolding(
    code: string,
    holding: boolean,
    shares?: number,
    cost?: number
  ) {
    const response = await fundApi.updateHolding(code, holding, shares, cost);
    if (response.success) {
      await fetchHoldings();
    }
    return response;
  }

  return { holdings, totalProfit, totalProfitPercent, loading, fetchHoldings, updateHolding };
});
```

### 5. Overview 卡片展开功能

#### 5.1 修改 `MarketOverview.vue`

**交互**：点击卡片展开/收起持仓详情

**展开后布局**：
```
┌─────────────────────────────────────────────────────────────────┐
│  持仓总值: ¥146,778       持有收益: +¥12,345.67 (+18.90%)    × │
├─────────────────────────────────────────────────────────────────┤
│  ↑ 收起                                                      │
├─────────────────────────────────────────────────────────────────┤
│  基金名称       份额      成本价    市值      持有收益    操作  │
├─────────────────────────────────────────────────────────────────┤
│  招商中证白酒   10,000    1.2345   14,678    +¥2,233    编辑    │
│  易方达消费     5,000     2.0000   9,450     -¥550      编辑    │
│  易方达消费     5,000     2.0000   9,450     -¥550      编辑    │
└─────────────────────────────────────────────────────────────────┘
```

**功能**：
1. 展示所有持仓基金的简洁列表
2. 每行显示：基金名称、份额、成本价、估算市值、持有收益、操作
3. 点击"编辑"打开份额编辑对话框
4. 展开状态下显示"收起"按钮

### 6. 基金详情弹窗

#### 6.1 新建 `FundDetailModal.vue` 组件

**设计**：全屏居中弹窗，背景半透明遮罩

**弹窗布局**：
```
┌─────────────────────────────────────────────────────────────────┐
│  易方达消费行业股票                                     ×        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  161039                                                      │
│  ───────────────────────────────────────────────────────────    │
│                                                                  │
│  ┌─────────────────────┐      ┌─────────────────────┐          │
│  │ 净值                │      │ 估值                │          │
│  │ 1.4567              │      │ 1.4678 (+0.76%)    │          │
│  │ 01/15 更新           │      │ 14:32 更新         │          │
│  └─────────────────────┘      └─────────────────────┘          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  [分时图] [K线图]                                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                                                             ││
│  │                    图表区域                                 ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  持有份额    10,000.00    单位成本    ¥1.2345           │  │
│  │  总成本      ¥12,345.00   估算市值    ¥14,678           │  │
│  │  持有收益    +¥2,333.00   收益率       +18.90%          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                    [编辑份额]  [取消持有]                           │
└─────────────────────────────────────────────────────────────────┘
```

**功能**：
1. 基本信息：基金代码、名称、净值、估值、涨跌
2. 图表区域：Tab 切换分时图/K线图
3. 持仓信息区域（仅持有时显示）
4. 操作按钮：编辑份额、取消持有

#### 6.2 修改 FundCard.vue

```typescript
// 添加点击事件，打开详情弹窗
const emit = defineEmits<{
  (e: 'click', code: string): void;
}>();

function onCardClick() {
  emit('click', props.fund.code);
}
```

#### 6.3 修改 FundsView.vue

```vue
<FundCard
  v-for="fund in fundStore.holdingFirstFunds"
  :key="fund.code"
  :fund="fund"
  @click="handleFundClick"
  @remove="handleRemoveFund"
/>

<FundDetailModal
  v-if="selectedFundCode"
  :code="selectedFundCode"
  :visible="showFundDetail"
  @close="showFundDetail = false"
/>

<script>
// ...
const selectedFundCode = ref<string | null>(null);
const showFundDetail = ref(false);

function handleFundClick(code: string) {
  selectedFundCode.value = code;
  showFundDetail.value = true;
}
</script>
```

### 7. 份额编辑弹窗

#### 7.1 新建 `EditHoldingDialog.vue` 组件

**功能**：
- 修改持有份额
- 修改单位成本价
- 保存后更新持仓信息

---

## 文件修改清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `api/routes/funds.py` | 修改 | 扩展 `/holding` API，新增 `holdings` API |
| `api/models.py` | 修改 | FundResponse 添加持仓相关字段 |
| `web/src/types/index.ts` | 修改 | 添加 shares、cost、holdingProfit 等字段 |
| `web/src/api/index.ts` | 修改 | 添加 getHoldings、updateHolding API |
| `web/src/stores/holdingStore.ts` | 新建 | 持仓管理 Pinia Store |
| `web/src/components/MarketOverview.vue` | 修改 | 添加展开/收起持仓详情功能 |
| `web/src/components/FundDetailModal.vue` | 新建 | 基金详情弹窗组件 |
| `web/src/components/EditHoldingDialog.vue` | 新建 | 份额编辑弹窗组件 |
| `web/src/components/FundCard.vue` | 修改 | 添加点击事件 |
| `web/src/views/FundsView.vue` | 修改 | 添加弹窗组件和事件处理 |

---

## 验证步骤

1. **API 测试**：
   ```bash
   # 更新持仓（带份额）
   curl -X PUT "http://localhost:8000/api/funds/161039/holding?holding=true&shares=10000&cost=1.2345"

   # 获取持仓列表
   curl http://localhost:8000/api/funds/holdings
   ```

2. **前端测试**：
   - 点击 Overview 卡片展开持仓列表
   - 点击基金卡片打开详情弹窗
   - 验证收益计算是否正确
   - 点击"编辑份额"修改份额和成本价

3. **Playwright 浏览器测试**：
   ```bash
   pnpm run dev:web
   # 使用 Playwright 检查控制台无错误
   ```
