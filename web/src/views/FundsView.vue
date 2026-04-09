<template>
  <div class="funds-view">

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
        <button class="btn-add" :class="{ 'pulse-hint': shouldShowPulseHint }" @click="showAddDialog = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M12 5V19M5 12H19"/>
          </svg>
          添加基金
        </button>
      </div>

      <div class="funds-grid">
        <TransitionGroup name="fund-card" tag="div" class="fund-list-container">
          <FundCard
            v-for="fund in fundStore.holdingFirstFunds"
            :key="fund.code"
            :fund="fund"
            @remove="handleRemoveFund"
            @show-history="handleShowHistory"
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

    <!-- Fund History Dialog -->
    <FundHistoryDialog
      :visible="showHistoryDialog"
      :fund-code="selectedFundCode || ''"
      :fund-name="selectedFundName"
      :fund="selectedFund"
      @close="showHistoryDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useFundStore } from '@/stores/fundStore';
import FundCard from '@/components/FundCard.vue';
import AddFundDialog from '@/components/AddFundDialog.vue';
import FundHistoryDialog from '@/components/FundHistoryDialog.vue';
import { confirm } from '@/utils/confirm';

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

// Fund History Dialog state
const showHistoryDialog = ref(false);
const selectedFundCode = ref<string | null>(null);
const selectedFundName = ref('');
const selectedFund = computed(() => {
  if (!selectedFundCode.value) return undefined;
  return fundStore.funds.find(f => f.code === selectedFundCode.value);
});

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

// 是否显示脉冲提示（当基金数量较少时）
const shouldShowPulseHint = computed(() => {
  return fundStore.holdingFirstFunds.length > 0 && fundStore.holdingFirstFunds.length < 3;
});

function handleShowHistory(fund: { code: string; name: string }) {
  selectedFundCode.value = fund.code;
  selectedFundName.value = fund.name;
  showHistoryDialog.value = true;
}

async function handleRemoveFund(code: string) {
  const confirmed = await confirm({
    title: '确认移除',
    message: `确定要从自选移除基金 ${code} 吗？`,
    confirmText: '移除',
    cancelText: '取消',
    type: 'warning',
  });

  if (confirmed) {
    await fundStore.removeFund(code);
  }
}

async function handleFundAdded() {
  await fundStore.fetchFunds();
  
  // 为新添加的基金获取分时数据
  for (const fund of fundStore.funds) {
    // 跳过无实时估值的基金（QDII 估值由后端基于海外指数推算）
    if (fund.hasRealTimeEstimate === false) {
      continue;
    }
    
    // 如果基金已有分时数据，跳过
    if (fund.intraday && fund.intraday.length > 0) {
      continue;
    }
    
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
}

onMounted(async () => {
  // 只在数据为空时加载基金列表
  if (fundStore.funds.length === 0) {
    await fundStore.fetchFunds();
  }

  // 加载每个基金的分时数据
  for (const fund of fundStore.funds) {
    // 跳过无实时估值的基金（QDII 估值由后端基于海外指数推算）
    if (fund.hasRealTimeEstimate === false) {
      continue;
    }

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
</script>

<style lang="scss" scoped>
.funds-view {
  animation: fadeIn var(--transition-normal);
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
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
  background: linear-gradient(90deg, var(--color-primary) 0%, var(--color-primary-light, #60a5fa) 50%, var(--color-primary) 100%);
  background-size: 200% 100%;
  border-radius: var(--radius-full);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: progress-shimmer 1.5s infinite;
}

@keyframes progress-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
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
  gap: var(--spacing-sm);
  flex-wrap: wrap;
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
  transition: background-color var(--transition-fast), border-color var(--transition-fast), opacity var(--transition-fast), transform var(--transition-fast);
  white-space: nowrap;

  svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
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

  // 脉冲提示动画
  &.pulse-hint {
    animation: pulse-ring 2s ease-out infinite;
  }
}

@keyframes pulse-ring {
  0% {
    box-shadow: 0 0 0 0 rgba(var(--color-primary-rgb, 59, 130, 246), 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(var(--color-primary-rgb, 59, 130, 246), 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(var(--color-primary-rgb, 59, 130, 246), 0);
  }
}

// ==================== 网格布局优化 ====================

.funds-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
  width: 100%;
}

// 响应式断点优化

// 大桌面 (>= 1440px)
@media (min-width: 1440px) {
  .funds-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

// 桌面 (1024px - 1439px)
@media (max-width: 1439px) {
  .funds-grid {
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  }
}

// 平板 (768px - 1023px)
@media (max-width: 1023px) {
  .funds-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: var(--spacing-sm);
  }
}

// 大手机/小平板 (640px - 767px)
@media (max-width: 767px) {
  .funds-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: var(--spacing-sm);
  }

  .list-header {
    margin-bottom: var(--spacing-md);
  }

  .section-title {
    font-size: var(--font-size-md);
  }
}

// 小手机 (< 640px) - 单列布局
@media (max-width: 639px) {
  .funds-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-sm);
  }

  .list-header {
    margin-bottom: var(--spacing-sm);
    padding: 0 var(--spacing-xs);
  }

  .header-left {
    gap: var(--spacing-sm);
  }

  .section-title {
    font-size: var(--font-size-md);
  }

  .fund-count {
    font-size: var(--font-size-xs);
  }

  .btn-add {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: var(--font-size-xs);

    svg {
      width: 14px;
      height: 14px;
    }
  }
}

// 超小屏 (< 480px)
@media (max-width: 479px) {
  .funds-grid {
    gap: var(--spacing-xs);
  }

  .list-header {
    padding: 0;
  }
}

// 基金列表容器样式
.fund-list-container {
  display: contents;
}

// 基金卡片过渡动画（用于添加/删除）
.fund-card-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.fund-card-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: absolute;
  width: 100%;
}

// 添加动画：从上方滑入 + 淡入
.fund-card-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.fund-card-enter-to {
  opacity: 1;
  transform: translateY(0);
}

// 删除动画：淡出 + 缩小
.fund-card-leave-from {
  opacity: 1;
  transform: scale(1);
}

.fund-card-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

// 列表移动动画（用于重新排序）
.fund-card-move {
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
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
    transition: background-color var(--transition-fast), border-color var(--transition-fast);

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
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
  width: 100%;
}

// 加载网格响应式
@media (max-width: 1439px) {
  .loading-grid {
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  }
}

@media (max-width: 1023px) {
  .loading-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }
}

@media (max-width: 767px) {
  .loading-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }
}

@media (max-width: 639px) {
  .loading-grid {
    grid-template-columns: 1fr;
  }
}

// 减少动画偏好支持
@media (prefers-reduced-motion: reduce) {
  .progress-fill {
    animation: none;
  }

  .btn-add.pulse-hint {
    animation: none;
  }

  .fund-card-enter-active,
  .fund-card-leave-active,
  .fund-card-move {
    transition: none;
  }
}
</style>
