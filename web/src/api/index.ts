import axios from 'axios';
import type { Fund, Commodity, Overview, HealthStatus, FundHistory, FundIntraday, MarketIndex, IndexListResponse, CommodityCategory, CommodityHistoryItem, WatchedCommodity, WatchlistResponse, CommoditySearchResult, CommoditySearchResponse, AddWatchedCommodityRequest, AddWatchedCommodityResponse, SectorListResponse, SectorDetailResponse } from '@/types';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// 错误码联合类型
export type ApiErrorCode =
  | 'NETWORK_ERROR'
  | 'TIMEOUT'
  | 'VALIDATION_ERROR'
  | 'NOT_FOUND'
  | 'SERVER_ERROR'
  | 'SERVICE_UNAVAILABLE'
  | 'UNKNOWN_ERROR';

// 自定义错误类
export class ApiError extends Error {
  code?: ApiErrorCode;
  detail?: string;
  timestamp?: string;
  statusCode?: number;

  constructor(
    message: string,
    code?: ApiErrorCode,
    detail?: string,
    timestamp?: string,
    statusCode?: number
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.detail = detail;
    this.timestamp = timestamp;
    this.statusCode = statusCode;
  }
}

// 网络错误检测
const isNetworkError = (error: unknown): boolean => {
  const err = error as { isAxiosError?: boolean; response?: { status?: number } };
  if (err.isAxiosError === true) {
    return !err.response?.status;
  }
  return error instanceof Error && (error.message.includes('Network Error') || error.message.includes('ECONNREFUSED'));
};

// 错误消息映射表
const errorMessageMap: Record<string, string> = {
  'Network Error': '网络连接失败，请检查网络设置',
  'ECONNREFUSED': '无法连接到服务器，请确保后端服务已启动',
  'timeout': '请求超时，请稍后重试',
  '500': '服务器内部错误，请稍后重试',
  '502': '服务器网关错误',
  '503': '服务暂时不可用',
  '504': '网关超时',
};

// 获取友好的错误消息
const getFriendlyErrorMessage = (error: { response?: { status?: number; data?: Record<string, unknown> }; message?: string }): string => {
  const statusCode = error.response?.status;
  const responseData = error.response?.data;

  if (responseData?.error && typeof responseData.error === 'string') {
    const detail = responseData.detail && typeof responseData.detail === 'string' ? responseData.detail : '';
    return detail ? `${responseData.error}: ${detail}` : responseData.error;
  }

  if (statusCode) {
    switch (statusCode) {
      case 400:
        return '请求参数错误，请检查输入内容';
      case 401:
        return '未授权访问，请重新登录';
      case 403:
        return '禁止访问';
      case 404:
        return '请求的资源不存在';
      case 422:
        return '请求参数验证失败';
      default:
        return errorMessageMap[String(statusCode)] || `请求失败 (${statusCode})`;
    }
  }

  const errorMsg = error.message || '';
  for (const [key, message] of Object.entries(errorMessageMap)) {
    if (errorMsg.includes(key)) {
      return message;
    }
  }

  return errorMsg || '未知错误，请稍后重试';
};

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,  // 60秒，基金数据获取可能较慢
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    config.params = {
      ...config.params,
      _t: Date.now(),
    };
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response.data,
  (error: unknown) => {
    const err = error as { response?: { status?: number; data?: Record<string, unknown> }; config?: { method?: string; url?: string }; message?: string };

    const responseData = err.response?.data;

    if (responseData && responseData.success === false) {
      const friendlyMessage = getFriendlyErrorMessage(err);
      console.error(`[API Error] ${err.config?.method?.toUpperCase()} ${err.config?.url}:`, {
        error: responseData.error,
        detail: responseData.detail,
        timestamp: responseData.timestamp,
      });

      throw new ApiError(
        friendlyMessage,
        responseData.error as ApiErrorCode,
        responseData.detail as string,
        responseData.timestamp as string,
        err.response?.status
      );
    }

    if (isNetworkError(error)) {
      const friendlyMessage = getFriendlyErrorMessage(err);
      console.error(`[Network Error] ${err.config?.method?.toUpperCase()} ${err.config?.url}:`, err.message);
      throw new ApiError(friendlyMessage, 'NETWORK_ERROR', err.message);
    }

    const friendlyMessage = getFriendlyErrorMessage(err);
    console.error(`[API Error] ${err.config?.method?.toUpperCase()} ${err.config?.url}:`, err.message);
    throw new ApiError(
      friendlyMessage,
      'UNKNOWN_ERROR',
      err.message,
      undefined,
      err.response?.status
    );
  }
);

// API Methods
export const fundApi = {
  async getFunds(): Promise<{ funds: Fund[]; total: number; timestamp: string }> {
    return api.get('/api/funds');
  },

  async getFund(code: string): Promise<Fund> {
    return api.get(`/api/funds/${code}`);
  },

  async getFundEstimate(code: string): Promise<{
    code: string;
    name: string;
    netValue: number;
    estimateValue: number;
    estimateChange: number;
    estimateChangePercent: number;
    timestamp: string;
    estimated_net_value?: number;
    unit_net_value?: number;
  }> {
    return api.get(`/api/funds/${code}/estimate`);
  },

  async getFundHistory(code: string, days: number = 30): Promise<{
    code: string;
    data: FundHistory[];
    count: number;
  }> {
    return api.get(`/api/funds/${code}/history`, { params: { days } });
  },

  async getFundIntraday(code: string): Promise<{
    fund_code: string;
    name: string;
    date: string;
    data: FundIntraday[];
    count: number;
    source: string;
  }> {
    return api.get(`/api/funds/${code}/intraday`);
  },

  async addToWatchlist(code: string, name: string): Promise<{
    success: boolean;
    message: string;
    fund: { code: string; name: string };
  }> {
    return api.post('/api/funds/watchlist', { code, name });
  },

  async removeFromWatchlist(code: string): Promise<{
    success: boolean;
    message: string;
  }> {
    return api.delete(`/api/funds/watchlist/${code}`);
  },

  async toggleHolding(code: string, holding: boolean): Promise<{
    success: boolean;
    message: string;
  }> {
    return api.put(`/api/funds/${code}/holding`, null, { params: { holding } });
  },
};

export const commodityApi = {
  async getCommodities(): Promise<{ commodities: Commodity[]; timestamp: string }> {
    return api.get('/api/commodities');
  },

  async getCommodity(type: string): Promise<Commodity> {
    return api.get(`/api/commodities/${type}`);
  },

  async getCategories(): Promise<{ categories: CommodityCategory[]; timestamp: string }> {
    return api.get('/api/commodities/categories');
  },

  async getHistory(commodityType: string, days: number = 30): Promise<{
    commodity_type: string;
    name: string;
    history: CommodityHistoryItem[];
    timestamp: string;
  }> {
    return api.get(`/api/commodities/history/${commodityType}`, { params: { days } });
  },

  async getGoldCNY(): Promise<{
    symbol: string;
    name: string;
    price: number;
    change: number;
    changePercent: number;
    timestamp: string;
  }> {
    return api.get('/api/commodities/gold/cny');
  },

  async getGoldInternational(): Promise<{
    symbol: string;
    name: string;
    price: number;
    change: number;
    changePercent: number;
    timestamp: string;
  }> {
    return api.get('/api/commodities/gold/international');
  },

  async getOilWTI(): Promise<{
    symbol: string;
    name: string;
    price: number;
    change: number;
    changePercent: number;
    timestamp: string;
  }> {
    return api.get('/api/commodities/oil/wti');
  },

  // 关注列表相关 API
  async searchCommodities(query: string): Promise<CommoditySearchResponse> {
    return api.get('/api/commodities/search', { params: { q: query } });
  },

  async getAvailableCommodities(): Promise<CommoditySearchResponse> {
    return api.get('/api/commodities/available');
  },

  async getWatchlist(): Promise<WatchlistResponse> {
    return api.get('/api/commodities/watchlist');
  },

  async addToWatchlist(request: AddWatchedCommodityRequest): Promise<AddWatchedCommodityResponse> {
    return api.post('/api/commodities/watchlist', request);
  },

  async removeFromWatchlist(symbol: string): Promise<AddWatchedCommodityResponse> {
    return api.delete(`/api/commodities/watchlist/${encodeURIComponent(symbol)}`);
  },

  async updateWatchedCommodity(symbol: string, name: string): Promise<AddWatchedCommodityResponse> {
    return api.put(`/api/commodities/watchlist/${encodeURIComponent(symbol)}`, { name });
  },

  async getWatchlistByCategory(category: string): Promise<WatchlistResponse> {
    return api.get(`/api/commodities/watchlist/category/${category}`);
  },

  async getCommodityByTicker(ticker: string): Promise<{
    commodity: string;
    symbol: string;
    name: string;
    price: number;
    currency: string;
    change: number | null;
    change_percent: number | null;
    source: string;
    timestamp: string;
  }> {
    return api.get(`/api/commodities/by-ticker/${encodeURIComponent(ticker)}`);
  },
};

export const overviewApi = {
  async getOverview(): Promise<Overview> {
    return api.get('/api/overview');
  },
};

export const healthApi = {
  async getHealth(): Promise<HealthStatus> {
    return api.get('/api/health');
  },

  async getSimpleHealth(): Promise<{ status: string; timestamp: string }> {
    return api.get('/api/health/simple');
  },
};

export const indexApi = {
  async getIndices(): Promise<IndexListResponse> {
    return api.get('/api/indices');
  },

  async getIndex(indexType: string): Promise<MarketIndex> {
    return api.get(`/api/indices/${indexType}`);
  },

  async getRegions(): Promise<{
    regions: Array<{
      name: string;
      indices: Array<{ index: string; name: string }>;
    }>;
    supported_indices: string[];
  }> {
    return api.get('/api/indices/regions');
  },
};

export const sectorApi = {
  async getIndustrySectors(): Promise<SectorListResponse> {
    return api.get('/api/sectors/industry');
  },

  async getConceptSectors(): Promise<SectorListResponse> {
    return api.get('/api/sectors/concept');
  },

  async getIndustryDetail(sectorName: string): Promise<SectorDetailResponse> {
    return api.get(`/api/sectors/industry/${encodeURIComponent(sectorName)}`);
  },

  async getConceptDetail(sectorName: string): Promise<SectorDetailResponse> {
    return api.get(`/api/sectors/concept/${encodeURIComponent(sectorName)}`);
  },
};

export { api };
