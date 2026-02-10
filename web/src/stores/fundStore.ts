import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { fundApi } from '@/api';
import type { Fund } from '@/types';
import { ApiError } from '@/api';

export interface FetchOptions {
  retries?: number;
  retryDelay?: number;
  showError?: boolean;
}

const DEFAULT_OPTIONS: FetchOptions = {
  retries: 2,
  retryDelay: 1000,
  showError: true,
};

// 延迟函数
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// 友好的错误消息映射
const friendlyErrorMessages: Record<string, string> = {
  '基金不存在': '未找到指定的基金信息',
  'NETWORK_ERROR': '网络连接失败，请检查网络设置',
  '请求参数验证失败': '请求参数错误，请检查输入',
  'Internal Server Error': '服务器暂时繁忙，请稍后重试',
  'timeout': '请求超时，请检查网络连接',
};

export const useFundStore = defineStore('funds', () => {
  // State
  const funds = ref<Fund[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdated = ref<string | null>(null);
  const refreshInterval = ref(30); // seconds
  const autoRefresh = ref(true);
  const retryCount = ref(0);
  const maxRetries = 2;

  // Getters
  const risingFunds = computed(() =>
    funds.value.filter((f) => f.estimateChangePercent > 0)
  );

  const fallingFunds = computed(() =>
    funds.value.filter((f) => f.estimateChangePercent < 0)
  );

  const neutralFunds = computed(() =>
    funds.value.filter((f) => f.estimateChangePercent === 0)
  );

  const topGainers = computed(() =>
    [...funds.value].sort((a, b) => b.estimateChangePercent - a.estimateChangePercent).slice(0, 5)
  );

  const topLosers = computed(() =>
    [...funds.value].sort((a, b) => a.estimateChangePercent - b.estimateChangePercent).slice(0, 5)
  );

  const averageChange = computed(() => {
    if (funds.value.length === 0) return 0;
    const sum = funds.value.reduce((acc, f) => acc + f.estimateChangePercent, 0);
    return sum / funds.value.length;
  });

  // 获取友好的错误消息
  function getFriendlyErrorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      // 优先使用 detail 或 code
      if (err.detail) {
        return friendlyErrorMessages[err.detail] || err.detail;
      }
      if (err.code && friendlyErrorMessages[err.code]) {
        return friendlyErrorMessages[err.code];
      }
      return err.message;
    }
    if (err instanceof Error) {
      return friendlyErrorMessages[err.message] || err.message || '获取基金列表失败';
    }
    return '获取基金列表失败';
  }

  // Actions
  async function fetchFunds(options: FetchOptions = DEFAULT_OPTIONS) {
    const { retries, retryDelay, showError } = { ...DEFAULT_OPTIONS, ...options };
    loading.value = true;
    error.value = null;
    retryCount.value = 0;

    let lastError: unknown;

    for (let attempt = 0; attempt <= retries; attempt++) {
      retryCount.value = attempt;
      try {
        const response = await fundApi.getFunds();
        funds.value = response.funds || [];
        lastUpdated.value = new Date().toLocaleTimeString('zh-CN');
        return; // 成功，退出函数
      } catch (err) {
        lastError = err;
        console.error(`[FundStore] fetchFunds attempt ${attempt + 1} error:`, err);

        // 如果还有重试次数，等待后重试
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
      console.error('[FundStore] fetchFunds failed after retries:', error.value);
    }
    loading.value = false;
  }

  async function fetchFundEstimate(code: string, options: FetchOptions = {}) {
    const { retries = 1, retryDelay = 500, showError = false } = options;

    try {
      const estimate = await fundApi.getFundEstimate(code);
      const index = funds.value.findIndex((f) => f.code === code);
      if (index !== -1 && estimate.code) {
        funds.value[index] = {
          code: estimate.code,
          name: estimate.name,
          netValue: estimate.netValue,
          netValueDate: funds.value[index]?.netValueDate || new Date().toISOString(),
          estimateValue: estimate.estimateValue,
          estimateChange: estimate.estimateChange,
          estimateChangePercent: estimate.estimateChangePercent,
          type: funds.value[index]?.type,
          source: funds.value[index]?.source,
        };
      }
    } catch (err) {
      console.error(`[FundStore] fetchFundEstimate error for ${code}:`, err);
      if (showError) {
        error.value = getFriendlyErrorMessage(err);
      }
    }
  }

  function setRefreshInterval(seconds: number) {
    refreshInterval.value = seconds;
  }

  function setAutoRefresh(enabled: boolean) {
    autoRefresh.value = enabled;
  }

  function clearError() {
    error.value = null;
  }

  // 重试函数
  async function retry() {
    await fetchFunds();
  }

  // 添加基金到自选
  async function addFund(code: string, name: string): Promise<boolean> {
    try {
      const response = await fundApi.addToWatchlist(code, name);
      if (response.success) {
        // 刷新基金列表
        await fetchFunds();
        return true;
      }
      return false;
    } catch (err) {
      console.error('[FundStore] addFund error:', err);
      error.value = getFriendlyErrorMessage(err);
      throw err;
    }
  }

  // 从自选移除基金
  async function removeFund(code: string): Promise<boolean> {
    try {
      const response = await fundApi.removeFromWatchlist(code);
      if (response.success) {
        // 从本地列表中移除
        funds.value = funds.value.filter((f) => f.code !== code);
        return true;
      }
      return false;
    } catch (err) {
      console.error('[FundStore] removeFund error:', err);
      error.value = getFriendlyErrorMessage(err);
      throw err;
    }
  }

  return {
    // State
    funds,
    loading,
    error,
    lastUpdated,
    refreshInterval,
    autoRefresh,
    retryCount,
    maxRetries,
    // Getters
    risingFunds,
    fallingFunds,
    neutralFunds,
    topGainers,
    topLosers,
    averageChange,
    // Actions
    fetchFunds,
    fetchFundEstimate,
    setRefreshInterval,
    setAutoRefresh,
    clearError,
    retry,
    addFund,
    removeFund,
  };
});
