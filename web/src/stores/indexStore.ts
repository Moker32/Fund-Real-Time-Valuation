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
        // 保留已有的 intraday 和 history 数据
        const newIndices = response.indices || [];
        indices.value = newIndices.map(newIdx => {
          const existingIdx = indices.value.find(i => i.index === newIdx.index);
          if (existingIdx) {
            return {
              ...newIdx,
              intraday: existingIdx.intraday,
              history: existingIdx.history,
            };
          }
          return newIdx;
        });
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
      // 更新对应指数的日内数据（使用数组替换确保 Vue 响应式更新）
      const index = indices.value.findIndex((i) => i.index === indexType);
      if (index !== -1) {
        const currentIndex = indices.value[index];
        if (currentIndex && cached.data.length > 0) {
          const newIndices = [...indices.value];
          newIndices[index] = {
            ...currentIndex,
            intraday: cached.data,
            history: currentIndex.history,
          };
          indices.value = newIndices;
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

        // 更新对应指数的分时数据（使用数组替换确保 Vue 响应式更新）
        const index = indices.value.findIndex((i) => i.index === indexType);
        if (index !== -1) {
          const currentIndex = indices.value[index];
          if (currentIndex) {
            const newIndices = [...indices.value];
            newIndices[index] = {
              ...currentIndex,
              intraday,
              history: currentIndex.history,
            };
            indices.value = newIndices;
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
  let wsInitialized = false;  // 防止重复初始化

  // 追加 intraday 数据点（streaming 模式，用于折线图实时绘制）
  function appendIntradayPoint(
    indexType: string,
    price: number,
    change?: number,
  ) {
    const index = indices.value.findIndex((i) => i.index === indexType);
    if (index === -1) {
      console.log('[IndexStore] appendIntradayPoint: index not found for', indexType);
      return;
    }

    const current = indices.value[index];
    if (!current) {
      console.log('[IndexStore] appendIntradayPoint: current is null for', indexType);
      return;
    }
    if (!current.intraday || current.intraday.length === 0) {
      console.log('[IndexStore] appendIntradayPoint: current.intraday is empty for', indexType);
      return;
    }

    // 构造当前时间点（HH:MM:SS，兼容日内数据格式）
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

    // 防抖：跳过与最后一个数据点时间相同的重复推送（push 间隔 10s，通常不重复）
    const lastPoint = current.intraday[current.intraday.length - 1];
    if (lastPoint && lastPoint.time === timeStr) return;

    const newPoint: IndexIntraday = { time: timeStr, price, change };
    const newIntraday = [...current.intraday, newPoint];

    // 超过 maxPoints 丢弃最老的点
    const maxPoints = 500;
    const trimmed = newIntraday.length > maxPoints ? newIntraday.slice(-maxPoints) : newIntraday;

    console.log('[IndexStore] appendIntradayPoint: appending to', indexType, '- old length:', current.intraday.length, 'new length:', trimmed.length);
    // 使用新对象替换，确保 Vue 能追踪变化
    const newIndex: MarketIndex = {
      ...current,
      intraday: trimmed,
    };
    console.log('[IndexStore] appendIntradayPoint: newIndex.intraday.length =', newIndex.intraday?.length ?? 'undefined');
    // 使用数组替换确保 Vue 响应式更新
    const newIndices = [...indices.value];
    newIndices[index] = newIndex;
    indices.value = newIndices;
  }

  // 更新单个指数数据（用于 WebSocket 实时更新）
  function updateIndexFromWS(update: Partial<MarketIndex> & { index: string }) {
    // 关键：WebSocket 消息不应该包含 intraday 和 history，这些是本地缓存的
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { intraday: _i, history: _h, ...safeUpdate } = update;

    const idx = indices.value.findIndex((i) => i.index === update.index);
    if (idx !== -1) {
      const current = indices.value[idx];
      if (current) {
        // 保留原有的 intraday 和 history，只更新基础字段
        const updated: MarketIndex = {
          ...current,
          ...safeUpdate,
          intraday: current.intraday,
          history: current.history,
        };
        // 强制替换整个数组以确保 Vue 响应式更新
        const newIndices = [...indices.value];
        newIndices[idx] = updated;
        indices.value = newIndices;
      }
    }
    // 同时追加 intraday 数据点（折线图 streaming 追加）
    if (safeUpdate.price !== undefined) {
      appendIntradayPoint(update.index, safeUpdate.price, safeUpdate.change);
    }
  }

  // 批量更新指数数据（用于 WebSocket 批量推送）
  function updateIndicesBatch(updates: (Partial<MarketIndex> & { index: string })[]) {
    console.log('[IndexStore] updateIndicesBatch called with', updates.length, 'updates');
    // 强制替换整个数组以确保 Vue 响应式更新
    const newIndices = [...indices.value];
    for (const update of updates) {
      // 关键：WebSocket 消息不应该包含 intraday 和 history，这些是本地缓存的
      // 如果 update 包含这些字段且为空，会导致数据丢失，需要排除
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { intraday: _i, history: _h, ...safeUpdate } = update;

      // 只有包含有效价格更新的才处理，静默跳过无效更新
      if (safeUpdate.price === undefined && safeUpdate.change === undefined && safeUpdate.changePercent === undefined) {
        console.log('[IndexStore] updateIndicesBatch: skipping', update.index, '- no relevant fields');
        continue;
      }

      const idx = newIndices.findIndex((i) => i.index === update.index);
      if (idx !== -1) {
        const current = newIndices[idx];
        if (current) {
          const oldIntradayLen = current.intraday?.length ?? 0;
          console.log('[IndexStore] Updating', update.index, '- current intraday:', oldIntradayLen);
          // 保留原有的 intraday 和 history，只更新基础字段
          newIndices[idx] = {
            ...current,
            ...safeUpdate,
            intraday: current.intraday,
            history: current.history,
          } as MarketIndex;
          const newLen = newIndices[idx]?.intraday?.length ?? 0;
          console.log('[IndexStore] After update', update.index, '- new intraday length:', newLen);
        }
      }
    }
    indices.value = newIndices;
    console.log('[IndexStore] updateIndicesBatch complete - total indices with intraday:', indices.value.filter(i => (i.intraday?.length ?? 0) > 0).length);
  }

  /**
   * 初始化 WebSocket 连接并订阅指数频道
   */
  function initWebSocket() {
    console.log('[IndexStore] initWebSocket called - wsInitialized =', wsInitialized);
    // 防止重复初始化
    if (wsInitialized) {
      console.log('[IndexStore] initWebSocket: already initialized, skipping');
      return;
    }
    wsInitialized = true;
    console.log('[IndexStore] initWebSocket: initializing WebSocket handlers');

    const wsStore = useWSStore();

    // 监听连接状态
    wsStore.on('connected', () => {
      console.log('[IndexStore] WebSocket connected event');
      wsConnected.value = true;
      wsStore.subscribe('indices');
      wsSubscribed.value = true;
    });

    wsStore.on('disconnected', () => {
      console.log('[IndexStore] WebSocket disconnected event');
      wsConnected.value = false;
      wsSubscribed.value = false;
    });

    // 监听指数更新消息
    wsStore.on('index_update', (data: unknown) => {
      console.log('[IndexStore] Received index_update WebSocket message');
      try {
        const payload = data as { indices?: (Partial<MarketIndex> & { index: string })[] };
        if (payload.indices && Array.isArray(payload.indices)) {
          // 检查是否有 index_update 消息包含了空的 intraday，这会导致数据丢失
          const hasIntradayInPayload = payload.indices.some(u => 'intraday' in u);
          console.log('[IndexStore] index_update has intraday field:', hasIntradayInPayload, '- count:', payload.indices.length);
          if (hasIntradayInPayload) {
            console.log('[IndexStore] WARNING: index_update contains intraday field, this may cause data loss!');
          }
          console.log('[IndexStore] Processing batch update for', payload.indices.length, 'indices');
          updateIndicesBatch(payload.indices);
        }
      } catch (e) {
        console.error('[IndexStore] 处理 WebSocket 消息失败:', e);
      }
    });

    // 如果已经连接，直接订阅
    if (wsStore.isConnected) {
      console.log('[IndexStore] WebSocket already connected on init');
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
