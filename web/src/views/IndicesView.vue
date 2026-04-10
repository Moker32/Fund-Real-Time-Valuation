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
        @click="openIndexDetail"
      />
    </div>

    <!-- Index Detail Modal -->
    <Teleport to="body">
      <div v-if="showDetailModal" class="modal-overlay" @click.self="closeDetailModal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>{{ selectedIndex?.name }}</h3>
            <button class="close-btn" @click="closeDetailModal">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>
          
          <!-- Period Selector -->
          <div class="period-selector">
            <button
              v-for="p in periods"
              :key="p.value"
              :class="{ active: selectedPeriod === p.value }"
              @click="selectPeriod(p.value)"
            >
              {{ p.label }}
            </button>
          </div>
          
          <!-- Chart -->
          <div class="modal-chart">
            <div v-if="historyLoading" class="chart-loading">
              加载中...
            </div>
            <div v-else-if="historyError" class="chart-error">
              {{ historyError }}
            </div>
            <LineChart
              v-else-if="historyData.length > 0"
              :data="chartData"
              :height="250"
              :trend="chartTrend"
            />
            <div v-else class="chart-empty">
              暂无数据
            </div>
          </div>
        </div>
      </div>
    </Teleport>

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
import { ref, computed, onMounted } from 'vue';
import { useIndexStore } from '@/stores/indexStore';
import { indexApi } from '@/api';
import IndexCard from '@/components/IndexCard.vue';
import LineChart from '@/components/LineChart.vue';
import type { MarketIndex, IndexHistory, FundHistory } from '@/types';

const indexStore = useIndexStore();

// Modal state
const showDetailModal = ref(false);
const selectedIndex = ref<MarketIndex | null>(null);
const selectedPeriod = ref('1y');
const historyData = ref<IndexHistory[]>([]);
const historyLoading = ref(false);
const historyError = ref<string | null>(null);
const historyPreloadLoading = ref(false);

// Period options
// eslint-disable-next-line no-useless-assignment
const periods = [
  { label: '1周', value: '1w' },
  { label: '1月', value: '1mo' },
  { label: '3月', value: '3mo' },
  { label: '半年', value: '6mo' },
  { label: '1年', value: '1y' },
  { label: '2年', value: '2y' },
];

// Transform history data for FundChart
// eslint-disable-next-line no-useless-assignment
const chartData = computed((): FundHistory[] => {
  return historyData.value.map(item => ({
    time: item.time,
    open: item.open ?? 0,
    high: item.high ?? 0,
    low: item.low ?? 0,
    close: item.close ?? 0,
    volume: item.volume ?? 0,
  }));
});

// Determine trend based on first and last data points
// eslint-disable-next-line no-useless-assignment
const chartTrend = computed((): 'rising' | 'falling' | 'neutral' => {
  if (historyData.value.length < 2) return 'neutral';
  const firstItem = historyData.value[0];
  const lastItem = historyData.value[historyData.value.length - 1];
  if (!firstItem || !lastItem) return 'neutral';
  const first = firstItem.close;
  const last = lastItem.close;
  if (first === null || last === null) return 'neutral';
  if (last > first) return 'rising';
  if (last < first) return 'falling';
  return 'neutral';
});

async function openIndexDetail(index: MarketIndex) {
  selectedIndex.value = index;
  showDetailModal.value = true;
  await fetchHistory();
}

function closeDetailModal() {
  showDetailModal.value = false;
  selectedIndex.value = null;
  historyData.value = [];
  historyError.value = null;
}

async function selectPeriod(period: string) {
  selectedPeriod.value = period;
  await fetchHistory();
}

async function fetchHistory() {
  if (!selectedIndex.value) return;
  
  historyLoading.value = true;
  historyError.value = null;
  
  try {
    const response = await indexApi.getIndexHistory(selectedIndex.value.index, selectedPeriod.value);
    historyData.value = response.data;
  } catch (error) {
    historyError.value = error instanceof Error ? error.message : '加载失败';
    historyData.value = [];
  } finally {
    historyLoading.value = false;
  }
}

// Empty index for loading skeleton
// eslint-disable-next-line no-useless-assignment
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

async function preloadIndexIntraday() {
  if (indexStore.indices.length === 0 || historyPreloadLoading.value) return;
  
  historyPreloadLoading.value = true;
  
  try {
    // 使用 store 中的 fetchIndexIntraday 方法获取日内数据（带缓存）
    // 预加载所有指数的日内数据
    const intradayPromises = indexStore.indices.map(async (idx) => {
      try {
        const intraday = await indexStore.fetchIndexIntraday(idx.index);
        return { indexType: idx.index, intraday: intraday || [] };
      } catch {
        return { indexType: idx.index, intraday: [] };
      }
    });
    
    const results = await Promise.all(intradayPromises);
    
    // 替换整个数组以确保响应式更新
    const updatedIndices = indexStore.indices.map(idx => {
      const result = results.find(r => r.indexType === idx.index);
      if (result) {
        return { ...idx, intraday: result.intraday };
      }
      return idx;
    });
    
    indexStore.indices.splice(0, indexStore.indices.length, ...updatedIndices);
  } catch (error) {
    console.error('[IndicesView] preloadIndexIntraday error:', error);
  } finally {
    historyPreloadLoading.value = false;
  }
}

onMounted(async () => {
  // 先获取指数列表
  if (indexStore.indices.length === 0) {
    await indexStore.fetchIndices({ force: true });
  }
  // 再预加载日内分时数据（无论是否已有数据）
  await preloadIndexIntraday();
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
  grid-template-columns: 1fr;
  gap: var(--spacing-md);

  @media (min-width: 640px) {
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  }
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
  grid-template-columns: 1fr;
  gap: var(--spacing-md);
  width: 100%;

  @media (min-width: 640px) {
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  }
}

// Modal Styles
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn var(--transition-fast);
}

.modal-content {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: auto;
  animation: slideUp var(--transition-normal);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-divider);

  h3 {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
  }
}

.close-btn {
  background: none;
  border: none;
  padding: var(--spacing-xs);
  cursor: pointer;
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--color-bg-tertiary);
    color: var(--color-text-primary);
  }

  svg {
    width: 20px;
    height: 20px;
  }
}

.period-selector {
  display: flex;
  gap: var(--spacing-xs);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-divider);

  button {
    padding: var(--spacing-xs) var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg-secondary);
    color: var(--color-text-secondary);
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      border-color: var(--color-border-light);
      color: var(--color-text-primary);
    }

    &.active {
      background: var(--color-primary);
      border-color: var(--color-primary);
      color: white;
    }
  }
}

.modal-chart {
  padding: var(--spacing-lg);
  min-height: 250px;
}

.chart-loading,
.chart-error,
.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 250px;
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.chart-error {
  color: var(--color-fall);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Responsive */
@media (max-width: 768px) {
  .view-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }

  .indices-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-sm);
  }

  .loading-grid {
    grid-template-columns: 1fr;
  }

  .quick-stats {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-sm);
  }

  .stats-card {
    padding: var(--spacing-sm);
  }

  .stats-value {
    font-size: var(--font-size-lg);
  }

  .market-status {
    padding: var(--spacing-sm);
  }

  .status-item {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-sm);
  }

  .modal-content {
    width: 95%;
    max-height: 90vh;
  }

  .period-selector {
    padding: var(--spacing-sm);
    overflow-x: auto;
    flex-wrap: nowrap;

    button {
      white-space: nowrap;
      padding: var(--spacing-xs) var(--spacing-sm);
      font-size: var(--font-size-xs);
    }
  }

  .modal-chart {
    padding: var(--spacing-md);
  }
}
</style>
