<template>
  <div class="funds-view">
    <!-- Market Overview -->
    <MarketOverview :overview="overviewData" :loading="fundStore.loading" />

    <!-- Error State -->
    <div v-if="fundStore.error" class="error-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8V12M12 16H12.01"/>
      </svg>
      <span>{{ fundStore.error }}</span>
      <button @click="fundStore.fetchFunds">重试</button>
    </div>

    <!-- Loading State -->
    <div v-else-if="fundStore.loading && fundStore.funds.length === 0" class="loading-state">
      <div class="loading-grid">
        <FundCard v-for="i in 6" :key="i" :fund="emptyFund" :loading="true" />
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="fundStore.funds.length === 0" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M3 3V21H21"/>
        <path d="M7 14L11 10L15 12L21 6"/>
      </svg>
      <span>暂无基金数据</span>
      <p>请在设置中添加自选基金</p>
    </div>

    <!-- Fund List -->
    <div v-else class="fund-list">
      <div class="list-header">
        <h2 class="section-title">自选基金</h2>
        <span class="fund-count">{{ fundStore.funds.length }} 只</span>
      </div>

      <div class="funds-grid">
        <FundCard
          v-for="fund in fundStore.funds"
          :key="fund.code"
          :fund="fund"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useFundStore } from '@/stores/fundStore';
import FundCard from '@/components/FundCard.vue';
import MarketOverview from '@/components/MarketOverview.vue';
import type { Overview, Fund } from '@/types';

const fundStore = useFundStore();

// Empty fund for loading skeleton
const emptyFund: Fund = {
  code: '---',
  name: '加载中...',
  netValue: 0,
  netValueDate: new Date().toISOString(),
  estimateValue: 0,
  estimateChange: 0,
  estimateChangePercent: 0,
} as Fund;

const overviewData = computed<Overview | null>(() => {
  if (fundStore.funds.length === 0) return null;

  const totalValue = fundStore.funds.reduce((sum, f) => {
    // Use estimate value as proxy if available
    return sum + (f.estimateValue || f.netValue || 0);
  }, 0);

  const avgChange = fundStore.averageChange;

  return {
    totalValue,
    totalChange: totalValue * (avgChange / 100),
    totalChangePercent: avgChange,
    fundCount: fundStore.funds.length,
    lastUpdated: fundStore.lastUpdated || '',
  };
});

onMounted(() => {
  fundStore.fetchFunds();
});
</script>

<style lang="scss" scoped>
.funds-view {
  animation: fadeIn var(--transition-normal);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.list-header {
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

.fund-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.funds-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-md);
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
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-md);
  width: 100%;
}
</style>
