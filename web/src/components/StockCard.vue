<template>
  <div class="stock-card" :class="{ loading: loading, rising: stock.change_pct > 0, falling: stock.change_pct < 0 }">
    <template v-if="loading">
      <div class="skeleton-content">
        <div class="skeleton skeleton-title"></div>
        <div class="skeleton skeleton-price"></div>
        <div class="skeleton skeleton-change"></div>
      </div>
    </template>

    <template v-else>
      <div class="card-header">
        <div class="stock-info">
          <span class="stock-name">{{ stock.name }}</span>
          <span class="stock-code">{{ stock.code }}</span>
        </div>
        <button class="action-btn delete-btn" title="从自选移除" @click.stop="$emit('remove', stock.code)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
          </svg>
        </button>
      </div>

      <div class="card-body">
        <div class="price-section">
          <span class="price font-mono" :class="{ 'value-updated': priceAnimating }">{{ formatPrice(stock.price) }}</span>
          <span class="currency">¥</span>
        </div>

        <div class="change-section" :class="[changeClass, { 'value-updated': changeAnimating }]">
          <span class="change-percent font-mono">{{ formatPercent(stock.change_pct) }}</span>
          <span class="change-indicator-value">
            <svg v-if="stock.change_pct > 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 19V5M5 12L12 5L19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <svg v-else-if="stock.change_pct < 0" viewBox="0 0 24 24" fill="none">
              <path d="M12 5V19M19 12L12 19L5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span v-else>—</span>
          </span>
          <span class="change-value font-mono">{{ formatChange(stock.change) }}</span>
        </div>
      </div>

      <div class="card-footer">
        <div class="footer-row">
          <div class="footer-item">
            <span class="label">高</span>
            <span class="value font-mono">{{ formatPrice(stock.high) }}</span>
          </div>
          <div class="footer-item">
            <span class="label">低</span>
            <span class="value font-mono">{{ formatPrice(stock.low) }}</span>
          </div>
        </div>
        <div class="footer-row">
          <div class="footer-item">
            <span class="label">今开</span>
            <span class="value font-mono">{{ formatPrice(stock.open) }}</span>
          </div>
          <div class="footer-item">
            <span class="label">昨收</span>
            <span class="value font-mono">{{ formatPrice(stock.pre_close) }}</span>
          </div>
        </div>
        <div class="footer-row">
          <div class="footer-item volume">
            <span class="label">成交量</span>
            <span class="value font-mono">{{ formatVolume(stock.volume) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import type { Stock } from '@/types';

interface Props {
  stock: Stock;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

defineEmits<{
  remove: [code: string];
}>();

// 动画状态
const priceAnimating = ref(false);
const changeAnimating = ref(false);

// 监听价格变化触发动画
watch(() => props.stock.price, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== oldVal) {
    priceAnimating.value = true;
    setTimeout(() => priceAnimating.value = false, 500);
  }
});

watch(() => props.stock.change_pct, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== oldVal) {
    changeAnimating.value = true;
    setTimeout(() => changeAnimating.value = false, 500);
  }
});

// 涨跌分类
const changeClass = computed(() => {
  if (props.stock.change_pct > 0) return 'rising';
  if (props.stock.change_pct < 0) return 'falling';
  return 'neutral';
});

// 格式化价格
function formatPrice(price: number | undefined | null): string {
  if (price === undefined || price === null || isNaN(price)) return '--';
  return price.toFixed(2);
}

// 格式化涨跌幅
function formatPercent(value: number | undefined | null): string {
  if (value === undefined || value === null || isNaN(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

// 格式化涨跌额
function formatChange(value: number | undefined | null): string {
  if (value === undefined || value === null || isNaN(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

// 格式化成交量
function formatVolume(vol: string | number | undefined | null): string {
  if (vol === undefined || vol === null) return '--';
  if (typeof vol === 'number') {
    if (vol >= 100000000) {
      return (vol / 100000000).toFixed(2) + '亿';
    } else if (vol >= 10000) {
      return (vol / 10000).toFixed(2) + '万';
    }
    return vol.toString();
  }
  return vol;
}
</script>

<style scoped>
.stock-card {
  background: var(--color-bg-secondary, #fff);
  border-radius: var(--radius-lg, 12px);
  padding: var(--spacing-sm, 12px);
  border: 1px solid var(--color-border, #e5e7eb);
  transition: all var(--transition-normal, 0.2s);
}

.stock-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-sm, 12px);
}

.stock-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stock-name {
  font-weight: var(--font-weight-semibold, 600);
  font-size: var(--font-size-sm, 14px);
  color: var(--color-text-primary, #1f2937);
}

.stock-code {
  font-size: 11px;
  color: var(--color-text-tertiary, #9ca3af);
}

.action-btn {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  color: var(--color-text-tertiary, #9ca3af);
  border-radius: var(--radius-sm, 4px);
  transition: all var(--transition-fast, 0.15s);
}

.action-btn:hover {
  background: var(--color-bg-tertiary, #f3f4f6);
  color: var(--color-text-primary, #1f2937);
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

.card-body {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-sm, 12px);
  margin-bottom: var(--spacing-xs, 8px);
}

.price-section {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.price {
  font-size: var(--font-size-lg, 18px);
  font-weight: var(--font-weight-bold, 700);
  color: var(--color-text-primary, #1f2937);
  line-height: 1;
  transition: all var(--transition-fast, 0.15s);
}

.price.value-updated {
  animation: value-pulse 0.5s ease-out;
}

.currency {
  font-size: var(--font-size-sm, 14px);
  color: var(--color-text-tertiary, #9ca3af);
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
  padding: var(--spacing-xs, 8px) var(--spacing-sm, 12px);
  border-radius: var(--radius-md, 8px);
  transition: all var(--transition-fast, 0.15s);
}

.change-section.rising {
  background: var(--color-rise-bg, #fef2f2);
  color: var(--color-rise, #ef4444);
}

.change-section.falling {
  background: var(--color-fall-bg, #f0fdf4);
  color: var(--color-fall, #22c55e);
}

.change-section.neutral {
  color: var(--color-text-tertiary, #9ca3af);
}

.change-section.value-updated {
  animation: change-pulse 0.5s ease-out;
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
  font-size: var(--font-size-base, 16px);
  font-weight: var(--font-weight-bold, 700);
}

.change-indicator-value {
  display: flex;
  align-items: center;
}

.change-indicator-value svg {
  width: 14px;
  height: 14px;
}

.change-value {
  font-size: var(--font-size-sm, 14px);
  font-weight: var(--font-weight-medium, 500);
}

.card-footer {
  padding-top: var(--spacing-sm, 12px);
  border-top: 1px solid var(--color-border, #e5e7eb);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs, 8px);
}

.footer-row {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-sm, 8px);
}

.footer-item {
  display: flex;
  justify-content: space-between;
  flex: 1;
  font-size: 12px;
}

.footer-item.volume {
  justify-content: flex-start;
}

.footer-item .label {
  color: var(--color-text-tertiary, #9ca3af);
}

.footer-item .value {
  font-weight: var(--font-weight-medium, 500);
  color: var(--color-text-primary, #1f2937);
}

.font-mono {
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}

/* Skeleton loading */
.skeleton-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton {
  background: linear-gradient(90deg, var(--color-bg-tertiary, #f3f4f6) 25%, var(--color-bg-secondary, #e5e7eb) 50%, var(--color-bg-tertiary, #f3f4f6) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm, 4px);
}

.skeleton-title {
  width: 60%;
  height: 20px;
}

.skeleton-price {
  width: 40%;
  height: 28px;
}

.skeleton-change {
  width: 50%;
  height: 18px;
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
</style>
