<template>
  <div class="sector-chart">
    <div class="chart-header">
      <div class="chart-title">
        <span class="symbol">{{ symbol }}</span>
        <span class="name">{{ name }}</span>
      </div>
      <div class="chart-meta">
        <span class="current-price font-mono" :class="priceClass">
          {{ formatPrice(currentPrice) }}
        </span>
        <span class="price-change font-mono" :class="priceClass">
          {{ formatChange(change) }} ({{ formatPercent(changePercent) }})
        </span>
      </div>
      <button class="close-btn" @click="$emit('close')" title="关闭">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
    </div>
    <LineChart
      :data="chartHistory"
      :height="chartHeight"
      :trend="trend"
      :show-axes="true"
      :show-tooltip="true"
      :streaming="true"
      :baseline="baseline"
      :max-points="500"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import LineChart from './LineChart.vue';

interface ChartDataItem {
  time: string;
  price: number;
}

const props = defineProps<{
  symbol: string;
  name: string;
  currentPrice: number;
  change: number;
  changePercent: number;
  high: number;
  low: number;
  chartHistory: ChartDataItem[];
  chartHeight?: number;
}>();

defineEmits<{
  close: [];
}>();

const trend = computed((): 'rising' | 'falling' | 'neutral' => {
  if (props.changePercent > 0) return 'rising';
  if (props.changePercent < 0) return 'falling';
  return 'neutral';
});

const priceClass = computed(() => {
  if (props.changePercent > 0) return 'rising';
  if (props.changePercent < 0) return 'falling';
  return 'neutral';
});

const baseline = computed(() => {
  // 用昨收作为基准线
  return props.currentPrice - props.change;
});

function formatPrice(value: number): string {
  if (value == null) return '--';
  if (value >= 1000) {
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return value.toFixed(2);
}

function formatChange(value: number): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

function formatPercent(value: number): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}
</script>

<style lang="scss" scoped>
.sector-chart {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.chart-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.chart-title {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
  flex-shrink: 0;
}

.symbol {
  font-size: var(--font-size-sm);
  font-family: var(--font-mono);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.name {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.chart-meta {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
  flex: 1;
}

.current-price {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  &.rising { color: var(--color-rise); }
  &.falling { color: var(--color-fall); }
  &.neutral { color: var(--color-neutral); }
}

.price-change {
  font-size: var(--font-size-sm);
  &.rising { color: var(--color-rise); }
  &.falling { color: var(--color-fall); }
  &.neutral { color: var(--color-neutral); }
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-xs);
  color: var(--color-text-tertiary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  flex-shrink: 0;

  svg {
    width: 16px;
    height: 16px;
  }

  &:hover {
    background: var(--color-bg-hover);
    color: var(--color-text-primary);
  }
}
</style>
