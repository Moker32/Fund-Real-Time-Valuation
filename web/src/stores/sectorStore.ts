import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { sectorApi } from '@/api';
import type { Sector, SectorStock, SectorListResponse, SectorDetailResponse } from '@/types';
import { ApiError } from '@/api';
import { useWSStore } from './wsStore';
import { formatTime } from '@/utils/time';

export interface FetchOptions {
  retries?: number;
  retryDelay?: number;
  showError?: boolean;
  force?: boolean;
}

// WebSocket 板块更新数据类型
interface WSSectorUpdate {
  name: string;
  change: number;
  changePercent: number;
  stockCount?: number;
  timestamp?: string;
}

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const friendlyErrorMessages: Record<string, string> = {
  'NETWORK_ERROR': '网络连接失败，请检查网络设置',
  '请求参数验证失败': '请求参数错误，请检查输入',
  'Internal Server Error': '服务器暂时繁忙，请稍后重试',
  'timeout': '请求超时，请检查网络连接',
};

export type SectorType = 'industry' | 'concept';

export const useSectorStore = defineStore('sectors', () => {
  // State
  const industrySectors = ref<Sector[]>([]);
  const conceptSectors = ref<Sector[]>([]);
  const currentType = ref<SectorType>('industry');
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdated = ref<string | null>(null);
  const retryCount = ref(0);
  const maxRetries = 2;

  // Detail state
  const selectedSector = ref<string | null>(null);
  const sectorDetail = ref<SectorStock[]>([]);
  const detailLoading = ref(false);
  const detailError = ref<string | null>(null);

  // WebSocket 相关状态
  const wsConnected = ref(false);
  const wsSubscribed = ref(false);

  // 折线图历史数据（用于 streaming 实时绘制）
  const sectorHistory = ref<Map<string, { time: string; price: number }[]>>(new Map());
  // 当前选中显示折线图的板块
  const selectedChartSymbol = ref<string | null>(null);
  const MAX_HISTORY_POINTS = 500;

  // Getters
  const currentSectors = computed(() => {
    return currentType.value === 'industry' ? industrySectors.value : conceptSectors.value;
  });

  const risingSectors = computed(() =>
    currentSectors.value.filter((s) => s.changePercent > 0)
  );

  const fallingSectors = computed(() =>
    currentSectors.value.filter((s) => s.changePercent < 0)
  );

  const sortedSectors = computed(() => {
    return [...currentSectors.value].sort((a, b) => {
      return b.changePercent - a.changePercent;
    });
  });

  // 获取当前选中的折线图历史数据
  const selectedChartHistory = computed((): { time: string; price: number }[] => {
    if (!selectedChartSymbol.value) return [];
    return sectorHistory.value.get(selectedChartSymbol.value) || [];
  });

  // 选中折线图板块
  function selectChartSymbol(symbol: string | null) {
    if (symbol === null) {
      selectedChartSymbol.value = null;
      return;
    }
    selectedChartSymbol.value = symbol;
    // 如果还没有该板块的历史，先初始化当前数据
    if (!sectorHistory.value.has(symbol)) {
      const sector = currentSectors.value.find(s => s.name === symbol);
      if (sector) {
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        sectorHistory.value.set(symbol, [{ time: timeStr, price: sector.changePercent || 0 }]);
      }
    }
  }

  // 获取友好的错误消息
  function getFriendlyErrorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      if (err.detail) {
        return friendlyErrorMessages[err.detail] || err.detail;
      }
      if (err.code && friendlyErrorMessages[err.code]) {
        return friendlyErrorMessages[err.code]!;
      }
      return err.message || '获取板块列表失败';
    }
    if (err instanceof Error) {
      return err.message || '获取板块列表失败';
    }
    return '获取板块列表失败';
  }

  // 获取板块列表
  async function fetchSectors(
    sectorType: SectorType,
    options: FetchOptions = {}
  ): Promise<void> {
    const { retries = maxRetries, showError = true, force = false } = options;

    // 如果正在加载且不是强制刷新，则跳过
    if (loading.value && !force) {
      return;
    }

    loading.value = true;
    error.value = null;
    retryCount.value = 0;

    while (retryCount.value <= retries) {
      try {
        const api = sectorType === 'industry'
          ? sectorApi.getIndustrySectors()
          : sectorApi.getConceptSectors();

        const response: SectorListResponse = await api;

        if (sectorType === 'industry') {
          industrySectors.value = response.sectors;
        } else {
          conceptSectors.value = response.sectors;
        }

        lastUpdated.value = response.timestamp;
        loading.value = false;
        return;
      } catch (err) {
        retryCount.value++;
        const errorMsg = getFriendlyErrorMessage(err);

        if (retryCount.value > retries) {
          error.value = errorMsg;
          loading.value = false;
          if (showError) {
            console.error('获取板块列表失败:', err);
          }
          return;
        }

        await delay(1000 * retryCount.value);
      }
    }

    loading.value = false;
  }

  // 加载行业板块
  async function fetchIndustrySectors(options?: FetchOptions): Promise<void> {
    currentType.value = 'industry';
    await fetchSectors('industry', options);
  }

  // 加载概念板块
  async function fetchConceptSectors(options?: FetchOptions): Promise<void> {
    currentType.value = 'concept';
    await fetchSectors('concept', options);
  }

  // 切换板块类型
  async function switchSectorType(type: SectorType): Promise<void> {
    if (currentType.value === type) return;

    currentType.value = type;

    // 如果数据已加载则不重新加载
    if (type === 'industry' && industrySectors.value.length > 0) {
      return;
    }
    if (type === 'concept' && conceptSectors.value.length > 0) {
      return;
    }

    await fetchSectors(type);
  }

  // 刷新数据
  async function refresh(options?: FetchOptions): Promise<void> {
    await fetchSectors(currentType.value, { ...options, force: true });
  }

  // 获取板块详情
  async function fetchSectorDetail(sectorName: string, sectorType: SectorType): Promise<void> {
    if (detailLoading.value) return;

    selectedSector.value = sectorName;
    detailLoading.value = true;
    sectorDetail.value = [];

    try {
      const api = sectorType === 'industry'
        ? sectorApi.getIndustryDetail(sectorName)
        : sectorApi.getConceptDetail(sectorName);

      const response: SectorDetailResponse = await api;
      sectorDetail.value = response.stocks;
    } catch (err) {
      console.error('获取板块详情失败:', err);
      detailError.value = getFriendlyErrorMessage(err);
    } finally {
      detailLoading.value = false;
    }
  }

  // 清除详情
  function clearDetail(): void {
    selectedSector.value = null;
    sectorDetail.value = [];
  }

  // 重试
  function retry(): void {
    error.value = null;
    refresh();
  }

  // ========== WebSocket 实时更新相关 ==========

  /**
   * 更新单个板块数据（用于 WebSocket 实时更新）
   */
  function updateSector(updatedData: WSSectorUpdate) {
    const { name, change, changePercent, stockCount, timestamp } = updatedData;

    // 更新 industrySectors 列表
    const industryIndex = industrySectors.value.findIndex((s) => s.name === name);
    if (industryIndex !== -1) {
      const current = industrySectors.value[industryIndex];
      if (current) {
        industrySectors.value[industryIndex] = {
          ...current,
          change,
          changePercent,
          stockCount: stockCount ?? current.stockCount,
          timestamp: timestamp ?? current.timestamp,
        };
      }
    }

    // 更新 conceptSectors 列表
    const conceptIndex = conceptSectors.value.findIndex((s) => s.name === name);
    if (conceptIndex !== -1) {
      const current = conceptSectors.value[conceptIndex];
      if (current) {
        conceptSectors.value[conceptIndex] = {
          ...current,
          change,
          changePercent,
          stockCount: stockCount ?? current.stockCount,
          timestamp: timestamp ?? current.timestamp,
        };
      }
    }

    // 更新最后更新时间
    lastUpdated.value = formatTime(new Date());

    // 追加到折线图历史（如果有选中该板块）
    if (selectedChartSymbol.value === name && changePercent !== undefined) {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      const history = sectorHistory.value.get(name) || [];
      // 防抖：跳过时间戳相同的重复推送
      const lastPoint = history[history.length - 1];
      if (!lastPoint || lastPoint.time !== timeStr) {
        const newHistory = [...history, { time: timeStr, price: changePercent }];
        if (newHistory.length > MAX_HISTORY_POINTS) {
          newHistory.splice(0, newHistory.length - MAX_HISTORY_POINTS);
        }
        sectorHistory.value.set(name, newHistory);
      }
    }
  }

  /**
   * 批量更新板块数据（用于 WebSocket 批量推送）
   */
  function updateSectorsBatch(updates: WSSectorUpdate[]) {
    for (const update of updates) {
      updateSector(update);
    }
  }

  /**
   * 初始化 WebSocket 连接并订阅板块频道
   */
  function initWebSocket() {
    const wsStore = useWSStore();

    // 监听连接状态
    wsStore.on('connected', () => {
      wsConnected.value = true;
      // 连接成功后订阅板块频道
      wsStore.subscribe('sectors');
      wsSubscribed.value = true;
    });

    wsStore.on('disconnected', () => {
      wsConnected.value = false;
      wsSubscribed.value = false;
    });

    // 监听板块更新消息
    wsStore.on('sector_update', (data: unknown) => {
      console.log('[SectorStore] 收到 sector_update:', JSON.stringify(data)?.substring(0, 200));
      try {
        // 后端推送格式: { industry: [...], concept: [...] }
        const payload = data as { industry?: WSSectorUpdate[]; concept?: WSSectorUpdate[] };
        if (payload.industry || payload.concept) {
          const updates: WSSectorUpdate[] = [];
          if (payload.industry) updates.push(...payload.industry);
          if (payload.concept) updates.push(...payload.concept);
          updateSectorsBatch(updates);
        } else {
          // 兼容旧格式：直接是数组或单个对象
          const update = data as WSSectorUpdate | WSSectorUpdate[];
          if (Array.isArray(update)) {
            updateSectorsBatch(update);
          } else {
            updateSector(update);
          }
        }
      } catch (e) {
        console.error('[SectorStore] 处理 WebSocket 消息失败:', e);
      }
    });

    // 如果已经连接，直接订阅
    if (wsStore.isConnected) {
      wsConnected.value = true;
      wsStore.subscribe('sectors');
      wsSubscribed.value = true;
    }
  }

  /**
   * 取消 WebSocket 订阅
   */
  function unsubscribeWebSocket() {
    const wsStore = useWSStore();
    wsStore.unsubscribe('sectors');
    wsSubscribed.value = false;
  }

  return {
    // State
    industrySectors,
    conceptSectors,
    currentType,
    loading,
    error,
    lastUpdated,
    selectedSector,
    sectorDetail,
    detailLoading,
    detailError,
    // WebSocket State
    wsConnected,
    wsSubscribed,
    // 折线图 State
    sectorHistory,
    selectedChartSymbol,

    // Getters
    currentSectors,
    risingSectors,
    fallingSectors,
    sortedSectors,
    selectedChartHistory,

    // Actions
    fetchIndustrySectors,
    fetchConceptSectors,
    switchSectorType,
    refresh,
    fetchSectorDetail,
    clearDetail,
    retry,
    // 折线图 Actions
    selectChartSymbol,
    // WebSocket Actions
    initWebSocket,
    unsubscribeWebSocket,
    updateSector,
    updateSectorsBatch,
  };
});
