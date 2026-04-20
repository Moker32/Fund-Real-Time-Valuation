import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { indexApi } from '@/api';
import type { MarketIndex, IndexHistory, IndexIntraday } from '@/types';
import { ApiError } from '@/api';
import { formatTime } from '@/utils/time';
import { useWSStore } from './wsStore';

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

  // 日内数据缓存（避免重复请求）
  const intradayCache = new Map<string, { data: IndexIntraday[]; timestamp: number }>();
  const INTRADAY_CACHE_DURATION = 60 * 1000; // 缓存 60 秒

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
        return friendlyErrorMessages[err.code] ?? err.message ?? '获取指数列表失败';
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
    const hasExistingData = indices.value.length > 0;
    if (!force && hasExistingData) {
      loading.value = false;
    } else {
      loading.value = true;
    }
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

  async function fetchIndexHistory(indexType: string, period: string = '1mo'): Promise<IndexHistory[]> {
    try {
      const response = await indexApi.getIndexHistory(indexType, period);
      return response.data || [];
    } catch (err) {
      console.error(`[IndexStore] fetchIndexHistory error for ${indexType}:`, err);
      return [];
    }
  }

  // 获取指数日内分时数据（带缓存）
  async function fetchIndexIntraday(indexType: string, forceRefresh = false): Promise<IndexIntraday[]> {
    // 检查缓存
    const cached = intradayCache.get(indexType);
    if (!forceRefresh && cached && Date.now() - cached.timestamp < INTRADAY_CACHE_DURATION) {
      // 更新对应指数的日内数据（使用 splice 确保 Vue 响应式更新）
      const index = indices.value.findIndex((i) => i.index === indexType);
      if (index !== -1) {
        const currentIndex = indices.value[index];
        if (currentIndex) {
          indices.value.splice(index, 1, { ...currentIndex, intraday: cached.data });
        }
      }
      return cached.data;
    }

    try {
      // 调用后端 API 获取完整的日内分时数据
      const response = await indexApi.getIndexIntraday(indexType);

      if (response.data && response.data.length > 0) {
        // 转换数据格式为 IndexIntraday
        const intraday: IndexIntraday[] = response.data.map((item: { time: string; price: number; change?: number }) => ({
          time: item.time,
          price: item.price,
          change: item.change,
        }));

        // 更新对应指数的分时数据（使用 splice 确保 Vue 响应式更新）
        const index = indices.value.findIndex((i) => i.index === indexType);
        if (index !== -1) {
          const currentIndex = indices.value[index];
          if (currentIndex) {
            indices.value.splice(index, 1, {
              ...currentIndex,
              intraday,
            });
          }
        }

        // 更新缓存
        intradayCache.set(indexType, { data: intraday, timestamp: Date.now() });

        return intraday;
      }

      return [];
    } catch (err) {
      console.error(`[IndexStore] fetchIndexIntraday error for ${indexType}:`, err);
      return [];
    }
  }

  function clearError() {
    error.value = null;
  }

  // WebSocket 相关状态
  const wsConnected = ref(false);
  const wsSubscribed = ref(false);

  // 更新单个指数数据（用于 WebSocket 实时更新）
  function updateIndexFromWS(update: Partial<MarketIndex> & { index: string }) {
    const idx = indices.value.findIndex((i) => i.index === update.index);
    if (idx !== -1) {
      const current = indices.value[idx];
      indices.value.splice(idx, 1, { ...current, ...update });
    }
  }

  // 批量更新指数数据（用于 WebSocket 批量推送）
  function updateIndicesBatch(updates: (Partial<MarketIndex> & { index: string })[]) {
    for (const update of updates) {
      const idx = indices.value.findIndex((i) => i.index === update.index);
      if (idx !== -1) {
        const current = indices.value[idx];
        indices.value.splice(idx, 1, { ...current, ...update });
      }
    }
  }

  /**
   * 初始化 WebSocket 连接并订阅指数频道
   */
  function initWebSocket() {
    const wsStore = useWSStore();

    // 监听连接状态
    wsStore.on('connected', () => {
      wsConnected.value = true;
      wsStore.subscribe('indices');
      wsSubscribed.value = true;
    });

    wsStore.on('disconnected', () => {
      wsConnected.value = false;
      wsSubscribed.value = false;
    });

    // 监听指数更新消息
    wsStore.on('index_update', (data: unknown) => {
      try {
        const payload = data as { indices?: (Partial<MarketIndex> & { index: string })[] };
        if (payload.indices && Array.isArray(payload.indices)) {
          updateIndicesBatch(payload.indices);
        }
      } catch (e) {
        console.error('[IndexStore] 处理 WebSocket 消息失败:', e);
      }
    });

    // 如果已经连接，直接订阅
    if (wsStore.isConnected) {
      wsConnected.value = true;
      wsStore.subscribe('indices');
      wsSubscribed.value = true;
    }
  }

  /**
   * 取消 WebSocket 订阅
   */
  function unsubscribeWebSocket() {
    const wsStore = useWSStore();
    wsStore.unsubscribe('indices');
    wsSubscribed.value = false;
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
    // WebSocket State
    wsConnected,
    wsSubscribed,
    // Getters
    indicesByRegion,
    risingIndices,
    fallingIndices,
    openMarketIndices,
    closedMarketIndices,
    sortedIndices,
    // Actions
    fetchIndices,
    fetchIndexHistory,
    fetchIndexIntraday,
    clearError,
    retry,
    // WebSocket Actions
    initWebSocket,
    unsubscribeWebSocket,
    updateIndexFromWS,
    updateIndicesBatch,
  };
});
