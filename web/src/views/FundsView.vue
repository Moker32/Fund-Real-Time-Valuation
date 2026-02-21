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
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 8V12M12 16H12.01"/>
      </svg>
      <span>{{ fundStore.error }}</span>
      <button @click="fundStore.fetchFunds">重试</button>
    </div>

    <!-- Loading State -->
    <div v-if="showSkeleton" class="loading-state">
      <div class="loading-grid">
        <FundCard v-for="i in LOADING_SKELETON_COUNT" :key="i" :fund="emptyFund" :loading="true" />
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasFunds && !hasError" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
        <path d="M3 3V21H21"/>
        <path d="M7 14L11 10L15 12L21 6"/>
      </svg>
      <span>暂无基金数据</span>
      <p>点击下方按钮添加自选基金</p>
      <button class="btn-primary" @click="showAddDialog = true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M12 5V19M5 12H19"/>
        </svg>
        添加基金
      </button>
    </div>

    <!-- Fund List -->
    <div v-if="showFundList" class="fund-list">
      <div class="list-header">
        <div class="header-left">
          <h2 class="section-title">自选基金</h2>
          <span class="fund-count">{{ fundStore.holdingFirstFunds.length }} 只</span>
        </div>
        <button class="btn-add" @click="showAddDialog = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M12 5V19M5 12H19"/>
          </svg>
          添加基金
        </button>
      </div>

      <div class="funds-grid">
        <TransitionGroup name="fund-card">
          <FundCard
            v-for="fund in fundStore.holdingFirstFunds"
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

    <!-- Confirm Remove Dialog -->
    <ConfirmDialog
      :visible="showConfirmDialog"
      title="确认移除"
      :message="`确定要从自选移除基金 ${removingFundCode} 吗？`"
      confirm-text="移除"
      cancel-text="取消"
      @confirm="confirmRemove"
      @cancel="showConfirmDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useFundStore } from '@/stores/fundStore';
import FundCard from '@/components/FundCard.vue';
import MarketOverview from '@/components/MarketOverview.vue';
import AddFundDialog from '@/components/AddFundDialog.vue';
import ConfirmDialog from '@/components/ConfirmDialog.vue';
import type { Overview } from '@/types';

// 加载骨架屏数量常量
const LOADING_SKELETON_COUNT = 6;

// 空基金状态类型（用于骨架屏显示）
interface EmptyFundState {
  code: string;
  name: string;
  netValue: number;
  netValueDate: string;
  estimateValue: number;
  estimateChange: number;
  estimateChangePercent: number;
}

const fundStore = useFundStore();
const showAddDialog = ref(false);
const isMounted = ref(true);

// 确认对话框状态
const showConfirmDialog = ref(false);
const removingFundCode = ref('');

// 空基金数据用于加载骨架屏
const emptyFund: EmptyFundState = {
  code: '---',
  name: '加载中...',
  netValue: 0,
  netValueDate: new Date().toISOString(),
  estimateValue: 0,
  estimateChange: 0,
  estimateChangePercent: 0,
};

// 计算属性：是否显示加载状态
const isLoading = computed(() => fundStore.loading);
const hasFunds = computed(() => fundStore.holdingFirstFunds.length > 0);
const hasError = computed(() => !!fundStore.error);

// 模板条件简化：显示骨架屏
const showSkeleton = computed(() => isLoading.value && !hasFunds.value);
// 模板条件简化：显示基金列表
const showFundList = computed(() => hasFunds.value && !hasError.value);

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
  removingFundCode.value = code;
  showConfirmDialog.value = true;
}

async function confirmRemove() {
  if (removingFundCode.value) {
    await fundStore.removeFund(removingFundCode.value);
    removingFundCode.value = '';
  }
}

function handleFundAdded() {
  fundStore.fetchFunds();
}

onMounted(async () => {
  isMounted.value = true;
  // 只在数据为空时加载基金列表
  if (fundStore.funds.length === 0) {
    await fundStore.fetchFunds();
  }

  // 加载每个基金的分时数据
  for (const fund of fundStore.funds) {
    // 尝试获取当天的日内数据
    const intraday = await fundStore.fetchIntraday(fund.code, true);
    
    // 如果当天没有数据，使用基金卡片上显示的更新时间对应的日期
    if (!intraday || intraday.length === 0) {
      const updateTime = fund.estimateTime || fund.netValueDate || '';
      const match = updateTime.match(/^(\d{4})-(\d{2})-(\d{2})/);
      if (match) {
        const dateStr = `${match[1]}-${match[2]}-${match[3]}`;
        await fundStore.fetchIntradayByDate(fund.code, dateStr);
      }
    }
  }
});

onUnmounted(() => {
  isMounted.value = false;
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

// 公共按钮样式
.btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);

  svg {
    width: 16px;
    height: 16px;
  }
}

.btn-add {
  @extend .btn;
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  color: white;

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

/* 移除 move 动画避免自动刷新时页面抖动 */
/* .fund-card-move {
  transition: transform 0.3s ease;
} */

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
  @extend .btn;
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  color: white;

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
