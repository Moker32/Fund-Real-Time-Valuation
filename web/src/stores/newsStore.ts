import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { newsApi } from '@/api';
import type { NewsItem, NewsCategory, FetchOptions } from '@/types';
import { ApiError } from '@/api';

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const friendlyErrorMessages: Record<string, string> = {
  'NETWORK_ERROR': '网络连接失败，请检查网络设置',
  '请求参数验证失败': '请求参数错误，请检查输入',
  'Internal Server Error': '服务器暂时繁忙，请稍后重试',
  'timeout': '请求超时，请检查网络连接',
  '503': '新闻服务暂时不可用',
};

export const useNewsStore = defineStore('news', () => {
  const news = ref<NewsItem[]>([]);
  const categories = ref<NewsCategory[]>([]);
  const activeCategory = ref('finance');
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastUpdated = ref<string | null>(null);
  const retryCount = ref(0);
  const maxRetries = 2;

  function getFriendlyErrorMessage(err: unknown): string {
    if (err instanceof ApiError) {
      return friendlyErrorMessages[err.message] || err.message || '获取新闻失败';
    }
    if (err instanceof Error) {
      return friendlyErrorMessages[err.message] || err.message || '获取新闻失败';
    }
    return '获取新闻失败';
  }

  async function fetchNews(options: FetchOptions = {}) {
    const retries = options.retries ?? maxRetries;
    const retryDelay = options.retryDelay ?? 1000;
    const showError = options.showError ?? true;
    const force = options.force ?? false;

    const hasExistingData = news.value.length > 0;
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
        const response = await newsApi.getNews(activeCategory.value);
        news.value = response.news || [];
        lastUpdated.value = new Date().toLocaleTimeString();
        return;
      } catch (err) {
        lastError = err;
        console.error(`[NewsStore] fetchNews attempt ${attempt + 1} error:`, err);

        if (attempt < retries && !(err instanceof ApiError && err.statusCode === 404)) {
          await delay(retryDelay * (attempt + 1));
          continue;
        }
        break;
      }
    }

    error.value = getFriendlyErrorMessage(lastError);
    if (showError) {
      console.error('[NewsStore] fetchNews failed after retries:', error.value);
    }
    loading.value = false;
  }

  async function fetchCategories() {
    try {
      const response = await newsApi.getCategories();
      categories.value = response.categories || [];
    } catch (err) {
      console.error('[NewsStore] fetchCategories error:', err);
      categories.value = [
        { id: 'finance', name: '财经要闻', icon: '📰' },
        { id: 'stock', name: '股票新闻', icon: '📈' },
        { id: 'fund', name: '基金新闻', icon: '💰' },
        { id: 'economy', name: '宏观经济', icon: '🏛️' },
        { id: 'global', name: '全球市场', icon: '🌍' },
        { id: 'commodity', name: '大宗商品', icon: '🛢️' },
      ];
    }
  }

  async function setCategory(category: string) {
    if (activeCategory.value !== category) {
      activeCategory.value = category;
      await fetchNews({ force: true });
    }
  }

  async function retry() {
    await fetchNews();
  }

  return {
    news,
    categories,
    activeCategory,
    loading,
    error,
    lastUpdated,
    retryCount,
    fetchNews,
    fetchCategories,
    setCategory,
    retry,
  };
});
