<template>
  <Transition name="dialog">
    <div v-if="visible" class="dialog-overlay" @click.self="close">
      <div class="dialog fund-history-dialog">
        <div class="dialog-header">
          <div class="header-info">
            <h3>{{ fundName }} ({{ fundCode }})</h3>
            <div v-if="fund?.manager" class="fund-meta">
              <span class="meta-item">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
                {{ fund.manager.name }}
              </span>
              <span v-if="fund.manager.tenure" class="meta-item meta-sep">任职: {{ fund.manager.tenure }}</span>
            </div>
          </div>
          <button class="close-btn" @click="close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="dialog-body">
          <!-- Period Selector -->
          <div class="period-selector">
            <button
              v-for="period in periods"
              :key="period.value"
              class="period-btn"
              :class="{ active: selectedPeriod === period.value }"
              @click="selectPeriod(period.value)"
            >
              {{ period.label }}
            </button>
          </div>

          <!-- Loading State -->
          <div v-if="loading" class="loading-state">
            <div class="loading-spinner"></div>
            <span>加载中...</span>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="error-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 8v4M12 16h.01"/>
            </svg>
            <span>{{ error }}</span>
            <button class="retry-btn" @click="fetchHistory">重试</button>
          </div>

          <!-- Chart -->
          <div v-else class="chart-container">
            <LineChart
              :data="chartData"
              :height="280"
              :baseline="baselineValue"
              :trend="trend"
            />
            <div class="chart-stats">
              <div class="stat-item">
                <span class="stat-label">最高</span>
                <span class="stat-value" :class="{ up: stats.high >= baselineValue, down: stats.high < baselineValue }">
                  {{ formatValue(stats.high) }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最低</span>
                <span class="stat-value" :class="{ up: stats.low >= baselineValue, down: stats.low < baselineValue }">
                  {{ formatValue(stats.low) }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">平均</span>
                <span class="stat-value">{{ formatValue(stats.avg) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">涨跌幅</span>
                <span class="stat-value" :class="{ up: stats.changePercent > 0, down: stats.changePercent < 0 }">
                  {{ stats.changePercent > 0 ? '+' : '' }}{{ formatPercent(stats.changePercent) }}%
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="close">关闭</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { fundApi } from '@/api';
import type { FundHistory, Fund } from '@/types';
import LineChart from './LineChart.vue';

interface Props {
  visible: boolean;
  fundCode: string;
  fundName: string;
  fund?: Fund;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

// Period options
const periods = [
  { label: '近一周', value: 7 },
  { label: '近一月', value: 30 },
  { label: '近三月', value: 90 },
  { label: '近六月', value: 180 },
  { label: '近一年', value: 365 },
] as const;

// State
const selectedPeriod = ref<number>(30);
const loading = ref(false);
const error = ref<string | null>(null);
const historyData = ref<FundHistory[]>([]);

// Cache data by period to avoid refetching
const dataCache = new Map<number, FundHistory[]>();

// Track the latest request timestamp to handle race conditions
let latestRequestTimestamp = 0;

// Computed
const chartData = computed(() => {
  return historyData.value.map(item => ({
    time: item.time,
    close: item.close,
  }));
});

const baselineValue = computed(() => {
  if (historyData.value.length === 0) return 0;
  // Use the second-to-last data point's close as baseline (yesterday's close)
  // The last item is today's K-line, whose open is yesterday's close
  if (historyData.value.length >= 2) {
    const lastItem = historyData.value[historyData.value.length - 1];
    return lastItem?.open ?? historyData.value[0]?.close ?? 0;
  }
  return historyData.value[0]?.close ?? 0;
});

const trend = computed<'rising' | 'falling' | 'neutral'>(() => {
  if (historyData.value.length < 2) return 'neutral';
  const first = historyData.value[0]?.close ?? 0;
  const last = historyData.value[historyData.value.length - 1]?.close ?? 0;
  if (last > first) return 'rising';
  if (last < first) return 'falling';
  return 'neutral';
});

const stats = computed(() => {
  if (historyData.value.length === 0) {
    return { high: 0, low: 0, avg: 0, changePercent: 0 };
  }

  const closes = historyData.value.map(item => item.close);
  const high = Math.max(...closes);
  const low = Math.min(...closes);
  const avg = closes.reduce((sum, val) => sum + val, 0) / closes.length;

  const first = historyData.value[0]?.close ?? 0;
  const last = historyData.value[historyData.value.length - 1]?.close ?? 0;
  const changePercent = first !== 0 ? ((last - first) / first) * 100 : 0;

  return { high, low, avg, changePercent };
});

// Methods
function selectPeriod(period: number) {
  selectedPeriod.value = period;
  fetchHistory();
}

async function fetchHistory() {
  if (!props.fundCode) return;

  // Check cache first
  if (dataCache.has(selectedPeriod.value)) {
    historyData.value = dataCache.get(selectedPeriod.value)!;
    return;
  }

  // Generate timestamp for this request
  const requestTimestamp = Date.now();
  latestRequestTimestamp = requestTimestamp;

  loading.value = true;
  error.value = null;

  try {
    const response = await fundApi.getFundHistory(props.fundCode, selectedPeriod.value);
    // Only update state if this is still the latest request
    if (requestTimestamp === latestRequestTimestamp) {
      historyData.value = response.data;
      dataCache.set(selectedPeriod.value, response.data);
    }
  } catch (err) {
    // Only show error if this is still the latest request
    if (requestTimestamp === latestRequestTimestamp) {
      console.error('获取基金历史数据失败:', err);
      error.value = '获取历史数据失败，请稍后重试';
    }
  } finally {
    // Only update loading state if this is still the latest request
    if (requestTimestamp === latestRequestTimestamp) {
      loading.value = false;
    }
  }
}

function close() {
  emit('close');
}

function handleKeydown(event: globalThis.KeyboardEvent) {
  if (event.key === 'Escape' && props.visible) {
    close();
  }
}

// Lifecycle hooks for keyboard events
onMounted(() => {
  document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown);
});

function formatValue(value: number): string {
  if (value === 0 || !isFinite(value)) return '--';
  return value.toFixed(4);
}

function formatPercent(value: number): string {
  if (!isFinite(value)) return '--';
  return value.toFixed(2);
}

// Watch for visibility changes
watch(() => props.visible, (visible) => {
  if (visible) {
    fetchHistory();
  }
  // Don't reset on close — keep cached data for instant re-open
});

// Watch for fund code changes (different fund opened)
watch(() => props.fundCode, () => {
  if (props.visible) {
    // Clear cache when switching funds
    dataCache.clear();
    historyData.value = [];
    selectedPeriod.value = 30;
    fetchHistory();
  }
});
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.dialog {
  width: 100%;
  max-width: 640px;
  max-height: 90vh;
  background: #1e1e1e;
  border-radius: 12px;
  border: 1px solid #2a2a2a;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
  gap: 12px;
}

.header-info {
  min-width: 0;
  flex: 1;
}

.dialog-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fund-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  color: #999;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 3px;
}

.meta-sep::before {
  content: '·';
  margin-right: 8px;
  opacity: 0.4;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #999;
  cursor: pointer;
  flex-shrink: 0;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.close-btn svg {
  width: 20px;
  height: 20px;
}

.dialog-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

/* Period Selector */
.period-selector {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.period-btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  background: #2a2a2a;
  border: 1px solid #2a2a2a;
  color: #999;
}

.period-btn:hover {
  background: #3a3a3a;
  border-color: #3a3a3a;
  color: #fff;
}

.period-btn.active {
  background: #1890ff;
  border-color: #1890ff;
  color: #fff;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: #999;
  font-size: 14px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 2px solid #2a2a2a;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Error State */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: #999;
  font-size: 14px;
}

.error-state svg {
  width: 40px;
  height: 40px;
  stroke: #ef4444;
}

.retry-btn {
  margin-top: 8px;
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  color: #fff;
  transition: all 0.15s ease;
}

.retry-btn:hover {
  background: #3a3a3a;
  border-color: #4a4a4a;
}

/* Chart Container */
.chart-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chart-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 16px;
  background: #2a2a2a;
  border-radius: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.stat-value.up {
  color: #ef4444;
}

.stat-value.down {
  color: #22c55e;
}

/* Dialog Footer */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, opacity 0.15s ease;
  border: 1px solid transparent;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #2a2a2a;
  border-color: #2a2a2a;
  color: #fff;
}

.btn-secondary:hover:not(:disabled) {
  background: #3a3a3a;
  border-color: #3a3a3a;
}

/* Transition Animations */
.dialog-enter-active,
.dialog-leave-active {
  transition: all 0.2s ease;
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-from .dialog,
.dialog-leave-to .dialog {
  transform: scale(0.95);
}

/* Mobile Responsive */
@media (max-width: 640px) {
  .dialog-overlay {
    padding: 0;
    align-items: flex-end;
  }

  .dialog {
    max-width: 100%;
    max-height: 85vh;
    border-radius: 12px 12px 0 0;
  }

  .dialog-header {
    padding: 12px 16px;
  }

  .dialog-header h3 {
    font-size: 15px;
  }

  .dialog-body {
    padding: 16px;
  }

  .period-selector {
    gap: 6px;
    margin-bottom: 16px;
  }

  .period-btn {
    padding: 5px 10px;
    font-size: 12px;
  }

  .chart-stats {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    padding: 12px;
  }

  .stat-item {
    align-items: flex-start;
  }

  .dialog-footer {
    padding: 12px 16px;
  }

  .btn {
    padding: 10px 20px;
    font-size: 14px;
  }
}

/* Small mobile screens */
@media (max-width: 380px) {
  .period-selector {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
  }

  .period-btn {
    text-align: center;
    padding: 6px 8px;
  }
}
</style>
