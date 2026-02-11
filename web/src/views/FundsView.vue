<template>
  <div class="funds-view">
    <!-- Market Overview -->
    <MarketOverview :overview="overviewData" :loading="fundStore.loading" />

    <!-- Loading Progress Bar -->
    <div v-if="fundStore.loading && fundStore.loadingProgress > 0 && fundStore.loadingProgress < 100" class="loading-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: fundStore.loadingProgress + '%' }"></div>
      </div>
      <span class="progress-text">正在加载基金数据... {{ fundStore.loadingProgress }}%</span>
    </div>

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
      <p>点击下方按钮添加自选基金</p>
      <button class="btn-primary" @click="showAddDialog = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5V19M5 12H19"/>
        </svg>
        添加基金
      </button>
    </div>

    <!-- Fund List -->
    <div v-else class="fund-list">
      <div class="list-header">
        <div class="header-left">
          <h2 class="section-title">自选基金</h2>
          <span class="fund-count">{{ fundStore.funds.length }} 只</span>
        </div>
        <button class="btn-add" @click="showAddDialog = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5V19M5 12H19"/>
          </svg>
          添加基金
        </button>
      </div>

      <div class="funds-grid">
        <TransitionGroup name="fund-card">
          <FundCard
            v-for="fund in fundStore.funds"
            :key="fund.code"
            :fund="fund"
            @remove="handleRemoveFund"
          />
        </TransitionGroup>
      </div>
    </div>

    <!-- Add Fund Dialog -->
    <AddFundDialog
      :visible="showAddDialog"
      @close="showAddDialog = false"
      @added="handleFundAdded"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useFundStore } from '@/stores/fundStore';
import FundCard from '@/components/FundCard.vue';
import MarketOverview from '@/components/MarketOverview.vue';
import AddFundDialog from '@/components/AddFundDialog.vue';
import type { Overview, Fund } from '@/types';

const fundStore = useFundStore();
const showAddDialog = ref(false);

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

async function handleRemoveFund(code: string) {
  if (confirm(`确定要从自选移除基金 ${code} 吗？`)) {
    await fundStore.removeFund(code);
  }
}

function handleFundAdded() {
  fundStore.fetchFunds();
}

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

.loading-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.progress-bar {
  width: 100%;
  max-width: 400px;
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.section-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.fund-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.btn-add {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  color: white;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);

  svg {
    width: 16px;
    height: 16px;
  }

  &:hover {
    opacity: 0.9;
    transform: translateY(-1px);
  }
}

.funds-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-md);
}

// 基金卡片过渡动画
.fund-card-enter-active,
.fund-card-leave-active {
  transition: all 0.3s ease;
}

.fund-card-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.fund-card-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

.fund-card-move {
  transition: transform 0.3s ease;
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

.btn-primary {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg);
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  color: white;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);

  svg {
    width: 16px;
    height: 16px;
  }

  &:hover {
    opacity: 0.9;
  }
}

.loading-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-md);
  width: 100%;
}
</style>
