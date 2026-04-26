import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { commodityApi } from '@/api';
import type { Commodity, CommodityCategory, CommodityCategoryItem, CommodityHistoryItem, CommoditySearchResult } from '@/types';
import { ApiError } from '@/api';
import { formatTime } from '@/utils/time';
import { useWSStore } from './wsStore';

// WebSocket 商品更新数据类型
interface WSCommodityUpdate {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  timestamp: string;
  high?: number;
  low?: number;
  open?: number;
  prevClose?: number;
}

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
  const categories = ref<CommodityCategory[]>([]);
  const activeCategory = ref<string | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdated = ref<string | null>(null);
  const retryCount = ref(0);
  const maxRetries = 2;

  // WebSocket 相关状态
  const wsConnected = ref(false);
  const wsSubscribed = ref(false);

  // 折线图历史数据（用于 streaming 实时绘制）
  const commodityHistory = ref<Map<string, { time: string; price: number }[]>>(new Map());
  // 当前选中显示折线图的商品
  const selectedChartSymbol = ref<string | null>(null);
  const MAX_HISTORY_POINTS = 500;

  // 日内分时数据（从后端 API 获取的完整日数据）
  const commodityIntraday = ref<Record<string, { time: string; price: number }[]>>({});
  // 版本计数器，确保 Pinia 解包 ref<Record> 后 computed 能正确追踪更新
  const intradayVersion = ref(0);

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

  // 获取当前选中的折线图历史数据
  const selectedChartHistory = computed(() => {
    if (!selectedChartSymbol.value) return [];
    return commodityHistory.value.get(selectedChartSymbol.value) || [];
  });

  // 获取指定商品的日内分时数据
  function getCommodityIntraday(commodityType: string) {
    return commodityIntraday.value[commodityType] || [];
  }

  // 选中折线图商品
  function selectChartSymbol(symbol: string | null) {
    if (symbol === null) {
      selectedChartSymbol.value = null;
      return;
    }
    selectedChartSymbol.value = symbol;
    // 如果还没有该商品的历史，先初始化当前价格
    if (!commodityHistory.value.has(symbol)) {
      const commodity = commodities.value.find(c => c.symbol === symbol);
      if (commodity) {
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        commodityHistory.value.set(symbol, [{ time: timeStr, price: commodity.price }]);
      }
    }
  }

  // 获取当前选中的分类数据
  const activeCategoryData = computed(() => {
    if (!activeCategory.value) {
      return null;
    }
    return categories.value.find(c => c.id === activeCategory.value) || null;
  });

  // 获取当前选中分类的商品列表
  const activeCommodities = computed((): Commodity[] => {
    if (activeCategory.value) {
      const category = categories.value.find(c => c.id === activeCategory.value);
      if (category) {
        return processApiCommodities(category.commodities);
      }
      return [];
    }
    return commodities.value;
  });

  // 获取分类列表（用于Tab显示）
  const categoryList = computed(() => {
    return categories.value.map(c => ({
      id: c.id,
      name: c.name,
      icon: c.icon,
    }));
  });

  // 获取所有分类中的商品（用于统计）
  const allCategoryCommodities = computed(() => {
    const all: Commodity[] = [];
    for (const category of categories.value) {
      for (const item of category.commodities) {
        // 避免重复添加相同 symbol 的商品
        if (!all.some(c => c.symbol === item.symbol)) {
          all.push({
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
          });
        }
      }
    }
    return all;
  });

  // 基于分类数据的涨跌统计
  const categoryRisingCount = computed(() =>
    allCategoryCommodities.value.filter((c) => c.changePercent > 0).length
  );

  const categoryFallingCount = computed(() =>
    allCategoryCommodities.value.filter((c) => c.changePercent < 0).length
  );

  const categoryNeutralCount = computed(() =>
    allCategoryCommodities.value.filter((c) => c.changePercent === 0).length
  );

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

  // 获取商品日内分时数据
  async function fetchCommodityIntraday(commodityType: string) {
    try {
      const response = await commodityApi.getIntraday(commodityType);
      if (response.data && response.data.length > 0) {
        commodityIntraday.value[commodityType] = response.data;
        intradayVersion.value++;
      }
      return response.data || [];
    } catch (err) {
      console.warn(`[CommodityStore] fetchIntraday error for ${commodityType}:`, err);
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

  // ========== 搜索相关 ==========

  // State - 搜索相关
  const searchQuery = ref('');
  const searchResults = ref<CommoditySearchResult[]>([]);
  const searchLoading = ref(false);
  const searchError = ref<string | null>(null);
  const lastSearchQuery = ref('');

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

  // 清除搜索错误
  function clearSearchError() {
    searchError.value = null;
  }

  // ========== WebSocket 实时更新相关 ==========

  /**
   * 更新单个商品数据（用于 WebSocket 实时更新）
   */
  function updateCommodity(updatedData: WSCommodityUpdate) {
    const { symbol, price, change, changePercent, timestamp, high, low, open, prevClose } = updatedData;

    // 更新 commodities 列表
    const index = commodities.value.findIndex((c) => c.symbol === symbol);
    if (index !== -1) {
      const current = commodities.value[index];
      if (current) {
        commodities.value[index] = {
          symbol: current.symbol,
          name: current.name,
          currency: current.currency,
          price,
          change,
          changePercent,
          timestamp,
          high: high ?? current.high,
          low: low ?? current.low,
          open: open ?? current.open,
          prevClose: prevClose ?? current.prevClose,
          source: current.source,
        };
      }
    }

    // 更新 categories 中的商品数据
    for (const category of categories.value) {
      const commodityIndex = category.commodities.findIndex((c) => c.symbol === symbol);
      if (commodityIndex !== -1) {
        const current = category.commodities[commodityIndex];
        if (current) {
          category.commodities[commodityIndex] = {
            symbol: current.symbol,
            name: current.name,
            currency: current.currency,
            price,
            change,
            changePercent,
            timestamp,
            high: high ?? current.high,
            low: low ?? current.low,
            open: open ?? current.open,
            prevClose: prevClose ?? current.prevClose,
            source: current.source,
          };
        }
        break; // 找到并更新后退出
      }
    }

    // 更新最后更新时间
    lastUpdated.value = formatTime(new Date());

    // 追加到折线图历史（如果有选中该商品）
    if (selectedChartSymbol.value === symbol && price !== undefined) {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      const history = commodityHistory.value.get(symbol) || [];
      // 防抖：跳过时间戳相同的重复推送
      const lastPoint = history[history.length - 1];
      if (!lastPoint || lastPoint.time !== timeStr) {
        const newHistory = [...history, { time: timeStr, price }];
        if (newHistory.length > MAX_HISTORY_POINTS) {
          newHistory.splice(0, newHistory.length - MAX_HISTORY_POINTS);
        }
        commodityHistory.value.set(symbol, newHistory);
      }
    }
  }

  /**
   * 批量更新商品数据（用于 WebSocket 批量推送）
   */
  function updateCommoditiesBatch(updates: WSCommodityUpdate[]) {
    for (const update of updates) {
      updateCommodity(update);
    }
  }

  /**
   * 初始化 WebSocket 连接并订阅大宗商品频道
   */
  function initWebSocket() {
    const wsStore = useWSStore();

    // 监听连接状态
    wsStore.on('connected', () => {
      wsConnected.value = true;
      // 连接成功后订阅大宗商品频道
      wsStore.subscribe('commodities');
      wsSubscribed.value = true;
    });

    wsStore.on('disconnected', () => {
      wsConnected.value = false;
      wsSubscribed.value = false;
    });

    // 监听大宗商品更新消息
    wsStore.on('commodity_update', (data: unknown) => {
      try {
        // 修复: 后端发送 { commodities: [...] }，需解包
        const payload = data as { commodities?: WSCommodityUpdate[] };
        const updates = payload.commodities;
        if (updates && Array.isArray(updates) && updates.length > 0) {
          updateCommoditiesBatch(updates);
        }
      } catch (e) {
        console.error('[CommodityStore] 处理 WebSocket 消息失败:', e);
      }
    });

    // 如果已经连接，直接订阅
    if (wsStore.isConnected) {
      wsConnected.value = true;
      wsStore.subscribe('commodities');
      wsSubscribed.value = true;
    }
  }

  /**
   * 取消 WebSocket 订阅
   */
  function unsubscribeWebSocket() {
    const wsStore = useWSStore();
    wsStore.unsubscribe('commodities');
    wsSubscribed.value = false;
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
    // WebSocket State
    wsConnected,
    wsSubscribed,
    // 折线图 State
    commodityHistory,
    selectedChartSymbol,
    selectedChartHistory,
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
    // 分类数据统计
    allCategoryCommodities,
    categoryRisingCount,
    categoryFallingCount,
    categoryNeutralCount,
    // Actions
    fetchCommodities,
    fetchCategories,
    setActiveCategory,
    fetchHistory,
    fetchGoldCNY,
    fetchOilWTI,
    clearError,
    retry,
    // 搜索 Actions
    searchCommodities,
    executeSearch,
    clearSearch,
    fetchAvailableCommodities,
    clearSearchError,
    // WebSocket Actions
    updateCommodity,
    updateCommoditiesBatch,
    initWebSocket,
    unsubscribeWebSocket,
    // 折线图 Actions
    selectChartSymbol,
    // 日内分时 Actions
    commodityIntraday,
    intradayVersion,
    fetchCommodityIntraday,
    getCommodityIntraday,
  };
}, {
  persist: {
    key: 'commodity-store',
    pick: ['activeCategory'],
  },
});
