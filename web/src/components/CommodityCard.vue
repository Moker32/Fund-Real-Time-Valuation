<template>
  <div class="commodity-card" :class="{ loading: loading }">
    <template v-if="loading">
      <div class="skeleton-content">
        <div class="skeleton skeleton-title"></div>
        <div class="skeleton skeleton-price"></div>
        <div class="skeleton skeleton-change"></div>
      </div>
    </template>

    <template v-else>
      <div class="card-header">
        <div class="commodity-info">
          <span class="commodity-symbol">{{ commodity.symbol }}</span>
          <span class="commodity-name">{{ commodity.name }}</span>
        </div>
        <span class="commodity-source">{{ commodity.source || 'API' }}</span>
      </div>

      <div class="card-body">
        <div class="price-section">
          <span class="price font-mono" :class="{ 'value-updated': priceAnimating }">{{ formatPrice(commodity.price) }}</span>
          <span class="currency">{{ commodity.currency }}</span>
        </div>

        <div class="change-section" :class="[changeClass, { 'value-updated': changeAnimating }]">
          <span class="change-percent font-mono">{{ formatPercent(commodity.changePercent) }}</span>
          <span class="change-indicator-value">
            <svg v-if="commodity.changePercent > 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 19V5M5 12L12 5L19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <svg v-else-if="commodity.changePercent < 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M19 12L12 19L5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span v-else>—</span>
          </span>
          <span class="change-value font-mono">{{ formatChange(commodity.change) }}</span>
        </div>
      </div>

      <div class="card-footer">
        <div class="price-range">
          <span class="range-item">
            <span class="label">高</span>
            <span class="value font-mono">{{ formatPrice(commodity.high) }}</span>
          </span>
          <span class="range-item">
            <span class="label">低</span>
            <span class="value font-mono">{{ formatPrice(commodity.low) }}</span>
          </span>
        </div>
        <span class="timestamp">{{ formatTime(commodity.timestamp) }}</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { Commodity } from '@/types';

interface Props {
  commodity: Commodity;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

const changeClass = computed(() => {
  if (props.commodity.changePercent > 0) return 'rising';
  if (props.commodity.changePercent < 0) return 'falling';
  return 'neutral';
});

// 价格动画状态
const priceAnimating = ref(false);
const changeAnimating = ref(false);

// 监听价格变化触发动画
watch(() => props.commodity.price, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== undefined && newVal !== oldVal) {
    triggerPriceAnimation();
  }
});

watch(() => props.commodity.changePercent, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== undefined && newVal !== oldVal) {
    triggerChangeAnimation();
  }
});

function triggerPriceAnimation() {
  priceAnimating.value = true;
  setTimeout(() => priceAnimating.value = false, 500);
}

function triggerChangeAnimation() {
  changeAnimating.value = true;
  setTimeout(() => changeAnimating.value = false, 500);
}

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

function formatTime(dateStr: string): string {
  if (!dateStr) return '--';
  try {
    // 后端返回 UTC 时间字符串，如 "2026-02-13 21:59:50 UTC"
    const utcStr = dateStr.replace(' UTC', '').trim();
    // 解析 "2026-02-13 21:59:50" 为 UTC 时间
    const date = new Date(utcStr + 'Z');
    return date.toLocaleTimeString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '--';
  }
}
</script>

<style lang="scss" scoped>
.commodity-card {
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
    width: 50%;
    height: 18px;
  }

  &.skeleton-price {
    width: 70%;
    height: 24px;
  }

  &.skeleton-change {
    width: 30%;
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.commodity-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.commodity-symbol {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  font-weight: var(--font-weight-medium);
}

.commodity-name {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.commodity-source {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  color: var(--color-text-secondary);
}

.card-body {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: var(--spacing-md);
}

.price-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.price {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: 1;
  transition: all 0.3s ease;

  &.value-updated {
    animation: value-pulse 0.5s ease-out;
  }
}

.currency {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

@keyframes value-pulse {
  0% {
    transform: scale(1);
    color: var(--color-text-primary);
  }
  30% {
    color: var(--color-rise);
  }
  50% {
    transform: scale(1.05);
  }
  100% {
    transform: scale(1);
    color: var(--color-text-primary);
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
    transform: scale(1.05);
  }
  100% {
    transform: scale(1);
  }
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

.price-range {
  display: flex;
  gap: var(--spacing-md);
}

.range-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.value {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.timestamp {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}
</style>
