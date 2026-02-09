<template>
  <div class="commodities-view">
    <!-- Header -->
    <div class="view-header">
      <h2 class="section-title">大宗商品行情</h2>
      <span class="last-updated" v-if="commodityStore.lastUpdated">
        更新时间: {{ commodityStore.lastUpdated }}
      </span>
    </div>

    <!-- Error State -->
    <div v-if="commodityStore.error" class="error-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8V12M12 16H12.01"/>
      </svg>
      <span>{{ commodityStore.error }}</span>
      <button @click="commodityStore.fetchCommodities">重试</button>
    </div>

    <!-- Loading State -->
    <div v-else-if="commodityStore.loading && commodityStore.commodities.length === 0" class="loading-state">
      <div class="loading-grid">
        <CommodityCard v-for="i in 6" :key="i" :commodity="emptyCommodity" :loading="true" />
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="commodityStore.commodities.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6V12L16 14"/>
      </svg>
      <span>暂无商品数据</span>
      <p>商品行情将显示在这里</p>
    </div>

    <!-- Commodity Grid -->
    <div v-else class="commodities-grid">
      <CommodityCard
        v-for="commodity in commodityStore.commodities"
        :key="commodity.symbol"
        :commodity="commodity"
      />
    </div>

    <!-- Quick Stats -->
    <div v-if="commodityStore.commodities.length > 0" class="quick-stats">
      <div class="stats-card">
        <span class="stats-label">上涨</span>
        <span class="stats-value rising">{{ commodityStore.risingCommodities.length }}</span>
      </div>
      <div class="stats-card">
        <span class="stats-label">下跌</span>
        <span class="stats-value falling">{{ commodityStore.fallingCommodities.length }}</span>
      </div>
      <div class="stats-card">
        <span class="stats-label">持平</span>
        <span class="stats-value neutral">{{ commodityStore.commodities.length - commodityStore.risingCommodities.length - commodityStore.fallingCommodities.length }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useCommodityStore } from '@/stores/commodityStore';
import CommodityCard from '@/components/CommodityCard.vue';
import type { Commodity } from '@/types';

const commodityStore = useCommodityStore();

// Empty commodity for loading skeleton
const emptyCommodity: Commodity = {
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
} as Commodity;

onMounted(() => {
  commodityStore.fetchCommodities();
});
</script>

<style lang="scss" scoped>
.commodities-view {
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

.commodities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
}

.quick-stats {
  display: flex;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-divider);
}

.stats-card {
  flex: 1;
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

  &.neutral {
    color: var(--color-neutral);
  }
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
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
  width: 100%;
}
</style>
