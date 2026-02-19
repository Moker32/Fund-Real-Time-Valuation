<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  code: string;
  name?: string;
  price?: number;
  change?: number;
  changePct?: number;
  volume?: number;
  amount?: number;
}

const props = withDefaults(defineProps<Props>(), {
  name: '',
  price: undefined,
  change: undefined,
  changePct: undefined,
  volume: undefined,
  amount: undefined,
});

const changeClass = computed(() => {
  if (props.changePct === undefined || props.changePct === null) return '';
  return props.changePct >= 0 ? 'positive' : 'negative';
});

function formatPrice(value: number | undefined | null): string {
  if (value === undefined || value === null) return '--';
  return value.toFixed(2);
}

function formatChange(value: number | undefined | null): string {
  if (value === undefined || value === null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

function formatChangePct(value: number | undefined | null): string {
  if (value === undefined || value === null) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function formatVolume(value: number | undefined | null): string {
  if (value === undefined || value === null) return '--';
  if (value >= 10000) {
    return (value / 10000).toFixed(1) + '万';
  }
  return value.toLocaleString();
}
</script>

<template>
  <div class="bond-card" :class="changeClass">
    <div class="bond-header">
      <span class="bond-code">{{ code }}</span>
      <span class="bond-name" :title="name">{{ name }}</span>
    </div>
    <div class="bond-body">
      <div class="bond-price">
        <span class="price">{{ formatPrice(price) }}</span>
      </div>
      <div class="bond-change">
        <span class="change">{{ formatChange(change) }}</span>
        <span class="change-pct">{{ formatChangePct(changePct) }}</span>
      </div>
    </div>
    <div class="bond-footer">
      <span class="label">成交量:</span>
      <span class="value">{{ formatVolume(volume) }}</span>
    </div>
  </div>
</template>

<style scoped>
.bond-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  transition: all var(--transition-normal);
  cursor: pointer;
}

.bond-card:hover {
  background: var(--color-bg-card-hover);
  border-color: var(--color-border-light);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.bond-card.positive {
  border-left: 3px solid var(--color-rise);
}

.bond-card.negative {
  border-left: 3px solid var(--color-fall);
}

.bond-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.bond-code {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
}

.bond-name {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}

.bond-body {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: var(--spacing-md);
}

.bond-price {
  flex: 1;
}

.price {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
}

.bond-change {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-md);
}

.positive .bond-change {
  background: var(--color-rise-bg);
}

.negative .bond-change {
  background: var(--color-fall-bg);
}

.positive .change,
.positive .change-pct {
  color: var(--color-rise);
}

.negative .change,
.negative .change-pct {
  color: var(--color-fall);
}

.change {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  font-family: var(--font-mono);
}

.change-pct {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  font-family: var(--font-mono);
}

.bond-footer {
  display: flex;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-divider);
}

.bond-footer .value {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}
</style>
