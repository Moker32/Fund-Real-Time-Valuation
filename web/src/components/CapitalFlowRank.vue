<template>
  <div class="capital-flow-rank">
    <div class="rank-header">
      <h3 class="rank-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
        {{ title }}
      </h3>
      <div class="rank-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="rank-list">
      <div
        v-for="(item, index) in displayList"
        :key="item.code"
        class="rank-item"
        :class="{ 'top-three': index < 3 }"
        @click="$emit('select', item)"
      >
        <div class="rank-number" :class="`rank-${index + 1}`">
          {{ index + 1 }}
        </div>
        <div class="rank-info">
          <span class="sector-name">{{ item.name }}</span>
          <span class="sector-change" :class="getChangeClass(item.changePercent)">
            {{ formatPercent(item.changePercent) }}
          </span>
        </div>
        <div class="rank-flow">
          <div class="flow-bar-container">
            <div
              class="flow-bar"
              :class="{ 'flow-in': item.mainInflow! > 0, 'flow-out': item.mainInflow! < 0 }"
              :style="{ width: getFlowWidth(item.mainInflow) }"
            />
          </div>
          <span class="flow-value" :class="{ 'text-rise': item.mainInflow! > 0, 'text-fall': item.mainInflow! < 0 }">
            {{ formatFlow(item.mainInflow) }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="displayList.length === 0" class="rank-empty">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6V12L16 14"/>
      </svg>
      <span>暂无数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { Sector } from '@/types';

interface Props {
  sectors: Sector[];
  title?: string;
  maxItems?: number;
}

const props = withDefaults(defineProps<Props>(), {
  title: '资金流向排行',
  maxItems: 10,
});

defineEmits<{
  select: [sector: Sector];
}>();

const activeTab = ref<'inflow' | 'outflow'>('inflow');

const tabs = [
  { key: 'inflow' as const, label: '净流入' },
  { key: 'outflow' as const, label: '净流出' },
];

// 过滤和排序数据
const displayList = computed(() => {
  let list = props.sectors.filter(s => s.mainInflow !== undefined);

  if (activeTab.value === 'inflow') {
    list = list.filter(s => (s.mainInflow || 0) > 0);
    list.sort((a, b) => (b.mainInflow || 0) - (a.mainInflow || 0));
  } else {
    list = list.filter(s => (s.mainInflow || 0) < 0);
    list.sort((a, b) => (a.mainInflow || 0) - (b.mainInflow || 0));
  }

  return list.slice(0, props.maxItems);
});

// 获取涨跌样式类
const getChangeClass = (value: number | undefined): string => {
  if (value === undefined) return 'neutral';
  if (value > 0) return 'rising';
  if (value < 0) return 'falling';
  return 'neutral';
};

// 格式化百分比
const formatPercent = (value: number | undefined): string => {
  if (value === undefined || isNaN(value)) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

// 格式化资金流向
const formatFlow = (value: number | undefined): string => {
  if (value === undefined || isNaN(value)) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}亿`;
};

// 计算资金流向条宽度
const maxFlowValue = computed(() => {
  const flows = props.sectors
    .filter(s => s.mainInflow !== undefined)
    .map(s => Math.abs(s.mainInflow || 0));
  return Math.max(...flows, 1);
});

const getFlowWidth = (value: number | undefined): string => {
  if (value === undefined || isNaN(value)) return '0%';
  const percentage = (Math.abs(value) / maxFlowValue.value) * 100;
  return `${Math.min(percentage, 100)}%`;
};
</script>

<style scoped>
.capital-flow-rank {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
}

.rank-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.rank-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.rank-title svg {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.rank-tabs {
  display: flex;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  padding: 2px;
}

.tab-btn {
  padding: 4px 12px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    color: var(--color-text-primary);
  }

  &.active {
    background: var(--color-bg-card);
    color: var(--color-text-primary);
    box-shadow: var(--shadow-sm);
  }
}

.rank-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.rank-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-bg-secondary);
  }

  &.top-three {
    background: var(--color-bg-secondary);
  }
}

.rank-number {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);

  &.rank-1 {
    background: linear-gradient(135deg, #ffd700, #ffed4a);
    color: #92400e;
  }

  &.rank-2 {
    background: linear-gradient(135deg, #c0c0c0, #e5e7eb);
    color: #4b5563;
  }

  &.rank-3 {
    background: linear-gradient(135deg, #cd7f32, #fbbf24);
    color: #92400e;
  }
}

.rank-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.sector-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sector-change {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);

  &.rising {
    color: var(--color-rise);
  }

  &.falling {
    color: var(--color-fall);
  }

  &.neutral {
    color: var(--color-text-tertiary);
  }
}

.rank-flow {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  min-width: 100px;
}

.flow-bar-container {
  width: 80px;
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.flow-bar {
  height: 100%;
  border-radius: 3px;
  transition: width var(--transition-normal);

  &.flow-in {
    background: linear-gradient(90deg, var(--color-rise), #f87171);
  }

  &.flow-out {
    background: linear-gradient(90deg, var(--color-fall), #4ade80);
  }
}

.flow-value {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  font-family: var(--font-mono);

  &.text-rise {
    color: var(--color-rise);
  }

  &.text-fall {
    color: var(--color-fall);
  }
}

.rank-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-xl);
  color: var(--color-text-tertiary);
  text-align: center;

  svg {
    width: 40px;
    height: 40px;
    opacity: 0.5;
  }

  span {
    font-size: var(--font-size-sm);
  }
}
</style>
