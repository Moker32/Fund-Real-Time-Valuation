import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { sectorApi } from '@/api';
import type { Sector, SectorStock, SectorListResponse, SectorDetailResponse } from '@/types';
import { ApiError } from '@/api';

export interface FetchOptions {
  retries?: number;
  retryDelay?: number;
  showError?: boolean;
  force?: boolean;
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

    // Getters
    currentSectors,
    risingSectors,
    fallingSectors,
    sortedSectors,

    // Actions
    fetchIndustrySectors,
    fetchConceptSectors,
    switchSectorType,
    refresh,
    fetchSectorDetail,
    clearDetail,
    retry,
  };
});
