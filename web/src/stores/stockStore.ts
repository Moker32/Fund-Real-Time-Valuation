import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { stockApi } from '@/api';
import type { Stock } from '@/types';

const STORAGE_KEY = 'stock-watchlist';

export const useStockStore = defineStore('stocks', () => {
  // State
  const stocks = ref<Stock[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdated = ref<string | null>(null);
  
  // 从 localStorage 读取自选股列表
  function loadWatchlist(): string[] {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.error('[StockStore] Failed to load watchlist:', e);
    }
    // 默认自选股
    return ['sh600519', 'sh000001', 'sz300750', 'AAPL', 'MSFT'];
  }

  const watchlist = ref<string[]>(loadWatchlist());

  // 保存到 localStorage
  function saveWatchlist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist.value));
    } catch (e) {
      console.error('[StockStore] Failed to save watchlist:', e);
    }
  }

  // Getters
  const risingStocks = computed(() =>
    stocks.value.filter((s) => s.change_pct > 0)
  );

  const fallingStocks = computed(() =>
    stocks.value.filter((s) => s.change_pct < 0)
  );

  const topGainers = computed(() =>
    [...stocks.value].sort((a, b) => b.change_pct - a.change_pct).slice(0, 5)
  );

  const topLosers = computed(() =>
    [...stocks.value].sort((a, b) => a.change_pct - b.change_pct).slice(0, 5)
  );

  // Actions
  async function fetchStocks() {
    if (watchlist.value.length === 0) {
      stocks.value = [];
      return;
    }

    loading.value = true;
    error.value = null;

    try {
      const data = await stockApi.getStocks(watchlist.value.join(','));
      stocks.value = data;
      lastUpdated.value = new Date().toISOString();
    } catch (e) {
      error.value = e instanceof Error ? e.message : '获取股票数据失败';
      console.error('[StockStore] Fetch error:', e);
    } finally {
      loading.value = false;
    }
  }

  function addToWatchlist(code: string) {
    const upperCode = code.toUpperCase();
    if (!watchlist.value.includes(upperCode)) {
      watchlist.value.push(upperCode);
      saveWatchlist();
    }
  }

  function removeFromWatchlist(code: string) {
    const upperCode = code.toUpperCase();
    const index = watchlist.value.indexOf(upperCode);
    if (index > -1) {
      watchlist.value.splice(index, 1);
      saveWatchlist();
      // 同时从列表中移除
      stocks.value = stocks.value.filter((s) => s.code.toUpperCase() !== upperCode);
    }
  }

  return {
    // State
    stocks,
    loading,
    error,
    lastUpdated,
    watchlist,
    // Getters
    risingStocks,
    fallingStocks,
    topGainers,
    topLosers,
    // Actions
    fetchStocks,
    addToWatchlist,
    removeFromWatchlist,
  };
});
