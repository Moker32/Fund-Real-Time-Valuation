import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { commodityApi } from '@/api';
import type { Commodity, CommodityCategory, CommodityCategoryItem, CommodityHistoryItem } from '@/types';
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
  '商品不存在': '未找到指定的商品信息',
  'NETWORK_ERROR': '网络连接失败，请检查网络设置',
  '请求参数验证失败': '请求参数错误，请检查输入',
  'Internal Server Error': '服务器暂时繁忙，请稍后重试',
  'timeout': '请求超时，请检查网络连接',
  '503': '商品服务暂时不可用',
};

// 分类图标映射
const categoryIcons: Record<string, string> = {
  'precious_metal': 'diamond',
  'energy': 'flame',
  'base_metal': 'cube',
};

export const useCommodityStore = defineStore('commodities', () => {
  // State
  const commodities = ref<Commodity[]>([]);
  const categories = ref<CommodityCategory[]>([]);
  const activeCategory = ref<string | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdated = ref<string | null>(null);
  const retryCount = ref(0);
  const maxRetries = 2;

  // Getters
  const risingCommodities = computed(() =>
    commodities.value.filter((c) => c.changePercent > 0)
  );

  const fallingCommodities = computed(() =>
    commodities.value.filter((c) => c.changePercent < 0)
  );

  const goldCommodities = computed(() =>
    commodities.value.filter((c) =>
      c.symbol.toLowerCase().includes('gold') ||
      c.symbol.toLowerCase().includes('xau') ||
      c.name.includes('黄金')
    )
  );

  const oilCommodities = computed(() =>
    commodities.value.filter((c) =>
      c.symbol.toLowerCase().includes('oil') ||
      c.symbol.toLowerCase().includes('wti') ||
      c.name.includes('原油')
    )
  );

  // 获取当前选中的分类数据
  const activeCategoryData = computed(() => {
    if (!activeCategory.value) {
      return null;
    }
    return categories.value.find(c => c.id === activeCategory.value) || null;
  });

  // 获取当前选中分类的商品列表
  const activeCommodities = computed(() => {
    if (!activeCategory.value) {
      return commodities.value;
    }
    const category = categories.value.find(c => c.id === activeCategory.value);
    return category?.commodities || [];
  });

  // 获取分类列表（用于Tab显示）
  const categoryList = computed(() => {
    return categories.value.map(c => ({
      id: c.id,
      name: c.name,
      icon: c.icon,
    }));
  });

  // 预处理 API 响应中的 commodities 字段
  function processApiCommodities(apiCommodities: CommodityCategoryItem[]): Commodity[] {
    return apiCommodities.map(item => ({
      symbol: item.symbol,
      name: item.name,
      price: item.price,
      currency: item.currency,
      change: item.change ?? 0,
      changePercent: item.changePercent,
      high: item.high ?? 0,
      low: item.low ?? 0,
      open: item.open ?? 0,
      prevClose: item.prevClose ?? 0,
      source: item.source,
      timestamp: item.timestamp,
    }));
  }

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
      return friendlyErrorMessages[err.message] || err.message || '获取商品列表失败';
    }
    return '获取商品列表失败';
  }

  // Actions
  async function fetchCommodities(options: FetchOptions = DEFAULT_OPTIONS) {
    const { retries, retryDelay, showError } = { ...DEFAULT_OPTIONS, ...options };
    loading.value = true;
    error.value = null;
    retryCount.value = 0;

    let lastError: unknown;

    for (let attempt = 0; attempt <= retries; attempt++) {
      retryCount.value = attempt;
      try {
        const response = await commodityApi.getCommodities();
        commodities.value = response.commodities || [];
        lastUpdated.value = new Date().toLocaleTimeString('zh-CN');
        return; // 成功，退出函数
      } catch (err) {
        lastError = err;
        console.error(`[CommodityStore] fetchCommodities attempt ${attempt + 1} error:`, err);

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
      console.error('[CommodityStore] fetchCommodities failed after retries:', error.value);
    }
    loading.value = false;
  }

  // 获取分类列表
  async function fetchCategories(options: FetchOptions = DEFAULT_OPTIONS) {
    const { retries, retryDelay, showError } = { ...DEFAULT_OPTIONS, ...options };
    loading.value = true;
    error.value = null;
    retryCount.value = 0;

    let lastError: unknown;

    for (let attempt = 0; attempt <= retries; attempt++) {
      retryCount.value = attempt;
      try {
        const response = await commodityApi.getCategories();
        categories.value = response.categories || [];
        // 如果还没有激活的分类，默认选中第一个有数据的分类
        if (!activeCategory.value && categories.value.length > 0) {
          const firstWithData = categories.value.find(c => c.commodities.length > 0);
          activeCategory.value = firstWithData?.id || categories.value[0].id;
        }
        lastUpdated.value = new Date().toLocaleTimeString('zh-CN');

        // 同时更新 commodities 以保持向后兼容
        const flatCommodities: Commodity[] = [];
        for (const category of categories.value) {
          flatCommodities.push(...processApiCommodities(category.commodities));
        }
        commodities.value = flatCommodities;

        return;
      } catch (err) {
        lastError = err;
        console.error(`[CommodityStore] fetchCategories attempt ${attempt + 1} error:`, err);

        if (attempt < retries && !(err instanceof ApiError && err.statusCode === 404)) {
          await delay(retryDelay * (attempt + 1));
          continue;
        }
        break;
      }
    }

    error.value = getFriendlyErrorMessage(lastError);
    if (showError) {
      console.error('[CommodityStore] fetchCategories failed after retries:', error.value);
    }
    loading.value = false;
  }

  // 设置当前选中的分类
  function setActiveCategory(categoryId: string) {
    activeCategory.value = categoryId;
  }

  // 获取商品历史数据
  async function fetchHistory(
    commodityType: string,
    days: number = 30
  ): Promise<CommodityHistoryItem[]> {
    try {
      const response = await commodityApi.getHistory(commodityType, days);
      return response.history || [];
    } catch (err) {
      console.error(`[CommodityStore] fetchHistory error for ${commodityType}:`, err);
      return [];
    }
  }

  async function fetchGoldCNY(options: FetchOptions = {}) {
    const { retries = 1, retryDelay = 500, showError = false } = options;

    let lastError: unknown;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const gold = await commodityApi.getGoldCNY();
        const index = commodities.value.findIndex((c) => c.symbol === 'GOLD_CNY');
        if (index !== -1 && gold.symbol) {
          commodities.value[index] = {
            symbol: gold.symbol,
            name: gold.name,
            price: gold.price,
            currency: 'CNY',
            change: gold.change,
            changePercent: gold.changePercent,
            high: commodities.value[index]?.high ?? gold.price,
            low: commodities.value[index]?.low ?? gold.price,
            open: commodities.value[index]?.open ?? gold.price,
            prevClose: commodities.value[index]?.prevClose ?? gold.price,
            source: commodities.value[index]?.source || 'akshare',
            timestamp: gold.timestamp,
          };
        } else {
          const newCommodity: Commodity = {
            symbol: gold.symbol || 'GOLD_CNY',
            name: gold.name || '黄金 (CNY)',
            price: gold.price,
            currency: 'CNY',
            change: gold.change,
            changePercent: gold.changePercent,
            high: gold.price,
            low: gold.price,
            open: gold.price,
            prevClose: gold.price,
            source: 'akshare',
            timestamp: gold.timestamp,
          };
          commodities.value.push(newCommodity);
        }
        return; // 成功，退出函数
      } catch (err) {
        lastError = err;
        console.error(`[CommodityStore] fetchGoldCNY attempt ${attempt + 1} error:`, err);

        if (attempt < retries) {
          await delay(retryDelay * (attempt + 1));
          continue;
        }
        break;
      }
    }

    if (showError) {
      error.value = getFriendlyErrorMessage(lastError);
    }
  }

  async function fetchOilWTI(options: FetchOptions = {}) {
    const { retries = 1, retryDelay = 500, showError = false } = options;

    let lastError: unknown;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const oil = await commodityApi.getOilWTI();
        const index = commodities.value.findIndex((c) => c.symbol === 'OIL_WTI');
        if (index !== -1 && oil.symbol) {
          commodities.value[index] = {
            symbol: oil.symbol,
            name: oil.name,
            price: oil.price,
            currency: 'USD',
            change: oil.change,
            changePercent: oil.changePercent,
            high: commodities.value[index]?.high ?? oil.price,
            low: commodities.value[index]?.low ?? oil.price,
            open: commodities.value[index]?.open ?? oil.price,
            prevClose: commodities.value[index]?.prevClose ?? oil.price,
            source: commodities.value[index]?.source || 'akshare',
            timestamp: oil.timestamp,
          };
        } else {
          const newCommodity: Commodity = {
            symbol: oil.symbol || 'OIL_WTI',
            name: oil.name || 'WTI 原油',
            price: oil.price,
            currency: 'USD',
            change: oil.change,
            changePercent: oil.changePercent,
            high: oil.price,
            low: oil.price,
            open: oil.price,
            prevClose: oil.price,
            source: 'akshare',
            timestamp: oil.timestamp,
          };
          commodities.value.push(newCommodity);
        }
        return; // 成功，退出函数
      } catch (err) {
        lastError = err;
        console.error(`[CommodityStore] fetchOilWTI attempt ${attempt + 1} error:`, err);

        if (attempt < retries) {
          await delay(retryDelay * (attempt + 1));
          continue;
        }
        break;
      }
    }

    if (showError) {
      error.value = getFriendlyErrorMessage(lastError);
    }
  }

  function clearError() {
    error.value = null;
  }

  // 重试函数
  async function retry() {
    await fetchCategories();
  }

  return {
    // State
    commodities,
    categories,
    activeCategory,
    loading,
    error,
    lastUpdated,
    retryCount,
    maxRetries,
    // Getters
    risingCommodities,
    fallingCommodities,
    goldCommodities,
    oilCommodities,
    activeCategoryData,
    activeCommodities,
    categoryList,
    // Actions
    fetchCommodities,
    fetchCategories,
    setActiveCategory,
    fetchHistory,
    fetchGoldCNY,
    fetchOilWTI,
    clearError,
    retry,
  };
});
