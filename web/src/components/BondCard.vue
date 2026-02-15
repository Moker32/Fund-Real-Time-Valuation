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
    <div class="bond-price">
      <span class="price">{{ formatPrice(price) }}</span>
    </div>
    <div class="bond-change">
      <span class="change">{{ formatChange(change) }}</span>
      <span class="change-pct">{{ formatChangePct(changePct) }}</span>
    </div>
    <div class="bond-volume">
      <span class="label">成交量:</span>
      <span class="value">{{ formatVolume(volume) }}</span>
    </div>
  </div>
</template>

<style scoped>
.bond-card {
  background: var(--card-bg, #fff);
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
}

.bond-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.bond-card.positive {
  border-left: 3px solid #52c41a;
}

.bond-card.negative {
  border-left: 3px solid #ff4d4f;
}

.bond-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.bond-code {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary, #333);
}

.bond-name {
  font-size: 12px;
  color: var(--text-secondary, #666);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}

.bond-price {
  margin-bottom: 4px;
}

.price {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #333);
}

.bond-change {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
}

.positive .change,
.positive .change-pct {
  color: #52c41a;
}

.negative .change,
.negative .change-pct {
  color: #ff4d4f;
}

.change {
  font-weight: 500;
}

.change-pct {
  font-weight: 600;
}

.bond-volume {
  display: flex;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary, #666);
}

.bond-volume .value {
  color: var(--text-primary, #333);
}
</style>
