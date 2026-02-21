import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { commodityApi } from '@/api';
import type { Commodity, CommodityCategory, CommodityCategoryItem, CommodityHistoryItem, WatchedCommodity, CommoditySearchResult } from '@/types';
import { ApiError } from '@/api';
import { formatTime } from '@/utils/time';
import { getCommodityName } from '@/utils/commodityNames';

// 防抖函数（支持异步函数返回 Promise）
function debounce<T extends (...args: Parameters<T>) => ReturnType<T>>(
  func: T,
  wait: number
): (...args: Parameters<T>) => Promise<Awaited<ReturnType<T>>> {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    return new Promise<Awaited<ReturnType<T>>>((resolve) => {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => {
        const result = func(...args);
        if (result instanceof Promise) {
          result.then(resolve);
        } else {
          resolve(result as Awaited<ReturnType<T>>);
        }
      }, wait);
    });
  };
}

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
  '商品不存在': '未找到指定的商品信息',
  'NETWORK_ERROR': '网络连接失败，请检查网络设置',
  '请求参数验证失败': '请求参数错误，请检查输入',
  'Internal Server Error': '服务器暂时繁忙，请稍后重试',
  'timeout': '请求超时，请检查网络连接',
  '503': '商品服务暂时不可用',
};

export const useCommodityStore = defineStore('commodities', () => {
  // State
  const commodities = ref<Commodity[]>([]);
  const watchedCommodityData = ref<Commodity[]>([]);  // 关注商品的实际行情数据
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

  // 获取当前选中分类的商品列表（包含关注列表 + 行情数据）
  const activeCommodities = computed(() => {
    // 如果是"我的关注"分类，返回关注商品的实际数据
    if (activeCategory.value === 'watched') {
      return watchedCommodities.value
        .map(watched => {
          const marketData = watchedCommodityData.value.find(c => c.symbol === watched.symbol);
          return marketData || {
            symbol: watched.symbol,
            name: watched.name,
            category: watched.category,
            price: undefined,
            change: undefined,
            changePercent: undefined,
            prevClose: undefined,
            time: undefined,
          };
        });
    }

    // 其他分类：从 categories 获取
    if (activeCategory.value) {
      const category = categories.value.find(c => c.id === activeCategory.value);
      return category?.commodities || [];
    }

    // 没有选中分类时，返回所有行情数据
    return commodities.value;
  });

  // 获取分类列表（用于Tab显示，包含"我的关注"）
  const categoryList = computed(() => {
    const list = categories.value.map(c => ({
      id: c.id,
      name: c.name,
      icon: c.icon,
    }));

    // 如果有关注商品，添加"我的关注"分类
    if (watchedCommodities.value.length > 0) {
      list.unshift({
        id: 'watched',
        name: '我的关注',
        icon: '⭐',
      });
    }

    return list;
  });

  // 预处理 API 响应中的 commodities 字段
  function processApiCommodities(apiCommodities: CommodityCategoryItem[]): Commodity[] {
    return apiCommodities.map(item => ({
      symbol: item.symbol,
      name: item.name,
      price: item.price,
      currency: item.currency,
      change: item.change ?? 0,
      changePercent: item.changePercent ?? 0,
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
        return friendlyErrorMessages[err.code] as string;
      }
      return err.message || '获取商品列表失败';
    }
    if (err instanceof Error) {
      return friendlyErrorMessages[err.message] || err.message || '获取商品列表失败';
    }
    return '获取商品列表失败';
  }

  // Actions
  async function fetchCommodities(options: FetchOptions = {}) {
    const retries = options.retries ?? 2;
    const retryDelay = options.retryDelay ?? 1000;
    const showError = options.showError ?? true;
    loading.value = true;
    error.value = null;
    retryCount.value = 0;

    let lastError: unknown;

    for (let attempt = 0; attempt <= retries; attempt++) {
      retryCount.value = attempt;
      try {
        const response = await commodityApi.getCommodities();
        commodities.value = response.commodities || [];
        lastUpdated.value = formatTime(new Date());
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
  async function fetchCategories(options: FetchOptions = {}) {
    const retries = options.retries ?? 2;
    const retryDelay = options.retryDelay ?? 1000;
    const showError = options.showError ?? true;
    const force = options.force ?? false;

    // 如果已有数据且不是强制刷新，不显示 loading
    const hasExistingData = categories.value.length > 0;
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
        const response = await commodityApi.getCategories();
        categories.value = response.categories || [];
        // 如果还没有激活的分类，默认选中第一个有数据的分类
        if (!activeCategory.value && categories.value.length > 0) {
          const firstWithData = categories.value.find(c => c.commodities.length > 0);
          activeCategory.value = firstWithData?.id || categories.value[0]?.id || null;
        }
        lastUpdated.value = formatTime(new Date());

        // 同时更新 commodities 以保持向后兼容
        const flatCommodities: Commodity[] = [];
        for (const category of categories.value) {
          flatCommodities.push(...processApiCommodities(category.commodities));
        }
        commodities.value = flatCommodities;

        loading.value = false;
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
      error.value = getFriendlyErrorMessage(err);
      throw err; // 抛出异常，让调用者能够区分"无数据"和"获取失败"
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

  // ========== 关注列表相关 ==========

  // State - 关注列表
  const watchedCommodities = ref<WatchedCommodity[]>([]);
  const watchlistLoading = ref(false);
  const watchlistError = ref<string | null>(null);

  // 搜索相关
  const searchQuery = ref('');
  const searchResults = ref<CommoditySearchResult[]>([]);
  const searchLoading = ref(false);
  const searchError = ref<string | null>(null);
  const lastSearchQuery = ref('');

  // Getters - 关注列表按分类分组
  const watchedByCategory = computed(() => {
    const grouped: Record<string, WatchedCommodity[]> = {};
    for (const item of watchedCommodities.value) {
      const category = item.category || 'other';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(item);
    }
    return grouped;
  });

  // 关注的分类列表
  const watchedCategories = computed(() => {
    return Object.keys(watchedByCategory.value);
  });

  // 获取某个分类的关注商品
  function getWatchedByCategory(category: string): WatchedCommodity[] {
    return watchedByCategory.value[category] || [];
  }

  // Actions - 关注列表

  // 获取关注列表
  async function fetchWatchedCommodities(options: FetchOptions = {}) {
    const { showError = true } = options;
    watchlistLoading.value = true;
    watchlistError.value = null;

    try {
      const response = await commodityApi.getWatchlist();
      watchedCommodities.value = response.watchlist || [];

      const fetchPromises = watchedCommodities.value.map(async (watched) => {
        try {
          let data: any;
          if (watched.symbol.toUpperCase() === 'AU99.99' || watched.symbol.toLowerCase() === 'sg=f') {
            data = await commodityApi.getGoldCNY();
          } else {
            data = await commodityApi.getCommodityByTicker(watched.symbol);
          }
          return {
            symbol: data.symbol,
            name: getCommodityName(data.symbol, data.name),
            price: data.price,
            currency: data.currency,
            change: data.change ?? data.change_percent ? (data.price * data.change_percent / 100) : 0,
            changePercent: data.change_percent ?? 0,
            high: data.high ?? 0,
            low: data.low ?? 0,
            open: data.open ?? 0,
            prevClose: data.prev_close ?? 0,
            source: data.source,
            timestamp: data.time ?? data.timestamp,
          } as Commodity;
        } catch (e) {
          console.warn(`[CommodityStore] Failed to fetch ${watched.symbol}:`, e);
          return null;
        }
      });

      const results = await Promise.all(fetchPromises);
      watchedCommodityData.value = results.filter((r): r is Commodity => r !== null);

      // 如果有关注的商品且当前没有选中分类，默认选中"我的关注"
      if (watchedCommodities.value.length > 0 && !activeCategory.value) {
        activeCategory.value = 'watched';
      }
    } catch (err) {
      watchlistError.value = getFriendlyErrorMessage(err);
      if (showError) {
        console.error('[CommodityStore] fetchWatchedCommodities error:', err);
      }
    } finally {
      watchlistLoading.value = false;
    }
  }

  // 添加关注
  async function addToWatchlist(
    symbol: string,
    name: string,
    category?: string
  ): Promise<boolean> {
    try {
      const response = await commodityApi.addToWatchlist({ symbol, name, category });
      if (response.success) {
        // 刷新关注列表
        await fetchWatchedCommodities({ showError: false });
        return true;
      }
      watchlistError.value = response.message;
      return false;
    } catch (err) {
      watchlistError.value = getFriendlyErrorMessage(err);
      console.error('[CommodityStore] addToWatchlist error:', err);
      return false;
    }
  }

  // 移除关注
  async function removeFromWatchlist(symbol: string): Promise<boolean> {
    try {
      const response = await commodityApi.removeFromWatchlist(symbol);
      if (response.success) {
        // 刷新关注列表
        await fetchWatchedCommodities({ showError: false });
        return true;
      }
      watchlistError.value = response.message;
      return false;
    } catch (err) {
      watchlistError.value = getFriendlyErrorMessage(err);
      console.error('[CommodityStore] removeFromWatchlist error:', err);
      return false;
    }
  }

  // 搜索商品
  async function searchCommodities(query: string): Promise<CommoditySearchResult[]> {
    if (!query.trim()) {
      searchResults.value = [];
      return [];
    }

    searchLoading.value = true;
    searchError.value = null;

    try {
      const response = await commodityApi.searchCommodities(query);
      searchResults.value = response.results || [];
      lastSearchQuery.value = query;
      return searchResults.value;
    } catch (err) {
      searchError.value = getFriendlyErrorMessage(err);
      console.error('[CommodityStore] searchCommodities error:', err);
      throw err; // 抛出异常，让调用者能够区分"无结果"和"获取失败"
    } finally {
      searchLoading.value = false;
    }
  }

  // 防抖搜索（支持异步函数）
  const debouncedSearch = debounce(async (query: string) => {
    return await searchCommodities(query);
  }, 300);

  // 执行防抖搜索
  function executeSearch(query: string): Promise<CommoditySearchResult[] | undefined> {
    searchQuery.value = query;
    return debouncedSearch(query);
  }

  // 清除搜索结果
  function clearSearch() {
    searchQuery.value = '';
    searchResults.value = [];
    searchError.value = null;
    lastSearchQuery.value = '';
  }

  // 获取所有可用商品
  async function fetchAvailableCommodities(): Promise<CommoditySearchResult[]> {
    searchLoading.value = true;
    searchError.value = null;

    try {
      const response = await commodityApi.getAvailableCommodities();
      searchResults.value = response.results || [];
      return searchResults.value;
    } catch (err) {
      searchError.value = getFriendlyErrorMessage(err);
      console.error('[CommodityStore] fetchAvailableCommodities error:', err);
      throw err; // 抛出异常，让调用者能够区分"无数据"和"获取失败"
    } finally {
      searchLoading.value = false;
    }
  }

  // 清除关注列表错误
  function clearWatchlistError() {
    watchlistError.value = null;
  }

  // 清除搜索错误
  function clearSearchError() {
    searchError.value = null;
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
    // 关注列表 State
    watchedCommodities,
    watchlistLoading,
    watchlistError,
    // 搜索 State
    searchQuery,
    searchResults,
    searchLoading,
    searchError,
    lastSearchQuery,
    // Getters
    risingCommodities,
    fallingCommodities,
    goldCommodities,
    oilCommodities,
    activeCategoryData,
    activeCommodities,
    categoryList,
    // 关注列表 Getters
    watchedByCategory,
    watchedCategories,
    // Actions
    fetchCommodities,
    fetchCategories,
    setActiveCategory,
    fetchHistory,
    fetchGoldCNY,
    fetchOilWTI,
    clearError,
    retry,
    // 关注列表 Actions
    fetchWatchedCommodities,
    addToWatchlist,
    removeFromWatchlist,
    getWatchedByCategory,
    // 搜索 Actions
    searchCommodities,
    executeSearch,
    clearSearch,
    fetchAvailableCommodities,
    clearWatchlistError,
    clearSearchError,
  };
}, {
  persist: {
    key: 'commodity-store',
    pick: ['activeCategory'],
  },
});
