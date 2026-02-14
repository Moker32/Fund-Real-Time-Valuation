<template>
  <div class="flow-summary">
    <div class="summary-header">
      <h3 class="summary-title">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          <path d="M9 12l2 2 4-4"/>
        </svg>
        资金流向概览
      </h3>
    </div>

    <div class="summary-stats">
      <div class="stat-card inflow">
        <div class="stat-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 19V5M5 12l7-7 7 7"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">主力净流入</span>
          <span class="stat-value">{{ formatFlow(totalInflow) }}</span>
        </div>
      </div>

      <div class="stat-card outflow">
        <div class="stat-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12l7 7 7-7"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">主力流出</span>
          <span class="stat-value">{{ formatFlow(totalOutflow) }}</span>
        </div>
      </div>

      <div class="stat-card net">
        <div class="stat-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">净流入</span>
          <span class="stat-value" :class="netFlowClass">{{ formatFlow(netFlow) }}</span>
        </div>
      </div>

      <div class="stat-card count">
        <div class="stat-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-label">板块数量</span>
          <span class="stat-value">{{ sectorCount }}</span>
        </div>
      </div>
    </div>

    <div class="summary-chart" v-if="hasFlowData">
      <div class="chart-legend">
        <span class="legend-item">
          <span class="legend-color inflow"></span>
          净流入
        </span>
        <span class="legend-item">
          <span class="legend-color outflow"></span>
          净流出
        </span>
      </div>
      <div class="flow-bar">
        <div
          class="flow-bar-fill inflow"
          :style="{ width: inflowPercentage + '%' }"
        />
        <div
          class="flow-bar-fill outflow"
          :style="{ width: outflowPercentage + '%' }"
        />
      </div>
      <div class="flow-bar-labels">
        <span>{{ inflowCount }} 个板块</span>
        <span>{{ outflowCount }} 个板块</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Sector } from '@/types';

interface Props {
  sectors: Sector[];
}

const props = defineProps<Props>();

// 计算资金流向数据
const flowData = computed(() => {
  if (!props.sectors || props.sectors.length === 0) {
    return {
      totalInflow: 0,
      totalOutflow: 0,
      netFlow: 0,
      inflowCount: 0,
      outflowCount: 0,
      hasFlowData: false,
    };
  }

  let totalInflow = 0;
  let totalOutflow = 0;
  let inflowCount = 0;
  let outflowCount = 0;

  for (const sector of props.sectors) {
    if (sector.mainInflow === undefined) continue;

    if (sector.mainInflow > 0) {
      totalInflow += sector.mainInflow;
      inflowCount++;
    } else if (sector.mainInflow < 0) {
      totalOutflow += sector.mainInflow;
      outflowCount++;
    }
  }

  return {
    totalInflow,
    totalOutflow,
    netFlow: totalInflow + totalOutflow,
    inflowCount,
    outflowCount,
    hasFlowData: inflowCount > 0 || outflowCount > 0,
  };
});

const totalInflow = computed(() => flowData.value.totalInflow);
const totalOutflow = computed(() => flowData.value.totalOutflow);
const netFlow = computed(() => flowData.value.netFlow);
const sectorCount = computed(() => props.sectors?.length || 0);
const hasFlowData = computed(() => flowData.value.hasFlowData);
const inflowCount = computed(() => flowData.value.inflowCount);
const outflowCount = computed(() => flowData.value.outflowCount);

const netFlowClass = computed(() => {
  if (netFlow.value > 0) return 'text-rise';
  if (netFlow.value < 0) return 'text-fall';
  return 'text-neutral';
});

const total = computed(() => Math.abs(totalInflow.value) + Math.abs(totalOutflow.value));
const inflowPercentage = computed(() => {
  if (total.value === 0) return 50;
  return (Math.abs(totalInflow.value) / total.value) * 100;
});
const outflowPercentage = computed(() => {
  if (total.value === 0) return 50;
  return (Math.abs(totalOutflow.value) / total.value) * 100;
});

function formatFlow(value: number): string {
  if (value === undefined || isNaN(value)) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}亿`;
}
</script>

<style scoped>
.flow-summary {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
}

.summary-header {
  margin-bottom: var(--spacing-md);
}

.summary-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.summary-title svg {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.stat-card.inflow {
  border-left: 3px solid var(--color-rise);
}

.stat-card.outflow {
  border-left: 3px solid var(--color-fall);
}

.stat-card.net {
  border-left: 3px solid var(--color-primary);
}

.stat-card.count {
  border-left: 3px solid var(--color-text-tertiary);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--color-bg-card);
}

.stat-icon svg {
  width: 20px;
  height: 20px;
}

.stat-card.inflow .stat-icon {
  color: var(--color-rise);
  background: var(--color-rise-bg);
}

.stat-card.outflow .stat-icon {
  color: var(--color-fall);
  background: var(--color-fall-bg);
}

.stat-card.net .stat-icon {
  color: var(--color-primary);
  background: var(--color-primary-bg);
}

.stat-card.count .stat-icon {
  color: var(--color-text-tertiary);
  background: var(--color-bg-tertiary);
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.stat-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  font-family: var(--font-mono);
  color: var(--color-text-primary);

  &.text-rise {
    color: var(--color-rise);
  }

  &.text-fall {
    color: var(--color-fall);
  }

  &.text-neutral {
    color: var(--color-text-tertiary);
  }
}

.summary-chart {
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-divider);
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;

  &.inflow {
    background: var(--color-rise);
  }

  &.outflow {
    background: var(--color-fall);
  }
}

.flow-bar {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--color-bg-secondary);
}

.flow-bar-fill {
  height: 100%;
  transition: width var(--transition-normal);

  &.inflow {
    background: linear-gradient(90deg, #f87171, var(--color-rise));
  }

  &.outflow {
    background: linear-gradient(90deg, var(--color-fall), #4ade80);
  }
}

.flow-bar-labels {
  display: flex;
  justify-content: space-between;
  margin-top: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}
</style>
