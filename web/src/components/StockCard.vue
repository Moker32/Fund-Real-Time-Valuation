<template>
  <div class="stock-card" :class="{ rising: stock.change_pct > 0, falling: stock.change_pct < 0 }">
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
      <div class="value-section">
        <div class="value-row">
          <span class="label">现价</span>
          <span class="value font-mono">{{ stock.price.toFixed(2) }}</span>
        </div>
        <div class="value-row">
          <span class="label">开盘</span>
          <span class="value font-mono">{{ stock.open.toFixed(2) }}</span>
        </div>
        <div class="value-row">
          <span class="label">最高</span>
          <span class="value font-mono">{{ stock.high.toFixed(2) }}</span>
        </div>
        <div class="value-row">
          <span class="label">最低</span>
          <span class="value font-mono">{{ stock.low.toFixed(2) }}</span>
        </div>
      </div>

      <div class="change-section" :class="{ positive: stock.change > 0, negative: stock.change < 0 }">
        <span class="change-percent font-mono">
          {{ stock.change > 0 ? '+' : '' }}{{ stock.change_pct.toFixed(2) }}%
        </span>
        <span class="change-indicator">
          <svg v-if="stock.change > 0" viewBox="0 0 24 24" fill="none">
            <path d="M12 19V5M5 12L12 5L19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <svg v-else-if="stock.change < 0" viewBox="0 0 24 24" fill="none">
            <path d="M12 5V19M19 12L12 19L5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <span v-else>—</span>
        </span>
        <span class="change-value font-mono">
          {{ stock.change > 0 ? '+' : '' }}{{ stock.change.toFixed(2) }}
        </span>
      </div>
    </div>

    <div class="card-footer">
      <span class="update-time">成交量: {{ formatVolume(stock.volume) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Stock } from '@/types';

interface Props {
  stock: Stock;
}

defineProps<Props>();

defineEmits<{
  remove: [code: string];
}>();

function formatVolume(vol: string | number): string {
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
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--color-border, #e5e7eb);
  transition: all 0.2s ease;
}

.stock-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.stock-card.rising {
  border-left: 3px solid #ef4444;
}

.stock-card.falling {
  border-left: 3px solid #22c55e;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.stock-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stock-name {
  font-weight: 600;
  font-size: 16px;
  color: var(--color-text, #1f2937);
}

.stock-code {
  font-size: 12px;
  color: var(--color-text-tertiary, #9ca3af);
}

.action-btn {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  color: var(--color-text-tertiary, #9ca3af);
  border-radius: 4px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--color-bg-tertiary, #f3f4f6);
  color: var(--color-text, #1f2937);
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

.card-body {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.value-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.value-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.value-row .label {
  color: var(--color-text-tertiary, #9ca3af);
}

.value-row .value {
  font-weight: 500;
  color: var(--color-text, #1f2937);
}

.change-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 80px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--color-bg-tertiary, #f9fafb);
}

.change-section.positive {
  background: #fef2f2;
  color: #ef4444;
}

.change-section.negative {
  background: #f0fdf4;
  color: #22c55e;
}

.change-percent {
  font-size: 18px;
  font-weight: 700;
}

.change-indicator {
  display: flex;
  align-items: center;
}

.change-indicator svg {
  width: 16px;
  height: 16px;
}

.change-value {
  font-size: 12px;
  font-weight: 500;
}

.card-footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border, #e5e7eb);
  font-size: 12px;
  color: var(--color-text-tertiary, #9ca3af);
}

.font-mono {
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}
</style>
