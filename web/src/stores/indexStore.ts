import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { indexApi } from '@/api';
import type { MarketIndex } from '@/types';
import { ApiError } from '@/api';
import { formatTime } from '@/utils/time';

export interface FetchOptions {
  retries?: number;
  retryDelay?: number;
  showError?: boolean;
  force?: boolean;  // 强制刷新
}

// 延迟函数
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// 友好的错误消息映射
const friendlyErrorMessages: Record<string, string> = {
  'NETWORK_ERROR': '网络连接失败，请检查网络设置',
  '请求参数验证失败': '请求参数错误，请检查输入',
  'Internal Server Error': '服务器暂时繁忙，请稍后重试',
  'timeout': '请求超时，请检查网络连接',
  '503': '指数服务暂时不可用',
};

export const useIndexStore = defineStore('indices', () => {
  // State
  const indices = ref<MarketIndex[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdated = ref<string | null>(null);
  const retryCount = ref(0);
  const maxRetries = 2;

  // Region order for sorting (A-shares first)
  const regionOrder: Record<string, number> = {
    'china': 0,
    'hk': 1,
    'asia': 2,
    'america': 3,
    'europe': 4,
  };

  // Getters
  const indicesByRegion = computed(() => {
    const grouped: Record<string, MarketIndex[]> = {};
    for (const index of indices.value) {
      const region = index.region || 'unknown';
      if (!grouped[region]) {
        grouped[region] = [];
      }
      grouped[region].push(index);
    }
    return grouped;
  });

  const risingIndices = computed(() =>
    indices.value.filter((i) => i.changePercent > 0)
  );

  const fallingIndices = computed(() =>
    indices.value.filter((i) => i.changePercent < 0)
  );

  const openMarketIndices = computed(() =>
    indices.value.filter((i) => i.tradingStatus === 'open')
  );

  const closedMarketIndices = computed(() =>
    indices.value.filter((i) => i.tradingStatus === 'closed' || i.tradingStatus === 'pre')
  );

  const sortedIndices = computed(() => {
    return [...indices.value].sort((a, b) => {
      // 开盘状态优先
      const aOpen = a.tradingStatus === 'open' ? 0 : 1;
      const bOpen = b.tradingStatus === 'open' ? 0 : 1;
      if (aOpen !== bOpen) return aOpen - bOpen;

      // 按区域排序
      const aRegion = regionOrder[a.region || 'unknown'] ?? 99;
      const bRegion = regionOrder[b.region || 'unknown'] ?? 99;
      if (aRegion !== bRegion) return aRegion - bRegion;

      // 按涨跌排序
      return b.changePercent - a.changePercent;
    });
  });

  // 获取友好的错误消息
  function getFriendlyErrorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      if (err.detail) {
        return friendlyErrorMessages[err.detail] || err.detail;
      }
      if (err.code && friendlyErrorMessages[err.code]) {
        return friendlyErrorMessages[err.code];
      }
      return err.message || '获取指数列表失败';
    }
    if (err instanceof Error) {
      return friendlyErrorMessages[err.message] || err.message || '获取指数列表失败';
    }
    return '获取指数列表失败';
  }

  // Actions
  async function fetchIndices(options: FetchOptions = {}) {
    const retries = options.retries ?? 2;
    const retryDelay = options.retryDelay ?? 1000;
    const showError = options.showError ?? true;
    const force = options.force ?? false;

    // 如果已有数据且不是强制刷新，不显示 loading
    if (!force && indices.value.length > 0) {
      return;
    }

    loading.value = true;
    error.value = null;
    retryCount.value = 0;

    let lastError: unknown;

    for (let attempt = 0; attempt <= retries; attempt++) {
      retryCount.value = attempt;
      try {
        const response = await indexApi.getIndices();
        indices.value = response.indices || [];
        lastUpdated.value = formatTime(new Date());
        return; // 成功，退出函数
      } catch (err) {
        lastError = err;
        console.error(`[IndexStore] fetchIndices attempt ${attempt + 1} error:`, err);

        if (attempt < retries && !(err instanceof ApiError && err.statusCode === 404)) {
          await delay(retryDelay * (attempt + 1)); // 指数退避
          continue;
        }
        break;
      }
    }

    // 所有重试都失败了
    error.value = getFriendlyErrorMessage(lastError);
    if (showError) {
      console.error('[IndexStore] fetchIndices failed after retries:', error.value);
    }
    loading.value = false;
  }

  function clearError() {
    error.value = null;
  }

  // 重试函数
  async function retry() {
    await fetchIndices();
  }

  return {
    // State
    indices,
    loading,
    error,
    lastUpdated,
    retryCount,
    maxRetries,
    // Getters
    indicesByRegion,
    risingIndices,
    fallingIndices,
    openMarketIndices,
    closedMarketIndices,
    sortedIndices,
    // Actions
    fetchIndices,
    clearError,
    retry,
  };
});
