<template>
  <div class="sector-card" :class="{ loading: loading }">
    <template v-if="loading">
      <div class="skeleton-content">
        <div class="skeleton skeleton-title"></div>
        <div class="skeleton skeleton-change"></div>
        <div class="skeleton skeleton-detail"></div>
      </div>
    </template>

    <template v-else>
      <div class="card-header">
        <div class="sector-info">
          <span class="sector-rank" v-if="sector.rank">{{ sector.rank }}</span>
          <span class="sector-name">{{ sector.name }}</span>
        </div>
        <div class="change-tag" :class="changeClass">
          {{ formatPercent(sector.changePercent) }}
        </div>
      </div>

      <div class="card-body">
        <div class="price-info">
          <span class="price font-mono">{{ formatPrice(sector.price) }}</span>
          <span class="change-value font-mono" :class="changeClass">
            {{ formatChange(sector.change) }}
          </span>
        </div>
      </div>

      <div class="card-footer">
        <div class="stock-counts">
          <span class="up-count">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 19V5M5 12L12 5L19 12" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ sector.upCount }}
          </span>
          <span class="down-count">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 5V19M19 12L12 19L5 12" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ sector.downCount }}
          </span>
        </div>
        <div class="lead-stock" v-if="sector.leadStock">
          <span class="label">领涨:</span>
          <span class="stock-name">{{ sector.leadStock }}</span>
          <span class="stock-change" :class="leadChangeClass">
            {{ formatPercent(sector.leadChange) }}
          </span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Sector } from '@/types';

interface Props {
  sector: Sector;
  loading?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
});

const changeClass = computed(() => {
  if (props.sector.changePercent > 0) return 'rising';
  if (props.sector.changePercent < 0) return 'falling';
  return 'neutral';
});

const leadChangeClass = computed(() => {
  if (props.sector.leadChange > 0) return 'rising';
  if (props.sector.leadChange < 0) return 'falling';
  return 'neutral';
});

function formatPrice(value: number | undefined): string {
  if (value == null || isNaN(value)) return '--';
  return value.toFixed(2);
}

function formatChange(value: number | undefined): string {
  if (value == null || isNaN(value)) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

function formatPercent(value: number | undefined): string {
  if (value == null || isNaN(value)) return '--';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}
</script>

<style lang="scss" scoped>
.sector-card {
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
  background: var(--color-skeleton);

  &.skeleton-title {
    width: 60%;
    height: 20px;
  }

  &.skeleton-change {
    width: 40%;
  }

  &.skeleton-detail {
    width: 80%;
  }
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.sector-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.sector-rank {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 6px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-tertiary);
}

.sector-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.change-tag {
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);

  &.rising {
    background: var(--color-rise-bg);
    color: var(--color-rise);
  }

  &.falling {
    background: var(--color-fall-bg);
    color: var(--color-fall);
  }

  &.neutral {
    background: var(--color-bg-secondary);
    color: var(--color-text-tertiary);
  }
}

.card-body {
  margin-bottom: var(--spacing-md);
}

.price-info {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
}

.price {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.change-value {
  font-size: var(--font-size-sm);

  &.rising {
    color: var(--color-rise);
  }

  &.falling {
    color: var(--color-fall);
  }

  &.neutral {
    color: var(--color-text-tertiary);
  }
}

.card-footer {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-divider);
}

.stock-counts {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);

  .up-count, .down-count {
    display: flex;
    align-items: center;
    gap: 4px;

    svg {
      width: 12px;
      height: 12px;
    }
  }

  .up-count {
    color: var(--color-rise);
  }

  .down-count {
    color: var(--color-fall);
  }
}

.lead-stock {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-xs);

  .label {
    color: var(--color-text-tertiary);
  }

  .stock-name {
    color: var(--color-text-primary);
    font-weight: var(--font-weight-medium);
  }

  .stock-change {
    font-weight: var(--font-weight-medium);

    &.rising {
      color: var(--color-rise);
    }

    &.falling {
      color: var(--color-fall);
    }

    &.neutral {
      color: var(--color-text-tertiary);
    }
  }
}
</style>
