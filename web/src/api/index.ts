import axios, { type AxiosInstance, type AxiosError } from 'axios';
import type { Fund, Commodity, Overview, HealthStatus } from '@/types';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// 自定义错误类
export class ApiError extends Error {
  constructor(
    message: string,
    public code?: string,
    public detail?: string,
    public timestamp?: string,
    public statusCode?: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// 网络错误检测
const isNetworkError = (error: unknown): boolean => {
  if (error instanceof AxiosError) {
    return !error.response;
  }
  return error instanceof Error && (error.message.includes('Network Error') || error.message.includes('ECONNREFUSED'));
};

// 错误消息映射表（更友好的提示信息）
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
const getFriendlyErrorMessage = (error: AxiosError): string => {
  const statusCode = error.response?.status;
  const responseData = error.response?.data as { error?: string; detail?: string } | undefined;

  // 优先使用后端返回的错误信息
  if (responseData?.error) {
    return responseData.detail ? `${responseData.error}: ${responseData.detail}` : responseData.error;
  }

  // 根据状态码返回友好消息
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

  // 根据错误消息返回友好消息
  for (const [key, message] of Object.entries(errorMessageMap)) {
    if (error.message.includes(key)) {
      return message;
    }
  }

  return error.message || '未知错误，请稍后重试';
};

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add timestamp to prevent caching
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

// Response interceptor - 改进错误处理
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  async (error: AxiosError) => {
    const responseData = error.response?.data as {
      success?: boolean;
      error?: string;
      detail?: string;
      timestamp?: string;
    } | undefined;

    // 检查是否是后端返回的错误响应格式
    if (responseData && responseData.success === false) {
      const friendlyMessage = getFriendlyErrorMessage(error);
      console.error(`[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}:`, {
        error: responseData.error,
        detail: responseData.detail,
        timestamp: responseData.timestamp,
      });

      throw new ApiError(
        friendlyMessage,
        responseData.error,
        responseData.detail,
        responseData.timestamp,
        error.response?.status
      );
    }

    // 处理网络错误
    if (isNetworkError(error)) {
      const friendlyMessage = getFriendlyErrorMessage(error);
      console.error(`[Network Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}:`, error.message);
      throw new ApiError(friendlyMessage, 'NETWORK_ERROR', error.message);
    }

    // 其他错误
    const friendlyMessage = getFriendlyErrorMessage(error);
    console.error(`[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}:`, error.message);
    throw new ApiError(
      friendlyMessage,
      'UNKNOWN_ERROR',
      error.message,
      undefined,
      error.response?.status
    );
  }
);

// API Methods
export const fundApi = {
  // Get all funds
  async getFunds(): Promise<{ funds: Fund[]; total: number; timestamp: string }> {
    return api.get('/api/funds');
  },

  // Get single fund
  async getFund(code: string): Promise<Fund> {
    return api.get(`/api/funds/${code}`);
  },

  // Get fund estimate
  async getFundEstimate(code: string): Promise<{
    code: string;
    name: string;
    netValue: number;
    estimateValue: number;
    estimateChange: number;
    estimateChangePercent: number;
    timestamp: string;
  }> {
    return api.get(`/api/funds/${code}/estimate`);
  },

  // Get fund history
  async getFundHistory(code: string, days: number = 30): Promise<{
    code: string;
    name: string;
    history: Array<{ date: string; value: number }>;
  }> {
    return api.get(`/api/funds/${code}/history`, { params: { days } });
  },
};

export const commodityApi = {
  // Get all commodities
  async getCommodities(): Promise<{ commodities: Commodity[]; timestamp: string }> {
    return api.get('/api/commodities');
  },

  // Get commodity by type
  async getCommodity(type: string): Promise<Commodity> {
    return api.get(`/api/commodities/${type}`);
  },

  // Get gold price (CNY)
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

  // Get international gold
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

  // Get WTI oil
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

// Export api instance for custom requests
export { api };
