<template>
  <div class="market-overview">
    <div class="overview-card" :class="{ loading: loading }">
      <template v-if="loading">
        <div class="skeleton-grid">
          <div class="skeleton-item" v-for="i in 3" :key="i">
            <div class="skeleton skeleton-label"></div>
            <div class="skeleton skeleton-value"></div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="overview-item">
          <span class="item-label">持仓总值</span>
          <span class="item-value font-mono">¥{{ formatValue(overview?.totalValue) }}</span>
        </div>

        <div class="overview-divider"></div>

        <div class="overview-item">
          <span class="item-label">今日涨跌</span>
          <div class="item-change" :class="changeClass">
            <span class="change-indicator">
              <svg v-if="overview && overview.totalChangePercent > 0" viewBox="0 0 24 24" fill="none">
                <path d="M12 19V5M5 12L12 5L19 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              <svg v-else-if="overview && overview.totalChangePercent < 0" viewBox="0 0 24 24" fill="none">
                <path d="M12 5V19M19 12L12 19L5 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              <span v-else>—</span>
            </span>
            <span class="change-value font-mono">{{ formatChange(overview?.totalChange) }}</span>
            <span class="change-percent font-mono">{{ formatPercent(overview?.totalChangePercent) }}</span>
          </div>
        </div>

        <div class="overview-divider"></div>

        <div class="overview-item">
          <span class="item-label">基金数量</span>
          <span class="item-value font-mono">{{ overview?.fundCount || 0 }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Overview } from '@/types';

interface Props {
  overview: Overview | null;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

const changeClass = computed(() => {
  if (props.overview && props.overview.totalChangePercent > 0) return 'rising';
  if (props.overview && props.overview.totalChangePercent < 0) return 'falling';
  return 'neutral';
});

function formatValue(value: number | undefined): string {
  if (value == null) return '--';
  if (value >= 10000) {
    return (value / 10000).toFixed(2) + '万';
  }
  return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
</script>

<style lang="scss" scoped>
.market-overview {
  margin-bottom: var(--spacing-xl);
}

.overview-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);

  &.loading {
    cursor: default;
    pointer-events: none;
  }
}

.skeleton-grid {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
  width: 100%;
}

.skeleton-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.skeleton {
  height: 20px;
  border-radius: var(--radius-sm);

  &.skeleton-label {
    width: 50%;
    height: 14px;
  }

  &.skeleton-value {
    width: 80%;
    height: 28px;
  }
}

.overview-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.overview-divider {
  width: 1px;
  height: 40px;
  background: var(--color-divider);
}

.item-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.item-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  min-width: 80px;
  text-align: right;
}

.item-change {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-md);

  &.rising {
    background: var(--color-rise-bg);
    color: var(--color-rise);

    .change-indicator svg {
      color: var(--color-rise);
    }
  }

  &.falling {
    background: var(--color-fall-bg);
    color: var(--color-fall);

    .change-indicator svg {
      color: var(--color-fall);
    }
  }

  &.neutral {
    color: var(--color-neutral);
  }
}

.change-indicator {
  display: flex;
  align-items: center;
  justify-content: center;

  svg {
    width: 16px;
    height: 16px;
  }
}

.change-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  min-width: 50px;
  text-align: right;
}

.change-percent {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  min-width: 50px;
}
</style>
