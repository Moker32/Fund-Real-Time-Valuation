<template>
  <div class="indices-view">
    <!-- Header -->
    <div class="view-header">
      <h2 class="section-title">全球市场指数</h2>
      <span class="last-updated" v-if="indexStore.lastUpdated">
        更新时间: {{ indexStore.lastUpdated }}
      </span>
    </div>

    <!-- Error State -->
    <div v-if="indexStore.error" class="error-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8V12M12 16H12.01"/>
      </svg>
      <span>{{ indexStore.error }}</span>
      <button @click="indexStore.retry">重试</button>
    </div>

    <!-- Loading State -->
    <div v-else-if="indexStore.loading && indexStore.indices.length === 0" class="loading-state">
      <div class="loading-grid">
        <IndexCard v-for="i in 12" :key="i" :index="emptyIndex" :loading="true" />
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="indexStore.indices.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6V12L16 14"/>
      </svg>
      <span>暂无指数数据</span>
      <p>全球市场指数将显示在这里</p>
    </div>

    <!-- Indices Grid -->
    <div v-else class="indices-grid">
      <IndexCard
        v-for="index in indexStore.sortedIndices"
        :key="index.index"
        :index="index"
      />
    </div>

    <!-- Quick Stats -->
    <div v-if="indexStore.indices.length > 0" class="quick-stats">
      <div class="stats-card">
        <span class="stats-label">上涨</span>
        <span class="stats-value rising">{{ indexStore.risingIndices.length }}</span>
      </div>
      <div class="stats-card">
        <span class="stats-label">下跌</span>
        <span class="stats-value falling">{{ indexStore.fallingIndices.length }}</span>
      </div>
      <div class="stats-card">
        <span class="stats-label">交易中</span>
        <span class="stats-value">{{ indexStore.openMarketIndices.length }}</span>
      </div>
      <div class="stats-card">
        <span class="stats-label">已收盘</span>
        <span class="stats-value">{{ indexStore.closedMarketIndices.length }}</span>
      </div>
    </div>

    <!-- Market Status -->
    <div v-if="indexStore.indices.length > 0" class="market-status">
      <div class="status-item" v-if="indexStore.openMarketIndices.length > 0">
        <span class="status-label">当前交易中:</span>
        <div class="status-indices">
          <span
            v-for="idx in indexStore.openMarketIndices.slice(0, 5)"
            :key="idx.index"
            class="status-index"
          >
            {{ idx.name }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useIndexStore } from '@/stores/indexStore';
import IndexCard from '@/components/IndexCard.vue';
import type { MarketIndex } from '@/types';

const indexStore = useIndexStore();

// Empty index for loading skeleton
const emptyIndex: MarketIndex = {
  index: '---',
  symbol: '---',
  name: '加载中...',
  price: 0,
  currency: 'USD',
  change: 0,
  changePercent: 0,
  high: 0,
  low: 0,
  open: 0,
  prevClose: 0,
  timestamp: new Date().toISOString(),
  source: '',
  region: 'unknown',
  tradingStatus: 'unknown',
  marketTime: '',
} as MarketIndex;

onMounted(() => {
  indexStore.fetchIndices();
});
</script>

<style lang="scss" scoped>
.indices-view {
  animation: fadeIn var(--transition-normal);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.view-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.section-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.last-updated {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.indices-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--spacing-md);
}

.quick-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-divider);
}

.stats-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stats-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.stats-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  font-family: var(--font-mono);

  &.rising {
    color: var(--color-rise);
  }

  &.falling {
    color: var(--color-fall);
  }
}

.market-status {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.status-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.status-indices {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.status-index {
  font-size: var(--font-size-sm);
  padding: 4px 12px;
  background: rgba(52, 199, 89, 0.15);
  color: #34c759;
  border-radius: var(--radius-full);
}

.error-state,
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
  gap: var(--spacing-md);
  color: var(--color-text-secondary);

  svg {
    width: 48px;
    height: 48px;
    opacity: 0.5;
  }

  span {
    font-size: var(--font-size-lg);
  }

  p {
    font-size: var(--font-size-sm);
    opacity: 0.7;
  }

  button {
    margin-top: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-lg);
    background: var(--color-bg-tertiary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-primary);
    font-size: var(--font-size-sm);
    transition: all var(--transition-fast);

    &:hover {
      background: var(--color-bg-card);
      border-color: var(--color-border-light);
    }
  }
}

.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--spacing-md);
  width: 100%;
}
</style>
