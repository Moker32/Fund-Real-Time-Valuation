<template>
  <div class="fund-card" :class="{ loading: loading }">
    <template v-if="loading">
      <div class="skeleton-content">
        <div class="skeleton skeleton-title"></div>
        <div class="skeleton skeleton-value"></div>
        <div class="skeleton skeleton-change"></div>
      </div>
    </template>

    <template v-else>
      <div class="card-header">
        <div class="fund-info">
          <span class="fund-code">{{ fund.code }}</span>
          <span class="fund-name" :title="fund.name">{{ fund.name }}</span>
        </div>
        <div class="card-actions">
          <button
            class="action-btn holding-btn"
            :class="{ active: fund.isHolding }"
            :title="fund.isHolding ? '取消持有' : '标记持有'"
            @click.stop="toggleHolding"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path v-if="fund.isHolding" d="M5 12l5 5L19 7" stroke-linecap="round" stroke-linejoin="round"/>
              <path v-else d="M12 5v14M5 12h14" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <span class="fund-type">{{ fund.type || '其他' }}</span>
          <button class="action-btn delete-btn" title="从自选移除" @click.stop="$emit('remove', fund.code)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="card-body">
        <div class="value-section">
          <div class="value-row">
            <span class="label">净值</span>
            <span class="value font-mono">{{ formatNumber(fund.netValue, 4) }}</span>
            <span class="value-date">{{ formatNetValueDate(fund.netValueDate) }}</span>
          </div>
          <!-- 非 QDII 基金显示估值 -->
          <div v-if="fund.hasRealTimeEstimate !== false" class="value-row">
            <span class="label">估值</span>
            <span class="value font-mono" :class="{ 'value-updated': valueAnimating }">{{ formatNumber(fund.estimateValue, 4) }}</span>
            <span class="value-date">{{ formatNetValueDate(fund.estimateTime) }}</span>
          </div>
          <!-- QDII 基金显示前日净值 -->
          <div v-else-if="fund.prevNetValue" class="value-row qdii-prev-row">
            <span class="label">前日</span>
            <span class="value font-mono">{{ formatNumber(fund.prevNetValue, 4) }}</span>
            <span class="value-date">{{ formatNetValueDate(fund.prevNetValueDate) }}</span>
          </div>
        </div>

        <div class="change-section" :class="[changeClass, { 'value-updated': changeAnimating }]">
          <span class="change-percent font-mono">{{ formatPercent(fund.estimateChangePercent) }}</span>
          <span class="change-indicator-value">
            <svg v-if="fund.estimateChangePercent > 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 19V5M5 12L12 5L19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <svg v-else-if="fund.estimateChangePercent < 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M19 12L12 19L5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span v-else>—</span>
          </span>
          <span class="change-value font-mono">{{ formatChange(fund.estimateChange) }}</span>
        </div>
      </div>

      <div class="card-footer">
        <span class="update-time">
          {{ fund.hasRealTimeEstimate === false ? '净值日期' : '更新' }}: {{ formatTime(fund.hasRealTimeEstimate === false ? fund.netValueDate : fund.estimateTime) }}
        </span>
        <span class="source" v-if="fund.source">{{ fund.source }}</span>
      </div>

      <!-- 分时图区域（当有日内数据时显示） -->
      <div v-if="shouldShowChart" class="fund-card-chart">
        <FundChart :data="fund.intraday" :height="80" chart-type="line" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useFundStore } from '@/stores/fundStore';
import type { Fund } from '@/types';
import FundChart from './FundChart.vue';

interface Props {
  fund: Fund;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

const fundStore = useFundStore();

defineEmits<{
  (e: 'remove', code: string): void;
}>();

// 是否显示图表
const shouldShowChart = computed(() => {
  return fundStore.showChart && props.fund.intraday && props.fund.intraday.length > 0;
});

// 涨跌样式
const changeClass = computed(() => {
  if (props.fund.estimateChangePercent > 0) return 'rising';
  if (props.fund.estimateChangePercent < 0) return 'falling';
  return 'neutral';
});

// 价格动画状态
const valueAnimating = ref(false);
const changeAnimating = ref(false);

// 监听价格变化触发动画
watch(() => props.fund.estimateValue, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== undefined && newVal !== oldVal) {
    triggerValueAnimation();
  }
});

watch(() => props.fund.estimateChangePercent, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== undefined && newVal !== oldVal) {
    triggerChangeAnimation();
  }
});

function triggerValueAnimation() {
  valueAnimating.value = true;
  setTimeout(() => valueAnimating.value = false, 500);
}

function triggerChangeAnimation() {
  changeAnimating.value = true;
  setTimeout(() => changeAnimating.value = false, 500);
}

async function toggleHolding() {
  await fundStore.toggleHolding(props.fund.code, !props.fund.isHolding);
}

function formatNumber(value: number, decimals: number = 2): string {
  if (value == null) return '--';
  return value.toFixed(decimals);
}

function formatChange(value: number): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(4)}`;
}

function formatPercent(value: number): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function formatTime(dateStr: string): string {
  if (!dateStr) return '--';
  try {
    const date = new Date(dateStr);
    // 如果没有时间部分（00:00），只显示日期
    const hours = parseInt(date.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false, hour: '2-digit' }), 10);
    const minutes = parseInt(date.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', minute: '2-digit' }), 10);
    if (hours === 0 && minutes === 0) {
      return date.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' });
    }
    return date.toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return dateStr;
  }
}

function formatNetValueDate(dateStr: string): string {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    return `${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')}`;
  } catch {
    return '';
  }
}
</script>

<style lang="scss" scoped>
.fund-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  transition: all var(--transition-normal);
  cursor: pointer;

  &:hover {
    background: var(--color-bg-card-hover);
    border-color: var(--color-border-light);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  &.loading {
    cursor: default;
    pointer-events: none;
  }
}

.skeleton-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.skeleton {
  height: 16px;
  border-radius: var(--radius-sm);

  &.skeleton-title {
    width: 60%;
    height: 18px;
  }

  &.skeleton-value {
    width: 80%;
  }

  &.skeleton-change {
    width: 40%;
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.card-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.fund-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.fund-code {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
}

.fund-name {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fund-type {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.action-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition: all var(--transition-fast);
  opacity: 0;

  svg {
    width: 16px;
    height: 16px;
  }

  &:hover {
    background: var(--color-bg-tertiary);
    color: var(--color-fall);
  }
}

.delete-btn:hover {
  background: var(--color-fall-alpha);
  color: var(--color-fall);
}

.holding-btn {
  svg {
    stroke-width: 2.5;
  }

  &:hover {
    background: var(--color-rise-alpha);
    color: var(--color-rise);
  }

  &.active {
    opacity: 1;
    color: var(--color-rise);

    &:hover {
      background: var(--color-rise-alpha);
    }
  }
}

.fund-card:hover .action-btn {
  opacity: 1;
}

.card-body {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: var(--spacing-md);
}

.value-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.value-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);

  &.qdii-prev-row {
    opacity: 0.7;
  }
}

.value-date {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
}

.label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  transition: all 0.3s ease;

  &.value-updated {
    animation: value-pulse 0.5s ease-out;
  }
}

@keyframes value-pulse {
  0% {
    transform: scale(1);
    color: var(--color-text-primary);
    background: transparent;
  }
  25% {
    background: var(--color-rise-bg);
  }
  50% {
    transform: scale(1.1);
    color: var(--color-rise);
  }
  75% {
    background: var(--color-rise-bg);
  }
  100% {
    transform: scale(1);
    color: var(--color-text-primary);
    background: transparent;
  }
}

.change-section {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);

  &.rising {
    background: var(--color-rise-bg);
    color: var(--color-rise);

    .change-indicator-value svg {
      color: var(--color-rise);
    }
  }

  &.falling {
    background: var(--color-fall-bg);
    color: var(--color-fall);

    .change-indicator-value svg {
      color: var(--color-fall);
    }
  }

  &.neutral {
    color: var(--color-neutral);
  }

  &.value-updated {
    animation: change-pulse 0.5s ease-out;
  }
}

@keyframes change-pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.15);
  }
  100% {
    transform: scale(1);
  }
}

.change-value {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.change-percent {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  line-height: 1;
}

.change-indicator-value {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 2px 0;

  svg {
    width: 14px;
    height: 14px;
  }
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-divider);
}

.update-time,
.source {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.fund-card-chart {
  margin-top: var(--spacing-sm);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-divider);
}
</style>
