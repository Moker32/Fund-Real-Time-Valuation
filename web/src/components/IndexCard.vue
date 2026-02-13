<template>
  <div class="index-card" :class="{ loading: loading }">
    <template v-if="loading">
      <div class="skeleton-content">
        <div class="skeleton skeleton-title"></div>
        <div class="skeleton skeleton-price"></div>
        <div class="skeleton skeleton-change"></div>
      </div>
    </template>

    <template v-else>
      <div class="card-header">
        <div class="index-info">
          <span class="index-name">{{ indexData.name }}</span>
          <span class="index-region" :class="`region-${indexData.region}`">{{ regionLabel }}</span>
        </div>
        <div class="header-tags">
          <div v-if="isDelayed" class="delay-tag">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6V12L16 14"/>
            </svg>
            <span>延时</span>
          </div>
          <div class="trading-status" :class="`status-${indexData.tradingStatus}`">
            <span class="status-dot"></span>
            <span class="status-text">{{ statusText }}</span>
          </div>
        </div>
      </div>

      <div class="card-body">
        <div class="price-section">
          <span class="price font-mono" :class="{ 'value-updated': priceAnimating }">{{ formatPrice(indexData.price) }}</span>
          <span class="currency">{{ indexData.currency }}</span>
        </div>

        <div class="change-section" :class="[changeClass, { 'value-updated': changeAnimating }]">
          <span class="change-percent font-mono" :key="indexData.changePercent">{{ formatPercent(indexData.changePercent) }}</span>
          <span class="change-indicator-value">
            <svg v-if="indexData.changePercent > 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 19V5M5 12L12 5L19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <svg v-else-if="indexData.changePercent < 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M19 12L12 19L5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span v-else>—</span>
          </span>
          <span class="change-value font-mono">{{ formatChange(indexData.change) }}</span>
        </div>
      </div>

      <div class="card-footer">
        <div class="footer-row">
          <div class="footer-item">
            <span class="label">高</span>
            <span class="value font-mono">{{ formatPrice(indexData.high) }}</span>
          </div>
          <div class="footer-item">
            <span class="label">低</span>
            <span class="value font-mono">{{ formatPrice(indexData.low) }}</span>
          </div>
        </div>
        <div class="footer-row">
          <div class="footer-item">
            <span class="label">今开</span>
            <span class="value font-mono">{{ formatPrice(indexData.open) }}</span>
          </div>
          <div class="footer-item" v-if="indexData.prevClose">
            <span class="label">昨收</span>
            <span class="value font-mono">{{ formatPrice(indexData.prevClose) }}</span>
          </div>
          <div class="market-time" v-if="indexData.timestamp">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6V12L16 14"/>
            </svg>
            <span>{{ formatMarketTime(indexData.timestamp) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue';
import type { MarketIndex } from '@/types';

interface Props {
  index: MarketIndex;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

// Use a computed property to handle potential undefined values
const indexData = computed(() => props.index);

const prevPrice = ref<number | undefined>();
const prevChangePercent = ref<number | undefined>();

// Watch for price changes to trigger animation
watch(() => props.index.price, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== oldVal) {
    triggerPriceAnimation();
  }
  prevPrice.value = newVal;
});

watch(() => props.index.changePercent, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== oldVal) {
    triggerChangeAnimation();
  }
  prevChangePercent.value = newVal;
});

const priceAnimating = ref(false);
const changeAnimating = ref(false);

function triggerPriceAnimation() {
  priceAnimating.value = true;
  setTimeout(() => priceAnimating.value = false, 500);
}

function triggerChangeAnimation() {
  changeAnimating.value = true;
  setTimeout(() => changeAnimating.value = false, 500);
}

const changeClass = computed(() => {
  if (props.index.changePercent > 0) return 'rising';
  if (props.index.changePercent < 0) return 'falling';
  return 'neutral';
});

const regionLabel = computed(() => {
  const labels: Record<string, string> = {
    'china': 'A股',
    'hk': '港股',
    'asia': '亚太',
    'america': '美股',
    'europe': '欧洲',
  };
  return labels[props.index.region || ''] || props.index.region || '';
});

const statusText = computed(() => {
  const labels: Record<string, string> = {
    'open': '交易中',
    'closed': '已收盘',
    'pre': '未开盘',
    'unknown': '未知',
  };
  return labels[props.index.tradingStatus || 'unknown'] || '未知';
});

// 判断是否为延时数据源
const isDelayed = computed(() => props.index.source === 'yfinance_index');

function formatPrice(value: number | undefined): string {
  if (value == null) return '--';
  if (value >= 10000) {
    return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return value.toFixed(2);
}

function formatChange(value: number | undefined): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

function formatPercent(value: number | undefined): string {
  if (value == null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function formatMarketTime(dateStr: string | undefined): string {
  if (!dateStr) return '--';
  try {
    const date = new Date(dateStr);
    // 统一使用上海时区
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
.index-card {
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
    height: 20px;
  }

  &.skeleton-price {
    width: 80%;
    height: 28px;
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

.header-tags {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.index-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.index-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.index-region {
  font-size: var(--font-size-xs);
  padding: 2px 8px;
  border-radius: var(--radius-full);

  &.region-china {
    background: rgba(255, 76, 76, 0.15);
    color: #ff4c4c;
  }

  &.region-hk {
    background: rgba(255, 159, 10, 0.15);
    color: #ff9f0a;
  }

  &.region-asia {
    background: rgba(52, 199, 89, 0.15);
    color: #34c759;
  }

  &.region-america {
    background: rgba(0, 122, 255, 0.15);
    color: #007aff;
  }

  &.region-europe {
    background: rgba(88, 86, 214, 0.15);
    color: #5856d6;
  }
}

.trading-status {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  &.status-open {
    background: rgba(52, 199, 89, 0.15);
    color: #34c759;

    .status-dot {
      background: #34c759;
      animation: pulse-dot 2s infinite;
    }
  }

  &.status-closed {
    background: rgba(142, 142, 147, 0.15);
    color: #8e8e93;

    .status-dot {
      background: #8e8e93;
    }
  }

  &.status-pre {
    background: rgba(255, 159, 10, 0.15);
    color: #ff9f0a;

    .status-dot {
      background: #ff9f0a;
    }
  }

  &.status-unknown {
    background: rgba(142, 142, 147, 0.15);
    color: #8e8e93;

    .status-dot {
      background: #8e8e93;
    }
  }
}

.delay-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  background: rgba(255, 159, 10, 0.15);
  color: #ff9f0a;

  svg {
    width: 12px;
    height: 12px;
  }
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
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

.currency {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
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
  flex-direction: column;
  gap: var(--spacing-xs);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-divider);
}

.footer-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.footer-item {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 90px;
}

.label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.value {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.market-time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-left: auto;

  svg {
    width: 12px;
    height: 12px;
  }
}
</style>
