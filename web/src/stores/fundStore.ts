import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { fundApi } from '@/api';
import type { Fund, FundHistory, FundIntraday } from '@/types';
import { ApiError } from '@/api';
import { formatTime } from '@/utils/time';

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
  const loadingProgress = ref(0);  // 加载进度 0-100
  const loadingTotal = ref(0);     // 需要加载的总数
  const error = ref<string | null>(null);
  const lastUpdated = ref<string | null>(null);
  // 从 localStorage 读取设置
  const STORAGE_KEY = 'fund-app-settings';
  function loadSettings(): { refreshInterval: number; autoRefresh: boolean; showChart: boolean } {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.error('[FundStore] Failed to load settings:', e);
    }
    return { refreshInterval: 30, autoRefresh: true, showChart: true };
  }

  const savedSettings = loadSettings();
  const refreshInterval = ref(savedSettings.refreshInterval); // seconds
  const autoRefresh = ref(savedSettings.autoRefresh);
  const showChart = ref(savedSettings.showChart); // 是否显示基金卡片图表，默认开启
  const retryCount = ref(0);
  const maxRetries = 2;

  // 日内数据缓存（避免重复请求）
  const intradayCache = new Map<string, { data: FundIntraday[]; timestamp: number }>();
  const INTRADAY_CACHE_DURATION = 60 * 1000; // 缓存 60 秒

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

  // 持有优先排序（保持原序）
  const holdingFirstFunds = computed(() => {
    const holding = funds.value.filter((f) => f.isHolding);
    const notHolding = funds.value.filter((f) => !f.isHolding);
    return [...holding, ...notHolding];
  });

  // 获取友好的错误消息
  function getFriendlyErrorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      // 优先使用 detail 或 code
      if (err.detail) {
        return friendlyErrorMessages[err.detail] || err.detail;
      }
      if (err.code && friendlyErrorMessages[err.code]) {
        return friendlyErrorMessages[err.code] || err.message;
      }
      return err.message || '获取基金列表失败';
    }
    if (err instanceof Error) {
      return friendlyErrorMessages[err.message] || err.message || '获取基金列表失败';
    }
    return '获取基金列表失败';
  }

  // Actions
  async function fetchFunds(options: FetchOptions = DEFAULT_OPTIONS) {
    const retries = options.retries ?? DEFAULT_OPTIONS.retries ?? 2;
    const retryDelay = options.retryDelay ?? DEFAULT_OPTIONS.retryDelay ?? 1000;
    const showError = options.showError ?? DEFAULT_OPTIONS.showError;
    loading.value = true;
    loadingProgress.value = 0;
    loadingTotal.value = 0;
    error.value = null;
    retryCount.value = 0;

    let lastError: unknown;

    for (let attempt = 0; attempt <= retries; attempt++) {
      retryCount.value = attempt;
      try {
        const response = await fundApi.getFunds();
        funds.value = response.funds || [];
        loading.value = false;
        loadingProgress.value = 100;  // 加载完成
        lastUpdated.value = formatTime(new Date());
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
    loadingProgress.value = 0;
  }

  async function fetchFundEstimate(code: string) {
    try {
      const estimate = await fundApi.getFundEstimate(code);
      const index = funds.value.findIndex((f) => f.code === code);
      if (index !== -1 && estimate.code) {
        const currentFund = funds.value[index];
        if (currentFund) {
          funds.value[index] = {
            ...currentFund,
            code: estimate.code ?? currentFund.code,
            name: estimate.name ?? currentFund.name,
            netValue: estimate.netValue ?? currentFund.netValue,
            netValueDate: currentFund.netValueDate || new Date().toISOString(),
            estimateValue: estimate.estimateValue ?? currentFund.estimateValue,
            estimateChange: estimate.estimateChange ?? currentFund.estimateChange,
            estimateChangePercent: estimate.estimateChangePercent ?? currentFund.estimateChangePercent,
          };
        }
      }
    } catch (err) {
      console.error(`[FundStore] fetchFundEstimate error for ${code}:`, err);
    }
  }

  // 保存设置到 localStorage
  function saveSettings() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        refreshInterval: refreshInterval.value,
        autoRefresh: autoRefresh.value,
        showChart: showChart.value,
      }));
    } catch (e) {
      console.error('[FundStore] Failed to save settings:', e);
    }
  }

  function setRefreshInterval(seconds: number) {
    refreshInterval.value = seconds;
    saveSettings();
  }

  function setAutoRefresh(enabled: boolean) {
    autoRefresh.value = enabled;
    saveSettings();
  }

  function setShowChart(enabled: boolean) {
    showChart.value = enabled;
    saveSettings();
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

  // 标记/取消持有
  async function toggleHolding(code: string, holding: boolean): Promise<boolean> {
    try {
      const response = await fundApi.toggleHolding(code, holding);
      if (response.success) {
        // 更新本地状态
        const index = funds.value.findIndex((f) => f.code === code);
        if (index !== -1) {
          const currentFund = funds.value[index];
          if (currentFund) {
            funds.value[index] = { ...currentFund, isHolding: holding };
          }
        }
        return true;
      }
      return false;
    } catch (err) {
      console.error('[FundStore] toggleHolding error:', err);
      error.value = getFriendlyErrorMessage(err);
      throw err;
    }
  }

  // 获取基金历史数据（包含今日实时 K 线）
  async function fetchHistory(code: string, days: number = 60): Promise<FundHistory[]> {
    try {
      // 并行获取历史数据和今日估值
      const [historyResponse, estimateResponse] = await Promise.allSettled([
        fundApi.getFundHistory(code, days),
        fundApi.getFundEstimate(code),
      ]);

      const history: FundHistory[] = historyResponse.status === 'fulfilled'
        ? (historyResponse.value.data || [])
        : [];

      // 构建今日 K 线数据
      let todayKLine: FundHistory | null = null;

      if (estimateResponse.status === 'fulfilled' && estimateResponse.value) {
        const estimate = estimateResponse.value;
        const todayStr = new Date().toISOString().split('T')[0];
        if (!todayStr) return history; // 处理日期异常

        // 找到昨日净值作为开盘价
        let openPrice: number | null = null;
        if (history.length > 0) {
          const lastItem = history[history.length - 1];
          if (lastItem && lastItem.close) {
            openPrice = lastItem.close;
          }
        }

        // 如果有开盘价和当前估值，构建今日 K 线
        if (openPrice !== null && estimate.netValue) {
          todayKLine = {
            time: todayStr,
            open: openPrice,
            high: Math.max(openPrice, estimate.netValue),
            low: Math.min(openPrice, estimate.netValue),
            close: estimate.netValue,
            volume: 0,
          };
        }
      }

      // 合并历史数据和今日 K 线
      const fullHistory = todayKLine ? [...history, todayKLine] : history;

      // 更新对应基金的历史数据
      const index = funds.value.findIndex((f) => f.code === code);
      if (index !== -1) {
        const currentFund = funds.value[index];
        if (currentFund) {
          funds.value[index] = { ...currentFund, history: fullHistory };
        }
      }

      return fullHistory;
    } catch (err) {
      console.error(`[FundStore] fetchHistory error for ${code}:`, err);
      return [];
    }
  }

  // 获取日内分时数据（带缓存）
  async function fetchIntraday(code: string, forceRefresh = false): Promise<FundIntraday[]> {
    // 检查缓存
    const cached = intradayCache.get(code);
    if (!forceRefresh && cached && Date.now() - cached.timestamp < INTRADAY_CACHE_DURATION) {
      // 更新对应基金的日内数据
      const index = funds.value.findIndex((f) => f.code === code);
      if (index !== -1) {
        const currentFund = funds.value[index];
        funds.value[index] = { ...currentFund, intraday: cached.data } as Fund;
      }
      return cached.data;
    }

    try {
      // 调用后端 API 获取完整的日内分时数据
      const response = await fundApi.getFundIntraday(code);

      if (response.data && response.data.length > 0) {
        // 转换数据格式为 FundIntraday
        const intraday: FundIntraday[] = response.data.map((item: { time: string; price: number; change?: number }) => ({
          time: item.time,
          price: item.price,
        }));

        // 更新对应基金的分时数据
        const index = funds.value.findIndex((f) => f.code === code);
        if (index !== -1) {
          const currentFund = funds.value[index];
          if (currentFund) {
            funds.value[index] = {
              ...currentFund,
              intraday,
            } as Fund;
          }
        }

        // 更新缓存
        intradayCache.set(code, { data: intraday, timestamp: Date.now() });

        return intraday;
      }

      return [];
    } catch (err) {
      console.error(`[FundStore] fetchIntraday error for ${code}:`, err);
      return [];
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
    showChart,
    retryCount,
    maxRetries,
    // Getters
    risingFunds,
    fallingFunds,
    neutralFunds,
    topGainers,
    topLosers,
    averageChange,
    holdingFirstFunds,
    // Actions
    fetchFunds,
    fetchFundEstimate,
    fetchHistory,
    fetchIntraday,
    setRefreshInterval,
    setAutoRefresh,
    setShowChart,
    clearError,
    retry,
    addFund,
    removeFund,
    toggleHolding,
  };
});
