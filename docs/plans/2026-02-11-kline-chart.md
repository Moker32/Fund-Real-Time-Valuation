# K 线图功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为基金卡片增加小型 K 线图，可视化展示基金历史净值走势。

**Architecture:** 采用轻量级图表库 `lightweight-charts`，在 FundCard 组件底部嵌入迷你 K 线图。复用现有的 `/history` API 端点获取数据，前端按需加载历史数据。

**Tech Stack:** Vue 3 + TypeScript + lightweight-charts + FastAPI

---

### Task 1: 添加 lightweight-charts 依赖

**Files:**
- Modify: `web/package.json` - 添加依赖

**Step 1: 运行测试验证当前状态**

```bash
cd web && pnpm run test 2>/dev/null || echo "无测试命令，检查 lint"
```

**Step 2: 添加依赖**

```bash
cd web && pnpm add lightweight-charts
```

**Step 3: 验证安装**

```bash
pnpm list lightweight-charts
```

---

### Task 2: 添加 FundHistory 类型定义

**Files:**
- Modify: `web/src/types/index.ts` - 添加 OHLCV 类型

**Step 1: 编写失败的测试**

```typescript
// tests/types/fund-history.test.ts
import { describe, it, expect } from 'vitest';
import type { FundHistory } from '@/types';

describe('FundHistory Type', () => {
  it('should have required fields', () => {
    const history: FundHistory = {
      time: '2024-01-10',
      open: 1.500,
      high: 1.520,
      low: 1.490,
      close: 1.510,
      volume: 1000000,
    };
    expect(history.time).toBe('2024-01-10');
    expect(history.open).toBe(1.500);
  });
});
```

**Step 2: 运行测试验证失败**

```bash
pnpm run test -- tests/types/fund-history.test.ts
```

**Step 3: 添加类型定义**

```typescript
// web/src/types/index.ts

export interface FundHistory {
  time: string;       // 日期时间
  open: number;       // 开盘价
  high: number;       // 最高价
  low: number;        // 最低价
  close: number;      // 收盘价
  volume: number;     // 成交量
}
```

**Step 4: 运行测试验证通过**

```bash
pnpm run test -- tests/types/fund-history.test.ts
```

---

### Task 3: 扩展 Fund 接口添加 history 字段

**Files:**
- Modify: `web/src/types/index.ts` - Fund 接口添加可选 history 字段

**Step 1: 编写测试**

```typescript
// tests/types/fund-with-history.test.ts
import { describe, it, expect } from 'vitest';
import type { Fund } from '@/types';

describe('Fund with History', () => {
  it('should allow optional history field', () => {
    const fund: Fund = {
      code: '161039',
      name: '富国中证新能源汽车指数',
      netValue: 2.0,
      netValueDate: '2024-01-10',
      estimateValue: 2.05,
      estimateChange: 0.05,
      estimateChangePercent: 2.5,
      history: [
        { time: '2024-01-10', open: 1.99, high: 2.01, low: 1.98, close: 2.0, volume: 1000000 },
      ],
    };
    expect(fund.history).toBeDefined();
    expect(fund.history?.length).toBe(1);
  });
});
```

**Step 2: 运行测试验证失败**

```bash
pnpm run test -- tests/types/fund-with-history.test.ts
```

**Step 3: 添加 history 字段到 Fund 接口**

```typescript
// web/src/types/index.ts
export interface Fund {
  // ... 现有字段
  history?: FundHistory[];  // 可选的历史 K 线数据
}
```

**Step 4: 运行测试验证通过**

```bash
pnpm run test -- tests/types/fund-with-history.test.ts
```

---

### Task 4: 创建 FundChart 组件

**Files:**
- Create: `web/src/components/FundChart.vue` - K 线图组件
- Create: `tests/components/FundChart.test.ts` - 组件测试

**Step 1: 编写组件测试（带 props 模拟）**

```typescript
// tests/components/FundChart.test.ts
import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import FundChart from '@/components/FundChart.vue';

describe('FundChart', () => {
  const mockData = [
    { time: '2024-01-10', open: 1.500, high: 1.520, low: 1.490, close: 1.510, volume: 1000000 },
    { time: '2024-01-11', open: 1.510, high: 1.530, low: 1.500, close: 1.520, volume: 1200000 },
  ];

  it('should render chart container', () => {
    const wrapper = mount(FundChart, {
      props: { data: mockData },
    });
    expect(wrapper.find('.fund-chart').exists()).toBe(true);
  });

  it('should handle empty data', () => {
    const wrapper = mount(FundChart, {
      props: { data: [] },
    });
    expect(wrapper.find('.fund-chart').exists()).toBe(true);
  });
});
```

**Step 2: 运行测试验证失败**

```bash
pnpm run test -- tests/components/FundChart.test.ts
```

**Step 3: 实现 FundChart 组件**

```vue
<!-- web/src/components/FundChart.vue -->
<template>
  <div class="fund-chart" ref="chartContainer"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { createChart, ColorType } from 'lightweight-charts';
import type { FundHistory } from '@/types';

const props = defineProps<{
  data: FundHistory[];
  height?: number;
}>();

const chartContainer = ref<HTMLElement | null>(null);
let chart: ReturnType<typeof createChart> | null = null;

const initChart = () => {
  if (!chartContainer.value) return;

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: props.height || 120,
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: '#666',
    },
    grid: {
      vertLines: { visible: false },
      horzLines: { color: '#f0f0f0' },
    },
    timeScale: {
      visible: false,
    },
    rightPriceScale: {
      visible: false,
    },
  });

  const candleSeries = chart.addCandlestickSeries({
    upColor: '#ef4444',
    downColor: '#22c55e',
    borderVisible: false,
    wickUpColor: '#ef4444',
    wickDownColor: '#22c55e',
  });

  if (props.data.length > 0) {
    candleSeries.setData(props.data);
  }
};

const updateData = () => {
  if (!chart) return;
  const series = chart.takeVisibleSeries();
  if (series && props.data.length > 0) {
    series.setData(props.data);
  }
};

watch(() => props.data, updateData, { deep: true });

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (chart) {
    chart.remove();
    chart = null;
  }
});

const handleResize = () => {
  if (chart && chartContainer.value) {
    chart.applyOptions({ width: chartContainer.value.clientWidth });
  }
};
</script>

<style scoped>
.fund-chart {
  width: 100%;
  min-height: 120px;
}
</style>
```

**Step 4: 运行测试验证**

```bash
pnpm run test -- tests/components/FundChart.test.ts
```

---

### Task 5: 在 FundCard 中集成 K 线图

**Files:**
- Modify: `web/src/components/FundCard.vue` - 添加图表区域
- Modify: `web/src/components/FundCard.test.ts` - 添加测试

**Step 1: 编写集成测试**

```typescript
// tests/components/FundCard-with-chart.test.ts
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import FundCard from '@/components/FundCard.vue';
import type { Fund } from '@/types';

describe('FundCard with K-line Chart', () => {
  const mockFund: Fund = {
    code: '161039',
    name: '富国中证新能源汽车指数',
    netValue: 2.0,
    netValueDate: '2024-01-10',
    estimateValue: 2.05,
    estimateChange: 0.05,
    estimateChangePercent: 2.5,
    type: '股票型',
    source: 'eastmoney',
    isHolding: true,
    hasRealTimeEstimate: true,
  };

  const mockHistory = [
    { time: '2024-01-10', open: 1.500, high: 1.520, low: 1.490, close: 1.510, volume: 1000000 },
  ];

  it('should render chart when history is provided', () => {
    const wrapper = mount(FundCard, {
      props: { fund: { ...mockFund, history: mockHistory } },
    });
    expect(wrapper.find('.fund-chart').exists()).toBe(true);
  });

  it('should not render chart when history is empty', () => {
    const wrapper = mount(FundCard, {
      props: { fund: mockFund },
    });
    expect(wrapper.find('.fund-chart').exists()).toBe(false);
  });
});
```

**Step 2: 运行测试验证失败**

```bash
pnpm run test -- tests/components/FundCard-with-chart.test.ts
```

**Step 3: 修改 FundCard.vue**

在模板底部（footer 之后）添加图表区域：

```vue
<!-- 在 <footer class="fund-card-footer"> 之后添加 -->
<footer v-if="fund.history && fund.history.length > 0" class="fund-card-chart">
  <FundChart :data="fund.history" :height="100" />
</footer>
```

添加 import：

```typescript
import FundChart from './FundChart.vue';
```

**Step 4: 运行测试验证通过**

```bash
pnpm run test -- tests/components/FundCard-with-chart.test.ts
```

---

### Task 6: 修改 history API 返回 OHLCV 数据

**Files:**
- Modify: `api/routes/funds.py` - 扩展 `/history` 端点

**Step 1: 编写 API 测试**

```python
# tests/test_fund_history.py
from fastapi.test_client import TestClient
from api.main import app

client = TestClient(app)

def test_fund_history_returns_ohlcv():
    """测试历史端点返回 OHLCV 数据"""
    response = client.get("/api/funds/161039/history")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) > 0
    # 验证 OHLCV 字段
    record = data["data"][0]
    assert "time" in record
    assert "open" in record
    assert "high" in record
    assert "low" in record
    assert "close" in record
    assert "volume" in record
```

**Step 2: 运行测试验证失败**

```bash
uv run pytest tests/test_fund_history.py -v
```

**Step 3: 扩展历史数据获取逻辑**

在 `api/routes/funds.py` 的 `FundHistorySource` 类中：

```python
class FundHistorySource:
    """基金历史净值数据源"""

    async def get_history(self, code: str, days: int = 60) -> list[dict]:
        """
        获取基金历史净值

        Returns:
            list[dict]: OHLCV 数据列表
                - time: 日期时间
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - volume: 成交量
        """
        try:
            import akshare as ak

            # 获取历史净值数据
            fund_df = ak.fund_nav_history(symbol=code)

            if fund_df.empty:
                return []

            # 转换为 OHLCV 格式
            result = []
            recent = fund_df.tail(days)

            for _, row in recent.iterrows():
                date = row.get('净值日期', row.get('date', ''))
                unit_nav = row.get('单位净值', row.get('unit_nav', 0))

                if date and unit_nav:
                    result.append({
                        "time": date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                        "open": round(float(unit_nav), 4),
                        "high": round(float(unit_nav), 4),  # 单点数据，high/low/close 同值
                        "low": round(float(unit_nav), 4),
                        "close": round(float(unit_nav), 4),
                        "volume": 0,  # 基金不提供成交量
                    })

            return result[::-1]  # 升序排列

        except Exception as e:
            logger.error(f"获取基金 {code} 历史数据失败: {e}")
            return []
```

**Step 4: 运行测试验证通过**

```bash
uv run pytest tests/test_fund_history.py -v
```

---

### Task 7: 添加历史数据获取到 Store

**Files:**
- Modify: `web/src/stores/fundStore.ts` - 添加 history 相关 action

**Step 1: 编写 Store 测试**

```typescript
// tests/stores/fundStore-history.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useFundStore } from '@/stores/fundStore';

vi.mock('@/api', () => ({
  fundApi: {
    getFundHistory: vi.fn(),
  },
}));

import { fundApi } from '@/api';

describe('FundStore - History', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should have fetchHistory action', () => {
    const store = useFundStore();
    expect(typeof store.fetchHistory).toBe('function');
  });
});
```

**Step 2: 运行测试验证失败**

```bash
pnpm run test -- tests/stores/fundStore-history.test.ts
```

**Step 3: 添加 API 方法**

```typescript
// web/src/api/fund.ts
export const getFundHistory = async (code: string): Promise<FundHistory[]> => {
  const response = await api.get<{ data: FundHistory[] }>(`/funds/${code}/history`);
  return response.data.data;
};
```

**Step 4: 添加 Store Action**

```typescript
// 在 fundStore.ts 中
async function fetchHistory(code: string) {
  try {
    const history = await fundApi.getFundHistory(code);
    const index = funds.value.findIndex((f) => f.code === code);
    if (index !== -1) {
      funds.value[index] = { ...funds.value[index], history };
    }
    return history;
  } catch (err) {
    console.error(`[FundStore] fetchHistory error for ${code}:`, err);
    return [];
  }
}
```

**Step 5: 运行测试验证通过**

```bash
pnpm run test -- tests/stores/fundStore-history.test.ts
```

---

### Task 8: 完善 FundChart 样式和交互

**Files:**
- Modify: `web/src/components/FundChart.vue` - 优化样式和交互

**Step 1: 添加样式**

```vue
<style scoped>
.fund-chart {
  width: 100%;
  min-height: 120px;
  margin-top: 8px;
  border-radius: 6px;
  overflow: hidden;
  background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent);
}
</style>
```

**Step 2: 添加 hover 提示功能（可选增强）**

```typescript
// 在 initChart 中添加 crosshair
chart.applyOptions({
  crosshair: {
    mode: CrosshairMode.Normal,
  },
});
```

---

### Task 9: 运行完整测试套件

**Files:**
- 运行所有相关测试

**Step 1: 运行前端测试**

```bash
cd web && pnpm run test
```

**Step 2: 运行后端测试**

```bash
uv run pytest tests/ -v
```

**Step 3: 运行类型检查**

```bash
cd web && pnpm run typecheck
```

**Step 4: 运行 lint**

```bash
cd web && pnpm run lint
uv run ruff check .
```

---

### Task 10: 提交代码

**Step 1: 检查更改**

```bash
git status
git diff --stat
```

**Step 2: 提交**

```bash
git add .
git commit -m "feat: add K-line chart to fund cards"
```
